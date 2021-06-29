from collections import defaultdict, Counter
import networkx as nx
from fuzzy_search.fuzzy_phrase_searcher import FuzzyPhraseSearcher
from fuzzy_search.fuzzy_phrase_model import PhraseModel

from .searchers import nm_to_delen, herensearcher
from ...model.republic_phrase_model import month_names_early, month_names_late
from ...helper.utils import reverse_dict, levenst_vals
from ...model.republic_attendancelist_models import *
from ...data.delegate_database import get_raa_db,ekwz
from .identify import *



abbreviated_delegates = get_raa_db()


def make_junksweeper(ekwz):
    provincies = ['Holland', 'Zeeland', 'West-Vriesland', 'Gelderland', 'Overijssel', 'Utrecht', 'Friesland']
    months = month_names_early + month_names_late
    indexkeywords = months + provincies
    junksweeper = FuzzyPhraseSearcher(fuzzysearch_config)
    variants = [{'phrase': k, 'variants': v} for k, v in ekwz.items()]
    phrase_model = PhraseModel(model=variants, )
    phrase_model.add_phrases(indexkeywords)
    junksweeper.index_phrase_model(phrase_model=phrase_model)
    return junksweeper


junksweeper = make_junksweeper(ekwz)
transposed_graph = reverse_dict(ekwz)
keywords = list(abbreviated_delegates.name)
kwrds = {key: nm_to_delen(key) for key in keywords}


