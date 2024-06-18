import os
import random
import re
import dateutil
import pandas as pd
import html
from names.common import *
from lxml import etree
from tarfile import TarFile, ReadError
from lxml.cssselect import CSSSelector

# from common import PREFIXES, POSTFIXES, VOORVOEGSELS, TUSSENVOEGSELS, ROMANS
# from common import ACHTERVOEGSELS, TERRITORIALE_TITELS, STOP_WORDS, R_STOPWORDS

# first we need selectors. For these files the following seem to be enough
sel1 = CSSSelector("fileDesc")
sel2 = CSSSelector("ref")
sel3 = CSSSelector("persName")
sel4 = CSSSelector("biography text")


"""
#test some
t = etree.parse("/Users/rikhoekstra/develop/namenindex/heinsius/out/2288.xml")
root = t.getroot()
ref = sel2(root)[0]
url = ref.get("target")
print(url.split('/')[-2:])
s4 = sel4(root)[0]
s4.text
"""


# pat = re.compile(r'(\(.*[0-9]+.*\))')
pat = re.compile(r'\((?P<group>.*?)([0-9]+)\)')

# byr = re.compile(r'\(?(?P<gebyr>[0-9]{4})-?(?P<dthyr>[.|†]*|[0-9]{4})\)')
byr = re.compile(r'\(?(?P<gebyr>\d{4})-?(?P<dthyr>\d{4}(?:[.|†])?\??)\)')


def spot_years(text):
    """print('new try with a function')
        print(spot_years('(1666-1729)'))
        print(spot_years('(?-1695)'))
        print(spot_years('(1695-)'))
        print(spot_years('(† 1725)'))
        print (spot_years(t1)) 
         """
    result = {'by': '',
              'dy': ''}
    byr = re.compile('\(([0-9]{4})') 
    eyr = re.compile("([0-9]{4})\)")
    byd = byr.search(text)
    if byd:
        by = byd.groups()[0]
        result['by'] = by
    eyrd = eyr.search(text)
    if eyrd:
        ey = eyrd.groups()[0]
        result['dy'] = ey
    return result



def get_events(infile):
    """get events such as birthday and death day from biodes
    ex: inf = etree.parse('/Users/rikhoekstra/develop/namenindex/raa/out/11.xml')
    """
    sel = CSSSelector('event')
    sel_p = CSSSelector('place')
    out = {}
    for item in sel(infile):
        t = item.attrib['type'] 
        out[t] = item.attrib['when']
        p = sel_p(item)
        if p is not []:
            p = p[0]
            out["{i}-{p}".format(i=t, p=p.tag)]= p.text

    if 'birth' in out.keys():
        try:
            b = out.get('birth').split('-')[0] # hope birthyears are all same format
            out['by'] = b
        except TypeError:
            pass
        try:
            d = out.get('death').split('-')[0]
            out['dy'] = d
        except TypeError:
            pass
    else:
        t = sel4(infile)
        t = '{}'.format(etree.tostring(t[0]))
#        print(t)
        out = spot_years(t)
    return(out)
        

def get_persnaam(infile):
    """get persname from biodes"""
    out = {}
    sel = CSSSelector('name')
    pnames = sel3(infile)[0]
    nms = sel(pnames)
    fullname = " ".join([n.text for n in nms])
    out['fullname'] = fullname
    for item in nms:
        t = item.get('type') 
        out[t] = item.text
    return out 





"""
oefenfile = etree.parse("/Users/rikhoekstra/develop/namenindex/heinsius/out/2288.xml")    
print(get_events(inf))
print(get_events(oefenfile))
"""


"""
test
vb = ['- hertog van, zie Johann Wilhelm.', '- hertog van, zie Johann Wilhelm.', 'zie ook Jansen', 'bla die bla']
for item in vb:
    try:
        print (pat.search(item).groups()[0])
    except AttributeError:
        pass
"""

# we'll create a new indexitem class with the things I need
# it'll take the xml as input and use cssselectors for getting data instead of arcane xpaths
# and steal from the old product what I can use



