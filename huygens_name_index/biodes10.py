import types
import tempfile
import atexit
import tarfile
import shutil
import os
import logging

from lxml import etree
from lxml.etree import Element, SubElement, XMLSyntaxError
from xml.sax.saxutils import unescape

from names import name

Name = name.Name

NAAM_TYPEN = ['prepositie', 'voornaam', 'intrapositie', 'geslachtsnaam', 'postpositie']

#arguments can be passed both in Dutch as in English
TRANSLATIONS = {
#       'bioport_id',
#        'local_id',
        'titel_biografie': 'title_biography',
        'naam': 'name',
        'auteur': 'author',
        'beroep': 'occupation',
        'laatst_veranderd': 'last_changed',
        'publicatiedatum': 'publication_date',
        'geboortedatum': 'birth_date',
        'geboortedatum_tekst': 'birth_date_text',
        'geboorteplaats': 'birth_place',
        'sterfdatum': 'death_date',
        'sterfdatum_tekst':'death_text',
        'sterfplaats':'death_place',
        'geslacht':'sex',
        'illustraties':'illustrations',
#        'figures', #a list of pairs of strings ('URL', 'caption')
        'namen':'names',
        'namen_en':'names_en',
        'tekst': 'text', #text of the biography
        'rechten':'rights',
#        'meta', #any information that is not strictly part of the biographical info, but useful for the system
        'naam_publisher':'name_publisher',
        'url_biografie':'url_biography',
#        'url_publisher':'url_publisher',
        }
        
        
class BDException(Exception):
    pass

class BDTypeError(BDException):
    pass

def _translate(k):
    return TRANSLATIONS.get(k)

def is_date(s):
    """return True if s represents a valid date, False otherwise
    
    dates are of the form 
	    yyyy-mm-dd
	    yyyy-mm
	    yyyy
       
    """
    if not s:
        return 0
    if s.startswith('-'):
        ymd = s[1:]
#        bce = True
    else:
#        bce = False
        ymd = s 
    if len(ymd.split('-')) == 3:
        y, m, d = ymd.split('-')
    elif len(ymd.split('-')) == 2:
        y, m = ymd.split('-')
        d = '01' 
    elif len(ymd.split('-')) == 1:
        y = ymd
        d = '01'
        m = '01' 
    else: 
        return False
    
    if (y.isdigit() and m.isdigit() and d.isdigit() and len(y) == 4 and len(m) == 2 
        and len(d)  == 2 and int(m) > 0 and int(m) < 13 and int(d) > 0 and int(d) < 32): # and int(y) < 2100:
        return True

    return False

def is_url(s):
    if s.startswith('http:') or s.startswith('https:') or s.startswith('file:'):
        return True
    else:  
        return False


class BioDesDoc:
    """
    A BioDes document

    >>> doc = BioDesDoc()
    >>> #create a file from some url
    >>> doc.from_url('http://somedoc.xml')
    <BioDesDoc ..>
    >>> doc.to_dict()
    <dictionary object with some essentiel info from the document in dictionary form>
    >>> d['geboortedatum']
    '2000-02-02'
    >>> #this will output a list of 6-tuples: the names
    >>> d['namen']
    [('Jelle Gerbrandy', '', 'Jelle', '', 'Gerbrandy', '', 'Gerbrandy, Jelle')]
    
    
    >>> doc = BioDesDoc()
    >>> doc.from_args(naam='Giampaolo', url_biografie='http://lksdfjlksadfj', ..... )
    >>> doc.to_file('path/to/document.xml')
    
    
    >>> doc.from_args(name='Giampaolo', url_biography='http://lksdfjlksadfj', ..... )
    
    """ 
    __version__ = '1.0.1'
    possible_arguments = [
            'bioport_id',
            'local_id',
            'titel_biografie', #title_biography
            'naam',#name
            'auteur', #author
            'beroep', #profession
            ] + NAAM_TYPEN + [
            'laatst_veranderd', #last_changed
            'publicatiedatum', #publication_data
            'geboortedatum', #birth_date
            'geboortedatum_tekst', #birth_text
            'geboorteplaats', #birth_place
            'sterfdatum', #death_
            'sterfdatum_tekst',
            'sterfplaats',
            'geslacht',
            'illustraties', #a list of URLs - please use "figures" instead
            'figures', #a list of pairs of strings ('URL', 'caption')
            'namen',
            'namen_en',
            'tekst', #text of the biography
            'rechten',
            'xml_source', #this is ignored
            'meta', #any information that is not strictly part of the biographical info, but useful for the system
            'adel',
            'adelspredikaat',
            'heerlijkheid',
            'geboortejaar',
            'onbepaaldgeboortedatum',
            'overlijdensjaar',
            'onbepaaldoverlijdensdatum',
            'opmerkingen',
            'periode',
            'overlijdensdag',
            'overlijdensmaand',
            'academischetitel',
            'adellijketitel'
            ]
    _mandatory_arguments = [
            'naam_publisher',
            'url_biografie',
            'url_publisher',                    
    ]
    possible_arguments = possible_arguments + _mandatory_arguments
    possible_arguments += [TRANSLATIONS.get(k) for k in possible_arguments if TRANSLATIONS.get(k)]
    possible_arguments.sort()
    #the following list shows where the key is stored
    #the format is:
    #     -id of the key
    #    - xpath to get the value of the key
    #    - type of the value
    _keys = [
        ('url_publisher', './fileDesc/publisher/ref/attribute::target', 'string'),
        ('url_biografie', './fileDesc/ref/attribute::target', 'string'),
        ('titel_biografie','./fileDesc/title/text()', 'string'),
        ('naam_publisher', './fileDesc/publisher/name/text()', 'string'),
        ('auteur','./fileDesc/author/text()', 'list'), 
        ('bioport_id','./person/idno[@type="bioport"]/text()', 'list'),
        ('local_id','./person/idno[@type="id"]/text()', 'string'),
        ('beroep','./person/state[@type="occupation"]/text()', 'list'),
        ('laatst_veranderd','./fileDesc/revisionDesc/changed/attribute::when', 'date'),
#        'publicatiedatum',
        ('geboortedatum',       './person/event[@type="birth"]/attribute::when', 'date'),
        ('geboortedatum_tekst', './person/event[@type="birth"]/date/text()','string'),
        ('geboorteplaats',      './person/event[@type="birth"]/place/text()', 'string'),
        ('sterfdatum',          './person/event[@type="death"]/attribute::when', 'date'),
        ('sterfdatum_tekst',    './person/event[@type="death"]/date/text()','string'),
        ('sterfplaats',         './person/event[@type="death"]/place/text()', 'string'),
        ('geslacht',            './person/sex/attribute::value', 'string'),
        ('illustraties',        './/graphic/attribute::url', 'list'),
        ('tekst',                './biography/text/text() | ./text/text()', 'string'),
#        'namen', #namen en naamsvarianten worden als 6-tuples uitgevoerd: (volledige naam, pre, voor, intra, geslacht, post)
#        'namen_en',
            ] 
    _key_mapping_nl = {}
    _key_mapping_en = {}
    for key in _keys:
        _key_mapping_nl[key[0]] = dict(list(zip(('path', 'type'), key[1:])))
        _key_mapping_en[_translate(key[0])] = dict(list(zip(('path', 'type'), key[1:])))
    _key_mapping = _key_mapping_nl
    _key_mapping.update(_key_mapping_en)
    
    
        
    def __str__(self):
        return '<BioDesDoc version %s>' % self.__version__

    def __repr__(self):
        return self.__str__()

    def __init__(self):
        self.root =  None

    def from_element(self, element):
        """Create a BioDesDoc from an lxml.Element"""
        
        self.root = element
        return self
    from_xml = from_element
    
    def from_dict(self, d):
        """Create a BioDesDoc from a dictionary of arguments"""
        return self.from_args(**d)
    
    def from_string(self, s):
        """Create a BiodesDoc from a string"""
        self.root = etree.fromstring(s)
        return self 
    
    from_document = from_string
    
    
    def from_url(self, url):
        """Create a BioDesDocument from a file
        
        arguments:
            url - either an URL or a path to a local file
        returns:
            self
        """
        try:
            parser = etree.XMLParser(no_network=False) 
            self.root = etree.parse(url, parser)
        except XMLSyntaxError as error:
