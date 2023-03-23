# Laad de benodigde modules in

import os
import re
import json
import ast
from string import Template

from collections import Counter
from collections import defaultdict
from itertools import combinations
from typing import Union, List, Iterable, Dict
import langid
import pandas as pd
import copy
import json
from analiticcl import VariantModel, Weights, SearchParameters
from fuzzy_search.fuzzy_string import score_levenshtein_similarity_ratio
from republic.helper.similarity_match import FuzzyKeywordGrouper
import republic.model.republic_document_model as rdm
from sklearn.mixture import BayesianGaussianMixture
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
import seqsim
from republic.helper import text_helper


def determine_klusters(wm):
    l=len(wm)
    n = 2
    dfr = {20:2,50:3,100:5,500:25,1000:50,1500:75}
    for k,v in dfr.items():
        if l<k:
            n=v
            break
    step = 5
    n_min = 2
    if 20<n<200:
        step = 10
    elif n<500:
        n_min = 20
        step = 20
    elif n<1000:
        n_min = 70
        step = 50
    else:
        n_min = 150
        n = 200
        step = 500
    silhouettes = {}
    for n_c in range(n_min,max(n,2)):
        try:
            clusterer = KMeans(n_clusters=n_c, random_state=42)
            cluster_labels = clusterer.fit_predict(wm)
            silhouette_avg = silhouette_score(wm, cluster_labels)
            silhouettes[n]=silhouette_avg
        except OverflowError:
            print('too many features, downscaling', n_c, len(wm))
    try:
        result = max(silhouettes.items(), key=lambda x: x[1])
    except ValueError:
        result = (1,0)
    return result

def cluster_stats(row):
    cl = list(row['unique'])
#     print(row)
    length = len(cl)
    if length>1:
#         try:
        m = [[seqsim.edit.birnbaum_dist(x,y) for y in list(cl)] for x in list(cl)]
#         except (ValueError,TypeError):
#             print(list(cl), row)
        means = pd.DataFrame(m).agg('mean', axis=1)
        man = means.mean()
    else:
        man = 0
    return (length, man)


# the dictionary below should go somewhere else
kws = {'ontfangen': ['ntfangen', 'ontfanten', 'oontfangen', 'ontfangen'],
       'achtentwintichsten': ['achtentwintichsten', 'seventwintichsten'],
       'heer': ['heeren',
                'vandeheeren',
                'heer',
                'aendeheeren',
                'vandenheer',
                'heere',
                'deheeren',
                'heerheer'],
       'schrijven': ['aengeschreven',
                     'geschreven',
                     'schepenen',
                     'schreve',
                     'schreven',
                     'aenschrijvinge'],
       'halewijn': ['hawelijn', 'halewijn', 'halewyn', 'alewijn'],
       'ambassadeur': ['ambassadeur', 'ambassadeurs'],
       'extraordinaris': ['dextraor',
                          'extract',
                          'extraords',
                          'extraordina',
                          'taris',
                          'naris',
                          'dinaris',
                          'extraordinaris',
                          'traordinaris',
                          'extra',
                          'saris',
                          'ordinaris',
                          'extraordi',
                          'ris',
                          'extraor',
                          'extraorinaris'],
       'bagage': ['bagage', 'begagie', 'bagagie', 'equipagie'],
       'burgemeester': ['burgemeester', 'borgemeesteren'],
       'hendrik': ['chendrick', 'hendrick'],
       'colonel': ['colonel', 'colonnel'],
       'commissaris': ['missaris',
                       'commissie',
                       'commissa',
                       'commissisaris',
                       'commis',
                       'commissaris'],
       'coningh': ['conck', 'coninck', 'coningh'],
       'dantzig': ['dantzick',
                   'dansigh',
                   'danrigh',
                   'danich',
                   'danlick',
                   'danzich',
                   'dantsick',
                   'dansich',
                   'dantsigh',
                   'dansick'],
       'gedeputeerde': ['gedeputeerde',
                        'gedeputeerden', 'puteerde', 'gedepu'],
       'gedesigneerde': ['gedesigneerde',
                         'gedesigneerden',
                         'designeerden', 'geassigneerde'
                         ],
       'desselfs': ['desselffs', 'desselfs', 'desselfs', 'derselver', 'dewelcke'],
       'envoye': ['envoijé', 'envoijéx'],
       'fort': ['furt', 'fort'],
       'frankfort': ['franckhuart', 'franckfurt', 'franckfort'],
       'gemelten': ['gemelte', 'meergemelten', 'welgemelten', 'gemelten', 'melten', 'gemelteheeren', 'meergenoemden',
                    'meergemeltenheer'],
       'gerescribeert': ['rescribeert', 'gerescribeert'],
       'gijsbert': ['vijsbert', 'gijsberth', 'gijsbert'],
       'hertogh': ['hertogh', 'hertoch'],
       'jan': ['jehan', 'jean', 'johan', 'jan'],
       'tegens': ['jegens', 'tegens'],
       'lieutenant': ['lieutenandt', 'neutenant', 'lieutenant'],
       'lisbon': ['lisbon', 'lisbona'],
       'mach': ['mach', 'magh'],
       'madrid': ['madrid', 'madridt', 'madrie'],
       'memoriaal': ['memoriael', 'memorie'],
       'mitsgaders': ['midtsgaders', 'mitsgaders', 'mitsga'],
       'missive': ['misssive', 'missiven', 'missive', 'misssiven', 'brieff'],
       'permitteren': ['mitteren', 'permitteren'],
       'nievelt': ['nievelt', 'nieuvelt'],
       'nodige': ['noodige', 'nodige', 'noodich'],
       'pieterszoon': ['pieterszon', 'pietersoon'],
       'requeste': ['requette', 'requeste'],
       'resident': ['residenten', 'resident'],
       'sijne': ['sijne', 'sijner', 'syne'],
       'spoedigsten': ['spoedichsten', 'spoedighsten'],
       'tijd': ['teijt', 'tijt'],
       'versoecken': ['versocht', 'versochte', 'versoeckende', 'versoecken', 'versoeck'],
       'van': ['van','vande', 'vander', 'vanden', ],
       'volgen': ['volgen', 'volgens'],
       'voornoemde': ['voors', 'voorn', 'voornoemde', 'voornoemt', 'meergenoemden', 'voorschreven'],
       'witt': ['wit', 'witt', 'with'],
       'ho:mo': ['ho', 'mo']}




