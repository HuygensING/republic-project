from typing import Dict, List, Union

from fuzzy_search.fuzzy_match import PhraseMatch
from fuzzy_search.fuzzy_phrase_searcher import FuzzyPhraseSearcher

import pagexml.model.physical_document_model as pdm


def sort_page_textregions(page: pdm.PageXMLPage) -> List[pdm.PageXMLTextRegion]:
    trs = page.extra + [tr for col in page.columns for tr in col.text_regions]
    return sorted(trs, key=lambda tr: tr.coords.y)


def get_session_info(trs: List[pdm.PageXMLTextRegion]) -> Dict[str, Union[bool, None]]:
    session_info = {
        'has_session_start': False,
        'has_attendance': False,
        'has_date': False,
        'has_short_date': False,
        'has_full_date': False,
        'full_date_tr': None,
        'attendance_tr': None
    }
    for tr in trs:
        if 'date' in tr.type:
            session_info['has_date'] = True
        if 'attendance' in tr.type:
            session_info['has_attendance'] = True
        if 'date' in tr.type:
            tr_text = '\n'.join([line.text for line in tr.get_lines() if line.text is not None])
            if len(tr_text) > 20:
                session_info['has_full_date'] = True
                session_info['full_date_tr'] = tr
            else:
                session_info['has_short_date'] = True
                session_info['short_date_tr'] = tr
        elif 'attendance' in tr.type:
            session_info['attendance_tr'] = tr
            session_info['has_attendance'] = True
    session_info['has_session_start'] = session_info['has_full_date'] or session_info['has_attendance']
    return session_info


def extract_best_date_match(matches: List[PhraseMatch]) -> Union[None, str]:
    if len(matches) == 0:
        return None
    best_match = sorted(matches, key=lambda m: m.levenshtein_similarity)[-1]
    return best_match.phrase.phrase_string


def find_session_date(trs: List[pdm.PageXMLTextRegion],
                      session_info: Dict[str, Union[bool, None, pdm.PageXMLTextRegion]],
                      date_searcher: FuzzyPhraseSearcher) -> List[str]:
    session_date = []
    if session_info['has_full_date']:
        date_tr = session_info['full_date_tr']
        tr_text = '\n'.join([line.text for line in date_tr.get_lines() if line.text is not None])
        matches = date_searcher.find_matches({'id': date_tr.id, 'text': tr_text})
        return extract_best_date_match(matches)
    elif session_info['has_attendance']:
        print('\tNO FULL DATE')
        attendance = session_info['attendance_tr']
        for tr in trs:
            for line in tr.lines:
                if line.text is None:
                    continue
                if pdm.vertical_distance(line, attendance) > 800:
                    continue
                matches = date_searcher.find_matches({'id': line.id, 'text': line.text})
                if len(matches) > 0:
                    session_dates.append
                print('CANDIDATE:', attendance.coords.top, line.coords.top, line.text)


def parse_page(page: pdm.PageXMLPage, date_searcher: FuzzyPhraseSearcher):
    trs = sort_page_textregions(page)
    session_info = get_session_info(trs)
    print(page.id, session_info['has_session_start'])
    if session_info['has_session_start']:
        session_date = find_session_date(trs, session_info)
