# coding=utf-8
import re
import types
from lxml import etree 
from lxml.etree import Element, SubElement
from .common import (STOP_WORDS, TUSSENVOEGSELS, ROMANS, PREFIXES,
                    serialize, remove_parenthesized, html2unicode, to_ascii,
                    POSTFIXES, fix_capitals, VOORVOEGSELS, TERRITORIALE_TITELS, 
#                    coerce_to_unicode, 
                    remove_stopwords)

#from plone.memoize import instance

from names.soundex import soundexes_nl 
#from names.common import R_ROMANS, R_TUSSENVOEGELS, wordsplit_re
from names.tokens import TokenDict,Token, tokens as words

STOP_WORDS_frozenset = frozenset(STOP_WORDS)
VOORVOEGSELS_EN_TERRITORIALE_TITELS = frozenset(VOORVOEGSELS + TERRITORIALE_TITELS)
ROMANS_FROZENSET = frozenset(ROMANS)

TYPE_PREPOSITION = 'prepositie'
TYPE_FAMILYNAME = 'geslachtsnaam' 
TYPE_GIVENNAME = 'voornaam'
TYPE_INTRAPOSITON = 'intrapositie'
TYPE_POSTFIX = 'postpositie'
TYPE_TERRITORIAL = 'territoriale_titel'

def is_initials(token):
    if re.match('(Th\.|[A-Z]\.)+\s*',token.word()):
        return True
    
class Name(object):
    """The name of a person
    
    this class contains different functions for analyzing and printing the name
    """
    _constituents = [
        TYPE_PREPOSITION,   #preposition
        TYPE_GIVENNAME,     #first name
        TYPE_INTRAPOSITON, #intraposition
        TYPE_FAMILYNAME,#last name
        TYPE_POSTFIX,  #postposition
        TYPE_TERRITORIAL, #'territoriale_titel',
    ]
   
    def __init__(self, naam=None, **args):
        self._root = None #etree.Element object met naamgegevens
        self._guessed_root = None #tree.Element object with the 'guessed' structure
        if naam:
            args['volledige_naam'] = html2unicode(naam)
        if args:
            self.from_args(**args)
   
    def __str__(self):
        try:
            val = self.volledige_naam()
        except AttributeError:
            return "*uninitialized*"
        if isinstance(val, str):
            return val.encode('ascii', 'replace')
        return val
    
    def __repr__(self):
        return '<Name %s>' % self.__str__()
    
    def __eq__(self, other):
        return self.to_string() == other.to_string()
    
    def from_args(self, **args):
        volledige_naam = args.get('volledige_naam', '')
        self.sort_name = args.get('sort_name', None)
        #store the data as an xml Element
        ### Create an XML structure
        self._root = Element('persName')
        last_element = None

        if volledige_naam:
            if re.match('\(.*\)$', volledige_naam):
                volledige_naam = volledige_naam[1:-1]
            volledige_naam = html2unicode(volledige_naam)
            self._root.text = volledige_naam
#            self._insert_constituent(TYPE_FAMILYNAME, args.get(TYPE_FAMILYNAME))
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
#                    el.text = html2unicode(args.get(c))
                    if last_element is not None:
                        last_element.tail = ' '
                    last_element = el
