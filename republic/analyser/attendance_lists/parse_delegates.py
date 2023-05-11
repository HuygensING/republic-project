from collections import defaultdict, Counter
import itertools
import re

import networkx as nx
import pandas as pd
import logging
import regex
from numpy import argmax
from fuzzy_search.search.phrase_searcher import FuzzyPhraseSearcher
from fuzzy_search.tokenization.string import score_levenshtein_similarity_ratio

from .searchers import nm_to_delen, herensearcher, junksweeper
from ...helper.utils import reverse_dict, levenst_vals, score_match
from ...model.republic_attendancelist_models import StringWithContext, Heer
from ...data.delegate_database import abbreviated_delegates, found_delegates, ekwz
from ...helper.similarity_match import FuzzyKeywordGrouper
from .identify import iterative_search

# repress the warnings from pandas
pd.set_option('mode.chained_assignment', None)

numpat = re.compile('[0-9]{2,}')

transposed_graph = reverse_dict(ekwz)
keywords = list(abbreviated_delegates.name)
kwrds = {key: nm_to_delen(key) for key in keywords}


def fndmatch(heer='',
             nwkw=list,
             rev_graph=nx.Graph,
             searcher=FuzzyPhraseSearcher,
             junksearcher=FuzzyPhraseSearcher,
             df=pd.DataFrame):
    result = match_previous(heer)
    if len(result) == 0:
        mf = FndMatch(rev_graph=transposed_graph,
                      searcher=FuzzyPhraseSearcher,
                      junksearcher=FuzzyPhraseSearcher,
                      df=df)
        mf.match_candidates(heer=heer)
        result = result.heer.serialize()
    return result


def get_delegates_from_spans(ob):
    result = {}
    for s in ob.spans:
        result['delegate'] = s.get_delegate()
        result['pattern'] = s.pattern
    return result


def matchwithlist(x, input):
    res = [i for i in input if score_levenshtein_similarity_ratio(x, i) > 0.6]
    if len(res) > 0:
        return True
    else:
        return False


