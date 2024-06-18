# coding=utf-8
from __future__ import absolute_import
from builtins import str
from builtins import chr
from builtins import range
from builtins import object
import re
from lxml import etree
from lxml.etree import Element, SubElement
from common import *
from similarity import soundex_nl

class Naam(object):
    """Representeert de naam van een persoon

    "naam" is ruim genomen; heeft ook methodes als "birth" en "death"



    """
    _constituents = [
        'prepositie',
        'voornaam',
        'intrapositie',
        'geslachtsnaam',
        'postpositie',
 #       'territoriale_titel',
    ]

    def __init__(self, naam=None, **args):
        self._root = None #etree.Element object met naamgegevens
        if naam:
            args['volledige_naam'] = naam
        if args:
            self.from_args(**args)



    def __str__(self):
        return "<Naam: '%s'>" %  self.to_string()

    def __repr__(self):
        return self.__str__()


    def x__eq__(self, other):
        return self.to_string() == other.to_string()
    def x__ne__(self, other):
        return self.to_string() != other.to_string()


    def from_args(self, **args):
        volledige_naam = args.get('volledige_naam',  '')
        self.sort_name = args.get('sort_name', None)


        #store the data as an xml Element
        ### Create an XML structure

        self._root = Element('persName')
        last_element = None
        if volledige_naam:
            self._root.text = volledige_naam
#            self._insert_constituent('geslachtsnaam', args.get('geslachtsnaam'))
            for c in self._constituents:
                self._insert_constituent(c, args.get(c))
#
            for c in ['territoriale_titel']:
                if args.get(c):
                    el = SubElement(self._root, 'name')
                    el.set('type', c)
                    el.text = args.get(c)
                    if last_element is not None:
                        last_element.tail = ',  '
                    else:
                        self._root.text +=  ', '
                    last_element = el
        else:
            for c in self._constituents:
                if args.get(c):
                    el = SubElement(self._root, 'name')
                    el.set('type', c)
                    el.text = args.get(c)
                    if last_element is not None:
                        last_element.tail = ' '
                    last_element = el


        return self

    def _insert_constituent(self, type, s):
        """tag the substring s of volledige_naam as being of type type

        arguments:
            type : one of ['prepositie', 'voornaam', etc]
            s : a string (must be a substring of self.volledige_naam())
        """
        if not s:
            return
        text = self._root.text
        new_el = Element('name')
        new_el.set('type', type)
        new_el.text = s

        candidate_strings = [self._root.text] + [n.tail for n in self._root]
        for i in range(len(candidate_strings)):
            text = candidate_strings[i]
            m = re.search(s, text)
            if m:
                if i == 0:
                    self._root.text = text[:m.start()]
                else:
                    self._root[i-1].tail = text[:m.start()]
                self._root.insert(i,new_el)
                new_el.tail = text[m.end():]
                return
        assert 0, 'The string %s (of type %s) should be a part of the volledige naam %s' % (s, type, candidate_strings)
    def from_string(self, s):
        self.from_xml(etree.fromstring(s))
        return self

    def from_soup(self, s, hints=[]):
        """als de input echt een troepje is, gebruik dan deze functie om de naam de instantieren"""
        self.source_string = s
        self.birth = None
        self.death = None
        s = coerce_to_unicode(s)
        s = s.strip()



        #gevallen als Jan klaasen (123-345)
        #kijk of er jaartallen, tussen haakjes, staan
        if s.endswith(')') and s.find('('):
            laatste_haakje = s.rfind('(')

            tussen_haakjes = s[laatste_haakje+1:-1]
            for splitter in ['-', '\u2011', u'‑']:
                if splitter in tussen_haakjes:
                    first, last = tussen_haakjes.split(splitter)

                else:
                    first = None
                    last = tussen_haakjes
                #XXX this is not really finished
                if last.isdigit():
                    self.birth = first
                    self.death = last

                    s = s[:laatste_haakje].strip()
                for att in ['birth', 'death']:
                    d = getattr(self, att)
                    if d:
                        for c in [u'±']:
                            if d.startswith(c):
                                    d = s[len(c):]
                        if not TypeChecker().is_date(d):
                            d = None
                    setattr(self, att, d)
        #territoriale titels
        self.territoriale_titel = None

        for t in TERRITORIALE_TITELS:

            if t in s:
                self.territoriale_titel = s[s.find(t):]
                self.territoriale_titel= self.territoriale_titel.strip()
                s = s[:s.find(t)]
        s = s.strip()
        for c in ',;:':
            if s.endswith(c):
                s = s[:-len(c)]
        s = s.strip()

        self.from_args(
           volledige_naam = s,
           # territoriale_titel=territoriale_titel,
            )
        self.guess_geslachtsnaam(hints=hints)

        return self

    def from_xml(self, element):
        return self.from_element(element)

    def from_element(self, element):
        """element is een etree.Element instance"""
        self._root = element
        return self