extra_kws = {'telwoord': ['1', '107', '10en', '1650', '4326808', 'drie', 'hondert', 'twaelff', 'twee', 'vijffthienden'],
             'achtervolgens': ['achtervolgens', 'vervolgens'],
             'acte': 'acte',
             'admiraliteijt': 'admiraliteijt',
             'adriaen': 'adriaen',
             'advis': 'advis',
             'aenge': 'aenge',
             'aenhalinge': 'aenhalinge',
             'aenrits': 'aenrits',
             'aenschrijvinge': 'aenschrijvinge',
             'aenspraecke': 'aenspraecke',
             'aernout': 'aernout',
             'aff': 'aff',
             'affgaen': 'affgaen',
             'affgesante': 'affgesante',
             'agent': 'agent',
             'alhier': 'alhier',
             'alsmede': 'alsmede',
             'alsnogh': 'alsnogh',
             'amerongen': 'amerongen',
             'amsterdam': 'amsterdam',
             'arrivement': 'arrivement',
             'autheurs': 'autheurs',
             'authorisatie': ['authorisatie', 'autho', 'authoriseren', 'authorisatie'],
             'basel': 'basel',
             'be': 'be',
             'behoeve': 'behoeve',
             'bekent': 'bekent',
             'beleeffde': 'beleeffde',
             'belofte': 'belofte',
             'beneficieren': 'beneficieren',
             'benoogen': 'benoogen',
             'bern': 'bern',
             'betaelt': 'betaelt',
             'bogaert': 'bogaert',
             'bosvelt': 'bosvelt',
             'brakell': 'brakell',
             'brittannien': ['brittannien', 'engelsch'],
             'brodden': 'brodden',
             'bruijnincx': 'bruijnincx',
             'brussel': 'brussel',
             'buirse': 'buirse',
             'canesas': 'canesas',
             'carel': 'carel',
             'cel': 'cel',
             'civile': 'civile',
             'clachten': 'clachten',
             'cleijnen': 'cleijnen',
             'collegien': 'collegien',
             'com': ['com', 'munniceert'],
             'concernerende': 'concernerende',
             'consenteert': 'consenteert',
             'conside': 'conside',
             'consideratien': 'consideratien',
             'consul': 'consul',
             'coopman': ['coopman', 'coop'],
             'coorte': 'coorte',
             'cornelis': 'cornelis',
             'credentie': 'credentie',
             'cussens': 'cussens',
             'daechs': 'daechs',
             'daerop': 'daerop',
             'dagelicx': 'dagelicx',
             'daghgelden': 'daghgelden',
             'damas': 'damas',
             'del': 'del',
             'dergelijcke': 'dergelijcke',
             'derhalven': 'derhalven',
             'ders': 'ders',
             'designatie': 'designatie',
             'deur': 'deur',
             'dicanten': 'dicanten',
             'lidwoord': ['dien', 'den', 'der', 'de', 'het', 'een', 'gene', 'geene', 'eene', 'een'],
             'dijckvelt': 'dijckvelt',
             'doctor': 'doctor',
             'dop': 'dop',
             'drijvers': 'drijvers',
             'duijtsche': 'duijtsche',
             'duplicaet': 'duplicaet',
             'eedt': 'eedt',
             'effect': 'effect',
             'evacuatie': 'evacuatie',
             'everhardt': 'everhardt',
             'evrije': 'evrije',
             'ex': 'ex',
             'examineren': 'examineren',
             'favoriseren': 'favoriseren',
             'fluweele': 'fluweele',
             'francisco': 'francisco',
             'franck': 'franck',
             'francois': 'francois',
             'frans': 'frans',
             'frederico': 'frederico',
             'geaddresseert': 'geaddresseert',
             'gebracht': 'gebracht',
             'gecommitteert': ['gecommitteert', 'gecom'],
             'gedachtenisse': ['gedachtenisse', 'gedach'],
             'gedaen': 'gedaen',
             'gelieffden': 'gelieffden',
             'gelijck': 'gelijck',
             'gemaeckt': 'gemaeckt',
             'gemoet': 'gemoet',
             'generael': 'generael',
             'generaelmeester': 'generaelmeester',
             'geordonneert': 'geordonneert',
             'gepersuadeert': 'gepersuadeert',
             'gequalificeert': 'gequalificeert',
             'gestelt': 'gestelt',
             'gevol': 'gevol',
             'gevolchde': 'gevolchde',
             'gevolmach': ['gevolmach', 'gevolmachtichde'],
             'geweldige': 'geweldige',
             'ghemmeingh': 'ghemmeingh',
             'goeree': 'goeree',
             'gorcum': 'gorcum',
             'groot': 'groot',
             'haerlem': 'haerlem',
             'hamel': 'hamel',
             'hebbende': 'hebbende',
             'hollandt': 'hollandt',
             'holm': 'holm',
             'hooren': 'hooren',
             'hoove': 'hoove',
             'houdende': ['houdende', 'hou'],
             'ijets': 'ijets',
             'ijver': 'ijver',
             'informatie': 'informatie',
             'ingehuijrt': 'ingehuijrt',
             'isbrant': 'isbrant',
             'jegenwoordich': 'jegenwoordich',
             'jonghst': 'jonghst',
             'keijserlijcke': 'keijserlijcke',
             'landt': 'landt',
             'leonard': 'leonard',
             'maart': 'maart',
             'machtichde': 'machtichde',
             'maeltijt': 'maeltijt',
             'mait': 'mait',
             'majesteijt': 'majesteijt',
             'maseijck': 'maseijck',
             'meerman': 'meerman',
             'memo': 'memo',
             'midtsdesen': 'midtsdesen',
             'militie': 'militie',
             'ministers': 'ministers',
             'moesbergen': 'moesbergen',
             'moeten': 'moeten',
             'mr': 'mr',
             'munte': 'munte',
             'naem': ['naem', 'name'],
             'namentlijck': 'namentlijck',
             'narich': 'narich',
             'neert': 'neert',
             'negenthienden': 'negenthienden',
             'nicolaes': 'nicolaes',
             'nispen': 'nispen',
             'noemden': 'noemden',
             'officien': 'officien',
             'ommeren': 'ommeren',
             'ontslaginge': 'ontslaginge',
             'onvermindert': 'onvermindert',
             'oorlogh': 'oorlogh',
             'orange': 'orange',
             'ordi': 'ordi',
             'ordonneren': 'ordonneren',
             'ordre': 'ordre',
             'overbrengen': 'overbrengen',
             'overgegeven': 'overgegeven',
             'paspoort': 'paspoort',
             'pensionnaris': 'pensionnaris',
             'per': 'per',
             'pertinen': 'pertinen',
             'pierre': 'pierre',
             'pieter': 'pieter',
             'pisse': 'pisse',
             'poincten': 'poincten',
             'quam': 'quam',
             'quitantie': 'quitantie',
             'raadt': 'raadt',
             'raelmeesters': 'raelmeesters',
             'raesfelt': 'raesfelt',
             'raet': 'raet',
             'raetsaem': 'raetsaem',
             'rapport': 'rapport',
             'ratien': 'ratien',
             'rece': 'rece',
             'reeckencamer': 'reeckencamer',
             'reijgersbergh': 'reijgersbergh',
             'reijnolt': 'reijnolt',
             'relaxatie': 'relaxatie',
             'remon': 'remon',
             'remonstrantie': 'remonstrantie',
             'resolutie': 'resolutie',
             'restitutie': 'restitutie',
             'retorsie': 'retorsie',
             'riael': 'riael',
             'rijcxdaelders': 'rijcxdaelders',
             'ripperda': 'ripperda',
             'riseren': 'riseren',
             'rit': 'rit',
             'ritmr': 'ritmr',
             'robbert': 'robbert',
             'roms': 'roms',
             'sadeur': 'sadeur',
             'saecke': 'saecke',
             'sall': 'sall',
             'salée': 'salée',
             'sat': 'sat',
             'schade': 'schade',
             'schimmelpenningh': 'schimmelpenningh',
             'schip': 'schip',
             'secre': ['secre', 'secretaris'],
             'seeckeren': 'seeckeren',
             'sessen': 'sessen',
             'sgravenhage': 'sgravenhage',
             'siderende': 'siderende',
             'sluijs': 'sluijs',
             'soldije': 'soldije',
             'stavenisse': 'stavenisse',
             'steenwijck': 'steenwijck',
             'stelick': 'stelick',
             'stock': 'stock',
             'stockholm': 'stockholm',
             'strantie': 'strantie',
             'sustinerende': 'sustinerende',
             'talen': 'talen',
             'teffelen': 'teffelen',
             'tenisse': 'tenisse',
             'teresteijn': 'teresteijn',
             'tgenen': 'tgenen',
             'theodore': 'theodore',
             'tichde': 'tichde',
             'tinge': 'tinge',
             'cirurgijn': 'tirurgijn',
             'toege': 'toege',
             'tour': 'tour',
             'train': 'train',
             'trouppes': 'trouppes',
             'valckenburgh': 'valckenburgh',
             'vanvall': 'vanvall',
             'vergaderinge': 'vergaderinge',
             'verleent': 'verleent',
             'vermunten': 'vermunten',
             'verstaen': 'verstaen',
             'vertrouwde': 'vertrouwde',
             'vervat': 'vervat',
             'vierssen': 'vierssen',
             'vijantlicke': 'vijantlicke',
             'vijgh': 'vijgh',
             'visiteren': 'visiteren',
             'voorburch': 'voorburch',
             'vranckrijck': 'vranckrijck',
             'vrijbergen': 'vrijbergen',
             'vroetschap': 'vroetschap',
             'vsochten': 'vsochten',
             'weduwe': 'weduwe',
             'weede': 'weede',
             'weijman': 'weijman',
             'wer': 'wer',
             'werckendam': 'werckendam',
             'wijders': 'wijders',
             'wijlen': 'wijlen',
             'wijn': 'wijn',
             'willem': 'willem',
             'winckel': 'winckel',
             'wirts': 'wirts',
             'wisselen': 'wisselen',
             'woonende': 'woonende',
             'wors': 'wors',
             'zas': 'zas',
             'zeelant': 'zeelant',
             'zijde': 'zijde'}

