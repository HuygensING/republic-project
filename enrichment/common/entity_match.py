from __future__ import annotations
from typing import Optional, Union
from dataclasses import dataclass, asdict, field
from json import dumps
from fuzzy_search.match.phrase_match import PhraseMatch
from re import Match

def serialise_with_sets(obj):
    if isinstance(obj, set):
        return list(obj)
    return obj

@dataclass
class JSONSerialisable:
    @property
    def json(self):
        return dumps(asdict(self), default=serialise_with_sets, indent=4)

@dataclass
class EntityReference(JSONSerialisable):
    layer: str
    inv: str
    tag_text: str
    resolution_id: str
    paragraph_id: str
    offset: int
    end: int
    tag_length: int

@dataclass
class EntityLabel(JSONSerialisable):
    name: str
    category: str
    labels: set[str] = field(default_factory=set)
    comment: str = field(default=None)

@dataclass
class EntityProvenance(JSONSerialisable):
    source: str
    criterium: str
    outcome: str
    conclusion: str

    @classmethod
    def from_match(self, source: str, match: Union[Match,PhraseMatch], conclusion: Optional[str] = None) -> EntityProvenance:
        '''
        Construct a provenance entry from a regular expression match object or 
        from a (fuzzy_search) phrase match.

        For a PhraseMatch the conclusion can be omitted: then, it will be 
        assumed the `label` of the PhraseMatch is the name of the assigned 
        entity.
        '''
        if isinstance(match, Match):
            if conclusion is None:
                raise ValueError(f'No conclusion for regular expression match {match.re}')
            return EntityProvenance(source, match.re.pattern, match[0], conclusion)
        elif isinstance(match, PhraseMatch):
            if conclusion is None:
                conclusion = f'Assign entity: {match.label}'
            return EntityProvenance(source, match.variant.phrase_string, match.string, conclusion)
        raise ValueError(f'Unknown match object: {match}')

@dataclass
class EntityMatch(JSONSerialisable):
    reference: EntityReference
    provenance: [EntityProvenance]
    entity: EntityLabel

