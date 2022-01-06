from typing import List, Dict, Union
from collections import defaultdict
import networkx as nx
from ..fuzzy.fuzzy_keyword import Keyword

pairs = {('s', 'f'): 0.2,
         ('s', ''): 0.2,
         ('c', 'k'): 0.5,
         ('j', 'i'): 0.5,
         ('r', 'i'): 0.5,
         ('r', 't'): 0.5,
         ('r', 'n'): 0.5,
         ('e', 'c'): 0.5,
         ('a', 'e'): 0.2,
         ('a', 'c'): 0.5,
         ('o', 'c'): 0.5,
         ('y', 'i'): 0.5,
         ('l', 'i'): 0.5,
         ('C', 'K'): 0.5,
         ('I', 'l'): 0.5,
         ('J', 'T'): 0.5,
         ('P', 'F'): 0.5,
         ('P', 'T'): 0.5,
         ('T', 'F'): 0.5,
         ('I', 'L'): 0.5,
         ('B', '8'): 0.5,
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
         ('u', 'ù'): 0.1}


# this is copied from the (old) fuzzy keyword searcher (for now).
# Depending on the way we code this, it should either be moved, replaced or or removed


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


def score_char_overlap(term1: int, term2: str) -> int:
    """Count the number of overlapping character tokens in two strings."""
    num_char_matches = 0
    for char in term2:
        if char in term1:
            term1 = term1.replace(char, "", 1)
            num_char_matches += 1
    return num_char_matches


def get_keyword_string(keyword):
    if isinstance(keyword, str):
        return keyword
    elif isinstance(keyword, Keyword):
        return keyword.name
    elif isinstance(keyword, dict) and "keyword_string" in keyword:
        return keyword["keyword_string"]
    else:
        return None


def confuse_distance(c1, c2):
    if (c1, c2) in pairs:
        return pairs[(c1, c2)]
    elif (c2, c1) in pairs:
        return pairs[(c2, c1)]
    else:
        return 1


class FuzzyKeywordGrouper(object):
    def __init__(self, keyword_list: List[str]):
        self.keyword_list = keyword_list
        self.distance_list = self.find_close_distance_keywords()

    def find_close_distance_keywords(self, max_distance_ratio: float = 0.3,
                                     max_length_difference: int = 3, min_char_overlap: float = 0.5,
                                     max_distance: int = 10) -> Dict[str, List[str]]:
        """TODO: should we make the arguments into a config?"""
        close_distance_keywords = defaultdict(list)
        for index, keyword1 in enumerate(self.keyword_list):
            string1 = get_keyword_string(keyword1).lower()
            close_distance_keywords[keyword1] = []
            for keyword2 in self.keyword_list[index + 1:]:
                string2 = get_keyword_string(keyword2).lower()
                if abs(len(string1) - len(string2)) > max_length_difference: continue
                # - keywords have low overlap in characters
                char_overlap = score_char_overlap(string1, string2)
                if char_overlap / len(string1) < min_char_overlap: continue
                distance = score_levenshtein_distance(string1, string2)
                if distance < max_distance and (
                        distance / len(string1) < max_distance_ratio or distance / len(string2) < max_distance_ratio):
                    close_distance_keywords[keyword1].append(keyword2)
                    close_distance_keywords[keyword2].append(keyword1)
        return close_distance_keywords

    def find_closer_terms(self, candidate, keyword, close_terms):
        closer_terms = {}
        keyword_distance = score_levenshtein_distance(keyword, candidate)
        # print("candidate:", candidate, "\tkeyword:", keyword)
        # print("keyword_distance", keyword_distance)
        for close_term in close_terms:
            close_term_distance = score_levenshtein_distance(close_term, candidate)
            # print("close_term:", close_term, "\tdistance:", close_term_distance)
            if close_term_distance < keyword_distance:
                closer_terms[close_term] = close_term_distance
        return sorted(closer_terms, key=lambda closer_terms: closer_terms[1])

    # def shorten_representation(self):
    #     G = nx.Graph()
    #     d_nodes = sorted(self.distance_list)
    #     for node in d_nodes:
    #         attached_nodes = cl_heren[node]
    #         G.add_node(node)
    #         for nod in attached_nodes:
    #             G.add_edge(node, nod)
    #     result = G.nx.connected_components(G)
    #     return result

    def vars2graph(self):
        G_differentiated = nx.Graph()
        d_nodes = sorted(self.distance_list)
        for node in d_nodes:
            attached_nodes = self.distance_list[node]
            G_differentiated.add_node(node)
            for nod in attached_nodes:
                G_differentiated.add_edge(node, nod)
        cl = (G_differentiated.subgraph(c).copy() for c in nx.connected_components(G_differentiated))
        cc = [list(c) for c in list(cl)]

        return cc

    def __call__(self):
        return self.distance_list