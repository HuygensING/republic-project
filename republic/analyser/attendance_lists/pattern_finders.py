import re
# import networkx as nx
from collections import Counter, defaultdict

from ...config.republic_config import base_config
from ...helper.utils import *
from ...fuzzy.fuzzy_keyword_searcher import FuzzyKeywordSearcher
from ...data.delegate_database import abbreviated_delegates, found_delegates
from .parse_delegates import FndMatch, match_previous

fuzzysearch_config = {
    "char_match_threshold": 0.8,
    "ngram_threshold": 0.6,
    "levenshtein_threshold": 0.5,
    "ignorecase": False,
    "ngram_size": 2,
    "skip_size": 2,
}
from .identify import iterative_search  # , identify


# #### praesentibus


def make_alternatives(searcher=None, term: str = '', alternatives: list = [], matchlist: dict = {}):
    """

    :param searcher: FuzzyKeywordSearcher
    :type matchlist: dictionary
    :type alternatives: list
    """
    alts = {}
    alternatives = alternatives
    for T in matchlist.keys():
        res = searcher.find_candidates_new(keyword=term, text=matchlist[T].text)
        if res:
            alternatives.append(res[0]['match_string'])
    alts[term] = list(set(alternatives))
    for variant in alts[term]:
        searcher.index_spelling_variant(term, variant)
    return alts


def president_searcher(presentielijsten, from_scratch=True):
    """search and mark president in delegate attendance list
       this returns heren, but marks the presidents
       in the presentielijsten texts"""
    fuzzysearch_config = {'char_match_threshold': 0.5,
                          'ngram_threshold': 0.5,
                          'levenshtein_threshold': 0.4,
                          'ignorecase': False,
                          'ngram_size': 2,
                          'skip_size': 2}
    president_searcher = FuzzyKeywordSearcher(config=fuzzysearch_config)
    president_searcher.use_word_boundaries = False
    president_searcher.index_keywords('PRAESIDE Den Heere')
    for variant in ['PRASIDE Den Heere',
                    'PRESIDE Den Heere',
                    'P R A E S I D E Den Heere',
                    'PRAESIDE Den Heere',
                    'P R A S I D E Den Heere',
                    'P R E S I D E Den Heere',
                    'P R AE S I D E Den Heere',
                    'DR AS 1D E Den Heere',
                    'PR ASL DE Den Heere',
                    'PR A31 DE; Den Heere',
                    'BR JE 3.1. DE, Den Heere']:
        president_searcher.index_spelling_variant('PRAESIDE', variant)
    presentibus_searcher = FuzzyKeywordSearcher(config=fuzzysearch_config)
    presentibus_searcher.index_keywords('PRAESENTIBUS')
    presentibus_searcher.use_word_boundaries = False
    for variant in ['PRASENTIBUS',
                    'PRESENTIBUS',
                    'P R A E S E N T I B U S',
                    'P RAE SE N TI B U S',
                    'PRA&SENTIBUS']:
        presentibus_searcher.index_spelling_variant('PRAESENTIBUS', variant)
    make_alternatives(term='PRAESENTIBUS', searcher=presentibus_searcher, matchlist=presentielijsten)
    heren = []
    pat = "%s(.*)%s"  # pat = "%s.*(.*)%s"  # de presidenten
    pats = []
    for T in list(presentielijsten.keys()):
        ob = presentielijsten[T].matched_text
        txt = ob.item
        president = president_searcher.find_candidates(keyword='PRASIDE Den Heere', include_variants=True, text=txt)
        presentibus = presentibus_searcher.find_candidates(keyword='PRAESENTIBUS', include_variants=True, text=txt)
        begin = 0  # in case we find no president marker
        end = 0
        try:
            spns = {}
            ofset = president[0]['match_offset'] or 0
            end = presentibus[0]['match_offset'] or len(txt)
            prez = president[0]['match_string'] or ''
            if ofset != 0:
                preamble_span = (0, ofset - 1)
                preamble = txt[preamble_span[0]:preamble_span[1]]
                spns['preamble'] = (preamble, preamble_span)
            pre_span = (ofset, ofset + len(prez))
            spns['pre'] = (prez, pre_span)
            prae = presentibus[0]['match_string'] or ''
            presentibus_span = (end, end + len(prae))
            spns['presentibus'] = (prae, presentibus_span)
            searchpat = pat % (re.escape(prez), re.escape(prae))
            r = re.search(searchpat, txt)
            if r and r.group(1):
                heer = r.group(1).strip()
                heer = re.sub('[^\s\w]*', '', heer)
                # print(r.group(1))
                heren.append(heer)
                s1 = txt.find(heer)
                s2 = s1 + len(heer)
                span = (s1, s2)  # get_span_from_regex(r)
                spns['president'] = (heer, span)
                for kw in spns.keys():
                    s = spns[kw][0]
                    spn = spns[kw][1]
                    ob.set_span(span=spn, pattern=s, clas=kw)
                    setattr(ob, 'found', {'president': heer})
                    # if prae != '':
                    #     prespan = get_span_from_regex(prae)
                    #     mt.set_span(prespan, "presentibus")
            else:
                # text_zonder_president.append(T)
                pats.append((searchpat, txt))

        except IndexError:
            pass
    return heren