class IndexItem(object):
    def __init__(self, src='', content=''):
        """src is the name of an xmlfile with biodes data
        adapted this so that if there is no filename but a string, this will also work"""
        if src != '':
            self.src = etree.parse(src)
        else:
            self.src = etree.fromstring(content)

        #self.names = [] # don't need this
        self.geslachtsnaam = ''
        self.fullname = ''
        self.birth = None
        self.death = None
        self.by = 0 # birth year (or should this be a period with start and end)
        self.dy = 0 # death year
        self.biography = ''
        self.reference = ''
        self.populate()
        
    def populate(self):
        self.get_names()
        self.get_years()
        self.get_biography()
        self.get_reference()
        self.guess_geslachtsnaam()
        self.guess_normal_form()
        
    def get_biography(self):
        b = sel4(self.src)
        if len(b) > 0:
            bio = b[0].text
            bio = html.unescape(bio)
            self.biography = bio
        
    def get_names(self):
        """get names from biodes. adapted this from above"""
        out = {}
        sel = CSSSelector('name')
        pnames = sel3(self.src)[0]
        ptext = pnames.text
        nms = sel(pnames)
        self.fullname = " ".join([n.text for n in nms])
        for item in nms:
            t = item.get('type') 
            setattr(self, t, item.text)
        if self.fullname == '':
            if ptext != '':
                self.fullname = ptext
        
    def get_years(self):
        """get events such as birthday and death day from biodes"""
        sel = CSSSelector('event')
        sel_p = CSSSelector('place')
        for item in sel(self.src):
            t = item.attrib['type'] 
            try:
                setattr(self, t, item.attrib['when'])
            except KeyError:
                pass
            p = sel_p(item)
            try:
                p = p[0]
                plc = "{i}-{p}".format(i=t, p=p.tag)
                setattr(self, plc, p.text)
            except IndexError:
                pass

        if self.birth or self.death is not None:
            try:
                b = getattr(self, 'birth').split('-')[0] # hope birthyears are all same format
                setattr(self, 'by', b)
            except (TypeError, AttributeError) :
                pass
            try:
                d = getattr(self, 'death').split('-')[0]
                self.dy = d
            except (TypeError, AttributeError):
                pass
        else:
            self.get_yrs_from_txt()
            
    def get_yrs_from_txt(self):
        """try to get birth and death years from biography"""
        t = sel4(self.src)
        try:
            t = '{}'.format(etree.tostring(t[0]))
            out = spot_years(t)
        
            for key in out.keys():
                setattr(self, key, out[key])
        except IndexError:
            pass
        
    def get_reference(self):
        """try to get reference from 'zie verwijzing'"""
        pat = re.compile('.* zie (.*)')
        try:
            reference = pat.search(self.biography).groups()[0]
            reference = reference.strip()
            if reference[-1] == '.':
                reference = reference[:-1]
            self.reference = reference
        except AttributeError: # lame but useful
            pass

    def _guess_geslachtsnaam_in_string(self, s, hints=[]):
        """TODO strip achtervoegsels (like Junior)"""
        naam = s
        #xXXX dit is HEEL primitief

        #alle woorden die tussen haakjes staan zijn niet de achternaam, en filteren we er uit
        #(maar de haakjes in "Ha(c)ks" blijven staan)
        naam = re.sub(r'(?<!\w)\(.*?\)', '', naam)
        naam = naam.strip()


        if ', ' in naam: #als er een komma in de naam staat, dan is dat wat voor de komma staat de achternaam
            guessed_naam = naam.split(',')[0]
        elif 'startswithgeslachtsnaam' in hints: #er staat geen komma (ofzo) in, maar we weten wel dat de naam
            #met een achternaam begint: dan moet het wel de hele string zijn
            guessed_naam = naam
        elif re.match('[A-Z]\.', naam):
            #als de naam met een initiaal begint, fitleren we alle intiitale er uit, en is de rest de achternaam
            guessed_naam = naam[re.match('([A-Z]\.)+',naam).end():]

        elif ' ' in naam:
            #als er een spatie
            candidates = naam.split(' ')
            if candidates[-1] in ROMANS:
                #als de naam op ene ORMAN numeral eindigt, dan gaan we er van uit dat er geen achternaam is
                #(merk op dat dit mis gaat bij amerikaanse namen als "John Styuivesandt III"
                guessed_naam = ''
            else:
                guessed_naam = candidates[-1]
        else:
            guessed_naam = naam


        #een speciaal geval zijn namen van getrouwde dames, zoals 'Angela Boter-de Groot'
        if '-' in naam:
            for tussenvoegsel in TUSSENVOEGSELS:
                if '-%s' % tussenvoegsel in naam:
                    i = naam.find('-%s' % tussenvoegsel)
                    if i > -1:
                        guessed_naam = self._guess_geslachtsnaam_in_string(naam[:i], hints)
                        guessed_naam = guessed_naam + naam[i:]
        guessed_naam = self._strip_tussenvoegels(guessed_naam)
        return guessed_naam

    def _strip_tussenvoegels(self,s):
        s = s.strip()
        for tussenvoegsel in TUSSENVOEGSELS:
            if s.startswith(tussenvoegsel +  ' ' ):
                s = s[len(tussenvoegsel):]
                s = self._strip_tussenvoegels(s)
                break
        return s.strip()
    
    def serialize(self, exclude=[]):
        try:
            input = sel3(self.src.getroot())[0]
        except AttributeError:
            input = self.src
        parts = serialize(input)
        for item in exclude:
            parts = parts.replace(item, '')
        return parts
    
    def volledige_naam(self):
        return self.get_volledige_naam()

    def sort_key(self):
        """this value shoudl assign the name its proper place in the alfabet

        """
        base = u' '.join([s for s in [
            self.geslachtsnaam(),
            self.prepositie(),
            self.voornaam(),
            self.intrapositie(),
            self.postpositie(),
            self.serialize(self._root),
            ] if s])
        base = base.strip()
        base = base.lower()
        ignore_these = '()'
        for c in ignore_these:
            base = base.replace(c, '')
        for s in PREFIXES:
            if base.startswith(s):
                base = base[len(s):]

        for s in '?.-': #placeholders voor als we de achternaam niet kennen
            if base.startswith(s):
                base = chr(126) + base #het streepje - komt na alle andere letters

        base = base.strip()
        base = base[:40]
        assert type(base) == type(u'')
        return base

    def _geslachtsnaam(self):
        return self.geslachtsnaam
    
    def guess_geslachtsnaam(self, hints=[], change_xml=True):
        """probeer te raden wat de geslachtsnaam is
        en verander de gegevens xml boom naargelang

        bv:
        >>> naam.to_string()
        '<persName>Puk, Pietje</persName>
        >>> naam.guess_geslachtsnaam()
        >>> naam.to_string()
        '<persName><name type="geslachtsnaam">Puk</name>, Pietje</persName>

        hints: is een lijst met de volgende mogelijkheden:
             ['startswithgeslachtsnaam']

        >>> naam.fromstring('AAA BBB')
        >>> naam.guess_geslachtsnaam()
        'BBB'
        >>> naam.guess_geslachtsnaam(hints=['startswithgeslachtsnaam'])
        'AAA'
        """
        #self._root = etree.Element 
        if self.geslachtsnaam: #als we al een geslachtsnaam hebben, is er weinig te raden
            pass

        else:
            guessed_geslachtsnaam = self._guess_geslachtsnaam_in_string(self.fullname, hints)
            self.geslachtsnaam = guessed_geslachtsnaam #but guessed
        return self
    
    def guess_normal_form(self, change_xml=True, ):
        """return 'normal form' van de vorm "Geslachtsnaam, prepositie voornaam intrapostie, postpostiie"""
        #als we de achternaam niet expliciet is gegeven, dan doen we een educted guess
        try:
            self.src
        except AttributeError:
            self.from_string(self.xml)
        try:
            return self._normal_form
        except AttributeError:

            self.guess_geslachtsnaam(change_xml=change_xml)
            if self.geslachtsnaam:
                rest = self.serialize(exclude=[self.geslachtsnaam])
                rest = rest.replace(',', '')
                rest = rest.replace('  ', ' ')
                rest = rest.strip()
                if rest:
                    s = '%s, %s' % (self._geslachtsnaam(),  rest)
                else:
                    s = '%s' % (self._geslachtsnaam())
            else:
                s = self.serialize()

            #alles wat tussen haakjes staat gaat er uit
            s = re.sub('\(.*?\)', '', s)

            #alles wat in HOOFDLETTERS staat wordt Hoofdletters, behavle tussenvoegsels en romans
            result = ''
            for s in s.split():
                if s == s.lower():
                    pass
                elif s in ROMANS + TUSSENVOEGSELS:
                    pass
                elif u'.' in s:
                    pass
                else:
                    s =  s.capitalize()
                result += ' '  + s
            result = result.strip()
            self._normal_form = result
        return result


    def initials(self):

        s = self.guess_normal_form()
        return ' '.join([s[0] for s in re.findall('\w+', s) if s not in STOP_WORDS])
    
    def soundex_nl(self, s=None, length=4, group=1):
        if not s:
            s = self.guess_normal_form()
        cache_key = u'_soundex_nl_%s_%s_%s' % (s, length, group)
        try:
            return getattr(self, cache_key)
        except:
            pass

        #splits deze op punten, spaties, kommas, etc
        #ls = re.split('[ \-\,\.]', s.lower())
        s = s.lower()
        ls = re.findall('\w+', s, re.UNICODE)
        #filter een aantal stopwoorden

        ls = [s for s in ls if s not in STOP_WORDS]

        #filter initialen er uit, behalve eerste en laate, want die kunnen nog wel de achternaam zijn
        if len(ls) > 1:
            ls =[s for s in ls[:] if len(s) > 1]

        result  = [soundex_nl(s, length=length, group=group) for s in ls]
        try:
            setattr(self, cache_key, result)
        except UnicodeEncodeError:
            pass
            #XXXX there should really be no exceptions here
            #raise Exception('WTF?? %s' % cache_key)
        return result