#        if volledige_naam and not self.geslachtsnaam():
#             we were instantiated from a string.
#            self.store_guessed_geslachtsnaam()
        return self

    def html2unicode(self):
        """convert all html-type character codes to proper unicode"""
        s = self.to_string()
        s = html2unicode(s)
        self.from_string(s)
        return self
    
    def _insert_constituent(self, constituent_type, text_to_replace, element=None, i = 0):
        """tag the substring s of volledige_naam as being of type constituent_type
        
        arguments:
            constituent_type : one of [TYPE_PREPOSITION, TYPE_GIVENNAME, etc]
            s : a string (must be a substring of self.volledige_naam()), or a match object
            
        e.g.:
            
        """     
        if not text_to_replace:
            return
        if element is None:
            element = self._root
      
        #these are candidate strings to replace
        if type(text_to_replace) in (str,):
            new_string = text_to_replace
            candidate_strings = [element.text] + [n.tail for n in element]
            for i in range(len(candidate_strings)):
                text = candidate_strings[i]
                #find word starting at word boundary (i.e. as alphanumeric, and ending in space of endofline
                m = re.search(r'\b%s(?=\s)|\b%s\Z|\b%s\b' % (text_to_replace,text_to_replace,text_to_replace), text)
                if m:
                    break
        else:
            m = text_to_replace
            new_string = m.group()
        if m:
            new_el = Element('name')
            new_el.set('type', constituent_type)
            new_el.text = new_string 
            if i == 0:
                before = element.text[:m.start()]
                after = element.text[m.end():]
                element.text = before 
            else:
                before = element[i-1].tail[:m.start()]
                after = element[i-1].tail[m.end():]
                element[i-1].tail = before 
            element.insert(i,new_el)
            new_el.tail =  after 
            return new_el
        msg = 'The string "%s" (of type %s) should be a part of the volledige naam %s' % (text_to_replace, constituent_type, candidate_strings)
        raise Exception(msg)
#    
    def from_string(self, s):
        s = s.replace('\n', ' ')
        s = s.strip()
        try:
            element =  etree.fromstring(s) #@UndefinedVariable
        except etree.XMLSyntaxError as err: #@UndefinedVariable
            if 'Entity' in err.message:
                #the string contains HTML Entities (probably)
                #and we provide some robustness by converting it to unicode
                s = html2unicode(s)
                element = etree.fromstring(s) #@UndefinedVariable
            else:                 
                raise str(err) + "\nculprit string=" + repr(s)
        self.from_xml(element)
        return self

    def from_xml(self, element,  store_guessed_geslachtsnaam=False):
        return self.from_element(element,  store_guessed_geslachtsnaam=store_guessed_geslachtsnaam)
    
    def from_element(self, element, store_guessed_geslachtsnaam=False):
        """A constructor for Name
        
        arguments:
            element is een etree.Element instance"
            store_guessed_geslachtsnaam:  try to guess the alst name, and store it in the result
            note that this has a default of TRUE
        XXX: should be decorated as "classmethod"
        """
        self._root = element
        if store_guessed_geslachtsnaam:
            self.store_guessed_geslachtsnaam()
        return self

    def get_volledige_naam(self):
        """return a string without (XML) markup in the original order""" 
        s = self.serialize(self._root).strip()
        return s

    def volledige_naam(self):
        return self.get_volledige_naam()

    def sort_key(self):
        """this value should assign the name its proper place in the alfabet
        """
        base = self.guess_normal_form()
        base = base.replace(',', '')
        base = base.replace('  ', ' ')
        base = base.strip()
        base = base.lower()
        ignore_these = '()'
        for c in ignore_these:
            base = base.replace(c, '')
            
        for s in PREFIXES: #we also strip prefixes (so "L'Eremite, B." sorts between "Eremite, A" and "Eremite, C")
            if base.startswith(s):
                base = base[len(s):]

        ls = base.split()
        for s in TUSSENVOEGSELS:
            if ls and ls[0] == s:
                base = ' '.join(ls[1:])
                
        for s in '?.-': #if the name starts with any of these characters, it comes last (not first)
            if base.startswith(s):
                base = chr(126) + base 
        
        base = to_ascii(base) 
        base = base.strip()
        base = base[:40]
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

    #@instance.memoize # used in similarity.ratio, our most expensive function
    # unfortunately tests won't pass with this enabled, because
    # the object changes between subsequent calls to this method,
    # and memoize gives the stale result

    def geslachtsnaam(self):
        return self.guess_geslachtsnaam() or ''
    
    def _get_geslachtsnaam_from_xml(self):
        result = self._root.xpath('./name[@type="geslachtsnaam"]/text()')
        result = ' '.join(result)  
        return result

    def geslachtsnaam_soundex(self):
        return self.soundex_nl(
            to_ascii(self.geslachtsnaam()),
            group=2, length=-1
        )

    def postpositie(self):
        result = self._root.xpath('./name[@type="postpositie"]/text()')
        result = ' '.join(result)
        return result

    def territoriale_titel(self):
        result = self._root.xpath('./name[@type="territoriale_titel"]/text()')
        result = ' '.join(result)
        return result
    
    def serialize(self, n = None, exclude=[]):
        if n is None: 
            n = self._root
        return serialize(n, exclude=exclude).strip()