kws.update(extra_kws)
rev_kws = {i:k for  k,v in kws.items() for i in v} # for easy lookup
# for e in eenkel:
#     if e not in menkel:
#         rev_kws[e]=e

# df_kws['norm_kw'] = df_kws.keyword.map(rev_kws)
# df_kws['norm_kw'].fillna(df_kws['keyword'], inplace=True)
# df_kws.groupby(['norm_kw']).agg({'keyword':lambda x:x.iloc[0],
#                                   'pre_context':sum,
#                                    'post_context':sum}).sort_values(['pre_context','post_context'],ascending=False)

def normalize(x):
    """for normalizing words in a dataframe"""
    result = x or ''
    result = result.strip()
    result = re.sub("""[,\.„—\'\"]+""",'',result)
    return result

def get_kw_for_term(x, rev_kws=rev_kws):
    preresult = normalize(x)
    r = rev_kws.get(preresult)
    if r:
        result = (f'<{preresult}>')
    else:
        result = preresult
    return result

def prune(x, selected=[], level=0):
    if x in selected + ['']:
        return x
    else:
        return f'VAR_{level}'

def strl2lst(s):
    """utility to convert string excel or html dataframes to frozenset columns"""
    lst = ast.literal_eval(s)
    res = frozenset(lst)
    return res



