from typing import Dict, List, Set, Union
from collections import Counter, defaultdict
import json
import os
import re
import pickle
import unicodedata
import math

from fuzzy_search.fuzzy_string import text2skipgrams
from nltk.tokenize import sent_tokenize
from elasticsearch import Elasticsearch


def make_term_query(term: str) -> Dict[str, any]:
    return {
        'query': {
            'bool': {
                'must': [
                    {'match': {'paragraphs.text': term}},
                    {'match': {'type': 'resolution'}}
                ]
            }
        },
        'aggs': {
            'doc_types': {
                'terms': {'field': 'type.keyword'}
            }
        }
    }


def find_term_in_context(es: Elasticsearch, term: str,
                         num_hits: int = 10, context_size: int = 3):
    query = make_term_query(term)
    query['size'] = num_hits
    response = es.search(index='resolutions', body=query)
    pre_regex = r'(\w+\W+){,' + f'{context_size}' + r'}\b('
    post_regex = r')\b(\W+\w+){,' + f'{context_size}' + '}'
    pre_width = context_size * 10
    contexts = []
    for hit in response['hits']['hits']:
        doc = hit['_source']
        for para in doc['paragraphs']:
            for match in re.finditer(pre_regex + term + post_regex, para['text'], re.IGNORECASE):
                main = match.group(2)
                pre, post = match.group(0).split(main, 1)
                context = {
                    'term': term,
                    'term_match': main,
                    'pre': pre,
                    'post': post,
                    'context': f"{pre: >{pre_width}}{main}{post}",
                    'para': para
                }
                contexts.append(context)
    return contexts


def get_word_freq_filename(period: Dict[str, any], word_freq_type: str, data_dir: str) -> str:
    filename = f'period_word_freq-{word_freq_type}-{period["period_start"]}-{period["period_end"]}.pcl'
    return os.path.join(data_dir, filename)


def write_word_freq_file(period: Dict[str, any], word_freq_type: str,
                         word_freq_counter: Counter, data_dir: str) -> None:
    period_word_freq_file = get_word_freq_filename(period, word_freq_type, data_dir)
    with open(period_word_freq_file, 'wb') as fh:
        return pickle.dump(word_freq_counter, fh)


def read_word_freq_file(period: Dict[str, any], word_freq_type: str, data_dir: str) -> Counter:
    period_word_freq_file = get_word_freq_filename(period, word_freq_type, data_dir)
    with open(period_word_freq_file, 'rb') as fh:
        return pickle.load(fh)


def read_word_freq_counter(inventory_config: dict, word_freq_type: str) -> Counter:
    period = inventory_config['spelling_period']
    return read_word_freq_file(period, word_freq_type, inventory_config['data_dir'])


# Turn a Unicode string to plain ASCII, thanks to
# https://stackoverflow.com/a/518232/2809427
def unicode_to_ascii(s):
    return ''.join(
        c for c in unicodedata.normalize('NFD', s)
        if unicodedata.category(c) != 'Mn'
    )


def replace_ck(word):
    vowels = {'a', 'e', 'i', 'o', 'u'}  # 'y' is a diphthong
    parts = word.split('ck')
    rewrite_word = ''
    for pi, curr_part in enumerate(parts[:-1]):
        rewrite_word += curr_part
        next_part = parts[pi + 1]
        # print('curr_part:', curr_part, 'next_part:', next_part, 'rewrite_word:', rewrite_word)
        if len(curr_part) == 0:
            rewrite_word += 'k'
        elif curr_part[-1].lower() not in vowels:
            # ck after a consonant becomes k
            rewrite_word += 'k'
        elif curr_part[-1].lower() in vowels and len(curr_part) >= 2 and curr_part[-2].lower() in vowels:
            # ck after a double vowel becomes k
            rewrite_word += 'k'
        elif len(next_part) == 0 or next_part[0].lower() not in vowels:
            # ck after single vowel and before a consonant becomes k
            rewrite_word += 'k'
        else:
            # ck after a single vowel and before a vowel becomes kk
            rewrite_word += 'kk'
    rewrite_word += parts[-1]
    return rewrite_word


