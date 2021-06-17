import itertools
import json

import pandas as pd
from ..fuzzy.fuzzy_keyword_searcher import FuzzyKeywordSearcher

fuzzysearch_config = {
    "char_match_threshold": 0.8,
    "ngram_threshold": 0.6,
    "levenshtein_threshold": 0.5,
    "ignorecase": False,
    "ngram_size": 2,
    "skip_size": 2,
}

keywsearcher = FuzzyKeywordSearcher(config=fuzzysearch_config)
yesterdays = ['gisteren', 'eergisteren', 'voorleden donderdag',
              'voorleden vrijdagh', 'voorlede saterdagh']
searchstring = "Resolutien {g} ge-"
samenv = []
for g in yesterdays:
    samenv.append(searchstring.format(g=g))
extra = [
    'Raefslitien oilteren geno-hen ',
    'Resolutien voorlede Sa-B DD erdagh genoomen ',
    'Kelolutien g1-fteren genomen ',
    'Resolutien eerg1-teren genomen ',
    'Relolútien sifteren veno-men ',
    'Relolutief Miteref sênio-B ND men',
    'Refolutien voorleden Don-derdach genoomen ',
]
samenv.extend(extra)
keywsearcher.index_keywords(samenv)


# we want this in an object so that we can store some metadata on it and retrieve them any time
class TextWithMetadata(object):
    def __init__(self, searchobject):
        metadata = searchobject['_source']['metadata']
        self.line_coords = []
        self.text = self.find_preslst_text(searchob=searchobject)
        # lineob = self.find_preslst_text(searchob=searchobject)
        # if lineob:
        #    self.meeting_lines = lineob['lines']
        #     self.line_coords = lineob['coords']
        #     self.text = " ".join([meetingline['txt'] for meetingline in self.meeting_lines])
        self.invnr = metadata['inventory_num']
        # the following assumes the attendance list is on the first scan, but should really check offsets
        scan = [s for s in searchobject['_source']['annotations'] if s['type'] == 'scan'][0]['id']
        volgnr = scan.split('_')[-1]
        self.volgnr = int(volgnr)
        md = metadata.get('session_date')
        self.id = metadata.get('id')
        if md:
            self.meeting_date = md
        self.matched_text = MatchedText(self.text)
        self.matched_text.para_id = self.id
        # self.delegates = {'president': None,
        #                   'provinces': None,
        #                   'delegates': []}

    def find_preslst_text(self, searchob=None):
        """
        :param searchob: dictionary
        :return: dictionary: lines, coords
        commented out old text recognition code

        TODO: change to paragraph texts
        """
        result = {"text": ""}  # , "coords": []}
        # lines = []
        # columns = searchob['_source']['columns']
        # result = {"lines": [], "coords": []}
        # for column in columns:
        #     for tr in column['textregions']:
        #         meetinglines = tr['lines']
        #         for line in meetinglines:
        #             txt = line['text']
        #             lineid = line['metadata']['id']
        #             if txt:
        #                 resumptie = keywsearcher.find_candidates_new(txt,
        #                                             include_variants=True)
        #                 if resumptie:
        #                     return result
        #                 else:
        #                     result["coords"].append(line['coords'])
        #                     result["lines"].append({'lineid':lineid,
        #                                             'txt': txt or ''})
        #             if len(result["lines"]) > 30:
        #                 return result

        # al = [p for p in searchob['_source']['annotations'] if p['type'] == 'attendance_list'][0] # there should be only one
        al = [p for p in searchob['_source']['annotations'] if 'attendance_list' in p['id']][0]
        txt = searchob['_source']['text']
        start = al['start_offset']
        end = al['end_offset']
        # resumption = keywsearcher.find_candidates(txt, include_variants=True)
        # if resumption:
        #     moffset = resumption[0].get('match_offset') or 0
        #     if moffset > 0:
        #         if moffset < end:
        #             end = moffset
        text = txt[start:end]
        return text

    def make_url(self):
        """should we make the url not so hard-coded?"""
        if self.line_coords != []:
            x = min([c.get('left') or 0 for c in self.line_coords])
            w = max([c.get('width') or 0 for c in self.line_coords])
            y = min([c.get('top') or 0 for c in self.line_coords])
            h = sum([c.get('height') or 0 for c in self.line_coords])
            url = f"""https://images.diginfra.net/iiif/NL-HaNA_1.01.02/{self.invnr}/NL-HaNA_1.01.02_{self.invnr}_{self.volgnr:04d}.jpg/{x},{y},{w},{h}/full/0/default.jpg"""
            return url

    def get_meeting_date(self):
        return self.meeting_date

    def set_txt(self, txt):
        self.txt = txt

    def get_txt(self):
        return self.txt

    def get_spans(self):
        return self.matched_text.spans

    def get_fragments(self):
        return self.matched_text.get_fragments()

    def to_dict(self):
        result = {"metadata": {
            "inventory_num": self.invnr,
            # "meeting_lines": self.meeting_lines,
            "coords": self.line_coords,
            "text": self.text,
            "zittingsdag_id": self.id,
            "url": self.make_url()},
            "spans": self.matched_text.to_dict()}
        return result

    def to_json(self):
        result = self.to_dict()
        return json.dumps(result)

    def __repr__(self):
        return self.text  # should I change this to a dict representation?