def fndmatch(heer='',
             nwkw=list,
             rev_graph=nx.Graph,
             searcher=FuzzyKeywordSearcher,
             junksearcher=FuzzyKeywordSearcher,
             df=pd.DataFrame):
    result = match_previous(heer)
    if len(result) == 0:
        mf = FndMatch(rev_graph=transposed_graph,
                      searcher=FuzzyKeywordSearcher,
                      junksearcher=FuzzyKeywordSearcher,
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




def find_delegates(input=[],
                   matchfnd=None,
                   df=None,
                   previously_matched=None,
                   year=None):
    """
    - input is grouped delegates
    - output is matched delegates and unmatched
    """
    #matched_heren = defaultdict(list)
    matched_deputies = defaultdict(list)
    unmatched_deputies = []
    for herengroup in input:
        # we add the whole group to recognized if one name has a result
        recognized_group = []
        keyword_counter = Counter()
        in_matched = False
        for heer in herengroup: # we try to fuzzymatch the whole group and give the string a score
            rslt = matchfnd.match_candidates(heer=heer)
            if rslt:
                in_matched = True
                match_kw = getattr(rslt,'match_keyword')
                match_distance = getattr(rslt,'levenshtein_distance')
                recognized_group.append((heer, match_kw, match_distance))
                keyword_counter.update([match_kw])
            else:
                recognized_group.append((heer, '', 0.0))
        if in_matched == True: # if there is at least one match, proceed
            kw = keyword_counter.most_common()[0][0]
            rec = previously_matched.loc[previously_matched.name == kw]
            #ncol = 'proposed_delegate'
            ncol = 'name'
            if len(rec) == 0:
                rec = iterative_search(name=kw, year=year, df=df)
                ncol = 'name'
            drec = rec.to_dict(orient="records")[0]
            m_id = drec['id']
#             if m_id == 'matched':
#                 print(rec, kw)
            name = drec[ncol]
            score = drec.get('score') or 0.0
            matched_deputies[m_id] = {'id': m_id,
                                      'm_kw':kw,
                                      'score':score,
                                      'name':name,
                                      'variants':recognized_group}
        else:
            unmatched_deputies.append(herengroup) # non-matched deputy-groups are also returned
    return({"matched":matched_deputies,
            "unmatched":unmatched_deputies})


class FndMatch(object):
    def __init__(self,
                 year=0,
                 searcher=FuzzyKeywordSearcher,
                 junksearcher=FuzzyKeywordSearcher,
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
        candidates = self.searcher.find_candidates(text=heer)
        if candidates:
            # sort the best candidate
            candidate = max(candidates, key=lambda x: x['levenshtein_distance'])
            levenshtein_distance = candidate['levenshtein_distance']
            searchterm = candidate['match_keyword']
            n_candidates = self.rev_graph.get(searchterm) or []
            found_heer.levenshtein_distance = levenshtein_distance
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
        return found_heer

    def composite_name(self, candidates=[], heer='', searchterm=str):
        dayinterval = pd.Interval(self.year, self.year, closed="both")
        candidate = dedup_candidates(proposed_candidates=candidates,
                                     register=self.register,
                                     searcher=cdksearcher,
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
            return True



class MatchAndSpan(object):
    def __init__(self,
                 ob,
                 junksweeper=None,
                 previously_matched=None,
                 match_search=None):
        self.ob = ob
        txt = self.ob.get_unmatched_text()
        self.maintext = self.ob.item
        self.matchres = {}
        self.search_results = {}
        self.previously_matched = previously_matched
        self.match_search = match_search
        unmarked_text = ''.join(ob.get_unmatched_text())
        splittekst = re.split(pattern="\s", string=unmarked_text)
        for s in splittekst:
            try:
                if len(s) > 2 and len(junksweeper.find_matches(s, include_variants=True)) == 0:
                    sr = self.match_unmarked(s)
                    if sr:
                        self.search_results.update(sr)
            except ValueError:
                pass # this sometimes happens if fuzzysearcher gets confused by our matches
        self.match2span()

    def match_unmarked(self, unmarked_text):
        s = unmarked_text
        mtch = self.previously_matched.name.apply(lambda x: score_levenshtein_distance_ratio(x, s) > 0.6)
        tussenr = self.previously_matched.loc[mtch]
        try:
            if len(tussenr) > 0:
                tussenr['score'] = tussenr.name.apply(lambda x: score_levenshtein_distance_ratio(x, s))
                matchname = tussenr.loc[tussenr.score == tussenr.score.max()]
                nm = matchname.name.iat[0]
                idnr = matchname.id.iat[0]
                score = tussenr.score.max()
                self.search_results[s] = {'match_term': nm, 'match_string': s, 'score': score}
            else:
                # matchname = iterative_search(
                search_result = self.match_search.find_candidates(s, include_variants=True)
                if len(search_result) > 0:
                    self.search_results[s] = max(search_result,
                                                 key=lambda x: x['levenshtein_distance'])

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
                     searcher=FuzzyKeywordSearcher,
                     register=dict,
                     dayinterval=pd.Interval,
                     df=pd.DataFrame,
                     searchterm=''):
    scores = {}
    for d in proposed_candidates:
        prts = nm_to_delen(d)
        for p in prts:
            if p != searchterm:
                score = cdksearcher.find_candidates(text=p)
                if len(score) > 1:
                    score=max(score, key=lambda x: x.get('levenshtein_distance'))
                if score:
                    try:
                        scores[d] = (score[0].get('levenshtein_distance'), p)
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


# In[29]:


# and a second try
cdksearcher = FuzzyKeywordSearcher(config=fuzzysearch_config)
#cdksearcher.index_keywords(list(cdk.keys()))

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
        msk = framed_gtlm.vs.apply(lambda x: levenst_vals(x, txt))
        mres = framed_gtlm.loc[msk==msk.max()]
        if len(mres)>0:
    #     if len(mres)>0:
    #         setattr(span, 'delegate_id', mres.uuid.iat[0])
    #         setattr(span, 'delegate_name', mres.name.iat[0])
        #print(kand, all_matched[kand])
            span.set_pattern(txt)
        if len(mres)>0:
            span.set_delegate(delegate_id=mres.ref_id.iat[0], delegate_name=mres.name.iat[0])


def match_previous(heer, res=pd.DataFrame, existing_herensearcher=herensearcher):
    result = pd.DataFrame()
    r = existing_herensearcher.find_candidates(text=heer)
    if len(r) > 0:
        result = res.loc[res.name == r[0]['match_keyword']]
    return result