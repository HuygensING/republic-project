try:
    import re2 as re
except ImportError:
    import re

from common import STOP_WORDS, ROMANS, PREFIXES, to_ascii, words
#from plone.memoize.ram import cache
STOP_WORDS_frozenset = frozenset(STOP_WORDS)
ROMANS_frozenset = frozenset(ROMANS)
#GROUPS2 defines a somewhat stricter soundex expression than GROUPS1 - fewer words have the same expression
_GROUPS2 = (
            ('', ['^%s' % s for s in PREFIXES]),
            ('' ,['[^a-z\?\*]']), # #remove all non-alphabetical characters, 
#            ('' ,[r'\(', r'\)']),  #remove brackets (
            ('jan', ['^johannes$','^johan$',]),
            ('end', ['eind$',]), #are we sure we want to be this specific?
            ('sz', ['szoon$',]), #are we sure we want to be this specific?
            ('tjes', ['tges$',]), 
            ('uut', ['^wt',]), 
            ('boom', ['baum'],), #are we sure that we want to be this specific? 
            ('huis', ['haus', 'husius$'],),
            ('berg', ('burg',)),
            ('woud', ('wold',)),
            ('jau', ('iau',)),
            ('ie', ('ieuw','ieu',)),
            ('o', ('eaux$', )),
            ('ng', ['(?<=i)ngk$', '(?<=i)nk$','(?<=i)nck'],), 
            ('na', ['naar$',]),
            ('', ('(?<=der)s$',)),
            ('ek', ('ecque$',)), #fransche namen
            ('elle', ('eille',)),
            ('rs', ('(?<=[aeiou])(rts|rds|rdz|rtz)(?=(e|$|k))',)),
            ('mm', ('(?<=[aeiou])(mb)(?=[e])',)),
            ('s',['sz', 'z',  '(?<!^)sch', '(?<!^)ssch','sch(?=[mnr])','(?<=[i])ch(?=[aeiou])','sc(?=[aeiou])', 'ss','(?<=.)c(?=[oi])']), #match 'sch' except when it is the start of the string 
            ('', ('(?<=..[bdfgjklmnprstvwzy])en$',)), #en at the end of a word that is not too short, preceded by a consonant, is completely ignored
            ('', ('(?<=..[bdfgjklmnprstvwzy])e$',)), #e at the aned of a word preceded by a consonant
#            ('', ('(?<=en)s$',)),
            ('', ('(?<=..[bdfgjklmnprstvwzy])ens$',)),
            
            ('', ('(?<=.....)a$',)),
            ('em', ('(?<=.)um$',)),
            ('e', ['en(?=[bdfklmnpqrstvwz][^s].)',]), #tussen -n
            ('k', ['cq$', 'ck$', 'q$']),
            ('q', ['kw', 'qu', 'q']),
            ('ute', ['^uite', '^uyte']), #not so sure about the generality of this
            ('7',['uy','uij', 'ui', ]), #'(?<=[^o])oij',  '(?<=[^o])oi', ]), 
            ('6',['ouw','aauw', 'auw', 'ou', 'au',  ]), #these become 'au' 
            ('5',['ue', 'uu','uh', ]), #these become 'u'
            ('4',['oh', 'oo', 'oe' , ]), #these come 'o' 
            ('1',['ah', 'ae','a']), #these become 'a' 
            ('3',['eij',  'ey', 'ij', 'ie', 'i',  'y','eei', 'ei', 'ie']), #these become 'i'
            ('2',['ee', 'eh','e', '(?<=.)a$']), #a at the and of a word longer than 1 char) these become 'e'
#            ('ei', ['eij', 'ey', 'y']), 
            ('p',['pp']), 
            ('b',['bb']), 
            ('g',[ 'ngh','ch', 'gg', 'gh', 'ng',]), 
            ('k',['cks','ck', 'ks','c', 'kx', 'x', 'kk', ]),
            ('t',[ 'tt', 'd$', 'dt$', 'th','d(?=s)','(?<=n)dt','(?<=n)d',]),
            ('d',[ 'dd']),
            ('f',['ph', 'v', 'w', 'ff']),
#            ('h',[]),
            ('l',['ll']),
            ('n',['nn', ]), 
            ('m',['mm']), 
            ('r',['rh', 'rr'] ), 
            ('a', [r'1+'],),
            ('e', [r'2+']),
            ('i', [r'3+']),
            ('o', [r'4+']),
            ('u', [r'5+']),
#            ('au',[r'6+']),
            ('o',[r'6+']),
            ('ui', [r'7+']),
#            ('', '1234567890')
)


#GROUPS1 defines the 'loose' soundex expression - many words have the same expression
_GROUPS1 = _GROUPS2 + (
            ('' ,['^h']), # strip h at start 
            ('k' ,['q']), #  q becomes k 
            ('p' ,['b']), #  b becomes p 
            ('t' ,['d']), #  d becomes t 
            ('.',['ah', 'eh','ij', 'a', 'e', 'i', 'o','u','y',]), #all consonants go away
            ('.', [r'\.+',]    ), 
)

