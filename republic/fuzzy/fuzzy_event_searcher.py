from typing import Dict, List, Union
from collections import defaultdict

from fuzzy_search.phrase.phrase_model import PhraseModel
from fuzzy_search.search.phrase_searcher import FuzzyPhraseSearcher
from fuzzy_search.match.phrase_match import PhraseMatch

# from republic.fuzzy.fuzzy_phrase_model import PhraseModel
# from republic.fuzzy.fuzzy_keyword_searcher import FuzzyKeywordSearcher


class EventSearcher:

    def __init__(self, window_size: int = 10):
        self.window_size = window_size
        # Initialize the sliding window with None elements, so first documents are appended at the end.
        self.sliding_window: List[Union[None, Dict[str, any]]] = [None] * self.window_size
        self.phrases = {}
        self.variants = {}
        self.labels = {}
        self.searchers: Dict[str, FuzzyPhraseSearcher] = {}
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
        searcher = FuzzyPhraseSearcher(searcher_config)
        searcher.index_phrase_model(phrase_model)
        # searcher.index_phrases(phrase_model.get_phrases())
        # make sure the EventSearcher knows which keywords and labels are registered
        # self.add_keywords(phrase_model)
        # self.add_labels(phrase_model)
        # searcher.index_variants(phrase_model.get_variants())
        # add the keyword searcher to the EventSearcher
        self.searchers[searcher_name] = searcher
        self.phrase_models[searcher_name] = phrase_model

    def add_phrases(self, phrase_model: PhraseModel):
        """Add all the phrases of a phrase model to the EventSearcher."""
        for phrase in phrase_model.get_phrases():
            self.phrases[phrase] = True

    def get_phrases(self):
        """Return all the phrases registered in the EventSearcher."""
        return list(self.phrases.keys())

    def has_phrase(self, phrase: str):
        """Check if phrase is registered in the EventSearcher."""
        return phrase in self.phrases

    def add_labels(self, phrase_model: PhraseModel):
        """Add the labels of all the phrases of a phrase model to the EventSearcher."""
        for phrase in phrase_model.get_phrases():
            for label in phrase.label_list:
                if phrase_model.has_label(label):
                    self.labels[phrase] = label

    def get_label(self, phrase: str):
        """Return all the phrases registered in the EventSearcher."""
        if not self.has_phrase(phrase):
            raise ValueError(f"Unknown phrase {phrase}")
        if not self.has_label(phrase):
            raise KeyError(f"Keyword {phrase} has no registered label")
        return list(self.phrases.keys())

    def has_label(self, phrase: str):
        """Check if phrase has a registered label in the EventSearcher."""
        return phrase in self.labels

    def search_document(self, doc: Dict[str, Union[str, int]],
                        searcher_name: str) -> List[PhraseMatch]:
        """Use a registered searcher to find fuzzy match for a document."""
        matches: List[PhraseMatch] = []
        # use the searcher to find fuzzy matches
        for match in self.searchers[searcher_name].find_matches(doc, include_variants=True):
            match_string = match.phrase.phrase_string
            # check if the phrase exceeds minimum or maximum offset thresholds
            if match_string in self.max_offsets and match.offset > self.max_offsets[match_string]:
                continue
            if match_string in self.min_offsets and match.offset < self.min_offsets[match_string]:
                continue
            # add the searcher_name to the match so we know where it came from
            if isinstance(match.label, str):
                match.label = [match.label]
            match.metadata['searcher'] = searcher_name
            # if the phrase has a label, add it to the match
            # if self.phrase_models[searcher_name].has_label(phrase):
            #     match['match_label'] = self.phrase_models[searcher_name].get_label(phrase)
            matches += [match]
        return matches

    def add_empty_document(self):
        """Append an empty placeholder document to the sliding window."""
        # if the window is too long, remove earliest docs to make room for the new doc
        if len(self.sliding_window) >= self.window_size:
            self.sliding_window = self.sliding_window[-self.window_size:]
        self.sliding_window += [None]

    def add_document(self, doc_id: Union[str, int], doc_text: str, text_object: any = None):
        """Add a text with identifier to the sliding window and run registered fuzzy searchers."""
        matches: List[PhraseMatch] = []
        doc = {'id': doc_id, 'text': doc_text, 'matches': matches}
        if text_object:
            doc['text_object'] = text_object
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
                matches.append({'text_index': text_index, 'id': text['id'], 'match': match})
        return matches
