from __future__ import annotations
from typing import Dict, Union
from datetime import datetime

from republic.fuzzy.fuzzy_keyword import Keyword
from republic.fuzzy.fuzzy_string import score_ngram_overlap_ratio
from republic.fuzzy.fuzzy_string import score_char_overlap_ratio
from republic.fuzzy.fuzzy_string import score_levenshtein_similarity_ratio


def validate_match_props(match_keyword: Keyword, match_variant: Keyword,
                         match_string: str, match_offset: int) -> None:
    """Validate match properties."""
    if not isinstance(match_keyword, Keyword):
        raise TypeError('match_keyword MUST be of class Keyword')
    if not isinstance(match_variant, Keyword):
        raise TypeError('match_variant MUST be of class Keyword')
    if not isinstance(match_string, str):
        raise TypeError('match string MUST be a string')
    if len(match_string) == 0:
        raise ValueError('match string cannot be empty string')
    if not isinstance(match_offset, int):
        raise TypeError('match_offset must be an integer')
    if match_offset < 0:
        raise ValueError('offset cannot be negative')


###############
# Match class #
###############

class Match:

    def __init__(self, match_keyword: Keyword, match_variant: Keyword,
                 match_string: str, match_offset: int,
                 text_id: Union[None, str]):
        validate_match_props(match_keyword, match_variant, match_string, match_offset)
        self.keyword = match_keyword
        self.variant = match_variant
        self.string = match_string
        self.offset = match_offset
        self.end = self.offset + len(self.string)
        self.text_id = text_id
        self.character_overlap: Union[None, float] = None
        self.ngram_overlap: Union[None, float] = None
        self.levenshtein_similarity: Union[None, float] = None
        self.created = datetime.now()

    def add_scores(self) -> None:
        """Compute overlap and similarity scores between the match variant and the match string
        and add these to the match object.

        :return: None
        :rtype: None
        """
        self.character_overlap = self.score_character_overlap()
        self.ngram_overlap = self.score_ngram_overlap()
        self.levenshtein_similarity = self.score_levenshtein_similarity()

    def score_character_overlap(self):
        """Return the character overlap between the variant keyword_string and the match_string

        :return: the character overlap as proportion of the variant keyword string
        :rtype: float
        """
        if not self.character_overlap:
            self.character_overlap = score_char_overlap_ratio(self.variant.keyword_string, self.string)
        return self.character_overlap

    def score_ngram_overlap(self) -> float:
        """Return the ngram overlap between the variant keyword_string and the match_string

        :return: the ngram overlap as proportion of the variant keyword string
        :rtype: float
        """
        if not self.ngram_overlap:
            self.ngram_overlap = score_ngram_overlap_ratio(self.variant.keyword_string,
                                                           self.string, self.keyword.ngram_size)
        return self.ngram_overlap

    def score_levenshtein_similarity(self):
        """Return the levenshtein similarity between the variant keyword_string and the match_string

        :return: the levenshtein similarity as proportion of the variant keyword string
        :rtype: float
        """
        if not self.levenshtein_similarity:
            self.levenshtein_similarity = score_levenshtein_similarity_ratio(self.variant.keyword_string,
                                                                             self.string)
        return self.levenshtein_similarity

    def overlaps(self, other: Match) -> bool:
        """Check if the match string of this match object overlaps with the match string of another match object.

        :param other: another match object
        :type other: Match
        :return: a boolean indicating whether the match_strings of the two objects overlap in the source text
        :rtype: bool"""
        if self.text_id is not None and self.text_id != other.text_id:
            return False
        if self.offset <= other.offset < self.end:
            return True
        elif other.offset <= self.offset < other.end:
            return True
        else:
            return False

    def as_web_anno(self) -> Dict[str, any]:
        """Turn match object into a W3C Web Annotation representation"""
        if not self.text_id:
            raise ValueError('Cannot make target: match object has no text_id')
        return {
            "motivation": "classifying",
            "created": self.created.isoformat(),
            "generator": {
                "id": "https://github.com/marijnkoolen/fuzzy-search",
                "type": "Software",
                "name": f"FuzzySearcher"
            },
            "target": {
                "source": self.text_id,
                "selector": {
                    "type": "TextPositionSelector",
                    "start": self.offset,
                    "end": self.end
                }
            },
            "body": {
                "type": "Dataset",
                "value": {
                    "match_keyword": self.keyword.keyword_string,
                    "match_variant": self.variant.keyword_string,
                    "match_string": self.string,
                    "keyword_metadata": self.keyword.metadata
                }
            }
        }