class DelegatesFromFragments(object):
    def __init__(self,
                 searchobs=[],
                 year=0,
                 junksweeper=junksweeper,
                 found=found_delegates,
                 df=abbreviated_delegates):
        self.noresults = []
        self.searchobs = searchobs
        self.js = junksweeper
        self.year = year
        self.df = df
        self.found = found
        self.xgroups = {}
        self.noresultscounter = None
        self.r_cons = None
        self.origkeys = None
        self.consolidated_groups = None
        self.consolidated_counter = None
        self.suspected_items = None
        self.keyframe = None
        self.def_keys_with_subPatterns = None
        self.match_records = None
        self.suspects = None

    def obs_to_fragments(self):
        """this collects spans without a tag from the searchobjects (=attendance lists)
        and groups them  with fuzzy grouper"""
        for ob in self.searchobs:
            so = self.searchobs[ob].matched_text
            jitems = ';'.join(so.get_unmatched_text())
            items = [item.strip() for item in re.split(r'[;,\.]+', jitems) if
                     item.strip() != '' and len(item.strip()) > 2]
            for item in items:
                contextitem = StringWithContext(item)
                contextitem.set_reference(so)
                self.noresults.append(contextitem)
        self.noresultscounter = Counter(self.noresults)
        unmatched_grouped = FuzzyKeywordGrouper([str(k) for k in self.noresultscounter.keys()]).vars2graph()
        self.consolidated_groups = {}
        for group in unmatched_grouped:
            i = argmax([self.noresultscounter[i] for i in group])
            self.consolidated_groups[group[i]] = [g for g in group if g != group[i]]
        self.origkeys = list(self.consolidated_groups.keys())
        self.r_cons = reverse_dict(self.consolidated_groups)

    def groups_to_counter(self):
        self.consolidated_counter = defaultdict(int)
        for key in self.noresultscounter:
            nkey = self.r_cons.get(key) or key
            self.consolidated_counter[nkey] += self.noresultscounter[key]

    def counter_to_delegates(self):
        """we try to split concatenated names"""
        self.groups_to_counter()
        self.suspected_items = [item for item in self.consolidated_groups.keys() if itj(item, js=self.js)]
        singlekeys = [k for k in self.consolidated_groups if self.consolidated_counter.get(k) == 1]
        to_compare = list(itertools.product(list(self.consolidated_groups.keys()), singlekeys))
        scores2 = []
        for key, cand in to_compare:  # itertools.combinations(list(consolidated_groups.keys()), 2):
            sc = name_matcher(key, cand, threshold=0.7)
            key, cand = sorted([key, cand], key=lambda x: len(x))
            if sc:
                if key not in self.suspected_items and cand not in self.suspected_items:
                    scores2.append({'orig_key': cand,
                                    'sub_pattern1': key,
                                    'similarity': sc['similarity'],
                                    'pre_pattern': sc['otherpart'],
                                    'trailing_pattern': sc['lastpart']})
        self.keyframe = pd.DataFrame.from_records(scores2)
        multiple_recog = self.keyframe.orig_key.value_counts() > 1
        ambiv = list(multiple_recog.index)
        self.keyframe.loc[self.keyframe.orig_key.isin(ambiv)]
        ks = [key for key in self.consolidated_groups.keys() if key not in self.suspected_items]
        both_keys = self.keyframe.loc[self.keyframe.trailing_pattern.isin(ks)]
        self.def_keys_with_subPatterns = [{'key': x[0], x[1]: x[1], x[2]: x[2]} for x in
                                          both_keys[['orig_key', 'sub_pattern1', 'trailing_pattern']].to_records(
                                              index=False)]
        grkeyframe = self.keyframe.groupby('orig_key')
        for group in grkeyframe.groups:
            subfr = grkeyframe.get_group(group)
            vals = subfr.sub_pattern1.unique()
            subfr['tr'] = subfr.trailing_pattern.apply(lambda x: levntest(x, vals))
            subfr['pr'] = subfr.pre_pattern.apply(lambda x: levntest(x, vals))
            deffr = subfr.loc[(subfr.tr > 0.75) | (subfr.pr > 0.75)]
            if len(deffr) > 0:
                pre = deffr.loc[(deffr.tr == deffr.tr.max())]
                post = deffr.loc[deffr.pr == deffr.pr.max()]
                result = {'key': group, pre.sub_pattern1.iloc[0]: post.pre_pattern.iloc[0],
                          post.sub_pattern1.iloc[0]: pre.trailing_pattern.iloc[0]}
                self.def_keys_with_subPatterns.append(result)
            else:
                deffr = subfr.loc[subfr.similarity > 0.75]
                if len(deffr) > 0:
                    result = {'key': group,
                              subfr.sub_pattern1.iloc[0]: subfr.sub_pattern1.iloc[0],
                              subfr.pre_pattern.iloc[0]: subfr.pre_pattern.iloc[0],
                              subfr.trailing_pattern.iloc[0]: subfr.trailing_pattern.iloc[0]}
                    self.def_keys_with_subPatterns.append(result)

    def groups_to_references(self):
        self.consolidated_counter = defaultdict(int)
        for key in self.noresultscounter:
            nkey = self.r_cons.get(key) or key
            self.consolidated_counter[nkey] += self.noresultscounter[key]
        nwrecords = defaultdict(list)
        quarantine = []
        # nokeys = [str(n) for n in self.noresults]
        for record in self.def_keys_with_subPatterns:
            for i in record:
                if i == 'key':
                    quarantine.append(record[i])
                else:
                    aant = self.consolidated_counter.get(i) or 0
                    if aant > 1:
                        if good_key(i):
                            refs = [ob.references for ob in
                                    list(filter(lambda x: x == i, self.noresults)) if len(ob.references) > 0][0]
                            nwrecords[i].extend(refs)
        rejected_keys = []

        for g in self.consolidated_groups:
            if str(g) not in quarantine:
                if not itj(str(g), sweep=True):
                    ks = [g] + self.consolidated_groups[g]
                    r = list(filter(lambda i: i in ks, self.noresults))
                    ng = defaultdict(list)
                    for key in list(set([str(i) for i in r])):
                        refs = filter(lambda x: x == key, r)
                        chrefs = list(itertools.chain([x.references for x in refs]))
                        ng[key].extend(list(itertools.chain.from_iterable(chrefs)))
                    self.xgroups[g] = ng
                else:
                    rejected_keys.append(g)
        for item in nwrecords:
            if self.xgroups.get(item):
                self.xgroups[item][item].extend(nwrecords[item])
            else:
                rejected_keys.append(item)
        self.suspects = sieve_keys(self.xgroups, js=self.js)
        self.identify_delegates(self.xgroups, self.suspects)

    def identify_delegates(self, xgroups, suspects):
        fndmatch = FndMatch(year=self.year,
                            searcher=herensearcher,
                            junksearcher=self.js,
                            register={},
                            rev_graph={},
                            df=abbreviated_delegates)
        self.match_records = {}
        for keyw in xgroups:
            if keyw not in suspects:
                r = match_from_dict(keyw, founddb=self.found, fndmatch=fndmatch)
            self.match_records[keyw] = r

    def run(self):
        self.obs_to_fragments()
        self.counter_to_delegates()
        self.groups_to_references()
        reverse_references(self.xgroups, self.match_records)


