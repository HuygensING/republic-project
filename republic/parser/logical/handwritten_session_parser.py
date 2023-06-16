import re
from collections import defaultdict
from itertools import combinations
from typing import Dict, List, Union

import pagexml.model.physical_document_model as pdm
from fuzzy_search.match.phrase_match import PhraseMatch
from fuzzy_search.search.phrase_searcher import FuzzyPhraseSearcher

from republic.classification.line_classification import NeuralLineClassifier
from republic.classification.page_features import get_line_base_dist
from republic.helper.text_helper import is_duplicate
from republic.helper.metadata_helper import coords_to_iiif_url
from republic.model.inventory_mapping import get_inventory_by_id
from republic.model.republic_date import DateNameMapper
from republic.model.republic_date import RepublicDate
from republic.model.republic_date import get_next_date_strings
from republic.model.republic_word_model import get_specific_date_words


def generate_date_string(curr_date: RepublicDate):
    date_mapper = DateNameMapper(text_type='handwritten', resolution_type='ordinaris',
                                 period_start=1600, period_end=1700)
    return get_next_date_strings(curr_date, num_dates=7)


def sort_lines_by_class(page, line_classifier: NeuralLineClassifier):
    class_lines = defaultdict(list)
    predicted_line_class = line_classifier.classify_page_lines(page)
    for col in sorted(page.columns, key=lambda c: c.coords.left):
        for tr in sorted(col.text_regions, key=lambda t: t.coords.top):
            # print(tr.type)
            for line in tr.lines:
                if 'marginalia' in tr.type:
                    class_lines['marginalia'].append(line)
                    line.metadata['line_class'] = 'marginalia'
                    line.metadata['line_classifier'] = 'loghi'
                elif line.id in predicted_line_class:
                    pred_class = predicted_line_class[line.id]
                    if 'date' in tr.type and pred_class != 'date':
                        line.metadata['line_class'] = 'date'
                        line.metadata['line_classifier'] = 'loghi'
                        if tr.stats['words'] >= 4:
                            # print('DISAGREEMENT', line.text)
                            class_lines['date'].append(line)
                            continue
                    # elif 'date' not in tr.type and pred_class == 'date':
                        # print('DISAGREEMENT', line.text)
                        # print('NLC predicts date')
                    if pred_class.startswith('para_'):
                        class_lines['para'].append(line)
                        line.metadata['line_class'] = pred_class
                        line.metadata['line_classifier'] = 'nlc_classifier'
                    else:
                        line.metadata['line_class'] = pred_class
                        line.metadata['line_classifier'] = 'nlc_classifier'
                        class_lines[pred_class].append(line)
                else:
                    line.metadata['line_class'] = 'unknown'
                    line.metadata['line_classifier'] = 'nlc_classifier'
                    class_lines['unknown'].append(line)
    return class_lines


def merge_line_class_trs(class_trs, line_class: str, page: pdm.PageXMLPage, distance_threshold: int = 400):
    """Check if pairs of text regions of the same class should be merged.
    This is only for attendance lists and session date references."""
    if len(class_trs) > 1:
        merged_trs = []
        prev_tr = class_trs[0]
        for curr_tr in class_trs[1:]:
            # print('prev', line_class, prev_tr.coords.bottom)
            # print('current', line_class, curr_tr.coords.top)
            if curr_tr.coords.top - prev_tr.coords.bottom < distance_threshold:
                # print('MERGING')
                merge_lines = prev_tr.lines + curr_tr.lines
                merge_coords = pdm.parse_derived_coords(merge_lines)
                metadata = make_text_region_metadata(line_class, merge_coords, page)
                merge_tr = pdm.PageXMLTextRegion(coords=merge_coords, lines=merge_lines, metadata=metadata)
                merge_tr.add_type(line_class)
                merge_tr.set_derived_id(merge_lines[0].metadata['scan_id'])
                merge_tr.metadata['text_region_class'] = curr_tr.metadata['text_region_class']
                merge_tr.metadata['text_region_links'] = []
                prev_tr = merge_tr
            else:
                # print('ADDING MERGED TR')
                merged_trs.append(prev_tr)
                # if curr_tr == class_trs[line_class][-1]:
                #     merged_trs.append(curr_tr)
                prev_tr = curr_tr
        # print('ADDING FINAL TR')
        merged_trs.append(prev_tr)
        return merged_trs
    else:
        return class_trs


