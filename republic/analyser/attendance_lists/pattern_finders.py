import re
import logging

from fuzzy_search.search.phrase_searcher import FuzzyPhraseSearcher
from fuzzy_search.phrase.phrase_model import PhraseModel

from ...helper.utils import best_match
from ...data.delegate_database import ekwz


fuzzysearch_config = {
    "char_match_threshold": 0.8,
    "ngram_threshold": 0.6,
    "levenshtein_threshold": 0.5,
    "ignorecase": True,
    "ngram_size": 3,
    "skip_size": 1,
}



def president_searcher(presentielijsten, from_scratch=True):
    """search and mark president in delegate attendance list
       this returns heren, but marks the presidents
       in the presentielijsten texts"""
    ps = make_president_searcher()
    heren = []
    pat = "%s(.*)%s"  # pat = "%s.*(.*)%s"  # de presidenten
    pats = []
    for T in list(presentielijsten.keys()):
        ob = presentielijsten[T].matched_text
        txt = ob.item
        heer = get_president(ob, pat, ps, txt)
        if heer:
            heren.append(heer)
    return heren


def make_president_searcher():
    fuzzysearch_config = {'char_match_threshold': 0.5,
                          'ngram_threshold': 0.5,
                          'levenshtein_threshold': 0.4,
                          'ignorecase': False,
                          'ngram_size': 2,
                          'skip_size': 2}
    president_searcher = FuzzyPhraseSearcher(config=fuzzysearch_config)
    vs = ['PRASIDE Den Heere',
          'PRA ESIDE Den Heere',
          'PRA ZSIDE Den Heere'
          'PRESIDE Den Heere',
          'P R A E S I D E Den Heere',
          'PRAESIDE Den Heere',
          'PRAESIDEDen Heere',
          'P R A S I D E Den Heere',
          'P R E S I D E Den Heere',
          'P R AE S I D E Den Heere',
          'DR AS 1D E Den Heere',
          'PR ASL DE Den Heere',
          'PR A31 DE; Den Heere',
          'BR JE 3.1. DE, Den Heere']
    vs = vs #+ ekwz['PRAS']
    pvs = ['PRASENTIBUS',
           'PRESENTIBUS',
           'P R A E S E N T I B U S',
           'P RAE SE N TI B U S',
           'PRA&SENTIBUS',
           'PRAESEN','PRAES']
    pvs = ekwz['PRASENTIBUS'] + pvs
    variants = [{'phrase': 'PRAESIDE Den Heere', 'label':'president', 'variants': vs},
                {'phrase': 'PRAESENTIBUS', 'label':'presentibus', 'variants': pvs},
                ]
    president_searcher.index_phrase_model(phrase_model=variants)
    return president_searcher


def get_president(ob, pat, ps, txt, debug=True):
    """TODO: split president getting and span setting"""
    ofset = 0  # in case we find no president marker
    end = 0
    prez = ''
    prae = ''
    matches = ps.find_matches(text=txt, include_variants=True, use_word_boundaries=False)
    presidents = [m for m in matches if m.label == 'president']
    president = best_match(presidents)
    if president:
        ofset = getattr(president, "offset") or 0
        prez = getattr(president, "string") or ''
    presentibi = [m for m in matches if m.label == 'presentibus']
    if presentibi:
        presentibus = best_match(presentibi)
        prae = presentibus.string or ''
        end = getattr(presentibus, "offset") or len(txt)
    spns = {}
    if ofset != 0:
        preamble_span = (0, ofset - 1)
        preamble = txt[preamble_span[0]:preamble_span[1]]
        spns['preamble'] = (preamble, preamble_span)
    pre_span = (ofset, ofset + len(prez))
    spns['pre'] = (prez, pre_span)
    presentibus_span = (end, end + len(prae))
    spns['presentibus'] = (prae, presentibus_span)
    searchpat = pat % (re.escape(prez), re.escape(prae))
    r = re.search(searchpat, txt)
    if r and r.group(1):
        heer = r.group(1).strip()
        # rex = re.search('e?r?e\s', heer)
        # if rex:
        #     if rex.span()[0] == 0:
        #         heer = heer[rex.span()[1]:]
        heer = re.sub('[^\s\w]*', '', heer)
        if debug:
            logging.info(heer)
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
        return heer


def make_province_searcher(config):
    pr_searcher = FuzzyPhraseSearcher(config)
    basephrase = [{'phrase':"extraordinaris Gedeputeerden uyt de provincie van",
                  'label':'extraordinaris',
                  'variants':[]}]
    prefix = [{'phrase':'met een', 'label':'prefix','variants':['met twee', 'met drie', 'een ', 'twee ', 'drie'
                                                                'vier', 'vijf']}]
    provinces = [{'phrase': "Gelderlandt",'label':'province',
                 'variants':["Hollandt ende West-Vrieslandt",
                 "Utrecht",
                 "Frieslandt",
                 "Overijssel",
                 "Groningen",
                 "Zeelandt"]}]
    rps = ['Raadtpenslonaris',
          'Raadtpenfionaris',
          'Raudtpensionaris',
          'Raaadtpensionaris',
          'Raadtpensonaris',
          'Raadtpensienaris',
          'Raaatpensionaris',
          'Raadtpensionaris']

    raadp = [{'phrase': 'Raadtpensionaris', 'label': 'raadpensionaris', 'variants': rps}]
    hrn = [{'phrase':'Den Heere', 'label': 'heere', 'variants':['Den Heere',
                                                                'De Heeren'
                                                                'Den Heeren',
                                                                'De Heer']}]
    nihil = [{'phrase':'Nihil actum est', 'label': 'nihil', 'variants':['Nihil actum est',
                                                                        'Nibil actum est']}]
    phrases = basephrase + prefix + provinces + raadp + hrn + nihil
    pmodel = PhraseModel(model=phrases, config=config)
    #print(phrases, phrase_model)
    pr_searcher.index_phrase_model(phrase_model=pmodel)
    return pr_searcher

def match_prov(matches):
    foundtexts = []
    bstr = [s for s in matches if s.label=='extraordinaris']
    for item in bstr:
        o = item.offset
        l = o + len(item.string)
        pre_searchtext = [p.offset for p in matches if p.label=='prefix' and p.offset in range(o-10,o)]
        if len(pre_searchtext)>0:
            o = pre_searchtext[0]
        post_searchtext = [p.offset + len(p.string) for p in matches if p.label=='province' and p.offset in range(l,l+30)]
        if len(post_searchtext) > 0:
            l = post_searchtext[0]
        foundtexts.append((o,l))
    return foundtexts

def province_searcher(presentielijsten, config=fuzzysearch_config):
    pr_searcher = make_province_searcher(config)
    for T in presentielijsten.keys():
        itm = presentielijsten[T]
        itm.matched_text
        txt = itm.text
        mt = itm.matched_text
        provs = pr_searcher.find_matches(text=txt, include_variants=True)
        rresult = [p for p in provs if p.label in ['raadpensionaris', 'heere', 'nihil']]
        for i in rresult:
            span = (i.offset, i.offset+len(i.string))
            mt.set_span(span, i.label)
        presults = match_prov(provs)
        for item in presults:
            span = (item[0], item[1])
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