def find_delegates(input=[],
                   matchfnd=None,
                   df=abbreviated_delegates,
                   previously_matched=found_delegates,
                   year: int = 0):
    matched_deputies = defaultdict(list)
    unmatched_deputies = []
    for herengroup in input:
        # we add the whole group to recognized if at least one name has a result
        recognized_group = []
        keyword_counter = Counter()
        in_matched = False
        for heer in herengroup:  # we try to fuzzymatch the whole group and give the string a score
            rslt = matchfnd.match_candidates(heer=heer)
            if rslt:
                match_kw = getattr(rslt, 'match_keyword')
                # print(match_kw)
                if match_kw != '':
                    in_matched = True
                    match_distance = getattr(rslt, 'levenshtein_distance')
                    recognized_group.append((heer, match_kw, match_distance))
                    keyword_counter.update([match_kw])
        if in_matched:
            kw = keyword_counter.most_common(10)[0][0]
            rec = previously_matched.loc[previously_matched.variants.apply(lambda x: matchwithlist(kw, x))]
            if len(rec) == 0:
                rec = iterative_search(name=kw, year=year, df=df)
            if len(rec) > 0:
                drec = rec.to_dict(orient="records")[0]
                m_id = drec['id']
                #             if m_id == 'matched':
                #                 print(rec, kw)
                name = drec['name']
                score = drec.get('score') or 0.0
                matched_deputies[m_id] = {
                    'id': m_id,
                    'm_kw': kw,
                    'score': score,
                    'name': name,
                    'variants': recognized_group
                }
            else:
                unmatched_deputies.append(recognized_group)
        else:
            unmatched_deputies.append(herengroup)
    return ({"matched": matched_deputies,
             "unmatched": unmatched_deputies})


class FndMatch(object):
    def __init__(self,
                 year: int,
                 searcher: FuzzyPhraseSearcher,
                 junksearcher: FuzzyPhraseSearcher,
                 # patterns=list,
                 register: dict = None,
                 rev_graph: dict = None,
                 df: pd.DataFrame = None):
        self.year = year
        self.searcher = searcher
        self.junksearcher = junksearcher
        self.register = register
        # self.patterns = patterns
        self.rev_graph = rev_graph
        self.df = df

    def match_candidates(self, heer: str):
        found_heer = Heer()
        try:
            candidates = self.searcher.find_matches(text=heer, include_variants=True)
            if candidates:
                # sort the best candidate
                candidate = max(candidates, key=lambda x: x.levenshtein_similarity)
                levenshtein_similarity = candidate.levenshtein_similarity
                searchterm = candidate.phrase.exact_string
                n_candidates = self.rev_graph.get(searchterm) or []
                found_heer.levenshtein_distance = levenshtein_similarity
                found_heer.searchterm = searchterm
                found_heer.match_keyword = searchterm
                found_heer.score = 1.0
                if len(n_candidates) == 0:
                    found_heer.fill('')
                elif len(n_candidates) == 1:
                    found_heer.proposed_delegate = n_candidates[0]
                    candidate = iterative_search(name=found_heer.proposed_delegate, year=self.year, df=self.df)
                    found_heer.fill(candidate)
                else:
                    candidate = self.composite_name(candidates=n_candidates, heer='')
                    found_heer.fill(candidate)
                found_heer.probably_junk = self.is_heer_junk(heer)
        except ValueError:
            logging.info(msg=f'{heer} ValueError')
            pass

        return found_heer

    def composite_name(self, candidates: list, heer: str, searchterm: str):
        dayinterval = pd.Interval(self.year, self.year, closed="both")
        candidate = dedup_candidates(proposed_candidates=candidates,
                                     register=self.register,
                                     searcher=herensearcher,
                                     searchterm=searchterm,
                                     dayinterval=dayinterval,
                                     df=self.df)
        if len(candidate) == 0:
            src = iterative_search(name=heer, year=self.year, df=self.df)
            #             if len(src) > 1:
            #                 src = src.loc[src.p_interval.apply(lambda x: x.overlaps(dayinterval))]
            #                 if len(src) == 0:
            #                     src = src.loc[src]
            #            src['levenshtein_distance'] = src.name.apply(lambda x: score_levenshtein_distance_ratio(term1=self.levenshtein_distance, term2=x))
            src.sort_values(['score', ])
            # self.heer.levenshtein_distance = self.levenshtein_distance
            candidate = src.iloc[src.index == src.first_valid_index()]  # brrrr

        return candidate

    def is_heer_junk(self, heer):
        probably_junk = False
        try:
            probably_junk_result = self.junksearcher.find_matches(text=heer, include_variants=True)
            if len(probably_junk_result) > 0:
                probably_junk = True
            return probably_junk
        except ValueError:
            logging.info(f"fuzzysearcher value error raised #{heer}#, {self.junksearcher.phrase_model.json}")
            return True