def get_formula_from_set(s={}, sentence=[], marker='_${pattern}_'):
    marker = Template(marker)
    r = []
    for e in sentence:
        if e in s:
            r.append(marker.substitute(pattern=e))
        else:
            r.append(e)
    res = ' '.join(r)
    return res


# Een handige 'Key Word In Context' functie om keywords/frasen en omringende tekst te zien
def get_keyword_context(text: str, keyword: str,
                        context_size: int = 3,
                        prefix_size: Union[None, int] = None,
                        suffix_size: Union[None, int] = None):
    if not prefix_size:
        prefix_size = context_size
    if not suffix_size:
        suffix_size = context_size
    text = re.sub(r'\s+',' ', text)
    prefix_pattern = r'(\w*\W*){' + f'{prefix_size}' + '}$'
    suffix_pattern = r'^(\w*\W*){' + f'{suffix_size}' + '}'
    contexts = []
    for match in re.finditer(r'\b' + keyword + r'\b', text):
        prefix_window = text[:match.start()]
        suffix_window = text[match.end():]
        prefix_terms = prefix_window.strip().split(' ')
        suffix_terms = suffix_window.strip().split(' ')
        prefix = ' '.join(prefix_terms[-prefix_size:])# re.search(prefix_pattern, prefix_window)
        suffix = ' '.join(suffix_terms[:suffix_size])# re.search(suffix_pattern, suffix_window)
        context = {
            'keyword': keyword,
            'prefix': prefix,
            'suffix': suffix,
            'keyword_offset': match.start(),
            'prefix_offset': match.start() - len(prefix),
            'suffix_offset': match.end()
        }
        contexts.append(context)
    return contexts

from collatex import Collation, collate
from io import StringIO

def df2collate(group):
    collation = Collation()
    for i in enumerate(group):
        nr = f'{i[0]}'
        witness = i[1]
        witness = re.sub('[<>]','',witness)
    #     witness = ' '.join([re.sub('\W+','',e) for e in list(i[1])])
        collation.add_plain_witness(nr, witness)
    alignment_tsv = collate(collation, near_match=True, segmentation=False, output="tsv")
    result = pd.read_csv(StringIO(alignment_tsv), sep='\t', header=None).fillna('')
    return result

def dfs_metrics(dfs):
    dfs[['length', 'means']] = dfs.apply(cluster_stats, axis=1, result_type="expand")
    return dfs

# set_inventory_indexes(ocr_type='pagexml', config=base_config)

# resolutions = resolutions_1672
bdir = '/Users/rikhoekstra/develop/analiticcl/'