def replace_ae(word):
    if len(word) > 2 and word.startswith('Ae'):
        word = 'Aa' + word[2:]
    parts = word.split('ae')
    rewrite_word = ''
    if word.lower() == 'lunae':
        return word
    for pi, curr_part in enumerate(parts[:-1]):
        rewrite_word += curr_part
        if pi == 0 and len(curr_part) == 2 and curr_part.lower() == 'pr':
            if word == 'prael':
                return 'praal'
            else:
                # latin phrase so ae becomes 'e'
                rewrite_word += 'e'
        elif rewrite_word.lower() == 'portug':
            rewrite_word += 'a'
        else:
            rewrite_word += 'aa'
    rewrite_word += parts[-1]
    return rewrite_word


def replace_gh(word):
    if word.lower() in {'vught'}:
        return word
    if word.lower() in {'dight', 'sigh'}:
        return word.replace('gh', 'ch')
    parts = word.split('gh')
    rewrite_word = ''
    for pi, curr_part in enumerate(parts[:-1]):
        next_part = parts[pi + 1]
        rewrite_word += curr_part
        if len(next_part) >= 3 and next_part[:3].lower() in {'eid', 'eit', 'eyd', 'eyt'}:
            rewrite_word += 'gh'
        elif len(next_part) >= 2 and next_part[:2].lower() in {'uy', 'ui'}:
            rewrite_word += 'gh'
        elif len(next_part) >= 1 and next_part[0].lower() == 't':
            if len(curr_part) >= 3 and curr_part[-3:].lower() in {'sle'}:
                rewrite_word += 'ch'
            elif len(curr_part) >= 3 and curr_part[-3:].lower() in {'vol', 'voe', 'voo', 'ver', 'lee', 'laa', 'lan',
                                                                    'len', 'raa', 'rey', 'rei', 'haa', 'hoo', 'tuy',
                                                                    'tui'}:
                rewrite_word += 'g'
            elif len(curr_part) >= 2 and curr_part[-2:].lower() in {'le', 'ti', 'di', 'ni', 'se'}:
                rewrite_word += 'g'
            elif len(curr_part) >= 2 and curr_part[-2:].lower() == 're':
                rewrite_word += 'ch'
            # gevoecht
            else:
                rewrite_word += 'ch'
        elif len(curr_part) >= 3 and curr_part[-3:].lower() in {'rou'}:
            rewrite_word += 'gh'
        elif len(curr_part) >= 2 and curr_part[-2:].lower() in {'li'}:
            if next_part == '':
                rewrite_word += 'g'
            else:
                rewrite_word += 'ch'
        else:
            rewrite_word += 'g'
    rewrite_word += parts[-1]
    return rewrite_word


def replace_ey(word):
    if word.startswith('Ey'):
        word = 'Ei' + word[2:]
    parts = word.split('ey')
    rewrite_word = ''
    exceptions = {"Hoey", "Bey", "Dey", "Peyrou", "Beyer", "Orkney"}
    if word in exceptions:
        return word
    for pi, curr_part in enumerate(parts[:-1]):
        rewrite_word += curr_part
        if len(parts) > pi + 1 and len(parts[pi + 1]) > 0:
            next_part = parts[pi + 1]
            if len(next_part) >= 2 and next_part[:2] in {'ck'}:
                if len(curr_part) >= 1 and curr_part[-1] in {'t'}:
                    rewrite_word += 'e'
                else:
                    rewrite_word += 'ei'
            elif len(curr_part) >= 1 and curr_part[-1:] in {'l', 'o'}:
                rewrite_word += 'ei'
            elif len(next_part) > 0 and next_part[0] in {'c', 'd', 'g', 'k', 'l', 'm', 'n', 's', 't', 'z'}:
                rewrite_word += 'ei'
            else:
                rewrite_word += 'ey'
        else:
            rewrite_word += 'ei'
    rewrite_word += parts[-1]
    return rewrite_word