#            print 'Error parsing %s' % url
            raise error
        return self
    
    def get_element_person(self):
        return self.get_root().find('person')
    
    def get_element_filedesc(self):
        return self.root.find('fileDesc')
    
    def from_args(self, **args):
        """create an xml file in the biodes format with content from the 
        given arguments
        """
        self._set_up_basic_structure()
        filedesc = self.get_element_filedesc()
        for k in self._mandatory_arguments:
            if k not in args and TRANSLATIONS.get(k) not in args:
                raise ValueError('"%s" is a mandatory argument' % TRANSLATIONS.get(k))
            
        if ('naam' in args
            and 'geslachtsnaam' in args
            and 'name' in args
            and 'namen' in args 
            and 'names' in args):
                raise ValueError('provide either a "naam", "name", "names" or "namen" argument' )
            
        for k in list(args.keys()):
            if k not in self.possible_arguments:
                raise ValueError('"%s" is not a valid argument; valid arguments are: %s' 
                                 % (k, self.possible_arguments))
        #set up basic structure
            self.element_filedesc = filedesc
        #INFO OVER BIOGRAFIE
        self.set_value(**args)
        #titel_biografie
        return self
    
    def is_date(self, s):
        return is_date(s)
    
    def get_value(self, k, default=None):
        """  """
        if k not in self.possible_arguments:
            raise ValueError('"%s" is not a valid argument; choose one of the following: %s' 
                             % (k, self.possible_arguments))
        if k in ('namen', _translate('namen')):
            return self.get_namen()
 
        if k in self._key_mapping:
            path = self._key_mapping[k]['path']
            type = self._key_mapping[k]['type']

            el = self.get_root()
            found_items = el.xpath(path)
            if found_items:
                if type in ['string', 'date']:
                    if k in ['tekst', 'text']:
                        return unescape(str(found_items[0]))
                    return str(found_items[0])
                elif type == 'list':
                    return [str(s) for s in found_items]
                else:
                    raise TypeError('unknown type %s' % type)
            return default
        return self.to_dict().get(k, default)

    def set_value(self, k=None, v=None, **args):
        """
        """
        if k and k not in self.possible_arguments:
            raise ValueError('This is not a valid argument: %s.\nValid arguments are: %s' 
                              % (k, self.possible_arguments))
        if k:
            args[k]=v
        filedesc = self.get_root().find('fileDesc')
        person = self.get_root().find('person')
       
        k = 'titel_biografie'
        s = args.get(k, args.get(_translate(k)))
        el = self.get_root().xpath('./fileDesc/title')
        if el:
            el = el[0]
        else:
            el =SubElement(filedesc, 'title')
        el.text = s

        #auteur van de biografie
        k = 'auteur'
        ls = args.get(k, args.get(_translate(k)))
        if ls:
            if not type(ls) == type([]):
                ls = [ls]
            for s in ls:
                SubElement(filedesc, 'author').text = s

        k = 'bioport_id'
        ls = args.get(k, args.get(_translate(k), []))
        if type(ls) != type([]):
            ls = [ls]
        for s in ls:
            self.set_idno(s, type='bioport')
        k = 'local_id'
        if args.get(k):
            self.set_idno(args.get(k), type='id')
        else:
            if hasattr(self, 'id') and not self.get_idnos(type='id'):
                self.set_idno(self.id, type='id')
        #url_biografie
        k = 'url_biografie'
        s = args.get(k, args.get(_translate(k)))
        if s is not None:
            if not is_url(s):
                raise ValueError('The value for %s is not a url (but %s)' % (k, s))
            el = self.get_root().find('fileDesc/ref')
            if el is None:
                el = SubElement(filedesc, 'ref')
