from typing import Dict, List, Union
import uuid
from itertools import combinations
from collections import defaultdict


class Keyword(object):

    def __init__(self, keyword: Union[str, Dict[str, str]], ngram_size: int = 2, skip_size: int = 2,
                 early_threshold: int = 3, late_threshold: int = 3, within_range_threshold: int = 3,
                 ignorecase: bool = False):
        if isinstance(keyword, str):
            keyword = {"keyword_string": keyword}
        self.keyword_string = keyword["keyword_string"]
        self.name = keyword["keyword_string"]
        self.properties = keyword
        self.ngram_size = ngram_size
        self.skip_size = skip_size
        self.early_threshold = early_threshold
        self.late_threshold = len(self.name) - late_threshold - ngram_size
        self.within_range_threshold = within_range_threshold
        self.ignorecase = ignorecase
        if ignorecase:
            self.keyword_string = self.keyword_string.lower()
        self.ngrams = [ngram for ngram in text2skipgrams(self.keyword_string,
                                                         ngram_size=ngram_size, skip_size=skip_size)]
        self.ngram_index = defaultdict(list)
        for ngram, offset in self.ngrams:
            self.ngram_index[ngram] += [offset]
        self.index_ngrams()
        self.early_ngrams = {ngram: offset for ngram, offset in self.ngrams if offset < early_threshold}
        self.late_ngrams = {ngram: offset for ngram, offset in self.ngrams if offset > self.late_threshold}
        self.set_within_range()
        self.ngram_distance = {}
        self.metadata = {}

    def add_metadata(self, metadata_dict: Dict[str, any]) -> None:
        """Add key/value pairs as metadata for this keyword.

        :param metadata_dict: a dictionary of key/value pairs as metadata
        :type metadata_dict: Dict[str, any]
        :return: None
        :rtype: None
        """
        for key in metadata_dict:
            self.metadata[key] = metadata_dict[key]

    def index_ngrams(self) -> None:
        """Turn the keyword into a list of ngrams and index them with their offset(s) as values."""
        self.ngram_index = defaultdict(list)
        for ngram, offset in self.ngrams:
            self.ngram_index[ngram] += [offset]

    def has_ngram(self, ngram: str) -> bool:
        """For a given ngram, return boolean whether it is in the index

        :param ngram: an ngram string
        :type ngram: str
        :return: A boolean whether ngram is in the index
        :rtype: bool"""
        return ngram in self.ngram_index.keys()

    def ngram_offsets(self, ngram: str) -> Union[None, List[int]]:
        """For a given ngram return the list of offsets at which it appears.

        :param ngram: an ngram string
        :type ngram: str
        :return: A list of string offsets at which the ngram appears
        :rtype: Union[None, List[int]]"""
        if not self.has_ngram(ngram):
            return None
        return self.ngram_index[ngram]

    def set_within_range(self):
        self.ngram_distance = {}
        for index1 in range(0, len(self.ngrams)-1):
            ngram1, offset1 = self.ngrams[index1]
            for index2 in range(index1+1, len(self.ngrams)):
                ngram2, offset2 = self.ngrams[index2]
                if offset2 - offset1 > self.within_range_threshold:
                    continue
                if (ngram1, ngram2) not in self.ngram_distance:
                    self.ngram_distance[(ngram1, ngram2)] = offset2 - offset1
                elif self.ngram_distance[(ngram1, ngram2)] > offset2 - offset1:
                    self.ngram_distance[(ngram1, ngram2)] = offset2 - offset1

    def within_range(self, ngram1, ngram2):
        if not self.has_ngram(ngram1) or not self.has_ngram(ngram2):
            return False
        elif (ngram1, ngram2) not in self.ngram_distance:
            return False
        elif self.ngram_distance[(ngram1, ngram2)] > self.within_range_threshold:
            return False
        else:
            return True

    def is_early_ngram(self, ngram: str) -> bool:
        """For a given ngram, return boolean whether it appears early in the keyword.

        :param ngram: an ngram string
        :type ngram: str
        :return: A boolean whether ngram appears early in the keyword
        :rtype: bool"""
        return ngram in self.early_ngrams


def insert_skips(window: str, ngram_combinations: List[List[int]]):
    """For a given skip gram window, return all skip gram for a given configuration."""
    for combination in ngram_combinations:
        prev_index = 0
        skip_gram = window[0]
        try:
            for index in combination:
                if index - prev_index > 1:
                    skip_gram += "_"
                skip_gram += window[index]
                prev_index = index
            yield skip_gram
        except IndexError:
            pass


def text2skipgrams(text: str, ngram_size: int = 2, skip_size: int = 2) -> iter(str, int):
    """Turn a text string into a list of skipgrams.

    :param text: an text string
    :type text: str
    :param ngram_size: an integer indicating the number of characters in the ngram
    :type ngram_size: int
    :param skip_size: an integer indicating how many skip characters in the ngrams
    :type skip_size: int
    :return: An iterator returning tuples of skip_gram and offset
    :rtype: iter(str, int)"""
    indexes = [i for i in range(0, ngram_size+skip_size)]
    ngram_combinations = [combination for combination in combinations(indexes[1:], ngram_size-1)]
    for offset in range(0, len(text)-1):
        window = text[offset:offset+ngram_size+skip_size]
        for skip_gram in insert_skips(window, ngram_combinations):
            yield skip_gram, offset


class PersonName(object):

    def __init__(self, person_name_string):
        self.person_name_id = str(uuid.uuid4())
        self.name_string = person_name_string
        self.normalized_name = normalize_person_name(person_name_string)
        self.name_type = "person_name"
        self.spelling_variants = []
        self.distractor_terms = []

    def to_json(self):
        return {
            "person_name_id": self.person_name_id,
            "name_string": self.name_string,
            "normalize_name": self.normalized_name,
            "name_type": self.name_type,
            "spelling_variants": self.spelling_variants,
            "distractor_terms": self.distractor_terms
        }

    def add_spelling_variants(self, spelling_variants):
        for spelling_variant in spelling_variants:
            if spelling_variant not in self.spelling_variants:
                self.spelling_variants += [spelling_variant]

    def add_distractor_terms(self, distractor_terms):
        for distractor_term in distractor_terms:
            if distractor_term not in self.distractor_terms:
                self.distractor_terms += [distractor_term]


def normalize_person_name(person_name_string):
    normalized = person_name_string.title()
    infixes = [" van ", " de ", " der ", " du ", " le ", " la "]
    for infix in infixes:
        normalized = normalized.replace(infix.title(), infix.lower())
    return normalized