def replace_uy(word):
    exceptions = {'Huy', 'Guy', 'Tuyl', 'Stuyling', 'celuy', 'Vauguyon', 'Uytters'}
    if word in exceptions:
        return word
    if word[:2] == 'Uy':
        if word in {'Uytrecht', 'Uytregt'}:
            return 'Utrecht'
        else:
            word = 'Ui' + word[2:]
    parts = word.split('uy')
    rewrite_word = ''
    for pi, curr_part in enumerate(parts[:-1]):
        rewrite_word += curr_part
        if len(parts) > pi + 1 and len(parts[pi + 1]) > 0:
            next_part = parts[pi + 1]
            if len(curr_part) >= 3 and curr_part.endswith('app'):
                rewrite_word += 'uy'
            elif len(next_part) > 0 and next_part[0] in {'r'}:
                rewrite_word += 'uu'
            elif len(next_part) > 1 and next_part[:2] in {'cl'}:
                rewrite_word += 'uy'
            elif next_part.startswith('k') or next_part.startswith('ck'):
                if len(curr_part) > 0 and curr_part[-1] in {'c', 'k', 'C', 'K'}:
                    rewrite_word += 'uy'
                else:
                    rewrite_word += 'ui'
            else:
                rewrite_word += 'ui'
        else:
            rewrite_word += 'ui'
    rewrite_word += parts[-1]
    return rewrite_word