"""
# test
i = IndexItem('/Users/rikhoekstra/develop/namenindex/raa/out/11.xml')
r = {k:vars(i)[k] for k in vars(i) if k not in ['src']}
print(r)

i = IndexItem("/Users/rikhoekstra/develop/namenindex/heinsius/out/2288.xml")
r = {k:vars(i)[k] for k in vars(i) if k not in ['src']}
print(r)


for f in randomfiles:
    i = IndexItem(f)
    r = {k:vars(i)[k] for k in vars(i) if k not in ['src']}
    print(r)

"""


def url_handler(term, baseurl):
    """converter for target url, 
    not yet used and not yet ok
    """
    
    baseurl = "http://resources.huygens.knaw.nl/retro/search/?{searchstring}" # daar gaan we nog s op kauwen
    searchstring = "SearchableText%3Austring%3Autf8={searchterm}"
    term = ""
    sstr = searchstring.format(searchterm=term)
    url = baseurl.format(searchstring=sstr)
    return url

def fl_to_rec(content, srcdir):
        i = IndexItem(content=content)
        r = {k:vars(i)[k] for k in vars(i) if k not in ['src', '_root']}
        r['collection'] = srcdir
        return r

def convert_sources_from_files(basedir, srcdir):
    fls = os.path.join(basedir, srcdir)
    rescoll = []
    for f in [fl for fl in os.listdir(fls) if '.xml' in fl.lower()]:
        with open(os.path.join(fls, f),'r') as flin:
            content = flin.read()
        r = fl_to_rec(content)
        rescoll.append(r)
    df = pd.DataFrame().from_records(rescoll)
    return df

def convert_sources_from_tar(basedir, srcdir):
    tar = TarFile.open(os.path.join(basedir, srcdir, "out.tar.gz"), "r:gz")
    rescoll = []
    for member in tar.getmembers():
        f = tar.extractfile(member)
        if f is not None:
            content = f.read()
            r = fl_to_rec(content, srcdir)
            rescoll.append(r)
    try:
        df = pd.DataFrame().from_records(rescoll)
        return df
    except TypeError:
        print(basedir, srcdir,rescoll)
        
dfs = None # placeholder because empty dataframes have no truth value

def convertall(basedir='', srcdirs=[]):
    for n in enumerate(srcdirs):
        item = n[1]
        print("converting: ", item)
        dirname = os.path.join(basedir, item)
        try:
            converted_sources = convert_sources_from_tar(basedir=basedir, srcdir=item)
        # else:
        #     convert_sources = convert_sources_from_files
            if n[0] == 0:
                print(f"dataframe created from {item}")
                df = converted_sources
            else:
                print("appending: ", item)
                dfss = converted_sources
                df = pd.concat([df, dfss], ignore_index=True, sort=False)
        except (FileNotFoundError,ReadError):
            print('cannot read', n)
            continue
    return df
    
    

