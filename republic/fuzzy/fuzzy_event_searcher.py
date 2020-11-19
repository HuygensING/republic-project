from typing import Dict, List, Union
from collections import defaultdict

from republic.fuzzy.fuzzy_phrase_model import PhraseModel
from republic.fuzzy.fuzzy_keyword_searcher import FuzzyKeywordSearcher


class EventSearcher:

    def __init__(self, window_size: int = 10):
        self.window_size = window_size
        # Initialize the sliding window with None elements, so first documents are appended at the end.
        self.sliding_window: List[Union[None, Dict[str, Union[str, int, list]]]] = [None] * self.window_size
        self.keywords = {}
        self.variants = {}
        self.labels = {}
        self.searchers: Dict[str, FuzzyKeywordSearcher] = {}
        self.phrase_models: Dict[str, PhraseModel] = {}
        self.max_offsets: Dict[str, int] = {}
        self.min_offsets: Dict[str, int] = {}

    def __repr__(self):
        return f"EventSearcher({self.searchers})"

    def reset_sliding_window(self, first_lines: Union[None, int] = None) -> None:
        """Reset the sliding window to an empty list."""
        if first_lines:
            for line_index in range(0, first_lines):
                self.sliding_window[line_index] = None
        else:
            self.sliding_window: List[Union[None, Dict[str, Union[str, int, list]]]] = [None] * self.window_size

    def add_searcher(self, searcher_config: dict, searcher_name: str,
                     phrase_model: PhraseModel):
        """Add a fuzzy keyword searcher with its own config and phrase model"""
        # Create a new fuzzy keyword searcher
        searcher = FuzzyKeywordSearcher(searcher_config)
        searcher.index_keywords(phrase_model.get_keywords())
        # make sure the EventSearcher knows which keywords and labels are registered
        self.add_keywords(phrase_model)
        self.add_labels(phrase_model)
        searcher.index_spelling_variants(phrase_model.variants)
        # add the keyword searcher to the EventSearcher
        self.searchers[searcher_name] = searcher
        self.phrase_models[searcher_name] = phrase_model

    def add_keywords(self, phrase_model: PhraseModel):
        """Add all the keywords of a phrase model to the EventSearcher."""
        for keyword in phrase_model.get_keywords():
            self.keywords[keyword] = True

    def get_keywords(self):
        """Return all the keywords registered in the EventSearcher."""
        return list(self.keywords.keys())

    def has_keyword(self, keyword: str):
        """Check if keyword is registered in the EventSearcher."""
        return keyword in self.keywords

    def add_labels(self, phrase_model: PhraseModel):
        """Add the labels of all the keywords of a phrase model to the EventSearcher."""
        for keyword in phrase_model.get_keywords():
            if phrase_model.has_label(keyword):
                self.labels[keyword] = phrase_model.get_label(keyword)

    def get_label(self, keyword: str):
        """Return all the keywords registered in the EventSearcher."""
        if not self.has_keyword(keyword):
            raise ValueError(f"Unknown keyword {keyword}")
        if not self.has_label(keyword):
            raise KeyError(f"Keyword {keyword} has no registered label")
        return list(self.keywords.keys())

    def has_label(self, keyword: str):
        """Check if keyword has a registered label in the EventSearcher."""
        return keyword in self.labels

    def search_document(self, doc: Dict[str, Union[str, int]],
                        searcher_name: str) -> List[Union[str, int, float]]:
        """Use a registered searcher to find fuzzy match for a document."""
        matches = []
        # use the searcher to find fuzzy matches
        for match in self.searchers[searcher_name].find_candidates(doc['text_string'], include_variants=True):
            keyword = match['match_keyword']
            # check if the keyword exceeds minimum or maximum offset thresholds
            if keyword in self.max_offsets and match['match_offset'] > self.max_offsets[keyword]:
                continue
            if keyword in self.min_offsets and match['match_offset'] < self.min_offsets[keyword]:
                continue
            # add the searcher_name to the match so we know where it came from
            match['searcher'] = searcher_name
            # if the keyword has a label, add it to the match
            if self.phrase_models[searcher_name].has_label(keyword):
                match['match_label'] = self.phrase_models[searcher_name].get_label(keyword)
            matches += [match]
        return matches

    def add_empty_document(self):
        """Append an empty placeholder document to the sliding window."""
        # if the window is too long, remove earliest docs to make room for the new doc
        if len(self.sliding_window) >= self.window_size:
            self.sliding_window = self.sliding_window[-self.window_size:]
        self.sliding_window += [None]

    def add_document(self, text_id: Union[str, int], text_string: str):
        """Add a text with identifier to the sliding window and run registered fuzzy searchers."""
        matches: List[Dict[str, Union[str, int, float]]] = []
        doc = {'text_id': text_id, 'text_string': text_string, 'matches': matches}
        # iterate over all registered searchers
        for searcher_name in self.searchers:
            # add the matches to the document
            doc['matches'] += self.search_document(doc, searcher_name)
        # add the document to the sliding window,
        self.sliding_window += [doc]
        # if the window is too long, remove earliest docs to make room for the new doc
        if len(self.sliding_window) >= self.window_size:
            self.sliding_window = self.sliding_window[-self.window_size:]

    def set_keyword_match_offsets(self, keyword_offsets: List[Dict[str, Union[str, int]]]):
        """Add a minimum and/or maximum document text offset threshold for a list keywords.
        Thresholds can be different for each keyword."""
        for offset in keyword_offsets:
            if 'keyword' not in offset:
                raise KeyError("Keyword offset dictionary must have a 'keyword' property")
            if 'max_offset' not in offset and 'min_offset' not in offset:
                raise KeyError("Keyword offset dictionary must at least one of 'max_offset' and 'min_offset'")
            if 'min_offset' in offset:
                self.min_offsets[offset['keyword']] = offset['min_offset']
            if 'max_offset' in offset:
                self.max_offsets[offset['keyword']] = offset['max_offset']

    def num_window_matches(self, use_labels=False):
        """Returns counts of the number of keyword matches for all the docs in the current sliding window."""
        counts = defaultdict(int)
        for doc in self.sliding_window:
            for match in doc['matches']:
                counts['_all'] += 1
                if use_labels and 'match_label' in match:
                    counts[match['match_label']] += 1
                else:
                    counts[match['match_keyword']] += 1
        return counts

    def get_window_matches(self) -> List[Dict[str, Union[str, int]]]:
        matches = []
        for text_index, text in enumerate(self.sliding_window):
            if text or len(text['matches']) == 0:
                continue
            for match in text['matches']:
                matches.append({'text_index': text_index, 'text_id': text['text_id'], 'match': match})
        return matches