#    def _strip_tussenvoegels(self,s):
#        s = s.strip()
#        for intraposition in TUSSENVOEGSELS:
#            if s.startswith(intraposition +  ' ' ):
#                s = s[len(intraposition):]
#                s = self._strip_tussenvoegels(s)
#                break
#        return s.strip()

    def store_guessed_geslachtsnaam(self):
        """Guess the geslachtsnaam, and store the result in the XML representation of the current object
        
        """
        if self._get_geslachtsnaam_from_xml():
            #we already have the last name explicitly stored in the XML, so we dont do anything
            pass
        else:
            self._root = self._guess_constituents([TYPE_FAMILYNAME])
        return self
    
    def guess_geslachtsnaam(self, hints=[]):
        """Try to guess the geslachtsnaam, and return it
        
        arguments:
             - hints: a list with one or more of the following hints: 
                 ['startswithgeslachtsnaam']
        returns:
             None if no geslachtsnaam is found
             The guessed string if such a name is found
         
        >>> name.to_string()
        '<persName>Puk, Pietje</persName>
        >>> name.store_guessed_geslachtsnaam()
        >>> name.guess_geslachtsnaam()
        'Puk'
        >>> name.to_string()
        '<persName><name type="geslachtsnaam">Puk</name>, Pietje</persName>
             
        >>> name.fromstring('AAA BBB')
        >>> name.guess_geslachtsnaam()
        'BBB'
        >>> name.guess_geslachtsnaam(hints=['startswithgeslachtsnaam'])
        'AAA'
        """
        if self._get_geslachtsnaam_from_xml(): #if we already have an explicitly given geslachtnaam, we dont try to guess, but return it
            return self._get_geslachtsnaam_from_xml()
        elif self._root.text and self._root.text.strip(): #we only try to guess if there is text that is not marked as a part of a name
            return self._guess_geslachtsnaam(hints=hints)
        else: #in case we did not find a last name, and return None
            return None

    def _guess_geslachtsnaam(self, hints):
        """ """
        orig_naam = self._root.text
        return Name().from_xml(self._guess_constituents())._get_geslachtsnaam_from_xml()

    
    def guess_normal_form2(self):
        """return 'normal form' of the name
           (prepositie voornaam intrapostie geslachstsnaam postpostie)
           NB: we rather simply serialize 'as is' then make a mistake,
           so we only change the order of the name if we are pretty sure
        """
        tokens = self._guess_normal_form_tokens2()
        s = tokens.serialize()
        s = remove_parenthesized(s)
        s = fix_capitals(s)
        return s


    def guess_normal_form(self):
        """return 'normal form' of the name (Geslachtsnaam, prepositie voornaam intrapostie, postpostie)
        
        returns:
            a string
        
        cf. also "guess_normal_form2"
        """
        tokens = self._guess_normal_form_tokens()
        s = tokens.serialize()
        s = remove_parenthesized(s)
        s = fix_capitals(s)
        s = str(s)
        return s
    
    def _guess_normal_form_tokens(self):
        """
        returns a TokenDict instance
        """
        tokens = self._guess_constituent_tokens()
        
        #rearrange tokens
        if not tokens:
            return TokenDict() 
        
        if tokens[0].ctype() == TYPE_FAMILYNAME:
            #if the name already starts with a family name, we assume it to be already normalized
            result = tokens
        else:
            #what we no need to to is, roughly, divide the tokens list in two parts - those that come before and those after
            #idx is the index of the token on which we split
            #
            for i, token in enumerate(tokens):
                idx = i 
                if token.ctype() in [TYPE_FAMILYNAME, TYPE_POSTFIX]: #, TYPE_TERRITORIAL]:
                    break
                idx = 0 #did not hit 'break': this one contains no family name or postfix
            result = TokenDict()
            for token in tokens[idx:]: #the second part
                result.append(token)
            if idx > 0 and idx < len(tokens):
                result.append(Token(',', ',', tail=' '))
            else:
                result[-1]._tail = ' '
            for token in tokens[:idx]: #the first part
                result.append(token)
        
        return result
    
    def _guess_normal_form_tokens2(self):
        """
        returns:
            a list of tokens in the 'second normal form' - that is first name intrapositions family_name ...
        """
        tokens = self._guess_constituent_tokens()
        idx = 0
        if not tokens:
            return TokenDict()
        if tokens[0].ctype() == TYPE_FAMILYNAME:
            for i, token in enumerate(tokens):
                if token.ctype() not in [TYPE_FAMILYNAME]:
                    idx = i
                    break
                
        if idx > 0 and idx < len(tokens):
            result = TokenDict()
            if tokens[idx].ctype() not in [',']:
                result.append(token)
            for token in tokens[idx+1:]:
                result.append(token)
            tokens[-1]._tail =  ' '
            for token in tokens[:idx]:
                result.append(token)

        else:
            result = tokens
        return result
    
    def initials(self):
        tokens = self._guess_normal_form_tokens2()
        result = '' 
        _in_parenthesis = False
        for token in tokens:
            if _in_parenthesis and token.word() == ')':
                _in_parenthesis = False 
            elif _in_parenthesis:
                pass
            elif token.word() == '(':
                _in_parenthesis = True
            elif token.word() in STOP_WORDS_frozenset:
                pass
            else:
                result += token.word()[0].upper()
        result = str(result)
        return result 
        result = ''.join([token.word()[0].upper() for token in result if token.word() not in STOP_WORDS_frozenset]) 