#            print args[k]
            el.set('target', s) 
            

        #publicatiedatum van de biografie
        k = 'publicatiedatum'
        s = args.get(k, args.get(_translate(k)))
        if s:
            if not is_date(s):
                raise ValueError('The value for %s must be of the form yyyy-mm-dd (e.g. 2008-02-03. (got %s instead)' % (k, s))
            SubElement(filedesc, 'date').set('when', s)

        #laatst veranderd datum van de biografie
        k = 'laatst_veranderd'
        s = args.get(k, args.get(_translate(k)))
        if s:
            if not is_date(s):
                raise ValueError('The value for %s is not a date (but %s)' % (k, s))
            revisiondesc = SubElement(filedesc, 'revisionDesc')
            SubElement(revisiondesc, 'changed').set('when', s)


        #INFO ABOUT PUBLISHER
        publisher = self.get_root().find('fileDesc/publisher') 
        if publisher is None:
            publisher = SubElement(filedesc, 'publisher')
            
        #naam_publisher
        k = 'naam_publisher'
        name_publisher = args.get(k, args.get(_translate(k)))
        if name_publisher is not None:
            el =  publisher.find('name') 
            if el is None:
                el = SubElement(publisher, 'name')
            el.text = name_publisher 

        #url publisher
        k = 'url_publisher'
        s = args.get(k, args.get(_translate(k)))
        if s is not None:
            if s and not is_url(s):
                raise ValueError('The value for %s is not a url' % (k, s))
            el =  publisher.find('ref') 
            if el is None:
                el = SubElement(publisher, 'ref')
            el.set('target', s)


    #ILLUSTRATIES
        #illustratie
        self._add_illustraties(**args)

    #FIGURES
        #figures
        for url, head in args.get('figures', []) :
            self._add_figure(url=url, head=head)
    #INFO OVER PERSOON

        #onderdelen van namen
        i = 0
        #er zijn drie mogelijkhen:
        # we hebben neen naam en geen onderverdeling
        # 2. we hebben een naam en een achternaam
        # 3. we hebben onderverdeling maar geen naam
        #de rest mag niet

        #naam
        k = 'naam'
        s = args.get(k, args.get(_translate(k)))
        if s is None:
            persname = None
        elif isinstance(s, Name):
            persName = s.to_xml()
            person.append(persName)
        else:
            persname = SubElement(person, 'persName')
            persname.text = s
    
        naam = args.get(k, args.get(_translate(k)))
        el = None
        for k in NAAM_TYPEN:
            s = args.get(k, args.get(_translate(k)))
            #let op volgorde subelementen 
            if s:
                if naam and k == 'geslachtsnaam':
                    naam = persname.text
                    if not s in naam:
                        # XXX - needs translation
                        raise BDException('U heeft zowel een "naam" als een "%s" gegeven. In dat geval moet de %s onderdeel zijn van de naam. Dat is niet het geval' % (k,k)) 
                    i = naam.find(s)
                    persname.text = naam[:i]
                    el = SubElement(persname, 'name')
                    el.tail = naam[i+len(s):] 
                elif naam:
                    # XXX - needs translation
                    raise BDException('U heeft zowel een "naam" als een "%s" gegeven, en dat mag niet')
                else:
                    if persname is None:
                        persname = SubElement(person, 'persName')
                    el = SubElement(persname, 'name')
                    el.tail = ' '
                try:
                    el.text = s
                except:
                    raise ValueError(' This value for %s? %s' % (k,s))
                el.set('type', k)
                i += 1 

        if el != None and el.tail  ==' ': 
            el.tail = '' 

            #namen
        #dit is een soort shortcut argument om namen toe te voegen
        #in een lijst zoals:
        #['Jan K.', ('', 'Jan', '', 'K.', ''), ('dr.','Jan', 'van', 'K', 'graaf van X')]

        k = 'namen'
        ls = args.get(k, args.get(_translate(k)))
        if ls:
            if not self.is_list(ls):
                raise BDException("Het argument 'namen' moet een lijst zijn.\nBijvoorbeeld ['Jan K.', ('', 'Jan', '', 'K.', ''), ('dr.','Jan', 'van', 'K', 'graaf van X')]\n Dus niet: %s" % ls)
            
            #remove all existing names
            for n in self.xpath('./person/persName'):
                n.getparent().remove(n)
                
            for s in ls:
                self._add_a_name(s)

        k = 'namen_en'
        ls = args.get(k, args.get(_translate(k)))
        if ls:
            if not self.is_list(ls):
                raise BDException("Het argument 'namen_en' moet een lijst zijn.\nBijvoorbeeld [('Jan K.', ('', 'Jan', '', 'K.', ''), ('dr.','Jan', 'van', 'K', 'graaf van X')]")

            for s in ls:
                self._add_a_name(s, lang='en')


        #geslacht
        k = 'geslacht'
        s = args.get(k, args.get(_translate(k)))
        if s is not None:
            if not s: 
                s = ''
            if s not in ['', 0, '0', 1, '1', 2, '2']:
                msg = "sex value must be 0 (unknown), 1 (male) or 2 (female). Got: %s instead" % repr(k)
                raise ValueError(msg)
                
            s = str(s)
            els = self.xpath('./person/sex')
            if len(els):
                el = els[0]
            else:
                el = SubElement(person, 'sex')
            el.set('value', s)


        #BIRTH
        k = 'geboortedatum'
        when = args.get(k, args.get(_translate(k)))
        k = 'geboorteplaats'
        place = args.get(k, args.get(_translate(k)))
        k = 'geboortedatum_tekst'
        date_text = args.get(k, args.get(_translate(k)))
        if when is not None or place is not None or date_text is not None:
            self.add_or_update_event(
                'birth', 
                when=when,
                place=place,
                date_text =date_text,
                )
        
        #DEATH
        k = 'sterfdatum'
        when = args.get(k, args.get(_translate(k)))
        k = 'sterfplaats'
        place = args.get(k, args.get(_translate(k)))
        k = 'sterfdatum_tekst'
        date_text = args.get(k, args.get(_translate(k)))
     
        if when is not None or place is not None or date_text is not None:
            self.add_or_update_event(
                'death', 
                when=when,
                place=place,
                date_text =date_text,
                )

        #beroep
        k = 'beroep'
        ls = args.get(k, args.get(_translate(k)))
        if type(ls) in (str,):
            ls = [ls]
        if ls:
            for s in ls:
                self.add_state(type='occupation', text=s)

        #claim_to_fame
        k = 'claim_to_fame'
        ls = args.get(k, args.get(_translate(k)))
        if type(ls) == type(''):
            ls = [ls]
        if ls:
            for s in ls:
                occupation = SubElement(person, 'occupation')
                occupation.text = s

        #interne bioport identifier
        k = 'bioport_id'
        #XXX todo
        
        k = 'tekst'
        s = args.get(k, args.get(_translate(k)))
        
        if s:
            el = self.get_element_biography().find('text')
            if el is None:
                el = SubElement(self.get_element_biography(), 'text')
            el.text = s
        
        k = 'rechten'
        s = args.get(k, args.get(_translate(k)))
        self._add_rights(s)        
        self._add_meta(args.get('meta')) 
        
    def set_idno(self, s, type):
    
        s = str(s)
        if self.get_idno(type=type) == s:
            #we already have this idno registered
            return
        
        new_el = SubElement(self.get_element_person(), 'idno')
        new_el.text = s
        new_el.set('type', type)   
    
    def get_idno(self, type='id'):
        ls = self.get_idnos(type=type)
