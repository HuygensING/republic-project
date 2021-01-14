from typing import Union
import hashlib
from fuzzy_search.fuzzy_match import PhraseMatch

from republic.model.republic_document_model import Resolution


def make_hash_id(match: Union[dict, PhraseMatch]):
    if isinstance(match, PhraseMatch):
        return hashlib.md5(f"{match.text_id}-{match.offset}-{match.end}".encode()).hexdigest()
    else:
        match_end = match['offset'] + len(match['string'])
        return hashlib.md5(f"{match['text_id']}-{match['offset']}-{match_end}".encode()).hexdigest()


def make_swao_anno(match: PhraseMatch, resolution: Resolution) -> dict:
    match_anno = match.as_web_anno()
    match_anno['target'] = make_nested_pid_target(match_anno['target'], resolution)
    match_anno['target_list'] = match_anno['target']
    match_anno['permissions'] = {
        "access_status": ["public"],
        "owner": "marijn"
    }
    return match_anno


def make_nested_pid_target(match_target: dict, resolution: Resolution) -> dict:
    match_target['refinedBy'] = match_target['selector']
    match_target['selector'] = {
        "@context": [
            "https://annotation.clariah.nl/ns/swao.jsonld",
            "https://annotation.republic-caf.diginfra.org/ns/republic.jsonld"
        ],
        "type": "NestedPIDSelector",
        "value": [
            {
                "id": resolution.metadata['id'].split('-resolution')[0],
                "type": "Meeting"
            },
            {
                "id": resolution.metadata['id'],
                "type": "Resolution"
            },
            {
                "id": match_target['source'],
                "type": "ResolutionParagraph"
            },
        ]
    }
    return match_target
