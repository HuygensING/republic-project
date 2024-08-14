from typing import Dict, List

import pagexml.model.physical_document_model as pdm

import republic.model.republic_document_model as rdm


def check_session(session: rdm.Session):
    # check that session has some evidence
    if session.evidence is None or (isinstance(session.evidence, list) and len(session.evidence) == 0):
        print(f"WARNING - no evidence for session {session.id}")
    # check that session has date metadata
    if session.date_metadata is None:
        raise ValueError(f"quality_control.check_session - no date metadata for session {session.id}")
    # check that session has no lines
    if len(session.lines) > 0:
        raise ValueError(f"quality_control.check_session - session {session.id} has lines ")
    # check that session has text regions
    if len(session.text_regions) == 0:
        raise ValueError(f"quality_control.check_session - session {session.id} has no text regions ")

    tr_fields = ['page_id', 'scan_id', 'inventory_num', 'inventory_id']
    line_fields = ['page_id', 'scan_id', 'inventory_num', 'inventory_id', 'text_region_id']
    for tr in session.text_regions:
        for field in tr_fields:
            if field not in tr.metadata:
                raise KeyError(f'{field} missing in metadata for text_region {tr.id} in session {session.id}')
            if tr.metadata[field] is None:
                raise KeyError(f'empty {field} field in metadata for text_region {tr.id} in session {session.id}')
        for line in tr.lines:
            for field in line_fields:
                if field not in line.metadata:
                    raise KeyError(f'{field} missing in metadata for line {line.id} in session {session.id}')
                if line.metadata[field] is None:
                    raise KeyError(f'empty {field} field in metadata for line {line.id} in session {session.id}')

    session_json = session.json
    if 'evidence' not in session_json:
        raise KeyError(f"quality_control.check_session - 'evidence' not in session_json "
                       f"for session {session.id}")
    if session_json['evidence'] is None:
        raise KeyError(f"quality_control.check_session - session_json['evidence'] is None "
                       f"for session {session.id}")
    if len(session_json['evidence']) != len(session.evidence):
        raise KeyError(f"quality_control.check_session - session_json['evidence'] has different "
                       f"number of matches ({len(session_json['evidence'])}) than "
                       f"session.evidence ({len(session.evidence)}) for session {session.id}")
    if 'date_metadata' not in session_json:
        raise KeyError(f"quality_control.check_session - 'date_metadata' not in session_json "
                       f"for session {session.id}")
    if session_json['date_metadata'] is None:
        raise KeyError(f"quality_control.check_session - session_json['date_metadata'] is None "
                       f"for session {session.id}")


def check_pages_to_sessions(session: rdm.Session, session_meta: Dict[str, any],
                            session_trs: List[pdm.PageXMLTextRegion]):
    if session.id != session_meta['id']:
        raise ValueError(f"session.id {session.id} not equal to session_meta['id']: {session_meta['id']}")

    # check that session has some evidence
    if session.evidence is None or (isinstance(session.evidence, list) and len(session.evidence) == 0):
        print(f"WARNING - no evidence for session {session.id}")
    # check that session_meta has same evidence
    if 'evidence' not in session_meta or session_meta['evidence'] is None \
            or not isinstance(session_meta['evidence'], list):
        raise ValueError(f"No evidence in session_meta: {session_meta['id']}")
    session_tr_ids = {tr.id for tr in session_trs}
    missing_meta = session_tr_ids - set(session_meta['text_region_ids'])
    missing_session_trs = set(session_meta['text_region_ids']) - session_tr_ids
    if len(missing_meta) > 0:
        raise KeyError(f"session_tr.ids {missing_meta} missing in "
                       f"session_meta['text_region_ids'] {session_meta['text_region_ids']}")
    if len(missing_session_trs) > 0:
        raise KeyError(f"session_meta['text_region_ids'] {missing_session_trs} missing in "
                       f"session_tr.ids {session_tr_ids}")
    return None


def check_session_to_resolutions(session: rdm.Session, resolutions: List[rdm.Resolution]):
    # check that all session lines are covered by resolutions
    # check that resolutions have only lines that are part of the session
    session_lines = {line.id: line for tr in session.text_regions for line in tr.lines}
    matched_lines = []
    for res in resolutions:
        for para in res.paragraphs:
            for tr in para.text_regions:
                for line in tr.lines:
                    if line.id not in session_lines:
                        raise IndexError(f"resolution {res.id} contains a line that is not part of "
                                         f"the session {session.id}: line {line.id}")
                    else:
                        matched_lines.append(line)
    return None
