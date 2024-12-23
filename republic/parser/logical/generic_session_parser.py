import copy
from typing import Dict, List, Union

import pagexml.model.physical_document_model as pdm
from fuzzy_search import PhraseMatch

import republic.model.republic_document_model as rdm
from republic.helper.metadata_helper import doc_id_to_iiif_url
from republic.model.republic_date import RepublicDate


TEXT_TYPE_MAP = {
    'handwritten': 'handgeschreven',
    'printed': 'gedrukt'
}


def map_text_type(text_type: str):
    if text_type in TEXT_TYPE_MAP:
        return TEXT_TYPE_MAP[text_type]
    elif text_type in TEXT_TYPE_MAP.values():
        return text_type
    else:
        accepted_values = [tt for item in TEXT_TYPE_MAP.items() for tt in item]
        raise ValueError(f"invalid text_type '{text_type}', must be one of {accepted_values}")


def get_page_from_parentage(doc: pdm.PageXMLDoc):
    """Find the page in the parentage hierarchy of a PageXMLDoc document."""
    if isinstance(doc, pdm.PageXMLPage):
        return doc
    if doc.parent is None:
        return None
    parent = doc.parent
    seen = {doc}
    while parent:
        if isinstance(parent, pdm.PageXMLPage):
            return parent
        if parent is not None:
            seen.add(parent)
        if parent.parent in seen:
            raise ValueError(f"loop in parentage hierarchy from doc {doc.id}, "
                             f"parent {parent.parent.id} of {parent.id} has already been encountered")
        parent = parent.parent
    return parent


def make_session_date_metadata(current_date: RepublicDate,
                               date_line: Union[pdm.PageXMLTextLine, List[pdm.PageXMLTextLine]],
                               fuzzy_date_match: PhraseMatch = None,
                               start_record: Dict[str, any] = None) -> Dict[str, any]:
    session_date = {
        'session_date': current_date.isoformat(),
        'session_year': current_date.year,
        'session_month': current_date.month,
        'session_day': current_date.day,
        'session_weekday': current_date.day_name,
        'is_workday': current_date.is_work_day(),
        'evidence': None,
        'date_phrase_string': None,
        'date_match_string': None,
        'page_id': None,
        'scan_id': None,
        'inventory_num': None,
        'inventory_id': None,
        'text_region_id': None,
        'line_id': None,
        'iiif_url': None
        # 'text': line.text
    }
    if fuzzy_date_match is not None:
        session_date['evidence'] = fuzzy_date_match.json()
        session_date['date_phrase_string'] = fuzzy_date_match.phrase.phrase_string
        session_date['date_match_string'] = fuzzy_date_match.string
    elif start_record is not None:
        session_date['evidence'] = copy.deepcopy(start_record)
        session_date['evidence']['type'] = 'manual_annotation'
        session_date['date_phrase_string'] = None
        session_date['date_match_string'] = None
    else:
        session_date['evidence'] = None
        session_date['date_phrase_string'] = None
        session_date['date_match_string'] = None
    if date_line is not None:
        date_lines = date_line if isinstance(date_line, list) else [date_line]
        session_date['page_id'] = sorted(set([dl.metadata['page_id'] for dl in date_lines]))
        session_date['scan_id'] = sorted(set([dl.metadata['scan_id'] for dl in date_lines]))
        first_line = date_lines[0]
        if 'inventory_num' in first_line.metadata:
            session_date['inventory_num'] = date_line.metadata['inventory_num']
            session_date['inventory_id'] = date_line.metadata['inventory_id']
        elif first_line.parent is not None:
            # date_tr = date_line.parent
            # print('date_tr:', date_tr)
            # date_col = date_tr.parent
            # print('date_col:', date_col)
            # date_page = date_col.parent
            date_page = get_page_from_parentage(first_line)
            if date_page is None:
                ValueError(f'no parent set in hierarchy above line {first_line.id}')
            # print(date_page)
            # print(date_line.id, date_tr.id, date_col, date_col.parent.id)
            # print('inventory_num' in date_tr.metadata)
            # print('inventory_num' in date_tr.parent.metadata)
            # print('inventory_num' in date_col.parent.metadata)
            session_date['inventory_num'] = date_page.metadata['inventory_num']
            session_date['inventory_id'] = date_page.metadata['inventory_id']
        else:
            raise KeyError(f'no inventory_num in line metadata and no parent for line {first_line.id}')
        session_date['text_region_id'] = first_line.metadata['text_region_id']
        session_date['line_id'] = first_line.id
        session_date['iiif_url'] = doc_id_to_iiif_url(first_line.id, margin=100)
    return session_date


def make_session_metadata(inv_metadata: Dict[str, any], session_date: Dict[str, any],
                          session_num: int, text_type: str, includes_rest_day: bool = False) -> Dict[str, any]:
    session_metadata = {
        'session_id': f'session-{inv_metadata["inventory_num"]}-num-{session_num}',
        'session_num': session_num,
        'session_date': session_date['session_date'],
        'session_year': session_date['session_year'],
        'session_month': session_date['session_month'],
        'session_day': session_date['session_day'],
        'is_workday': session_date['is_workday'],
        'session_weekday': session_date['session_weekday'],
        'inventory_id': inv_metadata['inventory_id'],
        'inventory_num': inv_metadata['inventory_num'],
        'series_name': inv_metadata['series_name'],
        'resolution_type': inv_metadata['resolution_type'],
        "attendants_list_id": None,
        "resolution_ids": [],
        'president': None,
        'has_session_date_element': False,
        'lines_include_rest_day': includes_rest_day,
        'text_type': map_text_type(text_type),
        'evidence': []
    }
    return session_metadata


def make_session(inv_metadata: Dict[str, any], session_date: Dict[str, any],
                 session_num: int, text_type: str,
                 session_trs: List[pdm.PageXMLTextRegion]) -> Dict[str, any]:
    session_metadata = make_session_metadata(inv_metadata, session_date, session_num, text_type)
    session = {
        'id': f'session-{inv_metadata["inventory_num"]}-num-{session_num}',
        'type': ['republic_doc', 'logical_structure_doc', 'session'],
        'domain': 'logical',
        'metadata': session_metadata,
        'date': session_date,
        'text_region_ids': [tr.id for tr in session_trs],
        'scan_ids': list(sorted(set([tr.metadata['scan_id'] for tr in session_trs]))),
        'page_ids': list(sorted(set([tr.metadata['page_id'] for tr in session_trs]))),
        'evidence': session_date['evidence'],
        'stats': {
            'words': sum([tr.stats['words'] for tr in session_trs]),
            'lines': sum([tr.stats['lines'] for tr in session_trs]),
            'text_regions': len(session_trs),
            'pages': len(set([tr.metadata['page_id'] for tr in session_trs])),
            'scans': len(set([tr.metadata['scan_id'] for tr in session_trs])),
        }
    }
    return session


def make_session_from_meta_and_trs(session_meta: Dict[str, any],
                                   session_trs: List[pdm.PageXMLTextRegion]) -> rdm.Session:
    if isinstance(session_meta['evidence'], list) is False:
        session_meta['evidence'] = [session_meta['evidence']]
    session_meta['evidence'] = [PhraseMatch.from_json(match) for match in session_meta['evidence']]
    return rdm.Session(doc_id=session_meta['id'], metadata=session_meta['metadata'],
                       date_metadata=session_meta['date'], evidence=session_meta['evidence'],
                       text_regions=session_trs)