class SearchResolutions(object):
    def __init__(self, searchterms: List, resolutions=Iterable):
        self.searchterms = searchterms
        self.resolutions = resolutions
        # self.resolutions = [r for r in self.resolutions.values() if len(
        #                     resolutions[r].paragraphs) > 0]  # filter out accidental empty paragraphs.
    def search_elastic(self):
        pass #tbd

    def search_analitic(self, bdir, threshold=0.75):
        # getting keywords with analytticl, but we can use anything as long as it returns resolutions
        result = defaultdict(list)
        resoluties = self.resolutions
        xmodel = VariantModel(os.path.join(bdir, "examples/simple.alphabet.tsv"), Weights(), debug=False)
        fn = (os.path.join('/tmp', 'analit_search.tsv'))
        with open(fn, 'w') as outfl:
            outfl.write('\n'.join(self.searchterms))
        xmodel.read_lexicon(fn)
        xmodel.build()
        for resolutie in resoluties:
            for p in enumerate(resolutie.paragraphs):
                res = xmodel.find_all_matches(p[1].text, SearchParameters(max_edit_distance=3))
                for x in res:
                    r = []
                    vs = x['variants']
                    if len(vs)>0:
                        for v in vs:
                            score = v.get('dist_score') or 0.0
        #                     print(v, score)
                            if score>threshold:
                                r.append(v)
                    if len(r)>0:
                        rv = {'p': p[0],
                              'input': x['input'],
                              'offset': x['offset'],
                              'variants':r}
                        result[resolutie.id].append(rv)

        # for r in result.keys():
        #     res = [x for x in resoluties if x.id == r]
        #     if len(res) > 0:
        #         filter_result[r] = res
        #

        return result

    def search_fuzzy(self):
        pass #tbd

# enkel = [c for c in cont if len(c)==1]

# menkel = {'aenschrijvinge': ['schrijven'],
#  'derselver': ['desselfs'],
#  'deses': ['desselfs'],
#  'designatie': ['gedesigneerde'],
#  'geassigneert': ['gedesigneerde'],
#  'gemelteheeren': ['gemelten'],
#  'gemention': ['gemelten'],
#  'gijsbrecht': ['gijsbert'],
#  'meergenoemden': ['voornoemde'],
#  'mitsga': ['mitsgaders'],
#  'syne': ['sijne']}


# menkel = {}
# eenkel = {}
# for i in [e[0] for e in enkel]:
#     res = [x for x in kws.keys() if score_levenshtein_similarity_ratio(i,x)>0.6]
#     if len(res)>0:
#         menkel[i] = res
#     else:
#         eenkel[i] = i


# langdict = defaultdict(list)
# for rslt in filter_result:
#     r = [r for r in ps if r.id==rslt][0]
#     id = r.metadata['id']
#     text = '\n'.join([p.text for p in r.paragraphs if langid.classify(p.text)[0]=='nl'])
#     lang = langid.classify(text)
#     langdict[lang[0]].append(id)

class StratifiedPhrase(object):
    def __init__(self,
                 resolutions: Iterable,
                 searchresult: Iterable,
                 langids: List = ['nl'],
                 searchterms: List = [],
                 prefix_size: [None, int]=5,
                 suffix_size: [None, int]=5,
                 context_size: [None, int]=5,):
        self.langids = langids
        self.searchterms = searchterms
        self.prefix_size = prefix_size
        self.suffix_size = suffix_size
        if self.prefix_size:
            self.context_size = self.prefix_size + self.suffix_size
        else:
            self.context_size = context_size
        self.resolutions = resolutions
        self.searchresult = searchresult
        self.gt = pd.DataFrame()

