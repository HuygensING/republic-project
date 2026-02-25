import json
import os

import settings


def read_term_dictionary(term_dictionary_file: str = None):
    if term_dictionary_file is None:
        dir_path, _filename = os.path.split(settings.__file__)
        term_dictionary_file = os.path.join(dir_path, 'data/phrase_lists/republic-term-dictionary.json')
    with open(term_dictionary_file, 'rt') as fh:
        return json.load(fh)


def get_word_date_categories(term_dictionary_file: str = None):
    term_dictionary = read_term_dictionary(term_dictionary_file)
    word_date_cat = {}
    for cat in term_dictionary['date']:
        for term in term_dictionary['date'][cat]:
            word_date_cat[term] = cat
    return word_date_cat


def get_date_words(words, word_date_cat):
    return [word for word in words if word in word_date_cat]


def get_specific_date_words(words, word_date_cat):
    return [word for word in words if word in word_date_cat and 'relative' not in word_date_cat[word]]

