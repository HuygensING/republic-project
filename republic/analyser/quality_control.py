from typing import List

import republic.model.republic_document_model as rdm
from republic.elastic.republic_elasticsearch import RepublicElasticsearch


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