class MatchAndSpan(object):
    def __init__(self,
                 ob,
                 junksweeper=None,
                 previously_matched=None,
                 match_search=None):
        self.ob = ob
        self.txt_fragments = self.ob.get_unmatched_text()
        self.maintext = self.ob.item
        self.matchres = {}
        self.search_results = {}
        self.nwsplit = []
        self.previously_matched = previously_matched
        self.match_search = match_search
        self.junksweeper = junksweeper
        self.txt_to_fragments()
        self.match2span()

    def txt_to_fragments(self):
        ut = ''.join(self.txt_fragments)
        st = re.sub(r"([A-Z]{1,20})", r" \1", ut)
        splittekst = [x for x in re.split('\s|,|\.', st) if x != '']
        self.nwsplit = []
        van = ''
        for item in splittekst:
            if van != '':
                item = ' '.join((van, item))
            if len(item) == 3 and score_levenshtein_similarity_ratio(item.lower(), 'van') > 0.5:
                van = item
                continue
            else:
                van = ''
            self.nwsplit.append(item)
        # splittekst = re.split(pattern="\s", string=unmarked_text)
        for s in self.nwsplit:  # splittekst
            try:
                if len(s) > 2:  # and len(self.junksweeper.find_matches(s, include_variants=True)) == 0:
                    sr = self.match_unmarked(s)
                    if sr:
                        self.search_results.update(sr)
            except ValueError:
                pass  # this sometimes happens if fuzzysearcher gets confused by our matches

    def match_unmarked(self, unmarked_text):
        s = unmarked_text

        mtch = self.previously_matched.variants.apply(lambda x: levenst_vals(x, s))
        # nmtch = self.previously_matched.name.apply(lambda x: score_levenshtein_similarity_ratio(x, s) > 0.6)
        tussenr = self.previously_matched.loc[mtch]
        try:
            if len(tussenr) > 0:
                matchname = tussenr
                nm = matchname.name
                idnr = tussenr.ref_id
                score = max(tussenr.variants, key=lambda x: score_levenshtein_similarity_ratio(x, s))
                self.search_results[s] = {'match_term': nm, 'match_string': s, 'score': score}
            else:
                # matchname = iterative_search(
                search_result = self.match_search.find_matches(s, include_variants=True)
                if len(search_result) > 0:
                    self.search_results[s] = max(search_result,
                                                 key=lambda x: x.levenshtein_similarity)

        except (TypeError, AttributeError):
            print(tussenr)
            raise

    def match2span(self):
        for ri in self.search_results:
            begin = self.maintext.find(ri)
            end = begin + len(ri)
            span = (begin, end)
            result = self.search_results[ri]
            comp = [s for s in self.ob.spans if not set(range(s.begin, s.end)).isdisjoint(span)]
            if len(comp) > 0:
                for cs in comp:
                    if not set(range(cs.begin, cs.end)).issubset(span):
                        try:
                            self.ob.spans.remove(cs)
                        except ValueError:
                            pass
                        self.ob.set_span(span, clas='delegate', pattern=self.maintext[begin:end])
            else:
                self.ob.set_span(span, clas='delegate')