#        s = self.guess_normal_form2() #take ther string with first_name, last_name etc
#        return u''.join(s[0] for s in words(s) if s not in STOP_WORDS_frozenset)
        
    def to_xml(self):
        """return an etree.Element instance"""
        
        if not hasattr(self,'_root') and hasattr(self, 'xml'):
            self.from_string(self.xml)
        return self._root

    def to_string(self):
        s = etree.tounicode(self.to_xml(), pretty_print=True) #@UndefinedVariable
        s = str(s)
        s = s.strip()
        return s
    
    def soundex_nl(self, s=None, length=4, group=1):
        if group == 1:
            res = self._soundex_group1(s)
        elif group == 2:
            res = self._soundex_group2(s)
        else:
            raise Exception('"group" argument must be either 1 or 2')
        if length < 0:
            return res
        else:
            return list(set([a[:length] for a in res]))

    def soundex_geslachtsnaam(self, length=4, group=1 ):
        """return a list of soundex expressions for all parts of the family name"""
        s = self.geslachtsnaam() 
        return self.soundex_nl(remove_stopwords(s), group=group, length=length)                    
        
    def get_normal_form_soundex(self):
        return self.soundex_nl(
            remove_stopwords(self.guess_normal_form()), group=2, length=-1
        )
  
    def _soundex_group1(self, s=None):
        if s is None:
            s = self.guess_normal_form()
        result = soundexes_nl(s, group=1, filter_initials=True)
        return result 

    def _soundex_group2(self, s=None):
        if s is None:
            s = self.guess_normal_form()
        result = soundexes_nl(s, group=2, filter_initials=True)
        return result 
#    
#    def _name_parts(self):
#        s = self.serialize()
#        return re.findall('\S+', s)
    
    def contains_initials(self):
        """Return True if the name contains initials"""
        #all parts of the name are initials, except  "geslachtsnaam" or ROMANS or TUSSENVOEGSELS
        for token in self._guess_constituent_tokens():
            if is_initials(token):
                return True
        return False
#    def get_ascii_normal_form(self):
#        #XXX THIS METHOD SHOULD BE RENAMES TO GUESS_NORMAL_FORM, BUT KEEPING IT HERE BECOASE NAMENINDEX_REPOSITORY CACHE DEPENDS ON IT BEING NAMED THUS
#        return self.guess_normal_form()
#        return to_ascii(self.guess_normal_form())
        
