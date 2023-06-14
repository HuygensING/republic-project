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
from republic.model.republic_date import get_next_date_strings
from republic.model.republic_word_model import get_specific_date_words


def sort_lines_by_class(page, line_classifier: NeuralLineClassifier):
    class_lines = defaultdict(list)
    predicted_line_class = line_classifier.classify_page_lines(page)
    for col in sorted(page.columns, key=lambda c: c.coords.left):
        for tr in sorted(col.text_regions, key=lambda t: t.coords.top):
            # print(tr.type)
            for line in tr.lines:
                if 'marginalia' in tr.type:
                    class_lines['marginalia'].append(line)
                elif line.id in predicted_line_class:
                    pred_class = predicted_line_class[line.id]
                    if 'date' in tr.type and pred_class != 'date':
                        if tr.stats['words'] >= 4:
                            print('DISAGREEMENT', line.text)
                            class_lines['date'].append(line)
                            continue
                    elif 'date' not in tr.type and pred_class == 'date':
                        print('DISAGREEMENT', line.text)
                        print('NLC predicts date')
                    if pred_class.startswith('para_'):
                        class_lines['para'].append(line)
                    else:
                        class_lines[pred_class].append(line)
                else:
                    class_lines['None'].append(line)
    return class_lines


def merge_line_class_trs(class_trs, line_class: str, distance_threshold: int = 400):
    if len(class_trs) > 1:
        merged_trs = []
        prev_tr = class_trs[0]
        for att_tr in class_trs[1:]:
            # print('prev', line_class, prev_tr.coords.bottom)
            # print('current', line_class, att_tr.coords.top)
            if att_tr.coords.top - prev_tr.coords.bottom < distance_threshold:
                # print('MERGING')
                merge_lines = prev_tr.lines + att_tr.lines
                merge_coords = pdm.parse_derived_coords(merge_lines)
                merge_tr = pdm.PageXMLTextRegion(coords=merge_coords, lines=merge_lines)
                merge_tr.add_type(line_class)
                prev_tr = merge_tr
            else:
                # print('ADDING MERGED TR')
                merged_trs.append(prev_tr)
                # if att_tr == class_trs[line_class][-1]:
                #     merged_trs.append(att_tr)
                prev_tr = att_tr
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
    return has_attendance


def link_para_marginalia(class_trs):
    has_marginalia = defaultdict(list)
    if 'para' in class_trs and 'marginalia' in class_trs:
        for para_tr in class_trs['para']:
            for marg_tr in class_trs['marginalia']:
                if pdm.is_vertically_overlapping(para_tr, marg_tr, threshold=0.01):
                    has_marginalia[para_tr].append(marg_tr)
    return has_marginalia


def has_session_start_class(class_lines: Dict[str, List[pdm.PageXMLTextLine]],
                            prev_page_class_lines: Dict[str, List[pdm.PageXMLTextLine]]):
    class_trs = defaultdict(list)
    for line_class in class_lines:
        line_groups = split_lines_on_vertical_gaps(class_lines[line_class])
        for line_group in line_groups:
            group_coords = pdm.parse_derived_coords(line_group)
            group_tr = pdm.PageXMLTextRegion(coords=group_coords, lines=line_group)
            group_tr.add_type(line_class)
            class_trs[line_class].append(group_tr)
    for line_class in ['date', 'attendance']:
        class_trs[line_class] = merge_line_class_trs(class_trs[line_class], line_class)
    has_attendance = link_date_attendance(class_trs)
    has_marginalia = link_para_marginalia(class_trs)
    if 'date' in class_trs and 'para' in class_trs:
        all_trs = sorted(class_trs['date'] + class_trs['para'], key=lambda tr: tr.coords.top)
        for ti, tr in enumerate(all_trs):
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


def extract_best_date_match(matches: List[PhraseMatch]) -> Union[None, PhraseMatch]:
    if len(matches) == 0:
        return None
    best_match = sorted(matches, key=lambda m: m.levenshtein_similarity)[-1]
    return best_match


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


def find_session_dates(pages, inv_start_date, word_date_cat):
    date_strings = get_next_date_strings(inv_start_date, num_dates=7, include_year=False)
    config = {'ngram_size': 2, 'skip_size': 2}
    date_searcher = FuzzyPhraseSearcher(phrase_model=date_strings, config=config)
    session_dates = []
    for pi, page in enumerate(pages):
        try:
            if pi > 1 and is_duplicate(page, pages[pi - 2]):
                print('FOUND duplicate page', page.id)
                continue
        except ZeroDivisionError:
            print(pi, page.id, pages[pi - 2].id)
            print(page.stats, pages[pi - 2].stats)
            raise
        print(page.id)
        trs = sort_page_textregions(page)
        session_info = get_session_info(trs, word_date_cat)
        matches = []
        # print('\t', session_info)
        if session_info['has_full_date']:
            if session_info['full_date_tr'] is None:
                raise ValueError('date_tr missing')
            # date_tr = session_info['full_date_tr']
            # tr_text = '\n'.join([line.text for line in date_tr.get_lines() if line.text is not None])
            # date_matches = date_searcher.find_matches({'id': date_tr.id, 'text': tr_text})
            # session_dates.append({'session_date': current_date, 'date_string': session_date_string})
        # elif session_info['has_attendance']:
        if session_info['has_session_start']:
            print('\t HAS FULL DATE')
            #         for phrase in sorted([phrase.phrase_string for phrase in date_searcher.phrases]):
            #             print('\t\t', phrase)
            attendance_tr = session_info['attendance_tr']
            date_tr = session_info['full_date_tr']
            for tr in trs:
                print('\t', tr.id)
                for line in tr.lines:
                    if line.text is None:
                        continue
                    # print('\tCANDIDATE:', tr.coords.top, line.coords.top, line.text)
                    # if attendance_tr and pdm.vertical_distance(line, attendance_tr) > 800:
                    #     continue
                    # elif date_tr and pdm.vertical_distance(line, date_tr) > 800:
                    #     continue
                    line_matches = date_searcher.find_matches({'id': line.id, 'text': line.text})
                    filtered_matches = [match for match in line_matches if match.offset < 50]
                    filtered_matches = [match for match in filtered_matches if
                                        abs(len(match.string) - len(line.text)) < 50]
                    best_match = extract_best_date_match(filtered_matches)
                    if best_match:
                        print('\t', best_match.phrase.phrase_string)
                        current_date = date_strings[best_match.phrase.phrase_string]
                        session_dates.append({
                            'session_date': current_date,
                            'date_phrase_string': best_match.phrase.phrase_string,
                            'date_match_string': best_match.string,
                            'page': page.id,
                            'text_region': tr.id,
                            'line': line.id,
                            'text': line.text
                        })
                        print('current_date:', current_date, best_match.string, page.id)
                        date_strings = get_next_date_strings(current_date, num_dates=7, include_year=False)
                        # print(date_strings.keys())
                        date_searcher = FuzzyPhraseSearcher(phrase_model=date_strings, config=config)
    return session_dates