#        assert len(ls) <= 1, ls
        if ls:
            return ls[-1]
        else:
            return None 
        
    def get_idnos(self, type='id'):
        if type:
            ls = self.xpath('person/idno[@type="%s"]' % type)
        else:
            ls = self.xpath('person/idno')
        return [n.text for n in ls]
    
    def to_string(self):
        if self.get_root() is None:
            return ''

        return etree.tostring(self.get_root(), pretty_print=True)

    def to_file(self, fn):
        open(fn, 'wb').write(self.to_string())

    def get_root(self):
        return self.root
    
    def to_dict(self):
        """returns a dictionary with (most of) the data contained  in this 
        Biodes docuemnt structured in dictionary format
        
        (WARNING: the information returned can be incomplete (that is, 
        not all information from the originel XML structure  finds its way
        into the dictionary). The XML source (self.root) remains the 
        uathoratative source.
        """
        keys = self._keys
        result = {}
        el = self.get_root()
        if el is None:
            return {}
        result['xml_source'] = etree.tostring(el)

        for k, path, type in keys:
            found_items = el.xpath(path)
            if found_items:
                if type in ['string', 'date']:
                    result[k] = found_items[0]
                elif type == 'list':
                    result[k] = [str(s) for s in found_items]
                else:
                    raise TypeError('unknown type %s' % type)

        #namen is a special case
        result['namen'] = self.get_namen()

        #figures is a special case
        result['figures'] = self.get_illustrations()
        
        #text can be escaped: we unescape it
        if 'tekst' in result:
            result['tekst'] = unescape(result['tekst'])
        return result

    def get_namen(self):
        el = self.get_root()
        result = []
        for n in el.xpath('/biodes/person/persName'):
            result.append(Name().from_element(n))
        return result