class TypedFragment(object):
    def __init__(self, fragment=(), t="", pattern="", idnr=0):
        self.type = t
        self.begin = fragment[0]
        self.end = fragment[1]
        self.idnr = 0
        self.pattern = ""
        self.delegate_id = 0
        self.delegate_name = ""
        self.delegate_gewest = ""
        self.delegate_score = 0.0

    def __repr__(self):
        return "fragment type {}: {}-{}".format(self.type, self.begin, self.end)

    def __lt__(self, other):
        return self.begin < other

    def __le__(self, other):
        return self.begin <= other

    def __ge__(self, other):
        return self.begin >= other

    def __gt__(self, other):
        return self.begin > other

    def to_json(self):
        return json.dumps({'fragment': (self.begin, self.end),
                           'class': self.type,
                           'pattern': self.pattern})

    def set_pattern(self, pattern):
        self.pattern = pattern

    def set_delegate(self,
                     delegate_id=0,
                     delegate_name='',
                     delegate_score=0.0,
                     delegate_gewest=""):
        self.delegate_id = delegate_id
        self.delegate_name = delegate_name
        self.delegate_gewest = delegate_gewest
        self.delegate_score = delegate_score

    def get_delegate(self):
        delegate = {"id": self.delegate_id,
                    "name": self.delegate_name,
                    "score": self.delegate_score, }
        # "gewest": self.delegate_gewest}
        return delegate


defaultcolormap = schema = ['rgb(166,206,227)',
                            'rgb(31,120,180)',
                            'rgb(178,223,138)',
                            'rgb(51,160,44)',
                            'rgb(251,154,153)',
                            'rgb(227,26,28)',
                            'rgb(253,191,111)',
                            'rgb(255,127,0)',
                            'rgb(202,178,214)',
                            'rgb(106,61,154)',
                            'rgb(255,255,153)',
                            'rgb(177,89,40)']


class MatchedText(object):
    nw_id = itertools.count()

    def __init__(self,
                 item: str = '',
                 mapcolors: dict = {}):
        self.item = item
        self.spans = []
        self.delegates = []
        if mapcolors != {}:
            self.colormap = mapcolors
        else:
            self.colormap = self.mapcolors(colorschema=defaultcolormap)
        self.template = "<div>{}</div><hr>"
        self.mtmpl = """<span style="color:{color}">{txt}</span>"""
        self.para_id = ""

    def color_match(self, fragment, color):
        """return marked fragment from item on basis of span"""
        output = self.mtmpl.format(txt=fragment, color=color)
        return output

    def get_types(self):
        frgmnts = [f['type'] for f in self.get_fragments()]
        tps = list(set(frgmnts))
        return tps

    def mapcolors(self, colorschema=None):
        if colorschema is None:
            colorschema = defaultcolormap
        if colorschema:
            try:
                self.colormap = {k[1]: schema[k[0]] for k in enumerate(self.get_types())}
            except IndexError:  # too many types
                print("too many types")
            except KeyError:
                pass

    def serialize(self):
        """serialize spans into marked item"""
        fragments = self.get_fragments()
        # fragment += "[{}]".format(i.idnr) # for now
        outfragments = []

        for fragment in fragments:
            if fragment['type'] != 'unmarked':
                tcolor = self.colormap.get(fragment['type']) or 'unknown'
                ff = self.color_match(fragment['pattern'], color=tcolor)
                outfragments.append(ff)
            else:
                outfragments.append(fragment['pattern'])
        txt = " ".join(outfragments)  # may want to turn this in object property
        return txt

    def set_span(self,
                 span=(0, 0),
                 clas="",
                 pattern="",
                 delegate_id=0,
                 delegate_name='',
                 delegate_gewest=0,
                 score=0):

        this_id = next(self.nw_id)
        if not pattern:
            pattern = self.item[span[0]:span[1]]
        sp = TypedFragment(fragment=span,
                           t=clas,
                           pattern=pattern,
                           idnr=this_id)
        sp.set_delegate(delegate_id, delegate_name, delegate_gewest, score)
        begin = span[0]
        end = span[1]
        span_set = set(range(begin, end))
        comp = [s for s in self.spans if not set(range(s.begin, s.end)).isdisjoint(span_set)]
        if comp != []:
            for cs in comp:
                if not set(range(cs.begin, cs.end)).issubset(span):
                    self.spans.remove(cs)
                    self.spans.append(sp)
        else:
            self.spans.append(sp)
        # delegate = Delegate(pattern=pattern, delegate=delegate, spanid=this_id, score=score)

        return this_id

    def get_span(self, idnr=None):
        res = [i for i in self.spans if i.idnr == idnr]
        if len(res) > 0:
            return res[0]
        else:
            raise Exception('Error', 'no such fragment')

    def get_fragments(self):
        """the text in the form of a list of fragments"""
        end = 0
        fragments = []
        self.spans.sort()
        txt = self.item
        begin = 0
        end = 0
        if self.spans != []:
            for i in self.spans:
                begin = i.begin
                if end < i.begin - 1:  # we need the intermediate text as well
                    fragments.append({'type': 'unmarked',
                                      'pattern': txt[end:begin],
                                      'end': end,
                                      'begin': begin - 1})

                end = i.end
                fragment = {'type': i.type,
                            'idnr': i.idnr,
                            'pattern': txt[begin:end],
                            'begin': begin,
                            'end': end,
                            'delegate_id': i.delegate_id,
                            'delegate_name': i.delegate_name,
                            'delegate_gewest': i.delegate_gewest,
                            'delegate_score': i.delegate_score}
                fragments.append(fragment)
                end = i.end
        if end < len(txt):
            fragments.append({'type': 'unmarked',
                              'pattern': txt[end:begin],
                              'begin': end,
                              'end': len(txt)})

        return fragments

    def get_unmatched_text(self):
        """text represented as unmatched items"""
        fr = self.get_fragments()
        prezidents = [p for p in fr if p['type'] == 'president']
        if prezidents:
            prez = prezidents[0]
            begin = prez['begin']
        else:
            begin = 0
        fragments = []
        for fragment in fr:
            if fragment['type'] == 'unmarked' and fragment['end'] > begin:
                f = fragment['pattern']
                if f == '':
                    f = self.item[fragment['begin']:fragment['end']]
                fragments.append(f)

        return fragments

    def to_dict(self):
        result = [{"offset": s.begin,
                   "end": s.end,
                   "class": s.type,
                   "pattern": s.pattern,
                   "delegate_id": int(s.delegate_id),
                   "delegate_name": s.delegate_name,
                   "delegate_score": s.delegate_score}
                  for s in self.spans]
        return result

    def to_json(self):
        """make json representation"""
        result = self.to_dict()
        return json.dumps(result)

    def from_json(self, json):
        """construct spans from jsoninput.
        Json could have an item and fragments with type
        TODO: construct colormap from classes"""
        for item in json:
            self.set_span(item.get('fragment'),
                          item.get("class"),
                          item.get('pattern'),
                          item.get('delegate_name'),
                          item.get('delegate_id'),
                          item.get('delegate_score'))


