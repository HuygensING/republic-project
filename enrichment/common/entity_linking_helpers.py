from fuzzy_search import PhraseModel, FuzzyPhraseSearcher
from fuzzy_search.phrase.phrase import Phrase
from fuzzy_search.match.phrase_match import PhraseMatch
from multiprocess import Pool
from tqdm.notebook import tqdm
from entity_match import *
import csv, re, os, sys

import os, sys
original_stdout = sys.stdout
devnull = open(os.devnull, 'w')

repo_name = 'republic-project'
repo_dir = os.getcwd().split(repo_name)[0] + repo_name
if repo_dir not in sys.path:
    sys.path.append(repo_dir)

CPU_CORES = 8
REGEX_SPELLING_FILE = f'{repo_dir}/enrichment/criteria/common/spelling-regexes.tsv'
FUZZY_SPELLING_FILE = f'{repo_dir}/enrichment/criteria/common/fuzzy-corrections.tsv'
INVENTORY_METADATA_FILE = f'{repo_dir}/data/inventories/inventory_metadata.tsv'

# saving metadata

jaargangen = { }

with open(INVENTORY_METADATA_FILE) as file:
    for row in csv.DictReader(file, delimiter='\t'):
        y = row['year_start'][0:4]
        if y == '':
            jaargangen[row['inventory_num']] = None
        else:
            jaargangen[row['inventory_num']] = int(y)

# applying the fuzzy searcher

def make_searcher(config, phrases):
    '''
    example_config = {
        'ngram_size': 3,
        'skip_size': 1,
        'include_variants': True,
        'ignorecase': True,
        'char_match_threshold': 0.7,
        'ngram_threshold': 0.7,
        'levenshtein_threshold': 0.7,
    }
    example_phrases = {
        { 'label': 'LABEL', 'phrase': 'MAINPHRASE', 'variants': [ 'VARIANTS', ... ] },
        ...
    }
    '''
    phrase_model = PhraseModel(model=phrases, config=config)
    phrase_searcher = FuzzyPhraseSearcher(config=config)
    phrase_searcher.index_phrase_model(phrase_model=phrase_model)
    return phrase_searcher

def score_match(m):
    if isinstance(m, PhraseMatch):
        if m.levenshtein_similarity is not None:
            return (m.levenshtein_similarity + m.character_overlap + m.ngram_overlap) / 3
    return 0

def choose_best_matches(matches):
    '''
    Filters out double matches on the same phrase.
    '''
    res = {}
    for m in matches:
        if m.label not in res or score_match(m) > score_match(res[m.label]):
            res[m.label] = m
    return list(res.values())

# running queries in parallel

def search_in_parallel(lst, search_fn, post_fn=None, cores=CPU_CORES):
    '''
    The `search_fn` may manipulate the items in the list;
    if a return value is required, a `post_fn` must be given to operate on the 
    list of return values of `search_fn`.

    During the run, we suppress `sys.stdout`, since fuzzy_search prints many 
    annoying messages that cannot be turned off.
    '''
    sys.stdout = devnull
    with Pool(cores) as p:
        res = list(tqdm(p.imap(search_fn, lst), total=len(lst)))
        res = [r for r in res if r]
        sys.stdout = original_stdout
        if post_fn is not None:
            post_fn(res)

# spelling harmonisation and error correction

spelling_regexes = [ ]
spelling_extras = [ ]
spelling_keywords = [ ]

spelling_searcher = None

spelling_config = {
    'ngram_size': 3,
    'skip_size': 1,
    'include_variants': True,
    'ignorecase': True,
    'char_match_threshold': 0.7,
    'ngram_threshold': 0.7,
    'levenshtein_threshold': 0.7,
}

def init_spelling(config=spelling_config):
    """
    We regularise entity references in two steps: first by means of regular 
    expressions, then by fuzzy matching on a keyword list.

    Extra (entity-class-specific) regexes can be given in spelling_extras, as 
    tuples `(pat,repl)`.
    """

    global spelling_regexes, spelling_extras, spelling_keywords, spelling_searcher

    spelling_regexes = [ ]
    spelling_keywords = [ ]

    with open(REGEX_SPELLING_FILE) as file:
        for (pat, repl, _) in csv.reader(file, delimiter='\t'):
            spelling_regexes.append((re.compile(pat), repl))

    with open(FUZZY_SPELLING_FILE) as file:
        for row in csv.reader(file, delimiter='\t'):
            if len(row) >= 1 and row[0][0] != '#':
                spelling_keywords.append(
                    { 'label': row[0]
                    , 'phrase': row[0]
                    , 'variants': row[1:]})

    spelling_searcher = make_searcher(config, spelling_keywords)

init_spelling()

def harmonise_spelling(s: str) -> str:
    """
    Returns both the harmonised string and detected fuzzy keywords.
    """

    for (pat, repl) in spelling_regexes:
        s = pat.sub(repl, s)
    for (pat, repl) in spelling_extras:
        s = pat.sub(repl, s)

    saved_stdout = sys.stdout
    sys.stdout = devnull
    matches = choose_best_matches(spelling_searcher.find_matches(s))
    sys.stdout = saved_stdout
    matches = sorted(matches, key=score_match, reverse=True)
    matches = [ (m.string, m.phrase.phrase_string) for m in matches ]
    # ensure plurals stay plurals
    matches = [ (pat, repl) for (pat, repl) in matches
        if (pat != repl) and (pat[-3:]!=' en')
        and ((pat[-2:]=='en') == (repl[-2:]=='en'))
        and ((pat[-1:]=='s') == (repl[-1:]=='s')) ]

    for (pat, repl) in matches:
        for (p, r) in spelling_regexes:
            repl = p.sub(r, repl)
        s = s.replace(pat, repl, 1)

    return s, matches

