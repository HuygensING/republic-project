import os
import json
from collections import Counter
from collections import defaultdict

from elasticsearch import Elasticsearch
import networkx as nx
import pandas as pd
import logging
from fuzzy_search.fuzzy_phrase_searcher import FuzzyPhraseSearcher
from fuzzy_search.fuzzy_phrase_model import PhraseModel

from republic.elastic.attendancelist_retrieval import make_presentielijsten
from republic.analyser.attendance_lists.pattern_finders import province_searcher, president_searcher, make_groslijst
from republic.model.republic_attendancelist_models import MatchHeer
import republic.analyser.attendance_lists.parse_delegates as parse_delegates
from republic.analyser.attendance_lists.searchers import make_junksweeper
from republic.helper.similarity_match import FuzzyKeywordGrouper
from republic.helper.utils import reverse_dict
from republic.data.delegate_database import abbreviated_delegates, found_delegates, ekwz


def start_logger(outdir, year):
    print(f"logging to {os.path.join(outdir, 'attendancelist.log')}")
    logging.basicConfig(filename=os.path.join(outdir, 'attendancelist.log'), level=logging.INFO)
    logging.info(f'{year} Started')


fuzzysearch_config = {
    "char_match_threshold": 0.8,
    "ngram_threshold": 0.6,
    "levenshtein_threshold": 0.5,
    "ignorecase": False,
    "ngram_size": 3,
    "skip_size": 1,
}

# we define a number of data sources at the module level
# in the hope this speeds things up a bit

junksweeper = make_junksweeper(ekwz=ekwz)
transposed_graph = reverse_dict(ekwz)
keywords = list(abbreviated_delegates.name)
kwrds = {key: parse_delegates.nm_to_delen(key) for key in keywords}


def sweep_list(dralist, junksweeper=junksweeper):
    def get_lscore(r):
        return r.score_levenshtein_similarity()

    rawres = []
    for t in dralist:
        #    t = rawlist[i]
        if len(t) > 1:
            rawtext = ' '.join(t)
        else:
            rawtext = t[0]
        rawtext = rawtext.strip()
        if rawtext == '':
            break
        try:
            r = junksweeper.find_matches(text=rawtext)
            try:
                nr = max(r, key=get_lscore)
                if nr.score_levenshtein_similarity() < 0.5:
                    rawres.append(t)
            except ValueError:
                rawres.append(t)
        except ValueError:
            pass
    return rawres


def list_tograph(inputlist: list):
    cl_heren = FuzzyKeywordGrouper(keyword_list=inputlist).find_close_distance_keywords()
    g_heren = nx.Graph()
    d_nodes = sorted(cl_heren)
    for node in d_nodes:
        attached_nodes = cl_heren[node]
        g_heren.add_node(node)
        for nod in attached_nodes:
            g_heren.add_edge(node, nod)
    return g_heren


matchfinder = parse_delegates.FndMatch(year=0, rev_graph=transposed_graph,
                                       searcher=parse_delegates.herensearcher,
                                       junksearcher=junksweeper,
                                       df=abbreviated_delegates)


def prepare_found_delegates(framed_gtlm, found_delegates, year):
    framed_gtlm['vs'] = framed_gtlm.gentleobject.apply(lambda x: [e for e in x.variants['general']])
    framed_gtlm['ref_id'] = framed_gtlm.gentleobject.apply(lambda x: x.heerid)
    # framed_gtlm['uuid'] = framed_gtlm.gentleobject.apply(lambda x: x.get_uuid())
    framed_gtlm['name'] = framed_gtlm.gentleobject.apply(lambda x: x.name)
    framed_gtlm['found_in'] = year
    return framed_gtlm