def link_date_attendance(class_trs):
    has_attendance = defaultdict(list)
    if 'date' in class_trs and 'attendance' in class_trs:
        for date_tr in class_trs['date']:
            for att_tr in class_trs['attendance']:
                if pdm.is_vertically_overlapping(date_tr, att_tr, threshold=0.01):
                    has_attendance[date_tr].append(att_tr)
                elif date_tr.coords.top > att_tr.coords.bottom:
                    if abs(date_tr.coords.top - att_tr.coords.bottom) < 400:
                        has_attendance[date_tr].append(att_tr)
                elif date_tr.coords.bottom < att_tr.coords.top:
                    if abs(date_tr.coords.bottom - att_tr.coords.top) < 400:
                        has_attendance[date_tr].append(att_tr)
    for date_tr in has_attendance:
        if 'text_region_links' not in date_tr.metadata:
            date_tr.metadata['text_region_links'] = []
        for att_tr in has_attendance[date_tr]:
            if 'text_region_links' not in att_tr.metadata:
                att_tr.metadata['text_region_links'] = []
            date_tr.metadata['text_region_links'].append({
                'text_region_id': att_tr.id,
                'link_type': 'has_attendance'
            })
            att_tr.metadata['text_region_links'].append({
                'text_region_id': date_tr.id,
                'link_type': 'has_date'
            })
    return has_attendance


def link_para_marginalia(class_trs):
    has_marginalia = defaultdict(list)
    if 'para' in class_trs and 'marginalia' in class_trs:
        for para_tr in class_trs['para']:
            for marg_tr in class_trs['marginalia']:
                if pdm.is_vertically_overlapping(para_tr, marg_tr, threshold=0.5):
                    has_marginalia[para_tr].append(marg_tr)
    for para_tr in has_marginalia:
        if 'text_region_links' not in para_tr.metadata:
            para_tr.metadata['text_region_links'] = []
        for marg_tr in has_marginalia[para_tr]:
            if 'text_region_links' not in marg_tr.metadata:
                marg_tr.metadata['text_region_links'] = []
            para_tr.metadata['text_region_links'].append({
                'text_region_id': marg_tr.id,
                'link_type': 'has_marginalia'
            })
            marg_tr.metadata['text_region_links'].append({
                'text_region_id': para_tr.id,
                'link_type': 'describes_paragraph'
            })
    return has_marginalia


def make_text_region_metadata(line_class: str, group_coords: pdm.Coords, page: pdm.PageXMLPage):
    metadata = {
        'text_region_class': line_class,
        'text_region_classifier': 'nlc_classifier'
    }
    fields = [
        'scan_id',
        'inventory_id',
        'inventory_num',
        'inventory_period_start',
        'inventory_period_end',
        'series_name',
    ]
    for field in fields:
        metadata[field] = page.metadata[field]
    metadata['page_id'] = page.id
    metadata['iiif_url'] = coords_to_iiif_url(page.metadata['scan_id'], group_coords)
    metadata['text_region_links'] = []
    return metadata


def make_classified_text_regions(class_lines: Dict[str, List[pdm.PageXMLTextLine]],
                                 page: pdm.PageXMLPage) -> Dict[str, List[pdm.PageXMLTextRegion]]:
    class_trs = defaultdict(list)
    for line_class in class_lines:
        line_groups = split_lines_on_vertical_gaps(class_lines[line_class])
        for line_group in line_groups:
            group_coords = pdm.parse_derived_coords(line_group)
            group_metadata = make_text_region_metadata(line_class, group_coords, page)
            group_tr = pdm.PageXMLTextRegion(coords=group_coords, lines=line_group, metadata=group_metadata)
            group_tr.add_type(line_class)
            group_tr.set_derived_id(line_group[0].metadata['scan_id'])
            class_trs[line_class].append(group_tr)
    for line_class in ['date', 'attendance']:
        class_trs[line_class] = merge_line_class_trs(class_trs[line_class], line_class, page)
    return class_trs


