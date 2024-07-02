import copy
import gzip
import json
import math
import os
import pickle
import re
import unicodedata
from collections import Counter, defaultdict
from typing import Callable, Dict, List, Set, Union

from fuzzy_search.tokenization.string import text2skipgrams
from fuzzy_search.tokenization.token import Doc
from fuzzy_search.tokenization.token import Tokenizer
from nltk.tokenize import sent_tokenize
from langdetect import detect_langs, LangDetectException
import pagexml.model.physical_document_model as pdm


class ResolutionSentences:

    def __init__(self, res_files,
                 lowercase: bool = True,
                 fields: str = 'text',
                 to_ascii: bool = False,
                 rewrite_dict: dict = None,
                 normalise: bool = False,
                 include_punct: bool = False,
                 split_pattern: str = None,
                 tokenise_sentences: bool = False,
                 includes_headers: bool = True,
                 use_headers: List[str] = None,
                 pre_tokenise_func: Callable = None,
                 pre_tokenise_field: str = None,
                 as_doc: bool = True,
                 debug: int = 0):
        self.res_files = res_files if isinstance(res_files, list) else [res_files]
        self.lowercase = lowercase
        if fields not in ['text', 'all']:
            raise ValueError('fields must be "text" or "all"')
        self.fields = fields
        self.to_ascii = to_ascii
        self.normalise = normalise
        self.rewrite_dict = rewrite_dict
        self.include_punct = include_punct
        self.tokenise_sentences = tokenise_sentences
        self.includes_headers = includes_headers
        self.use_headers = use_headers
        self.pre_tokenise_func = pre_tokenise_func
        self.pre_tokenise_field = pre_tokenise_field
        self.as_doc = as_doc
        self.doc_tokenize = Tokenizer(ignorecase=lowercase)
        self.debug = debug
        if split_pattern is None:
            # by default use all characters from string.punctuation, except
            # the hyphen, as we want to keep hyphenated words as one.
            split_chars = r'[\!"#$%&\'\(\)\*\+,\./:;<=>?@\[\\\]^\_`{|}~ ]+'
            split_pattern = re.compile(split_chars)
        self.split_regex = r'\b' if include_punct else split_pattern

    def __iter__(self):
        id_field = 'res_id'
        if self.use_headers:
            for header in self.use_headers:
                if header.endswith('_id'):
                    id_field = header
                    break
        if self.tokenise_sentences:
            if self.debug > 0:
                print('using sentences as document level')
            reader = self.read_sentences()
        else:
            if self.debug > 0:
                print('using paragraphs as document level')
            reader = self.read_paragraphs()
        if self.as_doc is True:
            for doc in reader:
                doc_id = doc[id_field] if id_field in doc else None
                metadata = {field: doc[field] for field in doc if field not in {'text', id_field}}
                doc = self.doc_tokenize.tokenize(doc['text'], doc_id)
                doc.metadata = metadata
                yield doc
        else:
            for doc in reader:
                yield self.dict_tokenize(doc)

    def dict_tokenize(self, doc):
        if self.to_ascii:
            doc['text'] = unicode_to_ascii(doc['text'])
        doc['words'] = self.word_tokenize(doc['text'])
        if self.normalise or self.rewrite_dict:
            # print('rewriting')
            doc['words'] = [self.rewrite_word(word) for word in doc['words']]
        if self.fields == 'text':
            return doc['words']
        else:
            return doc

    def word_tokenize(self, sent):
        sent = sent.lower() if self.lowercase else sent
        return [word for word in re.split(self.split_regex, sent.strip()) if word != '']

    def read_paragraphs(self):
        for para in read_resolution_paragraphs(self.res_files, includes_headers=self.includes_headers,
                                               headers=self.use_headers, pre_tokenise_func=self.pre_tokenise_func,
                                               pre_tokenise_field=self.pre_tokenise_field, debug=self.debug):
            yield para

    def read_sentences(self):
        for para in read_resolution_paragraphs(self.res_files, pre_tokenise_func=self.pre_tokenise_func,
                                               pre_tokenise_field=self.pre_tokenise_field, debug=self.debug):
            for si, sent in enumerate(sent_tokenize(para['text'])):
                if self.to_ascii:
                    yield sent

    def rewrite_word(self, word):
        if word in self.rewrite_dict:
            word = self.rewrite_dict[word]['most_similar_term']
        if self.normalise:
            return normalise_spelling(word)
        else:
            return word


