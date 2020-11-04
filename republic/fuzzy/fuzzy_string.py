from typing import List


#################################
# String manipulation functions #
#################################

def make_ngrams(text: str, n: int) -> List[str]:
    """Turn a term string into a list of ngrams of size n

    :param text: a text string
    :type text: str
    :param n: the ngram size
    :type n: int
    :return: a list of ngrams
    :rtype: List[str]"""
    text = "#{t}#".format(t=text)
    max_start = len(text) - n + 1
    return [text[start:start + n] for start in range(0, max_start)]


#####################################
# Term similarity scoring functions #
#####################################


def score_ngram_overlap(term1: str, term2: str, ngram_size: int):
    """Score the number of overlapping ngrams between two terms

    :param term1: a term string
    :type term1: str
    :param term2: a term string
    :type term2: str
    :param ngram_size: the character ngram size
    :type ngram_size: int
    :return: the number of overlapping ngrams
    :rtype: int
    """
    term1_ngrams = make_ngrams(term1, ngram_size)
    term2_ngrams = make_ngrams(term2, ngram_size)
    overlap = 0
    for ngram in term1_ngrams:
        if ngram in term2_ngrams:
            term2_ngrams.pop(term2_ngrams.index(ngram))
            overlap += 1
    return overlap


def score_ngram_overlap_ratio(term1, term2, ngram_size):
    """Score the number of overlapping ngrams between two terms as proportion of the length
    of the first term

    :param term1: a term string
    :type term1: str
    :param term2: a term string
    :type term2: str
    :param ngram_size: the character ngram size
    :type ngram_size: int
    :return: the number of overlapping ngrams
    :rtype: int
    """
    max_overlap = len(make_ngrams(term1, ngram_size))
    overlap = score_ngram_overlap(term1, term2, ngram_size)
    return overlap / max_overlap


def score_char_overlap_ratio(term1, term2):
    """Score the number of overlapping characters between two terms as proportion of the length
    of the first term

    :param term1: a term string
    :type term1: str
    :param term2: a term string
    :type term2: str
    :return: the number of overlapping ngrams
    :rtype: int
    """
    max_overlap = len(term1)
    overlap = score_char_overlap(term1, term2)
    return overlap / max_overlap


def score_char_overlap(term1: str, term2: str) -> int:
    """Count the number of overlapping character tokens in two strings.

    :param term1: a term string
    :type term1: str
    :param term2: a term string
    :type term2: str
    :return: the number of overlapping ngrams
    :rtype: int
    """
    num_char_matches = 0
    for char in term2:
        if char in term1:
            term1 = term1.replace(char, "", 1)
            num_char_matches += 1
    return num_char_matches


def score_levenshtein_similarity_ratio(term1, term2):
    """Score the levenshtein similarity between two terms

    :param term1: a term string
    :type term1: str
    :param term2: a term string
    :type term2: str
    :return: the number of overlapping ngrams
    :rtype: int
    """
    max_distance = max(len(term1), len(term2))
    distance = score_levenshtein_distance(term1, term2)
    return 1 - distance / max_distance


def score_levenshtein_distance(term1: str, term2: str) -> int:
    """Calculate Levenshtein distance between two string.

    :param term1: a term string
    :type term1: str
    :param term2: a term string
    :type term2: str
    :return: the number of overlapping ngrams
    :rtype: int
    """
    if len(term1) > len(term2):
        term1, term2 = term2, term1
    distances = range(len(term1) + 1)
    for i2, c2 in enumerate(term2):
        distances_ = [i2 + 1]
        for i1, c1 in enumerate(term1):
            if c1 == c2:
                distances_.append(distances[i1])
            else:
                distances_.append(1 + min((distances[i1], distances[i1 + 1], distances_[-1])))
        distances = distances_
    return distances[-1]
