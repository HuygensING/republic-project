from typing import List
import re
from collections import defaultdict

from sklearn.feature_extraction.text import TfidfVectorizer
from sparse_dot_topn import awesome_cossim_topn


def remove_non_string_terms(term_list: List[str]):
    string_terms = [term for term in term_list if type(term) == str]
    non_terms = [term for term in term_list if type(term) != str]
    if len(non_terms) > 0:
        print('Dropping non-string terms:', non_terms)
    return string_terms


class LemmaGrouper:

    def __init__(self, match_threshold=0.75, ngram_length: int = 3, ngram_remove: str = r'[,-./]',
                 use_lowercase: bool = False, debug_level: int = 0):
        self.group_lookup = {}
        self.all_terms = []
        self.use_lowercase = use_lowercase
        self.debug_level = debug_level
        self._ngram_length = ngram_length
        self._ngram_remove = ngram_remove
        self._match_threshold = match_threshold
        self.vectorizer = TfidfVectorizer(analyzer=self._ngrams_analyzer)

    def _ngrams_analyzer(self, string):
        string = re.sub(self._ngram_remove, r'', string)
        string = string.lower() if self.use_lowercase else string
        ngrams = zip(*[string[i:] for i in range(self._ngram_length)])
        return [''.join(ngram) for ngram in ngrams]

    def set_idf(self, all_terms: list = None):
        if all_terms is not None:
            self.all_terms = remove_non_string_terms(all_terms)
        if len(self.all_terms) == 0:
            raise ValueError('No or empty term list given')
        if self.debug_level > 0:
            print(f'setting IDF for {len(self.all_terms)} terms')
        self.vectorizer.fit(self.all_terms)

    def _get_tf_idf_matrix(self, term_list):
        return self.vectorizer.transform(term_list)

    def _get_coord_matrix(self, tfidf_1, tfidf_2_trans, top_n: int = None):
        if top_n is None:
            top_n = len(self.all_terms)
        return awesome_cossim_topn(tfidf_1, tfidf_2_trans, top_n,
                                   self._match_threshold).tocoo()

    def _find_group(self, y, x):
        if y in self.group_lookup:
            return self.group_lookup[y]
        elif x in self.group_lookup:
            return self.group_lookup[x]
        else:
            return None

    def _add_vals_to_lookup(self, group, y, x):
        self.group_lookup[y] = group
        self.group_lookup[x] = group

    def _add_pair_to_lookup(self, row, col):
        group = self._find_group(row, col)
        if group is None:
            group = row
        if self.debug_level > 1:
            print(f'add pair "{row}" and "{col}" to group "{group}"')
        self._add_vals_to_lookup(group, row, col)

    def group_terms(self, term_list):
        self.set_idf(term_list)
        tfidf = self._get_tf_idf_matrix(term_list)
        if self.debug_level > 0:
            print(f'TF-IDF matrix has shape:', tfidf.shape)
        coord_matrix = self._get_coord_matrix(tfidf, tfidf.transpose())
        if self.debug_level > 0:
            print(f'Coord matrix has shape:', coord_matrix.shape)
        for row, col in zip(coord_matrix.row, coord_matrix.col):
            if row != col:
                self._add_pair_to_lookup(term_list[row], term_list[col])
        if self.debug_level > 0:
            print(f'number of groups:', len(set(self.group_lookup.values())))
            print(f'number of grouped terms:', len(self.group_lookup.keys()))

    def group_terms_by_base_terms(self, messy_term_list, base_term_list, top_n: int = 1):
        messy_term_list = remove_non_string_terms(messy_term_list)
        base_term_list = remove_non_string_terms(base_term_list)
        self.set_idf(messy_term_list + base_term_list)
        messy_term_tfidf = self._get_tf_idf_matrix(messy_term_list)
        base_term_tfidf = self._get_tf_idf_matrix(base_term_list)
        self._add_base_terms_as_group(base_term_list)
        if self.debug_level > 0:
            print(f'Term TF-IDF matrix has shape:', messy_term_tfidf.shape)
            print(f'Base term TF-IDF matrix has shape:', base_term_tfidf.shape)
        coord_matrix = self._get_coord_matrix(messy_term_tfidf, base_term_tfidf.transpose(), top_n=top_n)
        if self.debug_level > 0:
            print(f'Coord matrix has shape:', coord_matrix.shape)
        for row, col in zip(coord_matrix.row, coord_matrix.col):
            if row != col:
                # only add term to base_term group
                self.group_lookup[messy_term_list[row]] = base_term_list[col]
                # self._add_pair_to_lookup(base_term_list[row], term_list[col])
        if self.debug_level > 0:
            print(f'number of groups:', len(set(self.group_lookup.values())))
            print(f'number of grouped terms:', len(self.group_lookup.keys()))

    def _add_base_terms_as_group(self, base_term_list):
        for base_term in base_term_list:
            self.group_lookup[base_term] = base_term