#    def get_ascii_geslachtsnaam(self):
#        return to_ascii(self.geslachtsnaam())
    
    

    def _tokenize(self):
        _root = self._root
        tokens = TokenDict() 
        for w, tail in words(self._root.text):
            tokens.append(Token(w, tail=tail))
        for n in self._root:
            for w, tail in words(n.text):
                tokens.append(Token(w, n.get('type'), tail=tail))
            if n.tail:
                m =  re.match('\s*', n.tail)
                if m:
                    tokens[-1]._tail += n.tail[:m.end()]
            for w, tail in words(n.tail):
                tokens.append(Token(w, None, tail=tail))
        return tokens
    
    def _detokenize(self, tokens):
        """Return a etree.Element represenation of the TokenDict
      
        arguments:
            tokens : a TokenDict instance
        returns:
            en etree.Element instance
            
        XXX: might want to move this funcion to TokenDict
        """
        persName = etree.Element('persName') #@UndefinedVariable
        new_el = None
        for i, token in enumerate(tokens):
            w = token.word()
            ctype = token.ctype()
            #insert a space before

            if ctype not in self._constituents:
                #we have an unknown type, and just add the text to the XML
                if new_el is None: #if we have a subelement, we add it to the tail of the elmeent
                    if persName.text:
                        persName.text += '%s%s' % (w, token.tail())
                    else:
                        persName.text = '%s%s' % (w, token.tail()) 
                else:
                    if new_el.tail:
                        new_el.tail += '%s%s' % (w, token.tail())
                    else:
                        new_el.tail =  '%s%s' % (w, token.tail()) 
            else: #we have a ctype type and add a new XML element
                if token.prev() and token.prev().ctype() == ctype and new_el is not None:
                    #if the previously added subelement is of the same type
                    new_el.text += token.prev().tail() + token.word() 
                    new_el.tail = token.tail()
                else:
                    new_el = etree.SubElement(persName, 'name')#@UndefinedVariable
                    new_el.text = w
                    new_el.set('type', ctype)
                    new_el.tail = token.tail() 
        return persName 
    
    def _guess_constituent_tokens(self, constituents=None):
        """Try to guess as many constituents as possible in the string
        
        returns:
            a TokenDict instance
        side effects:
            cachee the result in self._tokens
        """
        
        try:
            return self._tokens
        except AttributeError:
            pass
        tokens = self._tokenize()
       
        _divisor_token = None
        _default_token = None
        if not tokens:
            return TokenDict() 
        
        #first round - we tag evertyhing that we know for sure  
        for token in tokens:
            w = token.word()
            ctype = token.ctype()
            if not ctype:
                if w in ',-':
                    token._ctype = w 
                    if w == ',':
                        _divisor_token = token
                    elif w == '-' and token.tail() and token.prev().tail():
                        _divisor_token = token
                #intrapositions
                elif w  in TUSSENVOEGSELS:
                    token._ctype = TYPE_INTRAPOSITON
                    _default_token = TYPE_FAMILYNAME #everything that folloows an intraposition is, by default, a given name
                elif w in PREFIXES:
                    token._ctype = TYPE_FAMILYNAME
                    _default_token = TYPE_FAMILYNAME #everything that folloows an prefix is, by default, a given name
                    
                elif is_initials(token):
                    token._ctype = TYPE_GIVENNAME
                    if not token.prev():
                        #if the name starts with initials, we take everything that follows and that is not an initial as a fmaily name
                        _default_token = TYPE_FAMILYNAME
                elif w in  ROMANS_FROZENSET:
                    token._ctype = TYPE_GIVENNAME
                    #if there is somethign before that has not been tagged yet, it must be of type_Givenname
                    ntoken = token
                    while ntoken.prev() and not ntoken.prev()._ctype:
                        ntoken = ntoken.prev()
                        ntoken._ctype= TYPE_GIVENNAME
                elif w in POSTFIXES:
                    token._ctype= TYPE_POSTFIX
                elif w in TERRITORIALE_TITELS:
                    token._ctype = TYPE_TERRITORIAL 
                    if next(token) and token.next().word() in ['van']:
                        #everything of the form "Graaf van ... " becomes of type_territorial
                        token.next()._ctype = TYPE_TERRITORIAL
                        _default_token = TYPE_TERRITORIAL
                        _divisor_token = token
                elif w in  VOORVOEGSELS:
                    token._ctype = TYPE_PREPOSITION
                elif re.match('\(.*\)$', token.word()):
                    token._ctype = '_bracketed'
                else:
                    token._ctype = _default_token
        #(but we leave the brackets in "Ha(c)ks")
