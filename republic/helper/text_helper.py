from typing import Dict, List, Set, Union
from collections import Counter, defaultdict
import json
import os
import re
import pickle
import unicodedata

from nltk.tokenize import sent_tokenize


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
    parts = word.split('gh')
    if word.lower() in {'vught'}:
        return word
    if word.lower() in {'dight'}:
        return 'dicht'
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


def normalise_spelling(word):
    replace_word = word
    if 'ck' in replace_word:
        replace_word = replace_ck(replace_word)
    if 'ae' in replace_word:
        replace_word = replace_ae(replace_word)
    if 'gh' in replace_word:
        replace_word = replace_gh(replace_word)
    return replace_word


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
                 normalise: bool = False
                 ):
        self.res_files = res_files if isinstance(res_files, list) else [res_files]
        self.lowercase = lowercase
        if fields not in ['text', 'all']:
            raise ValueError('fields must be "text" or "all"')
        self.fields = fields
        self.to_ascii = to_ascii
        self.normalise = normalise
        self.rewrite_dict = rewrite_dict

    def __iter__(self):
        for si, sent in enumerate(self.read_sentences()):
            if self.fields == 'text':
                yield sent['words']
            else:
                yield sent

    def word_tokenize(self, sent):
        sent = sent.lower() if self.lowercase else sent
        return [word for word in re.split(r"\W+", sent.strip()) if word != '']

    def read_sentences(self):
        for para in read_resolution_paragraphs(self.res_files):
            for si, sent in enumerate(sent_tokenize(para['text'])):
                if self.to_ascii:
                    sent = unicode_to_ascii(sent)
                words = self.word_tokenize(sent)
                if self.rewrite_dict:
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

    def __init__(self, term_dict: Dict[str, any] = None, dict_file: str = None):
        self.term_cats = defaultdict(set)
        self.cat_terms = defaultdict(set)
        self.cat_has = defaultdict(set)
        self.cat_of = {}
        self.main_cats = set()
        self.leaf_cats = set()
        self.lower_of = defaultdict(set)
        self.title_of = defaultdict(set)
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

    def add_term_dict(self, term_dict: Dict[str, any], silent: bool = False) -> None:
        for main_cat in term_dict:
            self.add_main_cat(main_cat)
            if isinstance(term_dict[main_cat], dict):
                for sub_cat in term_dict[main_cat]:
                    self.add_sub_cat(sub_cat, main_cat)
                    for term in term_dict[main_cat][sub_cat]:
                        self.add_term(term, sub_cat)
            else:
                self.add_main_cat(main_cat)
                for term in term_dict[main_cat]:
                    self.add_term(term, main_cat)
        if silent is False:
            print(f'dictionary now has {len(self.main_cats)} main categories,'
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
        return dict_term is None

    def get_term_cats(self, term: str, ignorecase: bool = False) -> Set:
        dict_term = self.get_term(term, ignorecase=ignorecase)
        if dict_term is None:
            return set()
        else:
            return self.term_cats[term]

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
                return None
        if main_cat in self.leaf_cats:
            # if main_cat had no previous sub_cats, it is still in leaf cats
            self.leaf_cats.remove(main_cat)
        self.cat_has[main_cat].add(sub_cat)
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
            self.term_cats[term].add(main_cat)
            self.cat_terms[main_cat].add(term)

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