class Heer(object):
    def __init__(self):
        self.searchterm = ''
        self.match_keyword = ''
        self.levenshtein_distance = 0
        self.proposed_delegate = None
        self.id = 0
        self.score = 0
        self.probably_junk = False

    def fill(self, candidate):
        try:
            self.proposed_delegate = candidate['name'].iat[0]
        except (KeyError, IndexError, TypeError):
            self.proposed_delegate = ''

        try:
            self.id = candidate['p_id'].iat[0]
        except (KeyError, IndexError, TypeError):
            try:
                self.id = candidate['id'].iat[0]
            except (KeyError, IndexError, TypeError):
                self.id = None  # pd.nan
        try:
            self.score = candidate['score'].iat[0]
        except (KeyError, IndexError, TypeError):
            #             self.score = 0.0
            pass

    def serialize(self):
        result = {'match_keyword': self.match_keyword,
                  'levenshtein_distance': self.levenshtein_distance,
                  'proposed_delegate': self.proposed_delegate,
                  'p_id': self.id,
                  'score': self.score,
                  'probably_junk': self.probably_junk
                  }
        return result


import uuid


class Variant(object):
    def __init__(self, rec, heer, idnr):
        self.form = rec[0]
        self.match = rec[1]
        self.score = rec[2]
        self.heer = heer
        self.heerid = idnr

    def __repr__(self):
        return self.form


class MatchHeer(object):
    def __init__(self, rec):
        self.name = rec['name']
        self.heerid = rec['id']
        self.references = {}
        self.matchkw = rec['m_kw']
        self.variants = {}
        self.variants['general'] = [Variant(v, self.name, self.heerid) for v in rec['variants']]
        self.uuid = None

    def set_uuid(self):
        if not self.uuid:  # set only once
            self.uuid = uuid.uuid4()

    def get_uuid(self):
        if not self.uuid:
            self.uuid = uuid.uuid4()
        return self.uuid

    def __repr__(self):
        return f"{self.heerid}: {self.name}"


def fill_heer(proposed_delegate):
    result = {}
    candidate = proposed_delegate
    # candidate['levenshtein_distance'] = candidate.name.apply(lambda x: score_levenshtein_distance_ratio(term1=proposed_delegate, term2=x))
    for key in ['p_id', 'id', 'score']:
        try:
            result[key] = candidate[key].iat[0]
        except (KeyError, IndexError):
            result[key] = pd.nan
    return result
