import pandas as pd
import networkx as nx
from ..elastic.attendancelist_retrieval import make_presentielijsten
from ..analyser.attendance_lists.pattern_finders import *
from ..analyser.attendance_lists.parse_delegates import *
from ..helper.similarity_match import FuzzyKeywordGrouper
from ..data.delegate_database import abbreviated_delegates, found_delegates, ekwz
from ..helper.utils import reverse_dict


fuzzysearch_config = {
    "char_match_threshold": 0.7,
    "ngram_threshold": 0.5,
    "levenshtein_threshold": 0.5,
    "ignorecase": False,
    "ngram_size": 2,
    "skip_size": 2,
}

# we define a number of data sources at the module level
# in the hope this speeds things up a bit

junksweeper = make_junksweeper(ekwz=ekwz)
transposed_graph = reverse_dict(ekwz)
keywords = list(abbreviated_delegates.name)
kwrds = {key:nm_to_delen(key) for key in keywords}



def sweep_list(dralist, junksweeper=junksweeper):
    def get_lscore(r):
        return r['levenshtein_distance']

    rawres = []
    for t in dralist:
        #    t = rawlist[i]
        if len(t) > 1:
            rawtext = ' '.join(t)
        else:
            rawtext = t[0]
        r = junksweeper.find_candidates(rawtext)
        try:
            nr = max(r, key=get_lscore)
            if nr['levenshtein_distance'] < 0.5:
                rawres.append(t)
        except ValueError:
            rawres.append(t)
    return rawres

def list_tograph(inputlist: list):
    cl_heren = FuzzyKeywordGrouper(keyword_list=inputlist).find_close_distance_keywords()
    G_heren = nx.Graph()
    d_nodes = sorted(cl_heren)
    for node in d_nodes:
        attached_nodes = cl_heren[node]
        G_heren.add_node(node)
        for nod in attached_nodes:
            G_heren.add_edge(node, nod)
    return G_heren




matchfinder = FndMatch(year=0,
                       rev_graph=transposed_graph,
                       searcher=herensearcher,
                       junksearcher=junksweeper,
                       df=abbreviated_delegates)

def prepare_found_delegates(framed_gtlm, found_delegates, year):
    framed_gtlm['vs'] = framed_gtlm.gentleobject.apply(lambda x: [e for e in x.variants['general']])
    framed_gtlm['ref_id'] = framed_gtlm.gentleobject.apply(lambda x: x.heerid)
    #framed_gtlm['uuid'] = framed_gtlm.gentleobject.apply(lambda x: x.get_uuid())
    framed_gtlm['name'] = framed_gtlm.gentleobject.apply(lambda x: x.name)
    framed_gtlm['found_in'] = year
    return framed_gtlm




def run(year=0,  outdir='', verbose=True):
    runner = RunAll(year=year)
    if verbose == True:
        print ("- gathering attendance lists")
    runner.make_searchobs()
    if len(runner.searchobs) == 0:
        print ('no attendance lists found. Quitting')
        return
    if verbose == True:
        print("- running initial find")
    runner.initial_find()
    if verbose == True:
        print("- running gather_found_delegates")
    runner.gather_found_delegates()
    if verbose == True:
        print("- running identification")
    runner.identify_delegates()
    if verbose == True:
        print("- running verification")
    runner.verify_matches()
    outname = f'{outdir}/{year}_out.json'
    if verbose == True:
        print(f"- saving results to {outname}")
    yout = year_output(year, runner.searchobs)
    with open(outname, 'w') as fout:
        json.dump(fp=fout, obj=yout)
    #if verbose == True:
    #    print("saving found delegates")
    #save_db(runner.found_delegates)
    # try:
    #     Popen()
    # except os.error:
    #     pass # this needs to be replaced with something more elegant
    print (f"{year} done")
    return 'runner'

