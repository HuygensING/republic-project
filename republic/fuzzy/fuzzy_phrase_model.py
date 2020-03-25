from typing import Dict, List, Union
import json
import copy


class PhraseModel:

    def __init__(self, keywords: Union[None, List[Union[str, Dict[str, Union[str, list]]]]] = None,
                 variants: Union[None, List[Dict[str, List[str]]]] = None,
                 keyword_labels: Union[None, List[Dict[str, str]]] = None,
                 model: Union[None, List[Dict[str, Union[str, list]]]] = None,
                 custom: Union[None, List[Dict[str, Union[str, int, float, list]]]] = None):
        self.keywords = set()
        # only register variants of known keywords
        self.variants = {}
        self.labels = {}
        self.custom = {}
        if keywords:
            self.add_keywords(keywords)
        if variants:
            self.add_variants(variants)
        if keyword_labels:
            self.add_labels(keyword_labels)
        if model:
            self.add_model(model)
        if custom:
            self.add_custom(custom)

    def __repr__(self):
        """A phrase model to support fuzzy searching in OCR/HTR output."""
        return f"PhraseModel({json.dumps(self.to_json(), indent=2)})"

    def __str__(self):
        return self.__repr__()

    def add_model(self, model: List[Union[str, Dict[str, Union[str, list]]]]):
        self.add_keywords(model)
        self.add_variants(model)
        self.add_labels(model)
        self.add_custom(model)

    def to_json(self):
        model_json = []
        for keyword in self.keywords:
            entry = {'keyword': keyword}
            if keyword in self.variants:
                entry['variants'] = self.variants[keyword]
            if keyword in self.labels:
                entry['label'] = self.labels[keyword]
            model_json += [entry]
        return model_json

    def add_keywords(self, keywords: List[Union[str, Dict[str, Union[str, list]]]]):
        """Add a list of keywords to the phrase model. Keywords must be either:
        - a list of strings
        - a list of dictionaries with property 'keyword' and the keyword as a string value
        """
        for keyword in keywords:
            if isinstance(keyword, dict):
                if 'keyword' not in keyword:
                    raise KeyError("Keywords as list of dictionaries should have 'keyword' property")
                if not isinstance(keyword['keyword'], str):
                    raise TypeError('keywords mut be of type string')
            elif not isinstance(keyword, str):
                raise TypeError('keywords mut be of type string')
        for keyword in keywords:
            if isinstance(keyword, dict):
                self.keywords.add(keyword['keyword'])
            else:
                self.keywords.add(keyword)

    def remove_keywords(self, keywords: List[Union[str, Dict[str, Union[str, list]]]]):
        """Remove a list of keywords from the phrase model. If it has any registered spelling variants,
        remove those as well."""
        for keyword in keywords:
            if isinstance(keyword, dict):
                if 'keyword' not in keyword:
                    raise KeyError("Keywords as list of dictionaries should have 'keyword' property")
                else:
                    keyword = keyword['keyword']
            if keyword not in self.keywords:
                raise KeyError(f"Unknown keyword: {keyword}")
            self.keywords.remove(keyword)
            if keyword in self.variants:
                del self.variants[keyword]

    def get_keywords(self) -> List[str]:
        """Return a list of all registered keywords."""
        return list(self.keywords)

    def add_variants(self, variants: List[Dict[str, Union[str, List[str]]]], add_new_keywords: bool = True):
        """Add variants of a keyword. If the keyword is not registered, add it to the set.
        - input is a list of dictionaries:
        variants = [
            {'keyword': 'some keyword', 'variants': ['some variant', 'some other variant']}
        ]
        """
        # first, check that all variants of all keywords are strings
        for keyword_variants in variants:
            if not isinstance(keyword_variants['keyword'], str):
                raise TypeError('keywords must be of type string')
            if 'variants' not in keyword_variants:
                continue
            for variant in keyword_variants['variants']:
                if not isinstance(variant, str):
                    raise TypeError('spelling variants must be of type string')
        for keyword_variants in variants:
            if keyword_variants['keyword'] not in self.keywords and add_new_keywords:
                self.keywords.add(keyword_variants['keyword'])
            elif keyword_variants['keyword'] not in self.keywords:
                continue
            if 'variants' not in keyword_variants:
                continue
            # make sure the list variants is a copy of the original and not a reference to the same list
            self.variants[keyword_variants['keyword']] = copy.copy(keyword_variants['variants'])

    def remove_variants(self, variants: Union[List[Dict[str, List[str]]], None] = None,
                        keyword: Union[str, None] = None):
        """Remove a list of spelling variants of a keyword.
        - variants: a list of dictionaries with keywords as key and the list of variants to be removed as values
        variants = [
            {'keyword': 'some keyword', 'variants': ['some variant', 'some other variant']}
        ]
        - keyword: remove all variants of a given keyword"""
        if variants:
            for keyword_variants in variants:
                if keyword_variants['keyword'] not in variants:
                    raise KeyError(f"Cannot remove variants of unknown keyword {keyword_variants['keyword']}")
                for variant in keyword_variants['variants']:
                    if variant in self.variants[keyword]:
                        self.variants[keyword].remove(variant)
        if keyword and keyword in self.variants:
            del self.variants[keyword]

    def get_variants(self, keywords: List[str] = None) -> List[Dict[str, Union[str, List[str]]]]:
        """Return registered variants of a specific set of keywords or all registered keywords."""
        if keywords:
            for keyword in keywords:
                if not isinstance(keyword, str):
                    raise ValueError('Keywords must be of type string')
                if keyword not in self.keywords:
                    raise ValueError('Unknown keyword')
            return [{'keyword': keyword, 'variants': self.variants[keyword]} for keyword in keywords]
        else:
            return list(self.variants)

    def add_labels(self, keyword_labels: List[Dict[str, Union[str, list]]]):
        """Add a label to a keyword. This can be used to group keywords under the same label.
        - input is a list of keyword/label pair dictionaries:
        labels = [
            {'keyword': 'some keyword', 'label': 'some label'}
        ]
        """
        for keyword_label in keyword_labels:
            if not isinstance(keyword_label['label'], str):
                raise TypeError('keyword labels must be of type string')
        for keyword_label in keyword_labels:
            keyword = keyword_label['keyword']
            label = keyword_label['label']
            if keyword not in self.keywords:
                print(f'skipping label for unknown keyword {keyword}')
            self.labels[keyword] = label

    def remove_labels(self, keywords: List[str]):
        """Remove labels for known keywords. Input is a list of known keywords"""
        for keyword in keywords:
            if keyword not in self.keywords:
                raise TypeError(f'unknown keyword {keyword}')
            else:
                del self.labels[keyword]

    def has_label(self, keyword: str) -> bool:
        return keyword in self.labels

    def get_label(self, keyword: str) -> str:
        if keyword not in self.labels:
            raise KeyError(f"Unknown keyword: {keyword}")
        return self.labels[keyword]

    def check_entry_keyword(self, entry: Dict[str, Union[str, int, float, list]]):
        if 'keyword' not in entry:
            raise KeyError("Keywords as list of dictionaries should have 'keyword' property")
        if entry['keyword'] not in self.keywords:
            raise KeyError("Unknown keyword")

    def add_custom(self, custom: List[Dict[str, Union[str, int, float, list]]]):
        for entry in custom:
            self.check_entry_keyword(entry)
            # make sure the custom entry is a copy of the original and not a reference to the same object
            self.custom[entry['keyword']] = copy.copy(entry)

    def remove_custom(self, custom: List[Dict[str, Union[str, int, float, list]]]):
        """Remove custom properties for a list of keywords"""
        for entry in custom:
            self.check_entry_keyword(entry)
            for custom_property in entry:
                del self.custom[entry['keyword']][custom_property]

    def has_custom(self, keyword: str, custom_property: str) -> bool:
        """Check if a keyword has a given custom property."""
        return keyword in self.custom and custom_property in self.custom[keyword]

    def get(self, keyword: str, custom_property: str) -> Union[str, int, float, list]:
        """Get the value of a custom property for a given keyword."""
        if keyword not in self.keywords:
            raise KeyError("Unknown keyword")
        if not self.has_custom(keyword, custom_property):
            raise ValueError("Unknown custom property")
        return self.custom[keyword][custom_property]
