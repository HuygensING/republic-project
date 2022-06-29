# Laad de benodigde modules in

import os
import re
import json

from collections import Counter
from collections import defaultdict
from typing import Union, List, Iterable, Dict
import langid
import pandas as pd
import json
from analiticcl import VariantModel, Weights, SearchParameters
from fuzzy_search.fuzzy_string import score_levenshtein_similarity_ratio
from republic.helper.similarity_match import FuzzyKeywordGrouper
import republic.model.republic_document_model as rdm

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
       'van': ['vande', 'vander', 'vanden', ],
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
             'lidwoord': ['dien', 'de', 'het', 'een', 'gene', 'geene', 'eene', 'een'],
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

def normalize(x, rev_kws=rev_kws):
    """for normalizing words in a dataframe"""
    result = x or ''
    result = re.sub("""[,\.„—\'\"]+""",'',result)
    r = rev_kws.get(result)
    if r:
        result = r
    else:
        result = (f'<{result}>')
    return result

# def row_norm(row):
#     return list(map(norm_df, row))



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
#        self.resolutions = [r for r in self.resolutions.values() if len(resolutions[r].paragraphs)>0] # filter out accidental empty paragraphs. Perhaps we should report this


    def resolutions2kwic(self):
        """This is based on analitticl.
        Perhaps make it more versatile to also work with FuzzySearch"""
        xresult = []
        for rslt in self.searchresult: #filter_result:
            r = [r for r in self.resolutions if r.id==rslt][0]
            id = r.metadata['id']
            text = '\n'.join([p.text for p in r.paragraphs if langid.classify(p.text)[0]=='nl'])
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
                    xresult.append((id, v['input'], fnd, context, item['prefix'], item['suffix']))
        return xresult

    def res2frame(self):
        result = self.resolutions2kwic()
        self.df = pd.DataFrame(result, columns=['resolutie', 'keyword', 'found', 'context', 'prefix', 'suffix'])

    def stratified_df(self, what='context', norms: Dict={}, with_kw=False ):
        """should this get more configurable
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
            self.df[str(c)+'_norm'] = self.df[c].apply(lambda x:normalize(x,rev_kws=rev_kws))
        if with_kw is True:
            flds = ['keyword'] + flds
        strati_df = self.df.groupby(flds).agg({"resolutie":'count'}).sort_values('resolutie',ascending=False)
        return strati_df