def province_searcher(presentielijsten, config=base_config):
    kw_searcher = FuzzyKeywordSearcher(config)
    province_order = ["gelderlandt",
                      "hollandt ende west-frieslandt",
                      "utrecht",
                      "frieslandt",
                      "overijssel",
                      "groningen",
                      "zeelandt"]

    searchstring = "met {} extraordinaris gedeputeerde uyt de provincie van {}"
    provinces = []
    for provincie in province_order:
        for telwoord in ['een', 'twee', 'drie']:
            provinces.append(searchstring.format(telwoord, provincie))
    kw_searcher.index_keywords(provinces)
    kw_searcher.use_word_boundaries = False

    for T in presentielijsten.keys():
        itm = presentielijsten[T]
        txt = itm.text
        mt = itm.matched_text
        # for kw in provinces:
        provs = kw_searcher.find_candidates(text=txt)
        if len(provs) > 0:
            profset = provs[0].get('match_offset') or 0
        for res in provs:
            ofset = res['match_offset']
            span = (ofset, ofset + len(res['match_string']))
            mt.set_span(span, "province")


def make_groslijst(presentielijsten):
    """get rough list of unmarked text from presentielijsten"""
    groslijst = []
    interpunctie = re.compile("[;:,\. ]+")
    unmarked_texts = {}
    for T in presentielijsten:
        marked_item = presentielijsten[T].matched_text
        unmatched_texts = marked_item.get_unmatched_text()
        unmatched_texts = [u.strip() for u in unmatched_texts if len(u.strip()) > 2]
        for unmatched_text in unmatched_texts:
            if len(unmatched_text) > 2:
                interm = interpunctie.split(unmatched_text)
                interm = [i.strip() for i in interm if len(i.strip()) > 2]
                groslijst.extend(interm)
    return groslijst


def find_delegates(input=[],
                   matchfnd=None,
                   df=abbreviated_delegates,
                   previously_matched=found_delegates,
                   year: int = 0):
    # matched_heren = defaultdict(list)
    matched_deputies = defaultdict(list)
    unmatched_deputies = []
    for herengroup in input:
        # we add the whole group to recognized if one name has a result
        recognized_group = []
        keyword_counter = Counter()
        in_matched = False
        for heer in herengroup:  # we try to fuzzymatch the whole group and give the string a score
            rslt = matchfnd.match_candidates(heer=heer)
            if rslt:
                in_matched = True
                match_kw = getattr(rslt, 'match_keyword')
                match_distance = getattr(rslt, 'levenshtein_distance')
                recognized_group.append((heer, match_kw, match_distance))
                keyword_counter.update([match_kw])
            else:
                recognized_group.append((heer, '', 0.0))
        if in_matched == True:  # if there is at least one match, proceed
            kw = keyword_counter.most_common()[0][0]
            rec = previously_matched.loc[previously_matched.name == kw]
            # ncol = 'proposed_delegate'
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
                                      'm_kw': kw,
                                      'score': score,
                                      'name': name,
                                      'variants': recognized_group}
        else:
            unmatched_deputies.append(herengroup)  # non-matched deputy-groups are also returned
    return ({"matched": matched_deputies,
             "unmatched": unmatched_deputies})


# def find_unmarked_deputies(keywords=[], presentielijsten={}, ):
#     """mark deputies from keyword list """
#     kws = keywords
#     deputy_heuristic = FuzzyKeywordSearcher(config=base_config)
#     deputy_heuristic.index_keywords(kws)
#     deputy_heuristic.index_spelling_variants = True
#     ll = {}
#     deps = deputy_heuristic.find_close_distance_keywords(keyword_list=[w[0] for w in keywords])
#
#     merge(deps.values())
#     deputies = {d: deps[d] for d in kws}
#     deputy_searcher = FuzzyKeywordSearcher(config=base_config)
#     deputy_searcher.index_keywords(list(deputies.keys()))
#     deputy_searcher.index_spelling_variants = True
#     for k in deputies.keys():
#         for val in deputies[k]:
#             deputy_searcher.index_spelling_variant(k, val)
#     for T in presentielijsten.keys():
#         itm = presentielijsten[T]
#         txt = itm.text
#         mt = itm.matched_text
#         (text=txt, item=mt, keywords=kws, searcher=deputy_searcher,
#                itemtype="delegate2")


def fndmatch(heer='',
             keywords: list = [],
             rev_graph: object = None,
             searcher: object = None,
             junksearcher: object = None,
             register: dict = {},
             df: object = None):
    transposed_graph = reverse_dict(keywords)
    result = match_previous(heer)
    if len(result) == 0:
        mf = FndMatch(rev_graph=transposed_graph,
                      searcher=FuzzyKeywordSearcher,
                      junksearcher=FuzzyKeywordSearcher,
                      register=register,
                      df=df)
        mf.match_candidates(heer=heer)
        result = result.heer.serialize()
    return result


cdksearcher = FuzzyKeywordSearcher(config=fuzzysearch_config)
