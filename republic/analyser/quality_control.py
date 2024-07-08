from typing import Dict, List

import pagexml.model.physical_document_model as pdm

import republic.model.republic_document_model as rdm
from republic.elastic.republic_elasticsearch import RepublicElasticsearch


def check_pages_to_resolutions(session: rdm.Session, session_meta: Dict[str, any],
                               session_trs: List[pdm.PageXMLTextRegion]):
    # check that session has some evidence
    if session.evidence is None or (isinstance(session.evidence, list) and len(session.evidence) == 0):
        raise ValueError(f"No evidence for session {session.id}")
    # check that session_meta has same evidence

    return None


def check_session_to_resolutions(session: rdm.Session, resolutions: List[rdm.Resolution],
                                 rep_es: RepublicElasticsearch, delete_previous: bool = False):
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
    # check that index has no resolutions for that session
    retrieved = rep_es.retrieve_resolutions_by_session_id(session.id)
    if len(retrieved) > 0:
        print(f'check_session_to_resolutions - there are indexed resolutions for session {session.id}')
        if delete_previous is True:
            query = {'match': {'metadata.session_id.keyword': session.id}}
            rep_es.delete_by_query(rep_es.config['resolution_index'], query)
    return None