def run(es: Elasticsearch, year=0, outdir='', tofile=True, verbose=True):
    runner = RunAll(es=es, year=year)
    if verbose:
        print("- gathering attendance lists")
    if len(runner.searchobs) == 0:
        print('no attendance lists found. Quitting')
        return
    if verbose:
        print("- running initial find")
    runner.initial_find()
    # if verbose:
    #     print("- running gather_found_delegates")
    # runner.gather_found_delegates()
    # if verbose:
    #     print("- running identification")
    # runner.identify_delegates()
    # if verbose:
    #     print("- running verification")
    # runner.verify_matches()
    if verbose:
        print("- running delegates_from_fragments")

    runner.delegates_from_fragments()
    yout = year_output(year, runner.searchobs)
    if tofile is True:
        outname = f'{outdir}/{year}_out.json'
        if verbose:
            print(f"- saving results to {outname}")
        with open(outname, 'w') as fout:
            json.dump(fp=fout, obj=yout)
    else:
        return yout
    # if verbose == True:
    #    print("saving found delegates")
    # save_db(runner.found_delegates)
    # try:
    #     Popen()
    # except os.error:
    #     pass # this needs to be replaced with something more elegant
    print(f"{year} done")
    logging.info(f'{year} Finished')
    return 'runner'


class RunAll(object):

    def __init__(self, es: Elasticsearch,
                 year=0,
                 abbreviated_delegates=abbreviated_delegates,
                 kwrds=kwrds,
                 found_delegates=found_delegates,
                 matchfnd=matchfinder,
                 ekwz=ekwz,
                 outdir=''
                 ):
        start_logger(outdir, year)
        self.year = year
        self.searchobs = make_presentielijsten(es=es, year=self.year, index='resolutions')
        logging.info(f'year: {year}, nr of attendancelists {len(self.searchobs)}')
        self.junksweeper = make_junksweeper(ekwz)
        self.abbreviated_delegates = abbreviated_delegates
        self.found_delegates = found_delegates
        self.pm_heren = list(found_delegates['name'].unique())
        self.matchfnd = matchfnd
        self.herenkeywords = kwrds
        self.all_matched = None
        self.unmatched = None
        self.moregentlemen = None
        self.presidents = None
        self.framed_gtlm = None
        self.fragmentsearcher = None
        self.serializable_df = None

    def initial_find(self):
        print("1. finding presidents")
        presidents = president_searcher(presentielijsten=self.searchobs)  # update
        print(len(presidents), 'found')
        self.presidents = [h.strip() for h in presidents]
        print("2.find provincial extraordinaris gedeputeerden")
        ps = province_searcher(presentielijsten=self.searchobs)

    def find_unmarked_text(self, sweep=True):
        print("3. finding unmarked text")
        unmarked = make_groslijst(presentielijsten=self.searchobs)
        c = Counter(unmarked)
        tussenkeys = FuzzyKeywordGrouper(keyword_list=list(c.keys()))
        dralist = tussenkeys.vars2graph()
        if sweep:
            unmarked_text = sweep_list(dralist, junksweeper=self.junksweeper)
        else:
            unmarked_text = dralist
        return unmarked_text

    def gather_found_delegates(self):
        """try to find delegates in all as yet unmarked text.
        All identified delegates are collected in self.all_matched
        All unidentified keywords are left in self.unmatched for further processing
        """
        deputies = self.find_unmarked_text()
        # existing_herensearcher = FuzzyKeywordSearcher(config=fuzzysearch_config)
        # existing_herensearcher.index_keywords(self.pm_heren)
        self.presidents = [p for p in self.presidents if len(p) > 0]
        connected_presidents = FuzzyKeywordGrouper(self.presidents).vars2graph()
        print("4. joining presidents and delegates")
        found_presidents = parse_delegates.find_delegates(input=connected_presidents,
                                                          matchfnd=self.matchfnd,
                                                          df=self.abbreviated_delegates,
                                                          previously_matched=self.found_delegates,
                                                          year=self.year)
        new_found_delegates = parse_delegates.find_delegates(input=deputies,
                                                             matchfnd=self.matchfnd,
                                                             df=self.abbreviated_delegates,
                                                             previously_matched=self.found_delegates,
                                                             year=self.year)

        all_matched = {}
        for d in [found_presidents['matched'], new_found_delegates['matched']]:
            for key in d:
                if key not in all_matched.keys():
                    all_matched[key] = d[key]
                else:
                    all_matched[key]['variants'].extend(d[key]['variants'])
        print(f"total {len(all_matched)} found ")
        self.all_matched = all_matched
        self.unmatched = new_found_delegates['unmatched']
        self.moregentlemen = [MatchHeer(all_matched[d]) for d in all_matched.keys() if
                              type(d) == int]  # strange keys sneak in
        # patch up the dataframe for further matching
        framed_gtlm = pd.DataFrame(self.moregentlemen)
        framed_gtlm.rename(columns={0: 'gentleobject'}, inplace=True)
        framed_gtlm['variants'] = framed_gtlm.gentleobject.apply(lambda x: [e.form for e in x.variants['general']])
        framed_gtlm['ref_id'] = framed_gtlm.gentleobject.apply(lambda x: x.heerid)
        framed_gtlm['uuid'] = framed_gtlm.gentleobject.apply(lambda x: x.get_uuid())
        framed_gtlm['name'] = framed_gtlm.gentleobject.apply(lambda x: x.name)
        framed_gtlm['found_in'] = self.year
        self.framed_gtlm = framed_gtlm

    def identify_delegates(self):
        """make search objects from matched delegates that are in self.all_matched"""
        matchsearch = FuzzyPhraseSearcher(config=fuzzysearch_config)
        kws = defaultdict(list)
        matcher = {}
        phrases = []
        for key in self.all_matched:
            kw = self.all_matched[key]
            variants = kw.get('variants')
            variants = [v[1] for v in variants]
            keyword = kw.get('m_kw')
            id = kw.get('id')
            label = kw.get('name')
            if keyword != '':
                phrase = {'phrase': keyword, 'label': f"{label}({id})", 'variants': variants}
                phrases.append(phrase)
        phrase_model = PhraseModel(phrases=phrases, config=fuzzysearch_config)
        matchsearch.index_phrase_model(phrase_model=phrase_model)
        return matchsearch

    def verify_matches(self):
        """We try to turn the delegates that are collected in self.all_matched into text annotations
         all delegates have been identified (not necessarily correctly though)
         and the dictionary contains a number of variants. These _should_ be a good point of departure"""
        all_matched = self.all_matched

        print("5. verifying matches")
        # for T in self.searchobs:
        #     ob = self.searchobs[T].matched_text
        # delegate_results = Counter()
        # for T in self.searchobs:
        #     searchob = self.searchobs[T]
        #     result = get_delegates_from_spans(searchob.matched_text)
        #     try:
        #         id = result['delegate']['id']
        #         if id:
        #             delegate_results.update([id])
        #     except KeyError:
        #         pass


        # framed_gtlm.to_pickle('sheets/framed_gtlm.pickle')
        matchsearch = self.identify_delegates()
        print("6. verifying spans")
        for T in self.searchobs:
            searchob = self.searchobs[T]
            try:
                mo = parse_delegates.MatchAndSpan(searchob.matched_text,
                                                  junksweeper=self.junksweeper,
                                                  previously_matched=self.framed_gtlm,
                                                  match_search=matchsearch)
            except TypeError:
                print (T, searchob.matched_text.item)
                raise
            parse_delegates.delegates2spans(searchob, framed_gtlm=self.framed_gtlm)
        print("updating merged delegates database")
        merged_deps = pd.merge(left=self.framed_gtlm, right=abbreviated_delegates, left_on="ref_id", right_on="id",
                               how="left")
        serializable_df = merged_deps[['ref_id', 'geboortejaar', 'sterfjaar', 'colleges', 'functions',
                                       'period', 'sg', 'was_gedeputeerde', 'p_interval', 'h_life', 'variants', 'name_x',
                                       'found_in', ]]
        serializable_df.rename(columns={'name_x': 'name',
                                        'vs': 'variants',
                                        "h_life": "hypothetical_life",
                                        "p_interval": "period_active",
                                        "sg": "active_stgen"}, inplace=True)
        self.serializable_df = serializable_df
        print("7. finished to attendance lists and found database")

    def delegates_from_fragments(self):
        self.fragmentsearcher = parse_delegates.DelegatesFromFragments(searchobs=self.searchobs,
                                                                       year=self.year,
                                                                       junksweeper=junksweeper,
                                                                       found=found_delegates,
                                                                       df=abbreviated_delegates)
        self.fragmentsearcher.run()
        parse_delegates.reverse_references(self.fragmentsearcher.xgroups,
                                           self.fragmentsearcher.match_records)


def year_output(year, searchobs):
    out = []
    for T in searchobs:
        ob = searchobs[T]
        out.append(ob.to_dict())
    return out