#            if n.get('lang') == 'en':
#               pass
#               #XXX todo
#            else:
#                naam = self.element2text(n).strip()
#                d = {}
#                for type in NAAM_TYPEN:
#                    d[type] = ''
#                    for c in n:
#                        if c.get('type') == type:
#                            if d[type]:
#                                d[type] += ' ' 
#                            d[type] += self.element2text(c).strip()
#        
#                result['namen'].append(tuple( [naam.strip()] + [d[type] for type in NAAM_TYPEN] + [self.normalize_name(n)]))

    def is_list(self, s):
        return type(s) == type([])

    def element2text(self,n, with_tail=0):
        result = ''
        if n.text:
            result += n.text.replace('\n', ' ')
        for subn in n:
            result += self.element2text(subn, with_tail = 1)
        if with_tail and n.tail:
            result += n.tail.replace('\n', ' ')
        return result

    def xpath(self, s):
        return self.get_root().xpath(s)

    def get_names(self):
        """return a list of Name objecten"""
        if self.get_root() is None:
            return []
        result = []
        for n in self.xpath('./person/persName'):
            result.append(Name().from_xml(n, store_guessed_geslachtsnaam=False))    
        return result
    
    get_namen = get_names
    
    def normalize_name(self, el):
        # XXX - translate this
        """gegeven een name element, probeer het in de volgorde achternaam, 
        prepo voornaam intra, postpo te zetten
        """
        n = Name().from_xml(el)
        return n.guess_normal_form()

    def _add_rights(self, s):
        """argument: een tuple bestaand uit een 'status' en een 'tekxt'
        
        status must be one of 'free', 'unknown' or 'restricted'
        """
        if s:
            status, tekst = s
            el = SubElement(self.element_filedesc, 'availability')
            if status:
                assert status in ['free', 'unknown', 'restricted']
                el.set('status', status)
            if tekst:
                el.text = tekst    

  
    def _add_meta(self, d):
        #d must be  a dictionary
        if d:
            el = SubElement(self._element_filedesc, 'meta')
            for k in list(d.keys()):
                SubElement(el, k).text = d[k]
                
    def _add_illustraties(self, **args):
        k = 'illustraties'
        ls = args.get(k)
        if type(ls) in (str,):
            ls = [ls]
        if ls:
            for s in ls:
                if not is_url(s):
                    raise ValueError('The value for %s is not a url (but %s)' % (k, s))
                self._add_figure(url=s)
        
            
    def _add_figure(self, url, head=''):
        if not is_url(url): 
            raise ValueError('Url should be a valid URL (you gave "%s")' % url)
        el_figure = SubElement(self.get_element_biography(), 'figure')
        if head:
            el_head = SubElement(el_figure, 'head')
            el_head.text = head
        SubElement(el_figure, 'graphic').set('url', url)

    def add_figure(self, uri, text):
        self._add_figure(url=uri, head=text)
        
    def update_figure(self, index, uri, text=None):
        url = uri
        head = text
        if not is_url(url): 
            raise ValueError('Url should be a valid URL (you gave "%s")' % url)
        
        el_figure = self.get_figures()[index][1]
        assert el_figure.tag == 'figure' #sanity check
        if head is not None:
            el_head = el_figure.find('head')
            if el_head is None:
                el_head = SubElement(el_figure, 'head')
            el_head.text = head
        el_graphic = el_figure.find('graphic')
        assert el_graphic.tag == 'graphic'
        el_graphic.set('url', url)

    
    def get_illustrations(self):
        # there are two ways in which figures can be encoded - either in plain 
        # 'graphic' tags immediately in the biography element, or within a
        # 'figure' element
        if self.get_element_biography() is None:
            return []
        urls = self.get_element_biography().xpath('./graphic')
        result = []
        for url in urls:
            if 'url' in url.attrib:
                item = (url.attrib['url'], '')
                result.append(item)
        
        figures = self.get_element_biography().xpath('./figure')
        for figure in figures:
            head = ''
            if figure.find('head') is not None:
                head = figure.find('head').text
            url = figure.find('graphic').get('url')
            result.append((url, head))
        return result
    
    def get_figures(self):
        if self.get_element_biography() is None:
            return []
        return list(enumerate(self.get_element_biography().xpath('./figure')))

    def get_figures_data(self):
        """returns a list of (url, text) pairs"""
        result =[]
        for _index, figure in self.get_figures():
            head = ''
            if figure.find('head') is not None:
                head = figure.find('head').text
            url = figure.find('graphic').get('url')
            result.append((url, head))
        return result
    
    
    def get_element_biography(self):
        return self.get_root().find('biography')
    
    def _add_bibl(self, **args):
        """ add a 'bibliographical section'
        
        arguments can be:
           title
           author
           editor
           pages
           publisher
           date
        """
        
        element_bibl = SubElement(self._element_filedesc, 'bibl')
        if args.get('author'):
            SubElement(element_bibl, 'author'). text = args.get('author')        
        if args.get('editor'):
            SubElement(element_bibl, 'editor'). text = args.get('editor')        
            
        if args.get('title'):
            SubElement(element_bibl, 'title'). text = args.get('title')
        if args.get('publisher'):
            SubElement(element_bibl, 'publisher'). text = args.get('publisher')
        if args.get('date'):
            SubElement(element_bibl, 'date'). text = args.get('date')
        if args.get('pages'):
            SubElement(element_bibl, 'pages'). text = args.get('pages')
            
#            #or: this would be the TEI Way
#            el = SubElement(element_bibl, 'biblScope')
#            el.set('type', 'pages')
#            el.text = args.get('pages')
        
    def _set_up_basic_structure(self):
        if getattr(self, 'root', None) is None:
            self.root = Element('biodes')
            self.root.set('version', self.__version__)
            SubElement(self.root, 'fileDesc')
            #bibl = SubElement(filedesc, 'bibl')
            SubElement(self.root, 'person')
            SubElement(self.root, 'biography')