#        self.resolutions = [r for r in self.resolutions.values() if len(resolutions[r].paragraphs)>0] # filter out accidental empty paragraphs. Perhaps we should report this


    def resolutions2kwic(self, nl=True):
        """This is based on analitticl.
        Perhaps make it more versatile to also work with FuzzySearch"""
        xresult = []
        for rslt in self.searchresult: #filter_result:
            r = [r for r in self.resolutions if r.id==rslt][0]
            id = r.metadata['id']
            if nl is True:
                text = '\n'.join([p.text for p in r.paragraphs if langid.classify(p.text)[0]=='nl'])
            else:
                text = '\n'.join([p.text for p in r.paragraphs])
            s = self.searchresult[id]
            for v in s:
                offset = v['offset']
                variant = max(v['variants'], key=lambda x: x['dist_score'])
                fnd = variant['text']
                kwc = get_keyword_context(text.lower(),
                                          fnd.lower(),
                                          prefix_size=self.prefix_size,
                                          suffix_size=self.suffix_size,
                                          context_size=self.context_size)

                for item in kwc:
                    context = f"{item['prefix']} {item['keyword']} {item['suffix']}"
                    begin = item['prefix_offset']
                    end = begin+item['suffix_offset']+len(item['suffix'])
                    xresult.append((id, v['input'], fnd, context, item['prefix'], item['suffix'], begin, end))
        return xresult

    def res2frame(self):
        result = self.resolutions2kwic()
        self.df = pd.DataFrame(result, columns=['resolutie', 'keyword', 'found', 'context', 'prefix', 'suffix', 'begin','end'])

    def stratified_df(self, what='context', norms: Dict={}, with_kw=False, with_norms=False):
        """should this be more configurable
        norms should be a dictionary with normalized keywords for labelling and normalization"""
        if what=='prefix':
            size = self.prefix_size
        elif what=='suffix':
            size = self.suffix_size
        else:
            size = self.context_size
        flds = list(range(size))
        self.df[flds] = self.df[what].str.split(' ', expand=True)
        for c in flds:
            self.df[str(c)] = self.df[c].apply(lambda x: normalize(x))
            self.df[str(c)+'_norm'] = self.df[c].apply(lambda x:get_kw_for_term(x,rev_kws=rev_kws))
        if with_norms is True:
            flds = [str(c)+'_norm' for c in flds]
        if with_kw is True:
            flds = ['keyword'] + flds
        strati_df = self.df.groupby(flds).agg({"resolutie":'count'}).sort_values('resolutie',ascending=False)
        return strati_df

    def select_terms_raw(self):
        unselected = Counter()
        columns = [c for c in self.df.columns if type(c)==str and '_norm' in c]
        for c in columns:
            counts = self.df.groupby(c).resolutie.agg('count')
            unselected.update(counts.to_dict())
        return unselected

    def select_for_transition(self, minimum=10):
        unselected = self.select_terms_raw()
        selected = {k: v for k, v in unselected.items() if v > minimum}
        return list(selected.keys())


    def transitions(self):
        df2 = copy.deepcopy(self.df)
        selected = self.select_for_transition()
        columns = [c for c in self.df.columns if type(c) == str and '_norm' in c]
        for i in range(len(columns)):
            df2[f'{i}__p'] = df2[f'{i}_norm'].apply(lambda x: prune(x, selected=selected, level=i))
        z = df2.set_index([f'{i}__p' for i in range(10)])
        tdfs = {}
        for i in range(1, 11):
            cols = [f'{i}__p' for i in range(i)]
            if len(cols) > 1:
                cols = cols[-2:]
            grouped = z.groupby(cols).resolutie.agg('count')
            res = grouped.transform(lambda x: x / sum(x))
            tdfs[i] = res
        return tdfs

    def cluster_phrases(self, what='prefix'):
        flld = self.df[what].str.split('\W+').fillna('')
        dfs = pd.DataFrame()
        x1 = [list(x)[1:-1] for x in flld]
        df = pd.DataFrame(x1)
        df['length']= df.agg('count', axis=1) #.apply(lambda x:, axis=1)
        df = df.loc[df.length>0]
        gdf = df.groupby('length')
        for name, group in gdf:
            print(f'processing phrases with length {name}')
            if len(group)>2:
                dg = [list(x)[1:-3] for x in group.fillna('').to_records()]  # [c for c in group.columns if c!='']
                idx = [' '.join(x).strip() for x in dg]
                cluster_result = self.cluster(dg, idx)
                if len(dfs) == 0:
                    dfs = cluster_result
                else:
                    dfs = pd.concat([dfs, cluster_result])
            #         except ValueError:
            #             print (n, name)
            else:
                print(name, 'number of cases too small')
        dfs.columns = dfs.columns.droplevel(0)
        return dfs

    def cluster(self, dg, idx):

        m = [[seqsim.edit.birnbaum_dist(x, y) for y in dg if len(y) > 0] for x in dg if len(x) > 0]
        scaler = StandardScaler()
        wm = scaler.fit_transform(m)
        n = determine_klusters(wm)[0]
        bgm = BayesianGaussianMixture(n_components=n, init_params="kmeans", max_iter=200, random_state=42)
        ndf = pd.DataFrame(wm, index=idx)
        try:
            fitted = bgm.fit(wm)
        except ValueError:
            for new_n in [n // 2, n // 4]:
                try:
                    # print(new_n)
                    bgm = BayesianGaussianMixture(n_components=new_n, init_params="kmeans", max_iter=200,
                                                  random_state=42)
                    fitted = bgm.fit(wm)
                    n = new_n
                    # print(bgm)
                    break
                except ValueError:
                    pass
        ndf['label'] = bgm.fit_predict(wm)
        rdf = ndf.reset_index()
        groups = rdf.groupby('label')
        result = groups.agg({'index': ['unique', 'nunique', 'count']})
        return result


class FormulaExtractor(object):
    def __init__(self, df: pd.DataFrame) -> pd.DataFrame:
        self.df = df.drop_duplicates()
        self.gt = None
        if type(df.index) != pd.MultiIndex:
            self.df = self.frame2comp(self.df)
    def jaccard_frame(self, df: pd.DataFrame) -> pd.DataFrame:
        """this adds fields for jaccard comparison to a dataframe"""
        ks = df.index
        cks = [(frozenset(c[0]), frozenset(c[1])) for c in combinations(ks, r=2)]
        resf = pd.DataFrame(cks)
        resf['intersection'] = resf.apply(lambda row: row[0].intersection(row[1]), axis=1)
        resf = resf.loc[resf.intersection != frozenset([])]
        resf['intersection_length'] = resf.apply(lambda row: float(len(row.intersection)), axis=1)
        resf['union'] = resf.apply(lambda row: row[0].union(row[1]), axis=1)
        resf['union_length'] = resf.apply(lambda row: float(len(row.union)), axis=1)
        resf['issubset'] = resf.apply(lambda row: row[0].issubset(row[1]), axis=1)
        resf['jaccard'] = resf.apply(lambda row: row.intersection_length / row.union_length, axis=1)
        resf.sort_values(['jaccard', 'intersection_length'], inplace=True)
        return resf


    def frame2comp(self, df: pd.DataFrame) -> pd.DataFrame:
        names = df.index.names
        odf = df.reset_index()
        odf['oset'] = odf.apply(lambda row: frozenset(row[names]), axis=1)
        return odf

    def extract_formulas(self, df: pd.DataFrame,
                         threshold: int=5,
                         jaccard_min: int=0.5):
        falist = self.jaccard_frame(df)
        falist = falist.loc[falist.intersection_length>0]
        small_formulas = falist.loc[falist.issubset][0].unique()
        falist = falist.loc[~falist[0].isin(small_formulas)]
        discarded_formulas = falist.loc[falist.intersection_length<threshold ]
        resframe = pd.DataFrame(falist[(falist.intersection_length > 5) & (falist.jaccard)>jaccard_min]) #.intersection.value_counts())
        self.small_formulas = small_formulas
        self.extracted_formulas = resframe
        return {'small':small_formulas, 'frame':resframe}

    def layer_formula(self, df: pd.DataFrame) -> pd.DataFrame:
        """"this needs the output of extract_formulas"""
        valc = df.intersection.value_counts()
        rf = self.jaccard_frame(valc)
#        ljac = pd.DataFrame(rf[(rf.intersection_length > 0)].intersection.value_counts())
        nr = pd.merge(rf.loc[rf.intersection_length > 2], df, left_on=0, right_on='intersection')[
        ['intersection_x', 'intersection_length_x', '0_x',
         'intersection_y', '0_y']]
        nr = nr.drop_duplicates().rename(columns={'intersection_x': 'smallest_common',
                                              'intersection_length_x': 'small_common_length',
                                              '0_x': 'small_expansion',
                                              'intersection_y': 'larger_common',
                                              '0_y': 'larger_expansion'})
        return nr

    def df2layers(self):
        self.fml = self.extract_formulas(self.df)
        self.res = self.layer_formula(self.fml['frame'])
        cv = pd.DataFrame(self.res.smallest_common.value_counts())
        jf = self.jaccard_frame(cv)
        self.merged = pd.merge(self.fml['frame'], jf, left_on='intersection', right_on=1)
        mrgd = self.merged.groupby(['intersection', '0_x']).agg({'1_y': 'unique', '0_y': 'unique'})
        return mrgd
        # nnr = pd.merge(nr, falist, left_on='larger_expansion', right_on='intersection')[
        #     ['smallest_common', 'small_common_length', 'small_expansion', 'larger_common', 'larger_expansion',
        #      0, 1]]
        # # rf = pd.merge(nnr, falist, left_on='larger_expansion', right_on='intersection')[
        # #     ['smallest_common', 'small_common_length', 'small_expansion', 'larger_common', 'larger_expansion',
        # #      0, 1]]
        # full_trail = pd.merge(nnr, odf, left_on=1, right_on='oset').drop_duplicates()
        # grouped_trail = full_trail.groupby(['smallest_common', 'small_expansion', 'larger_expansion', 0,
        #                                     'oset'])
        # for i in range(5):
        #     odf[f'formula_{i}'] = ''
        # resultframe = pd.DataFrame()
        # for name, group in grouped_trail:
        #     select = odf.loc[odf.oset == name[-1]]
        #     for n in enumerate(name):
        #         select[f'formula_{n[0]}'] = '_'.join(n[1])
        #     if len(resultframe) == 0:
        #         resultframe = select
        #     else:
        #         resultframe = pd.concat([resultframe, select], ignore_index=True)
        # rf = resultframe[[c for c in odf.columns if c!='oset']]
        # return rf
        #

    def tagged_layers(self):
        mrgd = self.df2layers()
        names = self.df.index.names
        odf = self.df.reset_index()
        odf['original'] = odf.apply(lambda row: ' '.join(row[names]), axis=1)
        odf['oset'] = odf.apply(lambda row: frozenset(row[names]), axis=1)
        nnr = pd.merge(self.res, odf, left_on='larger_expansion', right_on='oset')[
            ['smallest_common', 'small_common_length', 'small_expansion', 'larger_common', 'larger_expansion', ]]
        nnr.groupby(['smallest_common']).agg({'larger_expansion': 'count'})
        self.full_trail = pd.merge(nnr, odf, left_on='larger_expansion', right_on='oset').drop_duplicates()
        grouped_trail = self.full_trail.groupby(['smallest_common', 'small_expansion', 'larger_expansion', 'oset'])
        self.gt = grouped_trail.agg({'original': 'first'})
        return self.gt

    def layer2orig(self):
        rgt = self.gt.reset_index()[['original', 'larger_expansion','small_expansion', 'smallest_common']].sort_values('original')
        for c in ['larger_expansion', 'small_expansion', 'smallest_common']:
            rgt[c] = tuple(rgt[c])
        return rgt

    def group_by_formula(self, formulalist: list=None):
        if len(self.gt)==0:
            self.tagged_layers()
        sm_c = self.gt.reset_index().set_index(['original', 'smallest_common'])
        grouped_by_sm_c = sm_c.groupby(['smallest_common', 'original']).agg({'small_expansion': 'unique'})
        extra_cols = grouped_by_sm_c.small_expansion.apply(pd.Series)
        exp_gr = pd.concat([grouped_by_sm_c, extra_cols], axis=1)
        exp_gr.fillna('', inplace=True)
        exp_gr.drop('small_expansion', axis=1, inplace=True)
        wel = exp_gr.loc[exp_gr.index.get_level_values(0).isin(formulalist)]
        niet = exp_gr.loc[~exp_gr.index.get_level_values(0).isin(formulalist)]
        result = {'matching': wel, 'nonmatching': niet}
        return result


from fuzzy_search.fuzzy_string import score_levenshtein_similarity_ratio
from string import Template


class Formula2Phrase(object):
    def __init__(self, formulaframe, label, frequency=0, unique=0, formulatype=''):
        self.unique = unique
        self.frequency = frequency
        self.formula = formulaframe
        self.label = label
        self.formulatype = formulatype
        self.cntrs = defaultdict(Counter)
        self.weighted = {}
        self.phrase = ''
        self.norm_phrase = ''
        self.variants = []
        self.ptempl = Template('START $rphrase END')
        self.VARS = {}
        self.nr = 0
        self.make_model()

    def make_model(self):
        self.frame2counter()
        self.formula_from_counter()
        self.make_phrase()
        self.make_variants()

    def frame2counter(self):
        for i in self.formula:
            wrds = list(i)
            for v in enumerate(wrds):
                try:
                    wrd = text_helper.normalise_spelling(v[1])
                except TypeError:
                    wrd = f'{v[1]}'
                wrd = wrd.strip()
                self.cntrs[v[0]].update([wrd])

    def formula_from_counter(self, threshold=3):
        weighted = {}
        for pos, vls in self.cntrs.items():
            tot = sum(vls.values())
            weighted[pos] = {'term': '', 'variants': []}
            mx = max(vls.items(), key=lambda x: x[1])
            if mx[1] > tot / threshold:
                weighted[pos]['term'] = mx[0]
                weighted[pos]['variants'] = [t[0] for t in vls.items() if t[0] != mx[0]
                                             and score_levenshtein_similarity_ratio(t[0], mx[0]) < 0.85]
            else:
                weighted[pos]['term'] = f'VAR{self.nr}'
                self.VARS[f'VAR{self.nr}'] = vls
                self.nr += 1
                # print(self.nr)
        self.weighted = weighted

    def make_phrase(self):
        rphrase = ' '.join([self.weighted[pos]['term'] for pos in range(len(self.weighted))])
        phrase = rphrase.strip()
        self.phrase = phrase
        return phrase

    def make_variants(self):
        # variants = []
        ps = list(range(len(self.weighted)))
        for pos in self.weighted:
            posities = (ps[:pos], ps[pos + 1:])
            # print(posities)
            if self.weighted[pos]['variants'] > []:
                for variant in self.weighted[pos]['variants']:
                    phrs = []
                    for psties in posities:
                        phrs.append(' '.join([self.weighted[pos]['term'] for pos in psties]))
                    rphrase = ' '.join([phrs[0], variant, phrs[1]])
                    self.variants.append(rphrase.strip())

    def normphrase(self):
        if not self.phrase:
            phrase = self.make_phrase()
        return self.ptempl.substitute(rphrase=self.phrase.strip())

    def phrasemodel(self, config):
        phrase = self.make_phrase()
        fphrase = [{'phrase': phrase,
                    'variants': self.variants,
                    'label': self.label}]

        pmodel = PhraseModel(model=fphrase, config=config)
        return (pmodel)

    def phrase_as_dict(self):
        record = {'phrase':self.phrase, 'variants':self.variants,
                  'uniques':self.unique, 'frequency':self.frequency}
        return record

    def terms_as_dict(self):
        record = {'terms':self.weighted,
                  'uniques':self.unique,
                  'frequency':self.frequency}
        return record
    def __repr__(self):
        return f'PHRASE: {self.phrase}'




def make_phrase(df, label='',formulatype=''):
    rs = FormulaStore()
    for i, row in df.iterrows():
        cl = list(row)
        freq = row['count']
        unique = row['nunique']
        if len(cl[0])>1:
            collated = df2collate(cl[0])
            truncated = collated[collated.columns[1:]].to_records()
            truncated = [list(t)[1:] for t in truncated]
            m = Formula2Phrase(truncated,
                               label=label,
                               formulatype=formulatype,
                               frequency=freq,
                               unique=unique)
            rs.update(m)

    return rs

class FormulaStore(object):
    def __init__(self):
        self.formulas = []
        self.types = []
    def add_formula(self, formula):
        if formula.formulatype not in self.types:
            self.types.append(formula.formulatype)
        self.formulas.append(formula)

    def update(self, formula):
        self.add_formula(formula)

    def serialize(self, types=[], how='phrases'):
        if types == []:
            types = self.types
        for t in types:
            if t not in self.types:
                print(f"{type} not in formula types")
        result = {}
        result = [f for f in self.formulas if f.formulatype in types]
        if how == 'terms':
            result = [f.terms_as_dict() for f in result]
        elif how == 'phrases':
            result = [f.phrase_as_dict() for f in result]
        return result
    #
    # def list_by_frequency(self, frequency=0, what='equal'):
    #     result = [f for f in self.formulas if f.frequency==frequency]