def replace_y(word):
    if word[0] == 'Y':
        capital_y = True
        word = 'y' + word[1:]
    else:
        capital_y = False
    parts = word.split('y')
    rewrite_word = ''
    exceptions = {
        'Haye', 'Hoey', 'Meyerye', 'Dey', 'Bey', 'Pays', 'payer', 'Bayreuth', 'Jacoby',
        'York', 'york'
    }
    if word in exceptions:
        return word
    for pi, curr_part in enumerate(parts[:-1]):
        rewrite_word += curr_part
        curr_part = curr_part.lower()
        if len(curr_part) >= 1 and curr_part[-1] in {'u', 'e'}:
            # if 'ey' and 'uy' are not replaced, don't replace 'y' now
            rewrite_word += 'y'
        elif rewrite_word in {'Baronn'}:
            # Baronnye -> Baronnie
            rewrite_word += 'i'
        elif rewrite_word in {'Jul', 'Jun'}:
            # Juny/July -> Juni/Juli
            rewrite_word += 'i'
        elif len(curr_part) >= 3 and curr_part[-3:] in {'hoo', 'koo', 'doo', 'moo', 'noo', 'foo'}:
            # hooy, kooy, dooyen, mooy, nooyt, fooy -> hooi, kooi, dooien, mooi, nooit, fooi
            rewrite_word += 'i'
        elif len(curr_part) >= 4 and curr_part[-4:] in {'troo'}:
            # trooy -> trooi (octrooy -> octrooi)
            rewrite_word += 'i'
        elif pi == 0 and curr_part == '' and len(parts[pi + 1]) > 0 and parts[pi + 1].startswith('e'):
            # ye -> ie (yemand -> iemand)
            rewrite_word += 'i'
        elif pi == 0 and curr_part == '' and len(parts[pi+1]) > 0 and parts[pi+1].startswith('r'):
            # yr -> ier (Yrland -> Ierland, Yrssche -> Ierssche)
            rewrite_word += 'ie'
        elif curr_part.endswith('o') or curr_part.endswith('on'):
            rewrite_word += 'y'
        elif len(parts) > pi + 1 and len(parts[pi + 1]) > 0:
            next_part = parts[pi + 1]
            # print('rewrite_word:', rewrite_word, 'next_part:', next_part)
            if curr_part.endswith('a') and next_part.startswith('r'):
                # ayr -> air
                rewrite_word += 'i'
            elif next_part.startswith('ork'):
                # york -> york (york, new york, newyork)
                rewrite_word += 'y'
            elif len(curr_part) >= 2 and curr_part[-2:] in {'pl', 'Pl'} and next_part.startswith('m'):
                # Plym -> Plym (Plymouth
                rewrite_word += 'y'
            elif curr_part.endswith('g') and next_part.startswith('p'):
                # gyp -> gyp (Egypten)
                rewrite_word += 'y'
            elif curr_part.endswith('e'):
                if next_part.startswith('er'):
                    # eyer -> eier
                    rewrite_word += 'y'
                else:
                    # ey -> ei
                    # should never be reached as replace_ey already changes
                    rewrite_word += 'i'
            elif curr_part.endswith('r') and next_part.startswith('e'):
                # rye -> rie (artillerye -> artillerie)
                rewrite_word += 'i'
            elif curr_part.endswith('aa'):
                rewrite_word += 'i'
            elif curr_part.endswith('a'):
                rewrite_word += 'y'
            else:
                rewrite_word += 'ij'
        elif len(parts[pi+1]) == 0 and len(curr_part) >= 3 and curr_part[-3:] in {'lar', 'nar', 'tar', 'ist'}:
            rewrite_word += 'ie'
        elif len(parts[pi+1]) == 0 and len(curr_part) >= 3 and curr_part[-3:] in {'uar', 'ust'}:
            rewrite_word += 'y'
        elif len(parts[pi+1]) == 0 and len(curr_part) >= 2 and curr_part[-3:] in {'ar'}:
            rewrite_word += 'y'
        elif curr_part.endswith('er'):
            rewrite_word += 'ij'
        elif curr_part.endswith('nn') or curr_part.endswith('rr') or curr_part.endswith('ic'):
            rewrite_word += 'y'
        elif curr_part.endswith('aa'):
            rewrite_word += 'i'
        elif curr_part.endswith('a'):
            rewrite_word += 'y'
        elif curr_part.endswith('b'):
            rewrite_word += 'ij'
        elif rewrite_word in {'h', 's', 'z', 'H', 'S', 'Z'}:
            # hy, sy, zy, Hy, Sy, Zy -> hij, sij, zij, Hij, Sij, Zij
            rewrite_word += 'ij'
        else:
            rewrite_word += 'y'
    rewrite_word += parts[-1]
    if capital_y is True:
        if rewrite_word.startswith('ij'):
            rewrite_word = 'IJ' + rewrite_word[2:]
        elif rewrite_word.startswith('i'):
            rewrite_word = 'I' + rewrite_word[1:]
        elif rewrite_word.startswith('y'):
            rewrite_word = 'Y' + rewrite_word[1:]
        else:
            raise ValueError(f'original word started with Y but rewrite word {rewrite_word} '
                             f'starts with unexpected character')
    return rewrite_word


def replace_t(word):
    exceptions = {'wordt', 'vindt'}
    if word in exceptions:
        return word
    if word == 'duisent':
        return 'duizend'
    if word.endswith('dt'):
        word = word[:-2] + 'd'
    if word.endswith('heit'):
        word = word[:-1] + 'd'
    return word


def normalise_spelling(word: str) -> str:
    replace_word = word
    if 'ck' in replace_word:
        replace_word = replace_ck(replace_word)
    if 'ae' in replace_word.lower():
        replace_word = replace_ae(replace_word)
    if 'gh' in replace_word:
        replace_word = replace_gh(replace_word)
    if 'uy' in replace_word.lower():
        replace_word = replace_uy(replace_word)
    if 'ey' in replace_word.lower():
        replace_word = replace_ey(replace_word)
    if 'y' in replace_word.lower():
        replace_word = replace_y(replace_word)
    if replace_word.lower().endswith('t'):
        replace_word = replace_t(replace_word)
    return replace_word