#_GROUPS1 = [(k, '|'.join(ls)) for k, ls in GROUPS1]
#_GROUPS2 = [(k, '|'.join(ls)) for k, ls in GROUPS2]
#GROUPS1_SINGLEREGEXP = re.compile('|'.join(["(%s)" % v for k, v in _GROUPS1]))
#GROUPS2_SINGLEREGEXP = re.compile('|'.join(["(%s)" % v for k, v in _GROUPS2]))
#GROUPS1_LOOKUP = dict((i+1, k) for (i, (k,v)) in enumerate(GROUPS1))
#GROUPS2_LOOKUP = dict((i+1, k) for (i, (k,v)) in enumerate(GROUPS2))
GROUPS1 = [(k, re.compile('|'.join(ls))) for k, ls in _GROUPS1]
GROUPS2 = [(k, re.compile('|'.join(ls))) for k, ls in _GROUPS2]

def dict_sub(d, text): 
    """ Replace in 'text' non-overlapping occurences of REs whose patterns are keys
    in dictionary 'd' by corresponding values (which must be constant strings: may
    have named backreferences but not numeric ones). The keys must not contain
    anonymous matching-groups.
    Returns the new string.""" 
    
    # Create a regular expression  from the dictionary keys
    regex = re.compile("|".join("(%s)" % k for k in d))
    # Facilitate lookup from group number to value
    lookup = dict((i+1, v) for i, v in enumerate(d.itervalues()))
    
    # For each match, find which group matched and expand its value
    return regex.sub(lambda mo: mo.expand(lookup[mo.lastindex]), text)
    
               
def multiple_replace(dict, text): 
    """ Replace in 'text' all occurences of any key in the given
    dictionary by its corresponding value.  Returns the new tring.""" 
    
    # Create a regular expression  from the dictionary keys
    regex = re.compile("(%s)" % "|".join(map(re.escape, dict.keys())))
    
    # For each match, look-up corresponding value in dictionary
    return regex.sub(lambda mo: dict[mo.string[mo.start():mo.end()]], text) 
    
def soundexes_nl(s, length=-1, group=2, 
     filter_stop_words=True, 
     filter_initials=False, 
     filter_custom=[], #a list of words to ignore
     wildcards=False):
    """return a list of soundexes for each of the words in s
   
    arguments:
        s - a string
	    filter_stop_words : filter stop words such as "van" en "of" 
	    wildcards: if True, leave '?' and '*' in place
	returns:
	    a list of strings
    """
    if not s:
        return []
    #splits deze op punten, spaties, kommas, etc
    #ls = re.split('[ \-\,\.]', s.lower())
#    s = s.lower()
    ls = words(s) 
    
    #filter een aantal stopwoorden
    if filter_stop_words:
        ls = [s for s in ls if s not in STOP_WORDS_frozenset]
        
    if filter_custom:
        ls = [s for s in ls if s not in filter_custom]
    #filter initials  - these are all words of lenght 1
    if len(ls) > 1 and  filter_initials and  len(ls) > 1:
        ls = [s for s in ls[:] if len(s) > 1]

    result  = [soundex_nl(s, length=length, group=group, wildcards=wildcards) for s in ls] 
    result = list(set(result)) #remove duplicates
    return result

def _cache_key(funcobj, s, length=4, group=1, wildcards=False):
    return "%s%i%i%i" % (s.encode('utf8'), length, group, wildcards)
    
#@cache(_cache_key)
def soundex_nl(s, length=4, group=1, wildcards=False):
    """
    return a string of length representing a phonetical canonical form of s
    stab at giving names a simplified canonical form based on Dutch phonetics and spelling conventions
    
    arguments:
        s : a string
        length : an integer. Length=-1 transforms the whole string
        group : an integer [1, 2]
        wildcards : if True, wildcard element (?, *) remain in place
    
    There are two groups:
        - group 1: identify lots
        - groep 2: identify somewhat less (stay close to actual phonetics)
        
    """
    #ignore Romans
    if s in ROMANS_frozenset:
        return s
    
    s = s.lower()
    s = to_ascii(s)
    if not wildcards:
        #remove 'wildcard' characters
        s = s.replace('*', '').replace('?', '')

    #strip off certain prefixes
    #XXX this should be in the regular expression specs
#    for x in PREFIXES:
#        if s.startswith(x):
#            s = s[len(x):]
    if group == 1:
        groups = GROUPS1
    elif group == 2:
        groups = GROUPS2 
    else:
        raise Exception('"group" argument must be either 1 or 2')

    s = apply_regexps(s, groups)

    if s.endswith('.'):
        s = s[:-1]
    if not s: 
        s = u'.'
    if length > 0:
        s = s[:length]
        
    s = unicode(s)
    return s

def apply_regexp(partial, retuple):
    return retuple[1].sub(retuple[0], partial)
def apply_regexps(original_string, regexps):
    return reduce(apply_regexp, regexps, original_string)
# The above two functions are an optimized version of the code below.
# The use of ``reduce`` allows us to spare the for loop
#    result = original_string
#    for substitution, regexp in regexps:
#        result = regexp.sub(substitution, result)
#    return result