def link_classified_text_regions(class_trs):
    has_attendance = link_date_attendance(class_trs)
    has_marginalia = link_para_marginalia(class_trs)
    linked_marginalia_trs = set([marg_tr for para_tr in has_marginalia for marg_tr in has_marginalia[para_tr]])
    linked_attendance_trs = set([att_tr for date_tr in has_attendance for att_tr in has_attendance[date_tr]])
    unlinked_att = [att_tr for att_tr in class_trs['attendance'] if att_tr not in linked_attendance_trs]
    unlinked_marg = [marg_tr for marg_tr in class_trs['marginalia'] if marg_tr not in linked_marginalia_trs]
    return unlinked_att, unlinked_marg


def print_trs(class_trs, has_attendance, has_marginalia):
    if 'date' in class_trs and 'para' in class_trs:
        main_trs = sorted(class_trs['date'] + class_trs['para'], key=lambda tr: tr.coords.top)
        for ti, tr in enumerate(main_trs):
            print('\t', ti, tr.coords.top, tr.coords.bottom, tr.type)
            for line in tr.lines:
                print('\t\t', line.text)
            if tr in has_attendance:
                for att_tr in has_attendance[tr]:
                    print('\t\tATTENDANCE', att_tr.coords.top, att_tr.coords.bottom, att_tr.type)
                    for line in att_tr.lines:
                        print('\t\t\t', line.text)
            if tr in has_marginalia:
                for marg_tr in has_marginalia[tr]:
                    print('\t\tMARGINALIA', marg_tr.coords.top, marg_tr.coords.bottom, marg_tr.type)
                    for line in marg_tr.lines:
                        print('\t\t\t', line.text)


def split_lines_on_vertical_gaps(lines: List[pdm.PageXMLTextLine]) -> List[List[pdm.PageXMLTextLine]]:
    lines = sorted(lines)
    line_groups = []
    if len(lines) == 0:
        return line_groups
    line_group = [lines[0]]
    if len(lines) == 1:
        return [line_group]
    for curr_line in lines[1:]:
        prev_line = line_group[-1]
        base_dist = get_line_base_dist(prev_line, curr_line)
        split = False
        if 'height' in curr_line.metadata and 'height' in prev_line.metadata:
            if base_dist > curr_line.metadata['height']['mean'] * 2:
                split = True
        elif base_dist > curr_line.coords.top + 50:
            split = True
        if split is True:
            line_groups.append(line_group)
            line_group = [curr_line]
        else:
            line_group.append(curr_line)
    if len(line_group) > 0:
        line_groups.append(line_group)
    return line_groups


def extract_best_date_match(matches: List[PhraseMatch]) -> Union[None, PhraseMatch]:
    if len(matches) == 0:
        return None
    best_match = sorted(matches, key=lambda m: m.levenshtein_similarity)[-1]
    return best_match


