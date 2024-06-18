#!/usr/local/bin/python
# -*- coding: utf-8 -*-

import unicodedata
import re

from htmlentitydefs import name2codepoint

wordsplit_re =  re.compile('[\w\?\*]+', re.UNICODE)

class TypeChecker:

    def is_url(self, s):
        return s.startswith('http://')
    
def to_ymd(s):
    """take a string of the form "YYYY-MM-DD" (or "YYYY"), terurn a tuple (year, month, date) of three integers
    
    if only 'YYYY' is given, return (year, None, None).
     (etc.)"""
    if not s:
        return
    if s.startswith('-'):
        bce = True
        s = s[1:]
    else:
        bce= False
    s = s + '--'
    y = s.split('-')[0]
    m = s.split('-')[1]
    d = s.split('-')[2]
    if y:
        y = int(y)
        if bce:
            y = -y
    else:
        y = None
    if m:
        m = int(m)
    else:
        m = None
    if d:
        d = int(d)
    else:
        d = None
    return (y, m, d)

def from_ymd(y, m=None, d=None):
    """take a year y, a month m or a d (all integers, or strings represeting integers) and return a stirng in the form "YYYY-MM-DD"
    """
    if not y:
        return ''
    if not unicode(y).isdigit():
        raise TypeError("The argument 'y' must be a number (not %s)" % y)
    if str(y).startswith('-'):
        y = '-' + str(y)[1:].zfill(4)
    if y and m and d:
        return '%s-%s-%s' % (str(y).zfill(4), str(m).zfill(2), str(d).zfill(2)) 
    elif y and m:
        return '%s-%s' % (str(y).zfill(4), str(m).zfill(2))
    elif y:
        return '%s' % (str(y).zfill(4))

def prettifydate(s, lang='nl'):
    """takes a data in normal form (yyyy-mm-dd) and returns a prettier string"""
    if not s:
        return s
    y, m, d = to_ymd(s)
    months = [
        'januari',
        'februari',
        'maart',
        'april',
        'mei',
        'juni',
        'juli',
        'augustus',
        'september',
        'oktober',
        'november',
        'december',
    ]
    if m: 
        mm = months[int(m) -1]
    if d:
        return '%s %s %s' % (d, mm, y)
    elif m:
        return '%s %s' % (mm, y)
    else:
        return '%s' % y
        
    
def coerce_to_unicode(s):
    if type(s) in (type(u''),):
        return s
    else:
        return unicode(s, 'utf-8')

def serialize(n, exclude=[], include_tail=True):
    result = u''
    if n.text:
        result += n.text
    for el in n:
        if el.tag not in exclude and el.attrib.get('type', None) not in exclude:
            result += serialize(el)
        else:
            if el.tail:
                result += el.tail
    if n.tail and include_tail:
        result += n.tail
    return result

def encodable(s, encoding):
    """is s encodable in encoding"""
    if  type(s) != type(r''):
        s = unicode(s)
    try:
        s.encode(encoding)
        return True 
    except UnicodeEncodeError:
        return False 

def coerce_to_ascii(s):
    """try to make the string ascii, by replacing á and à with "a" (etc)"""
    result = ''
    for c in s:
        result += unicodedata.normalize('NFD', c)[0] #cf. http://www.python.org/doc/2.5.2/lib/module-unicodedata.html
#    try:
#        result.encode('ascii') 
#    
#    except UnicodeEncodeError:
#        s = result
#        result = ''
#        for c in s:
#            result = to_ascii.get(c, c)
    result.encode('ascii')
    return result 

def coerce_to_encodable(s, encoding):
    """return a unicode string that does not raise errors if we try to encode it as latin1
    
    (we try to approximate the right result, without using DTML codes"""
    if  type(s) != type(r''):
        s = unicode(s)
    try:
        s.encode(encoding)
    except UnicodeEncodeError:
        if encoding.lower() in ['latin1', 'iso-8859-1']:
            d = {
                 r'\u0192': '&#x0192;', #'LATIN SMALL LETTER F WITH HOOK'
                 r'\u0227': '&#x0227;', #LATIN SMALL LETTER A WITH DOT ABOVE
                 r'\u1ebd': r'ê', #'LATIN SMALL LETTER E WITH TILDE'
                 r'\u03c0': '&#x03c0;', #'L'GREEK SMALL LETTER PI'
                 r'\u2153': '&#x2153;', #''VULGAR FRACTION ONE THIRD' (U+2153)
                 r'\u2018': '\'',
                 r'\u2019': '\'',
                 r'\u0305': '',
                 r'\u201d': '"', #'RIGHT DOUBLE QUOTATION MARK' (U+201D)
                 r'\u0259': '&#x0259;', #shwa 
                 r'\u2154': '&#x2154;',
                 r'\uf0c5': '&#xf0c5;',
                 }
        else:
            pass
        for k, v in d.items():
            s = s.replace(k, v)
        s.encode('latin1')
    return s

def html2unicode(s):
    #replace html characters with unicode codepoints
    keys = name2codepoint.keys()
    keys = [k for k in keys if k not in ['amp', 'gt', 'lt']]
    for k in keys: 
        
        s = s.replace('&%s;' % k,unichr( name2codepoint[k]))
    return s


special_chars = {
    u'ø':'oe',
    u'æ':'a',
    u'ç': 's',
    }
