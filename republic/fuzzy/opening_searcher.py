from typing import List
import fuzzy_search
import republic.model.republic_document_model as rdm
from fuzzy_search.search.phrase_searcher import FuzzyPhraseSearcher


def needs_followed_by_lookup(matches: List[fuzzy_search.PhraseMatch]) -> bool:
    if rdm.get_proposition_type_from_evidence(matches) not in {'onbekend', 'afhankelijk'}:
        return False
    return has_followed_by(matches)


def has_followed_by(matches: List[fuzzy_search.PhraseMatch]) -> bool:
    for match in matches:
        if 'followed_by' in match.phrase.properties:
            return True
    return False


def resolve_followed_by(followed_by_searcher: FuzzyPhraseSearcher,
                        matches: List[fuzzy_search.PhraseMatch], doc: dict[str, any]) -> List[fuzzy_search.PhraseMatch]:
    resolved_matches = [match for match in matches]
    for match in matches:
        if 'followed_by' in match.phrase.properties:
            following_matches = followed_by_searcher.find_matches(doc)
            # print(f"following_matches:", following_matches)
            resolved_matches.extend(following_matches)
    return resolved_matches


def make_followed_by_searcher(opening_searcher: FuzzyPhraseSearcher) -> FuzzyPhraseSearcher:
    following_phrases = []
    phrases = opening_searcher.phrase_model.phrase_index.values()
    for phrase in phrases:
        if 'followed_by' in phrase.properties:
            following_phrases.extend(phrase.properties['followed_by'])
    followed_by_searcher = FuzzyPhraseSearcher(phrase_list=following_phrases, config=opening_searcher.config)
    return followed_by_searcher