def calculate_word_freq(res_sents: ResolutionSentences) -> Counter:
    word_freq = Counter()
    for si, sent in enumerate(res_sents):
        try:
            if len(sent) == 0:
                continue
            if isinstance(sent, Doc):
                word_freq.update([token.n for token in sent.tokens])
            elif isinstance(sent, list) and isinstance(sent[0], str):
                word_freq.update(sent)
            else:
                print(sent)
                raise TypeError('unexpected type in res_sents, expected list of strings or Doc')
        except IndexError:
            print('Error in sent:', sent)
            raise
    return word_freq


def save_word_freq(word_freq: Counter, word_freq_file: str) -> None:
    with open(word_freq_file, 'wb') as fh:
        pickle.dump(word_freq, fh)


def load_word_freq(word_freq_file: str) -> Counter:
    with open(word_freq_file, 'rb') as fh:
        return pickle.load(fh)


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


def is_confuse_pair(c1, c2):
    if (c1, c2) in pairs["unidirectional"] or (c1, c2) in pairs["bidirectional"]:
        return True
    elif (c2, c1) in pairs["bidirectional"]:
        return True
    else:
        return False


def confuse_distance(c1: str, c2: str) -> Union[int, float]:
    if (c1, c2) in pairs["unidirectional"]:
        return pairs["unidirectional"][(c1, c2)]
    elif (c1, c2) in pairs["bidirectional"]:
        return pairs["bidirectional"][(c1, c2)]
    elif (c2, c1) in pairs["bidirectional"]:
        return pairs["bidirectional"][(c2, c1)]
    elif (not c1.isupper() and c2.isupper()) or (c1.isupper() and not c2.isupper()):
        # An uppercase character is rarely recognised as a different lowercase
        # character, unless it is in the pairs matrix
        return 2
    else:
        return 1


def score_levenshtein_distance_ratio(term1, term2):
    max_distance = max(len(term1), len(term2))
    distance = score_levenshtein_distance(term1, term2)
    return 1 - distance / max_distance


def score_levenshtein_distance(s1, s2, use_confuse=False, max_distance: Union[None, int] = None):
    """Calculate Levenshtein distance between two string. Beyond the
    normal algorithm, a confusion matrix can be used to get non-binary
    scores for common confusion pairs.
    To use the confusion matrix, config the searcher with use_confuse=True"""
    if len(s1) > len(s2):
        s1, s2 = s2, s1
    if not max_distance:
        max_distance = len(s1)
    distances = range(len(s1) + 1)
    for i2, c2 in enumerate(s2):
        distances_ = [i2 + 1]
        for i1, c1 in enumerate(s1):
            if c1 == c2:
                distances_.append(distances[i1])
            else:
                dist = confuse_distance(c1, c2) if use_confuse else 1
                distances_.append(dist + min((distances[i1], distances[i1 + 1], distances_[-1])))
        distances = distances_
    return distances[-1]


def map_alt_langs(langs):
    alt_langs = {
        # Dutch is often confused with
        'af': 'nl',  # Afrikaans
        'da': 'nl',  # Danish
        'no': 'nl',  # Norwegian
        'sl': 'nl',  # Slovenian
        'sv': 'nl',  # Swedish
        # Latin is often confused with
        'ca': 'la',  # Catalan
        'es': 'la',  # Spanish
        'it': 'la',  # Italian
        'pt': 'la',  # Portuguese
        'ro': 'la',  # Romanian
    }
    lang_dict = {lang.lang: lang for lang in langs}
    lang_list = list(lang_dict.keys())
    for lang in lang_list:
        if lang in alt_langs:
            main_lang = alt_langs[lang]
            if main_lang not in lang_dict:
                lang_dict[main_lang] = copy.deepcopy(lang_dict[lang])
                lang_dict[main_lang].lang = main_lang
            else:
                lang_dict[main_lang].prob += lang_dict[lang].prob
            lang_dict[lang].prob = 0.0
            del lang_dict[lang]
    return list(lang_dict.values())


def determine_language(text):
    try:
        langs = detect_langs(text)
        langs = map_alt_langs(langs)
    except LangDetectException:
        langs = []
    langs.sort(key=lambda x: x.prob, reverse=True)
    if len(langs) == 0:
        text_lang = 'unknown'
    elif len(langs) == 1:
        if len(text) > 100:
            text_lang = langs[0].lang
        elif langs[0].lang in {'fr', 'nl'}:
            text_lang = langs[0].lang
        elif len(text) < 40:
            text_lang = 'unknown'
        else:
            text_lang = 'unknown'
    elif len(text) < 40:
        text_lang = 'unknown'
    elif langs[0].prob > 0.6 and langs[0].lang in {'fr', 'la', 'nl'}:
        text_lang = langs[0].lang
    else:
        text_lang = 'unknown'
    return text_lang