def dedup_candidates(proposed_candidates: list,
                     searcher: FuzzyPhraseSearcher,
                     register: dict,
                     dayinterval: pd.Interval,
                     df: pd.DataFrame,
                     searchterm: str):
    scores = {}
    for d in proposed_candidates:
        prts = nm_to_delen(d)
        for p in prts:
            if p != searchterm:
                score = searcher.find_matches(text=p, include_variants=True, use_word_boundaries=False)
                if len(score) > 1:
                    n = argmax(score_match(score))
                    score = score[n]
                if score:
                    try:
                        scores[d] = (score.levenshtein_similarity, p)
                    except:
                        print(score)
    if not scores:
        candidate = proposed_candidates
    else:
        candidate = [max(scores)]
        register[p] = scores[candidate[0]][1]
    result = dedup_candidates2(proposed_candidates=candidate, dayinterval=dayinterval, df=df)
    if len(result) == 0:
        candidate = pd.DataFrame()  # searchterm
    return result


def dedup_candidates2(proposed_candidates: list, dayinterval: pd.Interval, df: pd.DataFrame):
    if type(proposed_candidates) == str:
        proposed_candidates = [proposed_candidates]
    nlst = proposed_candidates
    res = df.loc[df.name.isin(proposed_candidates)]
    if len(res) > 1:
        res = res[res.h_life.apply(lambda x: x.overlaps(dayinterval))]
    if len(res) > 1:
        res = res[res.p_interval.apply(lambda x: x.overlaps(dayinterval))]
    if len(res) > 1:
        res = res.loc[res.sg is True]
    return res


def delegates2spans(searchob, framed_gtlm):
    spans = searchob.matched_text.spans
    for span in spans:
        txt = searchob.matched_text.item[span.begin:span.end]
        msk = framed_gtlm.variants.apply(lambda x: levenst_vals(x, txt))
        mres = framed_gtlm.loc[msk is True]
        if len(mres) > 0:
            span.set_pattern(txt)
            span.set_delegate(delegate_id=mres.ref_id.iat[0], delegate_name=mres.name.iat[0])
        else:
            logging.info(f"not found {searchob}, {span}, {txt}")


def match_previous(heer, res: pd.DataFrame, existing_herensearcher=herensearcher):
    result = pd.DataFrame()
    r = existing_herensearcher.find_candidates(text=heer)
    if len(r) > 0:
        result = res.loc[res.name == r[0]['match_keyword']]
    return result


def name_matcher(naam1, naam2, threshold):
    result = False
    n1, n2 = sorted([naam1, naam2], key=lambda x: len(x))
    pat = regex.compile('(?P<otherpart>.*)(?P<namepart>' + regex.escape(n1) + '){e<=2}' + '(?P<lastpart>.*)',
                        flags=regex.BESTMATCH)
    r = pat.search(n2)
    if r:
        np = r.groupdict()['namepart']
        s = score_levenshtein_similarity_ratio(np, n1)
        if s > threshold:
            result = r.groupdict()
            result['similarity'] = s
    return result


vanpat = re.compile('vande[rn]?|([d|t]+e?[rn]?)\s+|van', re.I)


def is_namepart(phrase, found):
    result = {'phrase': phrase, 'contained': False, 'exactname': False}
    match = found.variants.apply(lambda x: levenst_vals(x, phrase))
    matchname = list(found.loc[match].name)[0]
    refid = list(found.loc[match].ref_id)[0]
    result['matchname'] = matchname
    result['id'] = refid
    # searchpat = [x.strip() for x in vanpat.split(phrase) if x and x.strip() !='']
    searchpat = [x.strip() for x in prefixpat.split(phrase) if x and x.strip() != '']
    for p in searchpat:
        if p in matchname:
            result['exactname'] = True
            if len(phrase) < len(matchname):
                result['contained'] = True
    return result


def levntest(x, lijst):
    result = 0
    for z in lijst:
        r = score_levenshtein_similarity_ratio(x, z)
        if r > result:
            result = r
    return result


def rate_match(key, match):
    return match.levenshtein_similarity * len(match.string) / len(key)


prefixpat = re.compile(
    r"à\b|\bà\b|\bd\'\b|\bde\b|\bden\b|\bder\b|\bdes\b|\bdi\b|\ben\b|\bhet\b|\bin 't\b|\bla\b|\bla\b|\ble\b|of|van|\bten\b|\bthoe\b|\btot\b|\b't\b|\bHeeren\b|\bvan\b|\bmet\b|\bHolland",
    flags=re.I)