#        
#    def _element_biography(self): 
#        try:
#            return self.element_biography
#        except:
#            els = self.root.xpath('./biography')
#            if els:
#                self.element_biography = els[0]
#            else:
#                self.element_biography = SubElement(self.root, 'biography')
#        return self.element_biography

    def get_events(self, type=None):
        if self.get_root() is None:
            return []
        if type:
            els = self.get_root().xpath('./person/event[@type="%s"]' % type)
        else:
            els = self.get_root().xpath('./person/event')
        return els

    def get_event(self, type):
        """return the first event Element of type type"""
        els = self.get_events(type)
        if els:
            if len(els) != 1:
                raise ValueError("There are %s events of type %s found -- " \
                                 "expected at most one" % (len(els), type))
            return els[0]
        
    def get_states(self, type=None):
        if self.get_root() is None:
            return []
        if type: 
            els = self.get_root().xpath('./person/state[@type="%s"]' % type)
        else:
            els = self.get_root().xpath('./person/state')
        return els
    
    def get_state(self, type):
        """return the first 'state' element of type type"""
        els = self.get_states(type)
        if els:        
            if len(els) != 1:
                raise ValueError("There are %s states of type %s found -- " \
                                 "expected at most one" % (len(els), type))
            return els[0]
        
    def add_or_update_event(self, type, text=None, when=None, place=None, 
                            place_id=None, date_text=None, notBefore=None,
                            notAfter=None):
        els = self.get_events(type) 
        if els:
            el = els[0]
        else:
            el_person = self.get_root().find('person')
            el = SubElement(el_person, 'event')
        self._set_event_properties(el, type=type, text=text, when=when, place=place, 
                                   place_id=place_id, date_text=date_text, 
                                   notBefore=notBefore, notAfter=notAfter)
    
    def _add_event(self, type, text=None, when=None, place=None,place_id=None, 
                   date_text=None,notBefore=None, notAfter=None):
        #geboortedatum
        el_person = self.get_root().find('person')
        el = SubElement(el_person, 'event')
        self._set_event_properties(el, text=text, type=type, when=when, 
                                   place=place,place_id=place_id,  
                                   date_text=date_text, notBefore=notBefore, 
                                   notAfter=notAfter)

    def _add_event_element(self, el):
        el_person = self.get_root().find('person')
        el_person.append(el)
        return el
    
                      
    def _add_state_element(self, el):
        el_person = self.get_root().find('person')
        el_person.append(el)
        return el
        
    def _set_event_properties(self, el, text, type, when, place, place_id, 
                                    date_text, notBefore, notAfter):
        el.set('type', type)
        if when == '':
            if 'when' in el.attrib:
                del el.attrib['when']
        elif when:
            if not is_date(when):
                msg = 'The value for event of type %s is not a date (but %s)' \
                       % (type, when)
                raise ValueError(msg)
            el.set('when', when)
            
        if notBefore == '':
            if 'notBefore' in el.attrib:
                del el.attrib['notBefore']
        elif notBefore:
            if not is_date(notBefore):
                raise ValueError('The value for notBefore for event of type %s is not a date (but %s)' % (type, notBefore))
            el.set('notBefore', notBefore)
            
        if notAfter == '':
            if 'notAfter' in el.attrib:
                del el.attrib['notAfter']
        elif notAfter:
            if not is_date(notAfter):
                raise ValueError('The value for notAfter for event of type %s is not a date (but "%s")' % (type, notAfter))
            el.set('notAfter', notAfter)


        if date_text is not None:
            el_date = el.find('date')
            if el_date is not None:
                if date_text == '':
                    el.remove(el_date)
                else:
                    el_date.text = date_text 
            elif date_text:
                el_date = SubElement(el, 'date')
                el_date.text = date_text
                
        if text is not None:
            el.text = text 

        if place is not None or place_id is not None:   
            el_place = el.find('place')
            if el_place== None:
                el_place = SubElement(el, 'place')
            if place is not None:
                el_place.text = place 
            if place_id is not None:
                el_place.set('key', str( place_id))

    def add_state(self, type=None, idno=None, frm=None, to=None, text=None, place=None, place_id=None):
        el_person = self.get_root().find('person')
        el = SubElement(el_person, 'state')
        self._set_state_attributes(el, type, idno, text, frm, to, place, place_id)
        return el


    def add_or_update_state(self, 
        type=None, 
        idno=None, 
        text=None, 
        frm=None, 
        to=None, 
        place=None, 
        place_id=None, 
        idx=0,
        add_new=False,
        ):
        """
        if add_new is True, then we will ad a new state
        if idx is given, then we will update the event 
        if a state of type 'type' exist, it will update it
        otherwise, we add a new one
        XXX: yes, this is TOO complicated...
        """
        if add_new:
            el = self.add_state(type=type)
        
        elif idx:
            el = self.get_element_person()[idx]
            #sanity check: dow e really have a 'state' element
            assert el.tag == 'state'
        else:
            if type:
                els =  self.xpath('./person/state[@type="%s"]' % type)
            else:
                els =  self.xpath('./person/state')
            if els:
                el = els[0]
            else:
                el = self.add_state(type=type)
        self._set_state_attributes(el, type=type, idno=idno, text=text, frm=frm, to=to, place=place, place_id=place_id)
        
        return el
    
    def _set_state_attributes(self, el, type, idno, text, frm, to, place=None, place_id=None):
        el.text = text 
        if type:
            el.set('type', type)
        if idno is not None:
            el.set('idno', idno)
        if frm is not None:
            if frm: assert is_date(frm)
            el.set('from', frm)
        if to is not None:
            if to: assert is_date(to)
            el.set('to', to)
            
        if place is not None or place_id is not None:   
            el_place = el.find('place')
            if el_place== None:
                el_place = SubElement(el, 'place')
            if place is not None:
                el_place.text = place 
            if place_id is not None:
                el_place.set('key', str( place_id))

    
    def remove_state(self, idx, type=None):
        if type:
            els =  self.xpath('./person/state[@type="%s"]' % type)
            el = els[idx]
            el.getparent().remove(el)
        else:
            self.remove_element_from_person(idx)
   
    def remove_figures(self): 
        for el in self.xpath('./biography/figure'):
            el.getparent().remove(el)
         
    def remove_figure(self, index): 
        """delete the element at index - 
        
        argument:
            index:  the position of this <reference> element with respect to othe r<reference> elements in the <person> tag
        """
        els = self.get_figures()
        index, el = els[index]
        assert el.tag == 'figure'
#        el = self.get_element_person()[index]
        el.getparent().remove(el)
     
    def remove_element_from_person(self, idx): 
        el = self.get_element_person()[idx]
        el.getparent().remove(el)
       
    def remove_relation(self, idx):
        el = self.get_element_person()[idx]
        assert el.tag == 'relation' 
        self.remove_element_from_person(idx)
        
    def update_relation(self, idx, person, relation): 
        """update the information of this relation"""
        self.remove_relation(idx)
        self.add_relation(person, relation)
        
    def add_relation(self, person, relation):
        """add a person that stands in a type of relation with our person
        
            - person - a string
            - relation - one of ['partner', 'father', 'mother', 'parent', 'child']
        """