pairs = {
    "unidirectional": {
        # common variants lower case
        ('f', 's'): 0.5,
        ('l', 's'): 0.5,
        ('t', 's'): 0.5,
        ('c', 'k'): 0.5,
        ('t', 'd'): 0.5,
        ('l', 'I'): 0.5,
    },
    "bidirectional": {
        # common confusions lower case
        ('j', 'i'): 0.5,
        ('p', 'd'): 0.5,
        ('r', 'i'): 0.5,
        ('r', 't'): 0.5,
        ('r', 'n'): 0.5,
        ('e', 'c'): 0.5,
        ('a', 'e'): 0.5,
        ('a', 'c'): 0.5,
        ('o', 'c'): 0.5,
        ('y', 'i'): 0.5,
        ('l', 'i'): 0.5,
        # common variants upper case
        ('C', 'K'): 0.5,
        # common confusions upper case
        ('I', 'l'): 0.5,
        ('J', 'T'): 0.5,
        ('P', 'F'): 0.5,
        ('P', 'T'): 0.5,
        ('T', 'F'): 0.5,
        ('I', 'L'): 0.5,
        ('B', '8'): 0.5,
        # lower case vs. upper case
        ('a', 'A'): 0.1,
        ('b', 'B'): 0.1,
        ('c', 'C'): 0.1,
        ('d', 'D'): 0.1,
        ('e', 'E'): 0.1,
        ('f', 'F'): 0.1,
        ('g', 'G'): 0.1,
        ('h', 'H'): 0.1,
        ('i', 'I'): 0.1,
        ('j', 'J'): 0.1,
        ('k', 'K'): 0.1,
        ('l', 'L'): 0.1,
        ('m', 'M'): 0.1,
        ('n', 'N'): 0.1,
        ('o', 'O'): 0.1,
        ('p', 'P'): 0.1,
        ('q', 'Q'): 0.1,
        ('r', 'R'): 0.1,
        ('s', 'S'): 0.1,
        ('t', 'T'): 0.1,
        ('u', 'U'): 0.1,
        ('v', 'V'): 0.1,
        ('w', 'W'): 0.1,
        ('x', 'X'): 0.1,
        ('y', 'Y'): 0.1,
        ('z', 'Z'): 0.1,
        # diacritic vs. no diacritic
        ('e', 'é'): 0.1,
        ('e', 'ë'): 0.1,
        ('e', 'è'): 0.1,
        ('a', 'ä'): 0.1,
        ('a', 'á'): 0.1,
        ('a', 'à'): 0.1,
        ('i', 'ï'): 0.1,
        ('i', 'í'): 0.1,
        ('i', 'ì'): 0.1,
        ('o', 'ó'): 0.1,
        ('o', 'ö'): 0.1,
        ('o', 'ò'): 0.1,
        ('u', 'ú'): 0.1,
        ('u', 'ü'): 0.1,
        ('u', 'ù'): 0.1,
    }
}


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
    if word.endswith('lant'):
        word = word[:-1] + 'd'
    if word.endswith('landt'):
        word = word[:-2] + 'd'
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


def read_resolution_paragraphs(res_files, pre_tokenise_func: Callable = None, pre_tokenise_field: str = None,
                               includes_headers: bool = True, headers: List[str] = None,
                               debug: int = 0):
    if pre_tokenise_func and not pre_tokenise_field:
        pre_tokenise_field = 'text'
    for res_file in res_files:
        opener = gzip.open if res_file.endswith('.gz') else open
        if debug > 0:
            print('parsing file', res_file)
        with opener(res_file, 'rt') as fh:
            if includes_headers is True and headers is None:
                headers = next(fh).strip().split('\t')
            elif headers is None:
                headers = ['resolution_id', 'paragraph_id', 'text']
            for line in fh:
                row = line.strip().split('\t')
                if len(row) != len(headers):
                    continue
                else:
                    doc = {header: row[hi] for hi, header in enumerate(headers)}
                    if pre_tokenise_func:
                        tokenized_doc = pre_tokenise_func(doc[pre_tokenise_field])
                        doc['tokens'] = tokenized_doc.tokens
                    yield doc


def write_rewrite_dictionary_json(rewrite_dict: Dict[str, str], dict_file: str):
    """Write a word replacement dictionary to a JSON file."""
    with open(dict_file, 'wt') as fh:
        json.dump(rewrite_dict, fh, indent=4)
    return None