def normalise_word(orig_word: str, rewrite_dict: Dict[str, any] = None, to_ascii: bool = False) -> str:
    copy_word = orig_word
    if to_ascii:
        copy_word = unicode_to_ascii(copy_word)
    if rewrite_dict is not None and copy_word.lower() in rewrite_dict:
        norm_word = normalise_spelling(rewrite_dict[copy_word.lower()]['most_similar_term'])
        if orig_word.isupper():
            norm_word = norm_word.upper()
        elif orig_word[0].isupper():
            norm_word = norm_word.title()
    else:
        if orig_word[0].isupper():
            copy_word = copy_word.title()
        norm_word = normalise_spelling(copy_word)
    if orig_word.isupper():
        return norm_word.upper()
    elif orig_word[0].isupper():
        return norm_word.title()
    else:
        return norm_word


def sent_to_vocab(sents: List[List[str]], min_freq: int = 5):
    vocab = Counter()
    for si, sent in enumerate(sents):
        if (si + 1) % 100000 == 0:
            print(si + 1, 'sentences parsed, vocab has', len(vocab), 'terms')
        vocab.update(sent)
    return [word for word, freq in vocab.most_common() if freq >= min_freq]


def read_resolution_paragraphs(res_files):
    for res_file in res_files:
        print('parsing file', res_file)
        with open(res_file, 'rt') as fh:
            for line in fh:
                parts = line.strip().split('\t')
                if len(parts) == 2:
                    continue
                elif len(parts) == 3:
                    res_id, para_id, para_text = parts
                    yield {'resolution_id': res_id, 'paragraph_id': para_id, 'text': para_text}


class ResolutionSentences:

    def __init__(self, res_files,
                 lowercase: bool = True,
                 fields: str = 'text',
                 to_ascii: bool = False,
                 rewrite_dict: dict = None,
                 normalise: bool = False,
                 include_punct: bool = False
                 ):
        self.res_files = res_files if isinstance(res_files, list) else [res_files]
        self.lowercase = lowercase
        if fields not in ['text', 'all']:
            raise ValueError('fields must be "text" or "all"')
        self.fields = fields
        self.to_ascii = to_ascii
        self.normalise = normalise
        self.rewrite_dict = rewrite_dict
        self.include_punct = include_punct
        self.split_regex = r'\b' if include_punct else r'\W+'

    def __iter__(self):
        for si, sent in enumerate(self.read_sentences()):
            if self.fields == 'text':
                yield sent['words']
            else:
                yield sent

    def word_tokenize(self, sent):
        sent = sent.lower() if self.lowercase else sent
        return [word for word in re.split(self.split_regex, sent.strip()) if word != '']

    def read_sentences(self):
        for para in read_resolution_paragraphs(self.res_files):
            for si, sent in enumerate(sent_tokenize(para['text'])):
                if self.to_ascii:
                    sent = unicode_to_ascii(sent)
                words = self.word_tokenize(sent)
                if self.normalise or self.rewrite_dict:
                    # print('rewriting')
                    words = [self.rewrite_word(word) for word in words]
                yield {
                    "resolution_id": para["resolution_id"],
                    "paragraph_id": para["paragraph_id"],
                    "sentence_num": si + 1,
                    "text": sent,
                    "words": words
                }

    def rewrite_word(self, word):
        if word in self.rewrite_dict:
            word = self.rewrite_dict[word]['most_similar_term']
        if self.normalise:
            return normalise_spelling(word)
        else:
            return word


def read_rewrite_dictionary(dict_file: str, include_uncertain: bool = False) -> Dict[str, any]:
    """Returns a dictionary of misspelled terms and their correctly spelled variant.
    Input must be a tab-separated file with the following columns:
    - mispelled_term
    - most_similar_term
    - uncertain_word (for cases where the correct spelling is not certain)
    """
    rewrite = {}
    misspelled = {}

    with open(dict_file, 'rt') as fh:
        line = next(fh)
        headers = line.strip().split('\t')
        for line in fh:
            row = line.strip().split('\t')
            term_info = {headers[ci]: cell for ci, cell in enumerate(row)}
            for header in headers:
                if header not in term_info or term_info[header] == '':
                    term_info[header] = False
                elif term_info[header] == 'y':
                    term_info[header] = True
            # skip if word is not actually a misspelling
            if term_info['misspelled_term'] == term_info['most_similar_term']:
                continue
            misspelled[term_info['misspelled_term']] = term_info
            # keep track of which terms should be rewritten
            if term_info['uncertain_word'] is False:
                rewrite[term_info['misspelled_term']] = term_info
    if include_uncertain:
        return misspelled
    else:
        return rewrite