def find_session_dates(pages, inv_start_date, neural_line_classifier):
    date_strings = get_next_date_strings(inv_start_date, num_dates=7, include_year=False)
    config = {'ngram_size': 2, 'skip_size': 2}
    date_searcher = FuzzyPhraseSearcher(phrase_model=date_strings, config=config)
    session_dates = {}
    session_trs = defaultdict(list)
    current_date = None
    for pi, page in enumerate(pages):
        try:
            if pi > 1 and is_duplicate(page, pages[pi - 2]):
                print('FOUND duplicate page', page.id)
                continue
        except ZeroDivisionError:
            print(pi, page.id, pages[pi - 2].id)
            print(page.stats, pages[pi - 2].stats)
            raise
        if 'inventory_id' not in page.metadata:
            page.metadata['inventory_id'] = f"{page.metadata['series_name']}_{page.metadata['inventory_num']}"
        class_lines = sort_lines_by_class(page, neural_line_classifier)
        class_trs = make_classified_text_regions(class_lines, page)
        has_attendance = link_date_attendance(class_trs)
        has_marginalia = link_para_marginalia(class_trs)
        unlinked_att_trs, unlinked_marg_trs = link_classified_text_regions(class_trs)
        main_trs = sorted(class_trs['date'] + class_trs['para'], key=lambda tr: tr.coords.top)

        for main_tr in main_trs:
            if current_date and main_tr.metadata['text_region_class'] == 'para':
                session_trs[current_date.isoformat()].append(main_tr)
                if main_tr in has_marginalia:
                    for marg_tr in has_marginalia[main_tr]:
                        session_trs[current_date.isoformat()].append(marg_tr)
                continue
            for line in main_tr.lines:
                if line.text is None:
                    continue
                line_matches = date_searcher.find_matches({'id': line.id, 'text': line.text})
                filtered_matches = [match for match in line_matches if match.offset < 50]
                filtered_matches = [match for match in filtered_matches if
                                    abs(len(match.string) - len(line.text)) < 50]
                best_match = extract_best_date_match(filtered_matches)
                if best_match:
                    print('\t', best_match.phrase.phrase_string)
                    current_date = date_strings[best_match.phrase.phrase_string]
                    session_dates[current_date.isoformat()] = {
                        'session_date': current_date.isoformat(),
                        'date_phrase_string': best_match.phrase.phrase_string,
                        'date_match_string': best_match.string,
                        'page_id': page.id,
                        'scan_id': page.metadata['scan_id'],
                        'inventory_id': page.metadata['inventory_id'],
                        'text_region_id': main_tr.id,
                        'line_id': line.id,
                        # 'text': line.text
                    }
                    session_trs[current_date.isoformat()].append(main_tr)
                    print('current_date:', current_date, best_match.string, page.id)
                    date_strings = get_next_date_strings(current_date, num_dates=7, include_year=False)
                    # print(date_strings.keys())
                    date_searcher = FuzzyPhraseSearcher(phrase_model=date_strings, config=config)
            if current_date and main_tr in has_attendance:
                for att_tr in has_attendance[main_tr]:
                    session_trs[current_date.isoformat()].append(att_tr)
        prev_dates = [session_date for session_date in session_trs if session_date != current_date.isoformat()]
        for prev_date in prev_dates:
            yield session_dates[prev_date], session_trs[prev_date]
            del session_trs[prev_date]
    yield session_dates[current_date.isoformat()], session_trs[current_date.isoformat()]
    return None


def get_sessions(inv_id: str, pages, neural_line_classifier):
    inv_metadata = get_inventory_by_id(inv_id)
    period_start = inv_metadata['period_start']
    pages.sort(key=lambda page: page.id)
    date_mapper = DateNameMapper(text_type='handwritten', resolution_type='ordinaris',
                                 period_start=1600, period_end=1700, include_year=False)
    # period_start = "1616-01-01"
    inv_start_date = RepublicDate(date_string=period_start, date_mapper=date_mapper)
    resolution_type = pages[0].metadata['resolution_type']
    text_type = pages[0].metadata['text_type']
    for session_date, session_trs in find_session_dates(pages, inv_start_date, neural_line_classifier):
        # print('-------------')
        if 3090 < inv_metadata['inventory_num'] < 3244:
            session_num = 1
        elif 3244 <= inv_metadata['inventory_num'] < 3284:
            session_num = 2
        elif 3284 <= inv_metadata['inventory_num'] < 3350:
            session_num = 1
        elif inv_metadata['inventory_num'] > 4500:
            session_num = 3
        else:
            session_num = 4
        session_metadata = {
            'id': f"session-{session_date['session_date']}-{resolution_type}-num-{session_num}",
            'session_id': f"session-{session_date['session_date']}-{resolution_type}-num-{session_num}",
            'type': 'session',
            'inventory_id': session_trs[0].metadata['inventory_id'],
            'inventory_num': session_trs[0].metadata['inventory_num'],
            'series_name': session_trs[0].metadata['series_name'],
            'resolution_type': resolution_type,
            'text_type': text_type
        }
        for session_tr in session_trs:
            session_tr.metadata['session_id'] = session_metadata['id']
        session = {
            'id': session_metadata['id'],
            'type': ['republic_doc', 'session'],
            'metadata': session_metadata,
            'date': session_date,
            'text_regions': [tr.id for tr in session_trs],
            'scan_ids': list(sorted(set([tr.metadata['scan_id'] for tr in session_trs]))),
            'page_ids': list(sorted(set([tr.metadata['page_id'] for tr in session_trs]))),
            'stats': {
                'words': sum([tr.stats['words'] for tr in session_trs]),
                'lines': sum([tr.stats['lines'] for tr in session_trs]),
                'text_regions': len(session_trs),
                'pages': len(set([tr.metadata['page_id'] for tr in session_trs])),
                'scans': len(set([tr.metadata['scan_id'] for tr in session_trs])),
            }
        }
        yield session, session_trs
        # print(json.dumps(session_metadata, indent=4))
        for tr in session_trs:
            # print(f'\tsession has text region:', tr.id)
            # print('\t\t', tr.metadata['text_region_links'])
            pass
            # for line in tr.lines:
            #     print(f"{line.metadata['line_class']: <14}\t{line.text}")
    # period_start = "1616-03-15"
    # inv_start_date = RepublicDate(date_string=period_start, date_mapper=date_mapper)
    # session_dates[inv_num] = find_session_dates(pages[294:306], inv_start_date, word_date_cat)