def read_rewrite_dictionary_json(dict_file: str) -> Dict[str, str]:
    """Read a JSON-formatted word replacement dictionary."""
    with open(dict_file, 'rt') as fh:
        rewrite_dict = json.load(fh)
    return rewrite_dict


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
                 max_length_diff: int = 2, include_boundaries: bool = False):
        self.ngram_length = ngram_length
        self.skip_length = skip_length
        self.include_boundaries = include_boundaries
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
        term = f'#{term}#' if self.include_boundaries else term
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
        # print(term, 'vl:', term_vl)
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


################################################################
# Duplicate page detection
#
# **Problem 2**: Some pages are duplicates of the preceding scan. When the page turning
# mechanism fails, subsequent scans are images of the same two pages. Duplicates page
# should therefore come in pairs, that is, even and odd side of scan $n$ are duplicates
# of even and odd side of scan $n-1$. Shingling or straightforward text tiling won't work
# because of OCR variation. Many words may be recognized slightly different and lines and
# words may not align.
#
# **Solution**: Compare each pair of even+odd pages against preceding pair of even+odd pages,
# using Levenshtein distance. This deals with slight character-level variations due to OCR.
# Most pairs will be very dissimilar. Use a heuristic threshold to determine whether pages
# are duplicates.
#
################################################################

def get_column_text(column: pdm.PageXMLColumn):
    return "\n".join([line.text for line in column.get_lines() if line.text is not None])


def compute_column_similarity(curr_column: pdm.PageXMLColumn, prev_column: pdm.PageXMLColumn,
                              chunk_size = 200, chunk_sim_threshold: float = 0.5):
    """Compute similarity of two Republic hOCR columns using levenshtein distance.
    Chunking is done for efficiency. Most pages have around 2200 characters.
        Comparing two 2200 character strings is slow.
    Similarity of individual chunk pairs can be lower than whole column similarity.
        => use lower threshold for cumulative chunk similarity.
    Approach:
        1. divide the text string of each column in chunks,
        2. calculate levenshtein distance of chunk pairs
        3. sum distances of chunk up to current chunk
        4. compute distance ratio as sum of distance divided by cumulative length of chunks up to current chunk
        5. compute cumulative chunk similarity as 1 - distance ratio
        6. if cumulative chunk similarity drops below threshold, stop comparison and return similarity (efficiency)
    Assumption: summing distances of 11 pairs of 200 character strings is a good approximation of overall distance
    Assumption: if cumulative chunk similarity drops below threshold, return with current chunk similarity
    Assumption: similarity is normalized by the length of the current page.
    """
    curr_text = get_column_text(curr_column)
    prev_text = get_column_text(prev_column)
    if len(curr_text) < len(prev_text):
        curr_text, prev_text = prev_text, curr_text  # use longest text for chunking
    sum_chunk_dist = 0
    chunk_sim = 1
    for start_offset in range(0, len(curr_text), chunk_size):
        end_offset = start_offset + chunk_size
        chunk_dist = score_levenshtein_distance(curr_text[start_offset:end_offset], prev_text[start_offset:end_offset])
        sum_chunk_dist += chunk_dist
        chunk_sim = 1 - sum_chunk_dist / min(end_offset, len(curr_text))
        if chunk_sim < chunk_sim_threshold:  # stop as soon as similarity drops below 0.5
            return chunk_sim
    return chunk_sim


def compute_page_similarity(curr_page: pdm.PageXMLPage, prev_page: pdm.PageXMLPage):
    """Compute similarity of two Republic hOCR pages using levenshtein distance.
    Assumption: pages should have equal number of columns, otherwise their similarity is 0.0
    Assumption: similarity between two pages is the sum of the similarity of their columns.
    Assumption: on each page, columns are in page order from left to right.
    Assumption: similarity is normalized by the length of the current page.
    """
    sim = 0.0
    if len(curr_page.columns) != len(prev_page.columns):
        return sim
    for column_index, curr_column in enumerate(curr_page.columns):
        prev_column = prev_page.columns[column_index]
        sim += compute_column_similarity(curr_column, prev_column)
    return sim / len(curr_page.columns)


def is_duplicate(page_doc: pdm.PageXMLPage, prev_page_doc: pdm.PageXMLPage,
                 similarity_threshold: float = 0.8):
    if len(page_doc.columns) == 0 or len(prev_page_doc.columns) == 0:
        return False
    return compute_page_similarity(page_doc, prev_page_doc) > similarity_threshold

