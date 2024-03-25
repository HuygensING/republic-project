from typing import Dict, List

import pagexml.model.physical_document_model as pdm
from fuzzy_search import PhraseMatch

from republic.helper.metadata_helper import doc_id_to_iiif_url
from republic.model.republic_date import RepublicDate


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


def make_session_date_metadata(current_date: RepublicDate, fuzzy_date_match: PhraseMatch,
                               date_line: pdm.PageXMLTextLine) -> Dict[str, any]:
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
        session_date['date_match_string'] = fuzzy_date_match.string,
    if date_line is not None:
        session_date['page_id'] = date_line.metadata['page_id']
        session_date['scan_id'] = date_line.metadata['scan_id']
        if 'inventory_num' in date_line.metadata:
            session_date['inventory_num'] = date_line.metadata['inventory_num']
            session_date['inventory_id'] = date_line.metadata['inventory_id']
        elif date_line.parent is not None:
            # date_tr = date_line.parent
            # print('date_tr:', date_tr)
            # date_col = date_tr.parent
            # print('date_col:', date_col)
            # date_page = date_col.parent
            date_page = get_page_from_parentage(date_line)
            if date_page is None:
                ValueError(f'no parent set in hierarchy above line {date_line.id}')
            # print(date_page)
            # print(date_line.id, date_tr.id, date_col, date_col.parent.id)
            # print('inventory_num' in date_tr.metadata)
            # print('inventory_num' in date_tr.parent.metadata)
            # print('inventory_num' in date_col.parent.metadata)
            session_date['inventory_num'] = date_page.metadata['inventory_num']
            session_date['inventory_id'] = date_page.metadata['inventory_id']
        else:
            raise KeyError(f'no inventory_num in line metadata and no parent for line {date_line.id}')
        session_date['text_region_id'] = date_line.metadata['text_region_id']
        session_date['line_id'] = date_line.id
        session_date['iiif_url'] = doc_id_to_iiif_url(date_line.id, margin=100)
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
        'text_type': text_type,
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