"""
def add_page_line_classes(page):
    page_lines = []
    for col in page.columns:
        for tr in col.text_regions:
            print('\t', tr.type)
            for line in tr.lines:
                if 'marginalia' in tr.type:
                    line_class = 'marginalia'
                elif line.id in predicted_line_class:
                    line_class = predicted_line_class[line.id]
                else:
                    line_class = 'None'
                line.metadata['line_class'] = line_class
                if line_class in skip_types:
                    continue
                page_lines.append(line)
    return page_lines


def sort_page_textregions(page: pdm.PageXMLPage) -> List[pdm.PageXMLTextRegion]:
    trs = page.extra + page.text_regions + [tr for col in page.columns for tr in col.text_regions]
    return sorted(trs, key=lambda tr: tr.coords.y)


def get_session_info(trs: List[pdm.PageXMLTextRegion],
                     word_date_cat: Dict[str, str]) -> Dict[str, any]:
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
        elif text_region_has_session_date(tr, word_date_cat):
            session_info['has_full_date'] = True
            session_info['has_date'] = True
            session_info['full_date_tr'] = tr
    session_info['has_session_start'] = session_info['has_full_date'] or session_info['has_attendance']
    return session_info


def session_date_elements_in_order(line_date_cats):
    in_order = []
    session_date_elements = ['date_weekday', 'date_monthday', 'date_month_specific']
    for cat1, cat2 in combinations(session_date_elements, 2):
        if cat1 in line_date_cats and cat2 in line_date_cats:
            in_order.append(line_date_cats.index(cat1) == line_date_cats.index(cat2) - 1)
    return any(in_order)


def is_session_date_line(line, word_date_cat):
    if line.text is None:
        return False
    words = [w for w in re.split(r'\W+', line.text) if w != '']
    date_words = get_specific_date_words(words, word_date_cat)
    date_cats = [word_date_cat[word] for word in date_words]
    return session_date_elements_in_order(date_cats)


def text_region_has_session_date(text_region, word_date_cat):
    for line in text_region.lines:
        if is_session_date_line(line, word_date_cat):
            return True
    return False


def find_session_date(trs: List[pdm.PageXMLTextRegion],
                      session_info: Dict[str, Union[bool, None, pdm.PageXMLTextRegion]],
                      date_searcher: FuzzyPhraseSearcher) -> List[str]:
    session_dates = []
    if session_info['has_full_date']:
        date_tr = session_info['full_date_tr']
        tr_text = '\n'.join([line.text for line in date_tr.get_lines() if line.text is not None])
        date_matches = date_searcher.find_matches({'id': date_tr.id, 'text': tr_text})
        best_match = extract_best_date_match(date_matches)
        session_dates.append(best_match.phrase.phrase_string)
    elif session_info['has_attendance']:
        print('\tNO FULL DATE')
        attendance = session_info['attendance_tr']
        for tr in trs:
            for line in tr.lines:
                if line.text is None:
                    continue
                if pdm.vertical_distance(line, attendance) > 800:
                    continue
                date_matches = date_searcher.find_matches({'id': line.id, 'text': line.text})
                if len(date_matches) > 0:
                    best_match = extract_best_date_match(date_matches)
                    session_dates.append(best_match.phrase.phrase_string)
                print('CANDIDATE:', attendance.coords.top, line.coords.top, line.text)
    return session_dates


def parse_page(page: pdm.PageXMLPage, date_searcher: FuzzyPhraseSearcher):
    trs = sort_page_textregions(page)
    session_info = get_session_info(trs)
    print(page.id, session_info['has_session_start'])
    if session_info['has_session_start']:
        session_date = find_session_date(trs, session_info, date_searcher)
"""

