from collections import defaultdict, Counter
import networkx as nx
import logging
#from scipy.special import softmax
from numpy import argmax
from fuzzy_search.fuzzy_phrase_searcher import FuzzyPhraseSearcher
from fuzzy_search.fuzzy_phrase_model import PhraseModel
from fuzzy_search.fuzzy_string import score_levenshtein_distance, score_levenshtein_similarity_ratio
from .searchers import nm_to_delen, herensearcher
from ...helper.utils import *
from ...model.republic_attendancelist_models import *
from ...data.delegate_database import abbreviated_delegates, found_delegates, ekwz
from .identify import *


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
                matched_deputies[m_id] = {'id': m_id,
                                          'm_kw': kw,
                                          'score': score,
                                          'name': name,
                                          'variants': recognized_group}
            else:
                unmatched_deputies.append(recognized_group)
        else:
            unmatched_deputies.append(herengroup)
    return ({"matched": matched_deputies,
             "unmatched": unmatched_deputies})

class FndMatch(object):
    def __init__(self,
                 year=0,
                 searcher=FuzzyPhraseSearcher,
                 junksearcher=FuzzyPhraseSearcher,
                 # patterns=list,
                 register=dict,
                 rev_graph=dict,
                 df=pd.DataFrame):
        self.year = year
        self.searcher = searcher
        self.junksearcher = junksearcher
        self.register = register
        # self.patterns = patterns
        self.rev_graph = rev_graph
        self.df = df

    def match_candidates(self, heer=str):
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

    def composite_name(self, candidates=[], heer='', searchterm=str):
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
                if len(s) > 2:# and len(self.junksweeper.find_matches(s, include_variants=True)) == 0:
                    sr = self.match_unmarked(s)
                    if sr:
                        self.search_results.update(sr)
            except ValueError:
                pass  # this sometimes happens if fuzzysearcher gets confused by our matches

    def match_unmarked(self, unmarked_text):
        s = unmarked_text

        mtch = self.previously_matched.variants.apply(lambda x: levenst_vals(x, s))
        #nmtch = self.previously_matched.name.apply(lambda x: score_levenshtein_similarity_ratio(x, s) > 0.6)
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
            if comp != []:
                for cs in comp:
                    if not set(range(cs.begin, cs.end)).issubset(span):
                        try:
                            self.ob.spans.remove(cs)
                        except ValueError:
                            pass
                        self.ob.set_span(span, clas='delegate', pattern=self.maintext[begin:end])
            else:
                self.ob.set_span(span, clas='delegate')


def dedup_candidates(proposed_candidates=[],
                     searcher=FuzzyPhraseSearcher,
                     register=dict,
                     dayinterval=pd.Interval,
                     df=pd.DataFrame,
                     searchterm=''):
    scores = {}
    for d in proposed_candidates:
        prts = nm_to_delen(d)
        for p in prts:
            if p != searchterm:
                score = searcher.find_matches(text=p, include_variants=True,use_word_boundaries=False)
                if len(score) > 1:
                    n = argmax(score_match(score))
                    score = score[n]
                if score:
                    try:
                        scores[d] = (score.levenshtein_similarity, p)
                    except:
                        print (score)
    if not scores:
        candidate = proposed_candidates
    else:
        candidate = [max(scores)]
        register[p] = scores[candidate[0]][1]
    result = dedup_candidates2(proposed_candidates=candidate, dayinterval=dayinterval, df=df)
    if len( result) == 0:
        candidate = pd.DataFrame() # searchterm
    return result


def dedup_candidates2(proposed_candidates=[], dayinterval=pd.Interval, df=pd.DataFrame):
    if type(proposed_candidates) == str:
        proposed_candidates = [proposed_candidates]
    nlst = proposed_candidates
    res = df.loc[df.name.isin(proposed_candidates)]
    if len(res)>1:
        res = res[res.h_life.apply(lambda x: x.overlaps(dayinterval))]
    if len(res)>1:
        res = res[res.p_interval.apply(lambda x: x.overlaps(dayinterval))]
    if len(res)>1:
        res = res.loc[res.sg == True]
    return res


def delegates2spans(searchob, framed_gtlm):
    spans = searchob.matched_text.spans
    for span in spans:
        txt = searchob.matched_text.item[span.begin:span.end]
        msk = framed_gtlm.variants.apply(lambda x: levenst_vals(x, txt))
        mres = framed_gtlm.loc[msk==True]
        if len(mres)>0:
            span.set_pattern(txt)
            span.set_delegate(delegate_id=mres.ref_id.iat[0], delegate_name=mres.name.iat[0])
        else:
            logging.info(f"not found {searchob}, {span}, {txt}")


def match_previous(heer, res=pd.DataFrame, existing_herensearcher=herensearcher):
    result = pd.DataFrame()
    r = existing_herensearcher.find_candidates(text=heer)
    if len(r) > 0:
        result = res.loc[res.name == r[0]['match_keyword']]
    return result