class RunAll(object):
    def __init__(self,
                 year=0,
                 abbreviated_delegates=abbreviated_delegates,
                 kwrds=kwrds,
                 found_delegates=found_delegates,
                 matchfnd = matchfinder,
                 ekwz=ekwz
                 ):
        self.year = year
        self.junksweeper = make_junksweeper(ekwz)
        self.abbreviated_delegates = abbreviated_delegates
        self.found_delegates = found_delegates
        self.pm_heren = list(found_delegates['name'].unique())
        self.matchfnd = matchfnd
        self.herenkeywords = kwrds

    def make_searchobs(self):
        make_presentielijsten(year=self.year)
        self.searchobs = make_presentielijsten(year=self.year)
        print('year: ', len(self.searchobs), 'presentielijsten')

    def initial_find(self):
        print ("1. finding presidents")
        presidents = president_searcher(presentielijsten=self.searchobs) # update
        print(len(presidents), 'found')
        self.presidents = [h.strip() for h in presidents]
        print("2.find provincial extraordinaris gedeputeerden")
        ps = province_searcher(presentielijsten=self.searchobs)

    def find_unmarked_text(self):
        print("3. finding unmarked text")
        unmarked = make_groslijst(presentielijsten=self.searchobs)
        c = Counter(unmarked)
        tussenkeys = FuzzyKeywordGrouper(keyword_list=list(c.keys()))
        dralist = tussenkeys.vars2graph()
        unmarked_text = sweep_list(dralist, junksweeper=self.junksweeper)
        return unmarked_text

    def gather_found_delegates(self):
        deputies = self.find_unmarked_text()
        # existing_herensearcher = FuzzyKeywordSearcher(config=fuzzysearch_config)
        # existing_herensearcher.index_keywords(self.pm_heren)
        self.presidents = [p for p in self.presidents if len(p) > 0]
        connected_presidents = FuzzyKeywordGrouper(self.presidents).vars2graph()
        print("4. joining presidents and delegates")
        found_presidents = find_delegates(input=connected_presidents,
                                          matchfnd=self.matchfnd,
                                          df=self.abbreviated_delegates,
                                          previously_matched=self.found_delegates,
                                          year=self.year)
        new_found_delegates = find_delegates(input=deputies,
                                             matchfnd=self.matchfnd,
                                             df=self.abbreviated_delegates,
                                             previously_matched=self.found_delegates,
                                             year=self.year)

        all_matched = {}
        for d in [found_presidents['matched'], new_found_delegates['matched']]:
            for key in d:
                if key not in all_matched.keys():
                    all_matched[key]= d[key]
                else:
                    all_matched[key]['variants'].extend(d[key]['variants'])
        print(f"total {len(all_matched)} found")
        self.all_matched = all_matched

    def identify_delegates(self):
        """make search objects from matched delegates that are in self.all_matched"""
        matchsearch = FuzzyKeywordSearcher(config=fuzzysearch_config)
        kws = defaultdict(list)
        matcher = {}
        for key in self.all_matched:
            variants = self.all_matched[key].get('variants')
            keyword = self.all_matched[key].get('m_kw')
            idnr = self.all_matched[key].get('id')
            name = self.all_matched[key].get('name')
            for variant in variants:
                kws[keyword].append(variant[0])
                matcher[variant[0]] = {'kw':keyword, 'id':idnr, 'name':name}
        matchsearch.index_keywords(list(kws.keys()))
        for k in kws:
            for v in kws[k]:
                matchsearch.index_spelling_variant(keyword=k,variant=v)
        return matchsearch

    def verify_matches(self):
        all_matched = self.all_matched

        print("5. verifying matches")
        for T in self.searchobs:
            ob = self.searchobs[T].matched_text
        delresults = Counter()
        for T in self.searchobs.keys():
            searchob = self.searchobs[T]
            result = get_delegates_from_spans(searchob.matched_text)
            try:
                id = result['delegate']['id']
                if id:
                    delresults.update([id])
            except KeyError:
                pass
        self.moregentlemen = [MatchHeer(all_matched[d]) for d in all_matched.keys() if
                              type(d) == int]  # strange keys sneak in
        framed_gtlm = pd.DataFrame(self.moregentlemen)
        framed_gtlm.rename(columns={0:'gentleobject'}, inplace=True)
        framed_gtlm['vs'] = framed_gtlm.gentleobject.apply(lambda x: [e for e in x.variants['general']])
        framed_gtlm['ref_id'] = framed_gtlm.gentleobject.apply(lambda x: x.heerid)
        framed_gtlm['uuid'] = framed_gtlm.gentleobject.apply(lambda x: x.get_uuid())
        framed_gtlm['name'] = framed_gtlm.gentleobject.apply(lambda x: x.name)
        framed_gtlm['found_in'] = self.year

        # framed_gtlm.to_pickle('sheets/framed_gtlm.pickle')
        matchsearch = self.identify_delegates()
        print("verifying spans")
        for T in self.searchobs:
            searchob = self.searchobs[T]
            mo = MatchAndSpan(searchob.matched_text, junksweeper=junksweeper, previously_matched=self.found_delegates, match_search=matchsearch)
            delegates2spans(searchob, framed_gtlm=framed_gtlm)
        print("updating merged delegates database")
        merged_deps = pd.merge(left=framed_gtlm, right=abbreviated_delegates, left_on="ref_id", right_on="id", how="left")
        serializable_df = merged_deps[['ref_id','geboortejaar', 'sterfjaar', 'colleges', 'functions',
           'period', 'sg', 'was_gedeputeerde', 'p_interval', 'h_life', 'vs','name_x', 'found_in',]]
        serializable_df.rename(columns={'name_x':'name',
                                    'vs':'variants',
                                    "h_life": "hypothetical_life",
                                    "p_interval":"period_active",
                                    "sg": "active_stgen"},  inplace=True)
        self.serializable_df = serializable_df
        print("6. finished to attendance lists and found database")


def year_output(year, searchobs):
    out = []
    for T in searchobs:
        ob = searchobs[T]
        out.append(ob.to_dict())
    return out