# r'\b|\b'.join(stopwords), flags =  re.I)


def match_ppat(x):
    result = False
    if prefixpat.search(x):
        result = True
    return result


def looks_like_a_name(pat):
    if pat == '':
        return False
    r = False
    pats = pat.split(' ')
    pats = [pat for pat in pats if not prefixpat.search(pat)]
    # starts with a prefix
    # if prefix:
    #     pats = pats[1:]
    for p in pats:
        if p.capitalize() == p:
            r = True
        else:
            r = False
            break
    return r


def good_key(pat):
    r = True
    # print(pat, r)
    if itj(pat):
        # print('junk',pat,r)
        r = False
    else:
        if not looks_like_a_name(pat):
            # print('name',pat,r)
            r = False
    return r


def is_this_junk(pat, js=junksweeper, sweep=False):
    suspect = False
    if numpat.search(pat):
        suspect = True
    elif pat == pat.lower():  # no capitals means no name
        suspect = True
    elif pat == pat.upper():
        suspect = True
    if sweep is True:
        if js.find_matches(pat):
            suspect = True
    return suspect


itj = is_this_junk


def sieve_keys(xgroups, js):
    js = js  # run_attendancelist.junksweeper
    suspects = []
    pat_nonstring = re.compile("\w+[0-9\(\)]+\w+")
    for k in xgroups:
        check = False
        key = re.sub(pat_nonstring, '', k)
        # if k!=key:
        #     print(k, "***", key)
        jmatches = js.find_matches(key, include_variants=True, use_word_boundaries=False)
        if len(jmatches) > 0:
            bestjmatch = max(jmatches, key=lambda m: rate_match(key, m))
            if len(bestjmatch.string) / len(key) > 0.5:  # more than half of the string is in vanpat
                vancheck = vanpat.search(bestjmatch.string)
                if vancheck:
                    if k != key:
                        key = k
                    suspects.append(key)
            # print(key, bestjmatch.string, check)
        return suspects


# def make_span(keyword):
#     r = match_from_dict(keyword, founddb=found, fndmatch=fndmatch)
#     for p in xgroups[keyword]:
#         obs = p.get_references()
#         for ob in obs:
#             s = re.search(re.escape(str(p)), ob.item)
#             if s:
#                 ob.set_span(s.span(),
#                             clas='delegate',
#                             pattern=p,
#                             score=levenst_vals(keyword, p),
#                             delegate_name=r.get('proposed_delegate'),
#                             delegate_id=r.get('p_id'))
#             else:
#                 print(keyword, p)

def reverse_references(xgroups, match_records):
    """ reverses matches in xgroups to searchobjects for faster matching"""
    reference_table = defaultdict(list)
    for mkey in xgroups.keys():
        grp = xgroups[mkey]
        for key in grp:
            for r in grp[key]:
                rec = {'dlg': match_records[mkey], 'srchpat': key}
                reference_table[r].append(rec)
    for ob in reference_table.keys():
        for m in reference_table[ob]:
            p = m['srchpat']
            r = m['dlg']
            s = re.search(re.escape(str(p)), ob.item)
            if s:
                ob.set_span(s.span(),
                            clas='delegate',
                            pattern=p,
                            score=levenst_vals(r.get('pattern'), p),
                            delegate_name=r.get('proposed_delegate'),
                            delegate_id=r.get('p_id'))


def match_from_dict(pattern, founddb=found_delegates, df=abbreviated_delegates,
                    fndmatch=fndmatch, year=0):
    """pattern should be string in context"""

    #     longpats = fs.find_matches(pattern, include_variants=True)
    #     if len(longpats)>0:
    #         result = max(longpats, key=lambda x: x.levenshtein_similarity)
    #     else:
    res = {}
    nm = ''
    idnr = 0
    match = founddb.variants.apply(lambda x: levenst_vals(x, pattern))
    result = founddb.loc[match]
    res['pattern'] = pattern
    if len(result) > 0:
        nm = result.name.iat[0]
        idnr = result.id.iat[0]
    else:
        result = fndmatch.match_candidates(heer=pattern).serialize()
        if result['score'] > 0.7:
            lookup = iterative_search(name=result['match_keyword'], year=year, df=df)
            if len(lookup) > 0:
                nm = lookup.name.iat[0]
                idnr = lookup.id.iat[0]
    res['proposed_delegate'] = nm
    res['p_id'] = idnr
    return res