#        possible_relations = ['partner', 'father', 'mother', 'parent', 'child', 'brother', 'sister']
#        if relation not in possible_relations:
#            raise ValueError('The "relation" argument must be one of %s' % possible_relations)
        
        #get an id for the main person of the biodes file
        root_id = self.get_element_person().get('id')
        if not root_id:
            root_id = '#1'
            self.get_element_person().set('id', root_id)
            
        #create a new person in the biodes file
        el = self.get_element_person()
        new_id = '#%s' % abs(hash('%s %s' % (person, relation)))
        el_person =  self._get_person_by_id(new_id)
        if el_person is not None:
            el_persName = el_person[0]
        else:
            el_person = SubElement(el, 'person') 
            el_person.set('id', new_id)
            el_persName = SubElement(el_person, 'persName')
        el_persName.text = person
        
        #guess the sex of the new person
#        sex = None
#        if relation in ['father']:
#            sex = '1'
#        elif relation in [ 'mother']:
#            sex = '2'
#        if sex:
#            el_person.set('sex', sex)

        #add the relation elemeent
        el_relation = SubElement(el, 'relation')
        if relation in ['partner']:
            el_relation.set('name', 'partner')
            el_relation.set('mutual', '%s %s' % (root_id, new_id))
#        relation in ['father', 'mother', 'parent', 'child']:
        else:
            el_relation.set('name', relation) 
            el_relation.set('passive', root_id)
            el_relation.set('active', new_id)
#        elif relation in ['child']:
#            el_relation.set('name', 'parent') 
#            el_relation.set('active', root_id)
#            el_relation.set('passive', new_id)
        
    def get_relations(self):
        """return a list of pairs (type, name_of_relation)"""
        root_id = self.get_element_person().get('id')
        el_relations = self.xpath('//relation')
        result = []
        for el_relation in el_relations:
            type = el_relation.get('name')
            person_ids =  [el_relation.get('active'), el_relation.get('passive')] + el_relation.get('mutual', '').split()
            person_ids = [x for x in person_ids if x != root_id and x]
            person_id = person_ids[0]
            el_person= self._get_person_by_id(person_id)
            result.append((el_relation, el_person))
        return result
    
    def get_relation(self, relation):
        root_id = self.get_element_person().get('id')
        if not root_id:
            return []
        relations = []
#        sex = None
#        if relation in ['father']:
#            sex = '1'
#        elif relation in ['mother']:
#            sex = '2'
        if relation in ['father', 'mother', 'parent', 'child']:
            relations = self.xpath('//relation[@name="%s"][@passive="%s"]' % (relation, root_id))
            person_ids =  ' '.join([el.get('active') for el in relations]).split()
#        elif relation in ['child']:
#            relations = self.xpath('//relation[@name="parent"][@active="%s"]' % root_id)
#            person_ids =  ' '.join([el.get('passive') for el in relations]).split()
        elif relation in ['partner']:
            relations = self.xpath('//relation[@name="partner"]')
            person_ids =  ' '.join([el.get('mutual') for el in relations]).split()
        persons = [self._get_person_by_id(person_id) for person_id in person_ids if person_id != '#1']
#        if sex:
#            persons = [el for el in persons if el.get('sex') == sex]
        return [el[0].text for el in persons]
    
    def _get_person_by_id(self, person_id):
        qry = '//person[@id="%s"]' % person_id
        ls = self.xpath(qry)
        if ls:
            assert len(ls) == 1
            return ls[0]

    def _add_a_name(self,s, lang=None):
        """Add a name
        
        arguments:
            s can be one of:
                - a string
                - a fivetuple of strings (prepositie, voornaam, intrapositie, geslachtsnaam, postpositie)
                - a Name instance (recommended)
        """
        
        person = self.get_root().find('person')
        if type(s) in (str,):
            naam = Name(volledige_naam=s)
        elif type(s) in [tuple, list]:
            assert len(s) == 5
            prepositie, voornaam, intrapositie, geslachtsnaam, postpositie = s
            naam = Name(
                prepositie=prepositie,
                voornaam=voornaam, 
                intrapositie=intrapositie,
                geslachtsnaam=geslachtsnaam,
                postpositie=postpositie,
                )
        else:
            naam = s
        person.append( naam.to_xml())
    
    def remove_name(self, idx):
        """remove a name
        arguments:
            idx - an integer - we remove the idx-th name
        """
        el_namen = self.get_root().xpath('./person/persName')
        el_naam = el_namen[idx]
        el_naam.getparent().remove(el_naam)       
    def _replace_name(self, naam, idx):
        """
        arguments:
            naam - a Name instance
            idx - an integer - we replace the idx-th name
        """
        el_namen = self.get_root().xpath('./person/persName')
        el_naam = el_namen[idx]
        new_el = naam.to_xml()
        el_naam.getparent().replace(el_naam, new_el)

    def _replace_names(self, names):
        """delete all existing names, and replace them by new name list"""
        el_namen = self.get_root().xpath('./person/persName')
        for el_naam in el_namen:
            el_naam.getparent().remove(el_naam)       
        for name in names:
            self._add_a_name(name)

    def _replace_references(self, references):
        """delete all existing references, and replace them by new references list
        
        arguments:
            references: a list of (url, text) tuples"""
        el_references = self.get_root().xpath('./person/ref')
        for el_ref in el_references:
            el_ref.getparent().remove(el_ref)       
        for url, text in references:
            self.add_reference(uri=url, text=text)

            
    def _replace_figures(self, figures):
        """delete all existing references, and replace them by new references list
        
        arguments:
            references: a list of (url, text) tuples"""
            
        for _index, el in self.get_figures():
            el.getparent().remove(el)       
        for url, text in figures:
            self.add_figure(uri=url, text=text)
            
        
    def add_note(self, text, type=None):
        notesStmt = self.xpath('./fileDesc/notesStmt')
        if not notesStmt:
            el_notesStmt = SubElement(self.get_element_filedesc(), 'notesStmt')
        else:
            el_notesStmt = notesStmt[0]
        el_note = SubElement( el_notesStmt,'note')
        el_note.text = text
        el_note.set('type', type)
        return el_note
    def add_or_update_note(self, text, type): 
        notes = self.get_notes(type=type)
        if notes:
            assert len(notes) == 1
            el_note = notes[0]
            el_note.text = text
        else:
            self.add_note(text=text, type=type)
    
    def add_reference(self, uri, text):
        """add an (external reference) - a <ref> element to the person element"""
        el = SubElement(self.get_element_person(), 'ref')
        el.set('target', uri)
        el.text = text
        return el
        
    def remove_reference(self, index): 
        """delete the element at index - 
        
        argument:
            index:  the position of this <reference> element with respect to othe r<reference> elements in the <person> tag
        """
        els = self.xpath('./person/ref')
        el = els[index]