class TermDictionary:

    def __init__(self, term_dict: Dict[str, any] = None, dict_file: str = None,
                 ngram_length: int = 2, skip_length: int = 0):
        self.term_cats = defaultdict(set)
        self.cat_terms = defaultdict(set)
        self.cat_has = defaultdict(set)
        self.cat_of = {}
        self.main_cats = set()
        self.leaf_cats = set()
        self.lower_of = defaultdict(set)
        self.title_of = defaultdict(set)
        self.ngram_length = ngram_length
        self.skip_length = skip_length
        self.skip_sim: SkipgramSimilarity = None
        if dict_file is not None:
            term_dict = read_republic_term_dictionary(dict_file)
        if term_dict is not None:
            self.set_term_dict(term_dict)

    def save(self, dict_file: str):
        with open(dict_file, 'wt') as fh:
            term_dict = {}
            for main_cat in self.main_cats:
                if main_cat in self.leaf_cats:
                    term_dict[main_cat] = list(self.cat_terms[main_cat])
                else:
                    term_dict[main_cat] = {}
                    for sub_cat in self.cat_has[main_cat]:
                        term_dict[main_cat][sub_cat] = list(self.cat_terms[sub_cat])
            json.dump(term_dict, fh, indent=4)

    def set_term_dict(self, term_dict: Dict[str, any], silent: bool = False) -> None:
        self.term_cats = defaultdict(set)
        self.cat_terms = defaultdict(set)
        self.add_term_dict(term_dict, silent=silent)
        self._index_term_skips()

    def _index_term_skips(self):
        self.skip_sim = SkipgramSimilarity(ngram_length=self.ngram_length,
                                           skip_length=self.skip_length,
                                           terms=list(self.term_cats.keys()))

    def add_term_dict(self, term_dict: Dict[str, any], silent: bool = False) -> None:
        for main_cat in term_dict:
            self.add_main_cat(main_cat)
            # print(f'adding main_cat {main_cat}')
            if isinstance(term_dict[main_cat], dict):
                for sub_cat in term_dict[main_cat]:
                    self.add_sub_cat(sub_cat, main_cat)
                    # print(f'adding sub_cat {sub_cat} in main_cat {main_cat}')
                    for term in term_dict[main_cat][sub_cat]:
                        # print(f'adding term {term} to sub_cat {sub_cat}')
                        self.add_term(term, sub_cat)
            else:
                self.add_main_cat(main_cat)
                for term in term_dict[main_cat]:
                    self.add_term(term, main_cat)
        if silent is False:
            print(f'dictionary now has {len(self.main_cats)} main categories, '
                  f'{len(self.leaf_cats)} leaf categories and {len(self.term_cats)} terms')

    def get_term(self, term: str, ignorecase: bool = False) -> Union[str, None]:
        if term in self.term_cats:
            return term
        elif ignorecase and term.title() in self.term_cats:
            return term.title()
        elif ignorecase and term.lower() in self.term_cats:
            return term.lower()
        else:
            return None

    def has_main_cat(self, main_cat: str) -> bool:
        return main_cat in self.main_cats

    def has_sub_cat(self, sub_cat: str) -> bool:
        return sub_cat in self.cat_of

    def has_cat(self, cat: str) -> bool:
        return self.has_main_cat(cat) or self.has_sub_cat(cat)

    def has_term(self, term: str, ignorecase: bool = False) -> bool:
        dict_term = self.get_term(term, ignorecase=ignorecase)
        return dict_term is not None

    def get_term_cats(self, term: str, ignorecase: bool = False,
                      leaf_cats_only: bool = False) -> Set:
        dict_term = self.get_term(term, ignorecase=ignorecase)
        if dict_term is None:
            return set()
        elif leaf_cats_only:
            return {cat for cat in self.term_cats[dict_term] if cat in self.leaf_cats}
        else:
            return self.term_cats[dict_term]

    def get_cat_terms(self, cat: str) -> Set:
        return self.cat_terms[cat] if cat in self.cat_terms else set()

    def add_main_cat(self, main_cat: str) -> None:
        if main_cat in self.cat_has:
            raise KeyError(f'main_cat {main_cat} is already in dictionary')
        self.main_cats.add(main_cat)
        self.leaf_cats.add(main_cat)

    def add_sub_cat(self, sub_cat: str, main_cat: str, add_missing: bool = False) -> None:
        if main_cat not in self.main_cats and add_missing is False:
            raise KeyError(f'unknown main_cat {main_cat}')
        if sub_cat in self.cat_of:
            if self.cat_of[sub_cat] != main_cat:
                raise KeyError(f'sub_cat {sub_cat} is already under {self.cat_of[sub_cat]}')
            else:
                # print(f'sub_cat {sub_cat} is already assigned to {self.cat_of[sub_cat]}')
                return None
        if main_cat in self.leaf_cats:
            # if main_cat had no previous sub_cats, it is still in leaf cats
            self.leaf_cats.remove(main_cat)
        self.cat_has[main_cat].add(sub_cat)
        self.cat_of[sub_cat] = main_cat
        self.leaf_cats.add(sub_cat)

    def add_term(self, term: str, cat: str) -> None:
        if cat not in self.leaf_cats:
            raise KeyError(f'unknown leaf_cat {cat}')
        if cat not in self.leaf_cats:
            raise ValueError(f'cat {cat} is not a leaf_cat')
        self.term_cats[term].add(cat)
        self.cat_terms[cat].add(term)
        if cat in self.cat_of:
            main_cat = self.cat_of[cat]
            # print(f'cat {cat} is a sub_cat of {main_cat}')
            self.term_cats[term].add(main_cat)
            self.cat_terms[main_cat].add(term)
        # else:
            # print(f'cat {cat} is not a sub_cat')

    def remove_term(self, term: str) -> None:
        if term not in self.term_cats:
            raise KeyError(f'unknown term {term}')
        for cat in self.term_cats:
            self.cat_terms[cat].remove(term)
        del self.term_cats[term]

    def remove_term_cat(self, term: str, cat: str) -> None:
        if term not in self.term_cats:
            raise KeyError(f'unknown term {term}')
        # if term no longer has a category, remove the term completely
        if cat not in self.term_cats[term]:
            raise KeyError(f'term {term} is not in cat {cat}')
        self.term_cats[term].remove(cat)
        if len(self.term_cats[term]) == 0:
            self.remove_term(term)
            print(f'term {term} has no other cats, removing term from dictionary')

    def remove_cat(self, cat: str) -> None:
        if cat not in self.cat_terms:
            raise KeyError(f'unknown cat {cat}')
        # remove term cat connection
        for term in self.cat_terms[cat]:
            self.remove_term_cat(term, cat)
        if cat in self.cat_of:
            main_cat = self.cat_of[cat]
            self.cat_has[main_cat].remove(cat)
            del self.cat_of[cat]
        if cat in self.cat_has:
            for sub_cat in self.cat_has[cat]:
                self.remove_cat(sub_cat)
            del self.cat_has[cat]
        if cat in self.leaf_cats:
            self.leaf_cats.remove(cat)
        if cat in self.main_cats:
            self.main_cats.remove(cat)

    def move_sub_cat(self, sub_cat: str, new_main_cat: str) -> None:
        if sub_cat not in self.cat_of:
            raise KeyError(f'cat {sub_cat} is not a sub_cat')
        old_main_cat = self.cat_of[sub_cat]
        # first move terms from current main_cat to new main_cat
        for term in self.cat_terms[sub_cat]:
            self.cat_terms[old_main_cat].remove(term)
            self.term_cats[term].remove(old_main_cat)
            self.cat_terms[new_main_cat].add(term)
            self.term_cats[term].add(new_main_cat)
        # move subcat across main cats
        self.cat_has[new_main_cat].add(sub_cat)
        self.cat_has[old_main_cat].remove(sub_cat)
        # finally, assign new_main_cat as parent of sub_cat
        self.cat_of[sub_cat] = new_main_cat

    @property
    def stats(self):
        return {
            "main_cats": len(self.main_cats),
            "sub_cats": len(self.leaf_cats),
            "terms": len(self.term_cats)
        }