#    def to_dict(self):
#        args = {}
#        for c in self._constituents:
#            args[c] = [el.text for el in element.xpath('./name[@type="%s"]' % c)]
#        for k in args.keys():
#            setattr(k, args[k])
#        return args

    def get_volledige_naam(self):
        s = self.serialize(self._root).strip()
        return s

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


        #XXX use "to_ascii" dictionary
        base = to_ascii(base)

        base = base.strip()
        base = base[:40]
        assert type(base) == type(u'')
        return base


    def prepositie(self):
        result = self._root.xpath('./name[@type="prepositie"]/text()')
        result = ' '.join(result)
        return result

    def voornaam(self):
        result = self._root.xpath('./name[@type="voornaam"]/text()')
        result = ' '.join(result)
        return result

    def intrapositie(self):
        result = self._root.xpath('./name[@type="intrapositie"]/text()')
        result = ' '.join(result)
        return result

    def geslachtsnaam(self):
        result = self._root.xpath('./name[@type="geslachtsnaam"]/text()')
        result = u' '.join(result)
        return result

    def postpositie(self):
        result = self._root.xpath('./name[@type="postpositie"]/text()')
        result = u' '.join(result)
        return result

    def territoriale_titel(self):
        result = self._root.xpath('./name[@type="territoriale_titel"]/text()')
        result = u' '.join(result)
        return result

    def serialize(self, n = None, exclude=[]):
        if n is None:
            n = self._root

        return serialize(n, exclude=exclude).strip()
    def _guess_geslachtsnaam_in_string(self, s, hints=[]):
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
        if self.geslachtsnaam(): #als we al een geslachtsnaam hebben, is er weinig te raden
            pass

        elif self._root.text and self._root.text.strip(): #we rpobern alleen te raden als er "losse" tekst is
            orig_naam = self._root.text
            guessed_geslachtsnaam = self._guess_geslachtsnaam_in_string(orig_naam, hints)

            if guessed_geslachtsnaam and change_xml:
                guessed_geslachtsnaam = guessed_geslachtsnaam.strip()
                el_name = SubElement(self._root, 'name')
                el_name.set('type','geslachtsnaam')
                el_name.text = guessed_geslachtsnaam
                idx = orig_naam.rfind(guessed_geslachtsnaam)
                self._root.text, el_name.tail =  orig_naam[:idx], orig_naam[idx + len(guessed_geslachtsnaam):]

        else: # de ovrige gevallen (alleeen een voornaam, bv) laten we de geslachtsnaam leeg
                pass
        return self


    def guess_normal_form(self, change_xml=True, ):
        """return 'normal form' vna de vorm "Gesalchtsnaam, prepositie voornaam intrapostie, postpostiie"""
        #als we de achternaam niet expliciet is gegeven, dan doen we een educted guess
        try:
            self._root
        except AttributeError:
            self.from_string(self.xml)
        try:
            return self._normal_form
        except AttributeError:

            self.guess_geslachtsnaam(change_xml=change_xml)
            if self.geslachtsnaam():
                rest = self.serialize(exclude=['geslachtsnaam'])
                rest = rest.replace(',', '')
                rest = rest.replace('  ', ' ')
                rest = rest.strip()
                if rest:
                    s = '%s, %s' % (self.geslachtsnaam(),  rest)
                else:
                    s = '%s' % (self.geslachtsnaam())
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

    def to_xml(self):
        if not hasattr(self,'_root') and hasattr(self, 'xml'):
            self.from_string(self.xml)
        return self._root

    def to_string(self):
        s = etree.tounicode(self.to_xml(), pretty_print=True)
        s = str(s)
        s = s.strip()
        return s

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
    def _name_parts(self):
        s = self.serialize()
        return re.findall('\S+', s)

    def contains_initials(self):
        #all parts of the name are initials, except  "geslachtsnaam" or ROMANS or TUSSENVOEGSELS
        g = self.guess_geslachtsnaam().geslachtsnaam()
        for p in self._name_parts():
            if p.endswith('.') and p not in VOORVOEGSELS + TERRITORIALE_TITELS:
                return True
#            if (p in g) or p.endswith('.') or p.endswith(',') or p in TUSSENVOEGSELS:
#                pass
#           else:
#               return False
        return False