#        el = self.get_element_person()[index]
        assert el.tag == 'ref' #check sanity
        el.getparent().remove(el)
    
    def update_reference(self, index, uri, text):
        """update the reference at index witht he given info"""
        el = self.xpath('./person/ref')[index]
        assert el.tag == 'ref' #check sanity
        el.set('target', uri)
        el.text = text
        return el
    
    def get_references(self): 
        return list(enumerate(self.xpath('./person/ref')))

    def add_extrafield(self, key, value):
        """add an (external reference) - a <ref> element to the person element
           
        returns the Element that was added
        """
        el = SubElement(self.get_element_person(), 'extrafield')
        el.set('target', key)
        el.text = value
        return el
        
    def remove_extrafield(self, index): 
        """delete the element at index - 
        
        argument:
            index:  the position of this <extrafield> element with respect to other <extrafield> elements in the <person> tag
        """
        els = self.xpath('./person/extrafield')
        el = els[index]
#        el = self.get_element_person()[index]
        assert el.tag == 'extrafield' #check sanity
        el.getparent().remove(el)
    
    def update_extrafield(self, index, key, value):
        """update the field at index witht he given info"""
        el = self.xpath('./person/extrafield')[index]
        assert el.tag == 'extrafield' #check sanity
        el.set('target', key)
        el.text = value
        return el
 

    def _replace_extrafields(self, extrafields):
        """delete all existing extra fields, and replace them by new extrafields list
        
        arguments:
            references: a list of (key, value) tuples (both strings)"""
        el_extrafields = self.get_root().xpath('./person/extrafield')
        for el_field in el_extrafields:
            el_field.getparent().remove(el_field)       
        for key, value in extrafields:
            self.add_extrafield(key=key, value=value)
  
    def get_extrafields(self): 
        """return a list of Element instances"""
        return list(self.xpath('./person/extrafield'))
        
    def get_notes(self, type=None): 
        if type:
            return self.xpath('./fileDesc/notesStmt/note[@type="%s"]' % type)
        else:
            return self.xpath('./fileDesc/notesStmt/note' )
    
def create_biodes_document(**args):
    biodesdoc = BioDesDoc()
    biodesdoc.from_args(**args)
    return biodesdoc.to_string()
    
    
create_xml = create_biodes_document 

def parse_list(url):
    """get the list of biodes documents from the url

    return a list of urls to biodes documents
    """
    #XXX USE biodes_list.BiodesList instead
    if url.endswith('tar.gz'):
        """we expect an archive containing biodes XML files"""
        from gerbrandyutils import sh
        def cleanup(tempdir):
            logging.info("Removing tempdir used for sources import %s" %tempdir)
            if os.path.isdir(tempdir):
                shutil.rmtree(tempdir)

        archive = os.path.basename(url)
        tempdir = tempfile.mkdtemp(prefix="bioport_")
        atexit.register(cleanup, tempdir)
        
        # XXX - specifiy user and password in the url -argument 
        if url.startswith('http'):
            sh("wget %s --user=%s --password=%s" % (url, 'giampaolo', 'N@p0li'))
        elif url.startswith('file://'):
            _file = url.replace('file://', '')
            shutil.copy(_file, '.')
        else:
            raise ValueError("don't know what to do with url %s" % url)
        try: 
            tar = tarfile.open(archive)
            tar.extractall(tempdir)
            tar.close()
        finally:
            # move the archive to temp dir so that it gets deleted later
            shutil.move(archive, tempdir)

        ls = []
        for name in os.listdir(tempdir):
            fullname = os.path.join(tempdir, name)
            if fullname.endswith('.xml'):
                ls.append(fullname)
        return ls
    else:
        """we expect an XML file"""
        parser = etree.XMLParser(no_network=False)
        root = etree.parse(url, parser )
        result = []
        for n in root.xpath('//a'):
            result.append(n.get('href'))
        return result

def parse_document(url=None, document=None):
    """parse the xml file found at the url
   
    return a dictionary with data found in the biodes document at the given url 
    
    NOTE: that not all information in the document ends up in the dictionary 
    (the biodes format is richer than its representation as a dictionary). 

    raise an error if the xml file is not of the right type
    """

    biodesdoc = BioDesDoc()
    if url:
        biodesdoc.from_url(url)
    elif document:
        biodesdoc.from_document(document)

    return biodesdoc.to_dict()

def analyze_element(el):
    """given an etree.Element with root 'biodes'
        return a dictionary with (most of) the data contained in the element """
    biodesdoc = BioDesDoc()
    biodesdoc.from_element( el)
    return biodesdoc.to_dict()

def is_valid_document(s):
    """return true if this document is a valid BioDes document"""
    #XXX implement this!
    return True