#        name = re.sub(r'(?<!\w)\(.*?\)', '', name)
#        name = name.strip()
        if _divisor_token:
            #if there is a ", " in the name, everything that comes before is the family name
            #e.g. 'Alighieri, Dante'
            #(not that this goes wrong with 'John Johnson, MD)'
            #identify our token and make sure it is of the correct form
            _pre = True
            for token in tokens:
                if token == _divisor_token:
                    _pre = False 
                if not token.ctype():
                    if _pre:
                        token._ctype = TYPE_FAMILYNAME
                    else:
                        token._ctype = TYPE_GIVENNAME

            #if we know the first token is a given name 
            for token in tokens:
                if not token.ctype():
                    token._ctype = TYPE_FAMILYNAME
                
#        elif ' - ' in name: #a real use case: "Hees - B.P. van"
#            guessed_name = name.split(' - ')[0] 
#            guessed_name = (0, len(guessed_name))

#            #if the naa starts with initals, we filter those, and the rest is the family name
#            guessed_name = (re.match('(Th\.|[A-Z]\.)+\s*',name).end(), len(name)) 
#            
        elif tokens[-1].word() in ROMANS_FROZENSET:
            #if the name ends with a roman numeral, (as in "Karel II"), it will be considered part of the given name
            #(cf. http://www.biografischportaal.nl/about/biodes/persoonsnamen)
            #(XXX: note American names as well, such as "John Styuivesandt III"
            for token in tokens:
                if not token.ctype():
                    token._ctype = TYPE_GIVENNAME
        elif is_initials(tokens[-1]):
            #the name ends with intitials
            for token in tokens:
                if not token.ctype():
                    token._ctype = TYPE_FAMILYNAME
         
        elif tokens[-1].word().isdigit():
            #this is a weird case - we just tag everything as familyname
            for token in tokens:
                token._ctype = TYPE_FAMILYNAME
        elif tokens[-1].word() in POSTFIXES or tokens[-1].ctype() == '_bracketed':
            if len(tokens) == 1:
                pass
            else:
                if not tokens[-2].ctype():
                    tokens[-2]._ctype = TYPE_FAMILYNAME
                for token in tokens:
                    if not token.ctype():
                        token._ctype = TYPE_GIVENNAME
            
            
        elif is_initials(tokens[-1]):
            for token in tokens[:-1]:
                token._ctype = TYPE_FAMILYNAME
#            elif re.match('(Th\.|[A-Z]\.)+',candidates[-1].group()):
##                 only initials in last element
#                guessed_name = (0, candidates[-2].end()) 

        else:
            tokens[-1]._ctype = TYPE_FAMILYNAME
            for token in tokens:
                if not token.ctype():
                    token._ctype = TYPE_GIVENNAME
            
        if '-' in tokens.types():
            #this case should cover that of married women
            token = [t for t in tokens if t.ctype() == '-'][0]
            if not token.tail() and next(token) and token.next().ctype() in [TYPE_INTRAPOSITON, TYPE_FAMILYNAME] and token.prev() and not token.prev().tail():
                token.prev()._ctype = TYPE_FAMILYNAME
                token.next()._ctype = TYPE_FAMILYNAME
                token._ctype = TYPE_FAMILYNAME
#        else:
#            guessed_name = (0, len(name ))
#            
#        #special case is that of married women, such as 'Angela Boter-de Groot' 
#        #(in which case ??
#        if '-' in name:
#            for intraposition in TUSSENVOEGSELS:
#                if '-%s' % intraposition in name:
#                    i = name.find('-%s' % intraposition)
#                    if i > -1:
#                        start, end = self._guess_geslachtsnaam_in_string(name[:i], hints) 
#                        guessed_name = (start, len(name))
#
        self._tokens = tokens
        return self._tokens
    
    def _guess_constituents(self, constituents=None):
        return self._detokenize(self._guess_constituent_tokens(constituents=constituents))
    
Naam = Name #for backwards compatibility