html_codes = {
     r'&aacute;':r'a',
    r'&agrave;':r'a',
    r'&atilde;':r'a',
    r'&auml;':r'a',
    r'&eacute;':r'e',
    r'&egrave;':r'e',
    r'&etilde;':r'e',
    r'&euml;':r'e',
    
    r'&ouml;':r'e',
    r'&ograve;':r'e',
    r'&oacute;':r'e',
    r'&ouml;':r'e',
    r'&uuml;':r'ue',
     r'&uacute;':r'ue', 
              }
def fix_capitals(s):
    """Try to capitalize the name in the right way..
   s 
    """
    
    result = ''
    
    for w, rest in re.findall('(\w+[\']*)([^\w]*)', s, re.UNICODE):
        if w == w.lower():
            pass
        elif w in ROMANS + TUSSENVOEGSELS:
            pass
        elif w.lower() in PREFIXES:
            w = w.lower()
        elif u'.' in w:
            pass
        elif w.startswith('IJ'):
            w = 'IJ' + w[len('IJ'):]
        else:
            w = w.capitalize()
        result += w + rest
    result = result.strip()
    return result

def remove_parenthesized(s):
    """remove everything between parentheses"""
    
    #'(xxx)' becomes 'xxx'
    if s.startswith('(') and s.endswith(')'):
        s = s[1:-1]
    s = re.sub('\(.*?\)', '', s)
    s = remove_double_spaces(s)
    return s
def remove_double_spaces(s):
    s = re.sub('\s+', ' ', s)
    return s

def to_ascii(s):
    """return ascii version of character
    
    >>> to_ascii('é')
    'e'
    >>> to_ascii('&oacute;')
    'o'
    
    #XX this code is very complicated because it handles html strings
    #XXX better, perhaps, to simply avoid these and have Naam store only uncidoe strings
    """
    try:
        new_s = s.decode('ascii')
    except (UnicodeDecodeError, UnicodeEncodeError):
        new_s = ''
        while s:
            c, s = (s[0], s[1:])
            if c == '&':
                if not ';' in s:
                    pass
                else:
                    c, s = s.split(';', 1)
                    if c in name2codepoint:
                        c = name2codepoint[c] 
                    c = unichr(int(c))
            try:
                new_c = special_chars[c]
            except KeyError:
                new_c = unicodedata.normalize('NFD', c)[0]
            new_s += new_c 
    return new_s
#these prefixes will be ignored when sorting, or when creating soundex represenations
PREFIXES =  [ 
    r"'s-",
    r"'s ",
    r"'t ",
    r"t'",
    r"T'",
    r"'t-",
    r"l'",
    r"1'", #this is the numer "1" (a typical OCR artefact)
    r"d'",
    r"'", 
    r"o'",
    ]

POSTFIXES = [
   r'azn.',
   r'Azn.',
   r'cz.',
   r'Cz.',
   r'Hz.',
   r'jr.',
   r'sr.',
   r'Wzn'
   r'Wzn.'
   
]

VOORVOEGSELS = [
   r'dr',                
   r'dr.',                
   r'Dr',
   r'Dr.',
   r'jhr',
   r'jhr.',
   r'Jhr',
   r'mr',
   r'mr.',
   r'Mr',
   r'Mr.',
   r'prof',
   r'prof.',
   r'Prof',
   r'Prof.',
]

TUSSENVOEGSELS = [
    u'à',
    u'\xe0',
    r'd\'',
    r'de',
    r'den',
    r'der',
    r'des',
    r'di',
    r'en', 
    r'het',
    r"in 't",
    r'la',
    r'la', 
    r'le',
    r'of',
    r'van',
    r'ten', 
    r'thoe', 
    r'tot', 
    r"'t",
]

ROMANS = [
    r'I',
    r'II',
    r'III',
    r'IV',
    r'V',
    r'VI',
    r'VII',
    r'VIII', 
    r'IX',
    r'X',
    r'XI',
    r'XII',
    r'XIII',
    r'XIV',
    r'XV',
    r'XVI',
    r'XVII',
    r'XVIII',
    r'XIX',
    r'XX',
]

TERRITORIALE_TITELS = [
    r'baron',
    r'count',
    r'graaf',
    r'gravin',
    r'grootvorstin',
    r'heer',
    r'jhr', 
    r'jhr.',
    r'jonkheer',
    r'keizer', 
    r'keizerin',
    r'koning',
    r'koningin',
    r'prince',
    r'princess',
    r'prins', 
    r'prinses',
    r'vorst',
]

STOP_WORDS = [] + PREFIXES + VOORVOEGSELS + TUSSENVOEGSELS + POSTFIXES + ROMANS + \
    TERRITORIALE_TITELS

R_STOPWORDS = re.compile(u'|'.join([r'\b%s\b' % w for w in STOP_WORDS]), re.UNICODE | re.IGNORECASE)
R_ROMANS = re.compile('|'.join(ROMANS))
R_TUSSENVOEGELS = re.compile('|'.join([r'\b%s\b' % w for w in TUSSENVOEGSELS]), re.UNICODE)

def remove_stopwords(s):
    return R_STOPWORDS.sub('', s).strip()

def remove_tags(s, pattern='<.*?>'):
    return re.sub(pattern, '', s)

def words(s):
    """returns the 'words' in s
    
    words are all white-space o
    
    arguments:
        s is a string
    returns:
        a list of strings
    """
    if s:
        return wordsplit_re.findall(s) 
    else:
        return []