def read_republic_term_dictionary(dict_file: str) -> Dict[str, any]:
    with open(dict_file, 'rt') as fh:
        return json.load(fh)


def write_republic_term_dictionary(term_dict, dict_file: str) -> None:
    with open(dict_file, 'wt') as fh:
        return json.dump(term_dict, fh)


def vector_length(skipgram_freq):
    return math.sqrt(sum([skipgram_freq[skip] ** 2 for skip in skipgram_freq]))


class SkipgramSimilarity:

    def __init__(self, ngram_length: int = 3, skip_length: int = 0, terms: List[str] = None,
                 max_length_diff: int = 2):
        self.ngram_length = ngram_length
        self.skip_length = skip_length
        self.vocab = {}
        self.vocab_map = {}
        self.vector_length = {}
        self.max_length_diff = max_length_diff
        self.skipgram_index = defaultdict(lambda: defaultdict(Counter))
        if terms is not None:
            self.index_terms(terms)

    def _reset_index(self):
        self.vocab = {}
        self.vocab_map = {}
        self.vector_length = {}
        self.skipgram_index = defaultdict(lambda: defaultdict(Counter))

    def index_terms(self, terms: List[str], reset_index: bool = True):
        if reset_index is True:
            self._reset_index()
        for term in terms:
            if term in self.vocab:
                continue
            self._index_term(term)

    def _term_to_skip(self, term):
        skip_gen = text2skipgrams(term, ngram_size=self.ngram_length, skip_size=self.skip_length)
        return Counter([skip.string for skip in skip_gen])

    def _index_term(self, term: str):
        term_id = len(self.vocab)
        self.vocab[term] = term_id
        self.vocab_map[term_id] = term
        skipgram_freq = self._term_to_skip(term)
        self.vector_length[term_id] = vector_length(skipgram_freq)
        for skipgram in skipgram_freq:
            # print(skip.string)
            self.skipgram_index[skipgram][len(term)][term_id] = skipgram_freq[skipgram]

    def _get_term_vector_length(self, term, skipgram_freq):
        if term not in self.vocab:
            return vector_length(skipgram_freq)
        else:
            term_id = self.vocab[term]
            return self.vector_length[term_id]

    def _compute_dot_product(self, term):
        skipgram_freq = self._term_to_skip(term)
        term_vl = self._get_term_vector_length(term, skipgram_freq)
        print(term, 'vl:', term_vl)
        dot_product = defaultdict(int)
        for skipgram in skipgram_freq:
            for term_length in range(len(term) - self.max_length_diff, len(term) + self.max_length_diff + 1):
                for term_id in self.skipgram_index[skipgram][term_length]:
                    dot_product[term_id] += skipgram_freq[skipgram] * self.skipgram_index[skipgram][term_length][
                        term_id]
                    # print(term_id, self.vocab_map[term_id], dot_product[term_id])
        for term_id in dot_product:
            dot_product[term_id] = dot_product[term_id] / (term_vl * self.vector_length[term_id])
        return dot_product

    def rank_similar(self, term: str, top_n: int = 10):
        dot_product = self._compute_dot_product(term)
        top_terms = []
        for term_id in sorted(dot_product, key=lambda t: dot_product[t], reverse=True):
            term = self.vocab_map[term_id]
            top_terms.append((term, dot_product[term_id]))
            if len(top_terms) == top_n:
                break
        return top_terms
