import copy
from collections import defaultdict
from typing import Dict, List, Tuple, Union

import pagexml.model.physical_document_model as pdm
from pagexml.helper.pagexml_helper import make_text_region_text
from fuzzy_search.match.phrase_match import PhraseMatch
from fuzzy_search.search.phrase_searcher import FuzzyPhraseSearcher

import republic.model.republic_document_model as rdm
from republic.classification.line_classification import NeuralLineClassifier
from republic.classification.page_features import get_line_base_dist
from republic.helper.text_helper import is_duplicate
from republic.helper.metadata_helper import coords_to_iiif_url
from republic.model.inventory_mapping import get_inventory_by_id
from republic.model.republic_date import DateNameMapper
from republic.model.republic_date import RepublicDate
from republic.model.republic_date import get_next_date_strings
from republic.parser.logical.date_parser import get_date_token_cat
from republic.parser.logical.date_parser import get_session_date_line_structure
from republic.parser.logical.date_parser import get_session_date_lines_from_pages


def generate_date_string(curr_date: RepublicDate, date_mapper: DateNameMapper):
    return get_next_date_strings(curr_date, date_mapper=date_mapper, num_dates=7)


def get_predicted_line_classes(page: pdm.PageXMLPage, line_classifier: NeuralLineClassifier,
                               debug: int = 0):
    lines = page.get_lines()
    classified = [line for line in lines if 'line_class' in line.metadata]
    if len(classified) >= len(lines) - 10:
        if debug > 1:
            print('lines already classified for page', page.id)
        predicted_line_class = {}
        for line in page.get_lines():
            if 'line_class' not in line.metadata:
                if line.text and len(line.text) < 3:
                    line.metadata['line_class'] = 'noise'
                else:
                    if debug > 1:
                        print('\nMISSING LINE_CLASS:', line.text)
                        print('\t', line.parent.type)
                    continue
            predicted_line_class[line.id] = line.metadata['line_class']
    elif len(classified) < len(lines) - 10:
        try:
            predicted_line_class = line_classifier.classify_page_lines(page)
        except Exception:
            print(f'\tERROR classifying lines of page {page.id}')
            raise
        if debug > 1:
            print('NON-CLASSIFIED LINSE FOR PAGE:', page.id, '\tLINES:', len(lines),
                  '\tCLASSIFIED:', len(classified), '\tNLC:', len(predicted_line_class))
            print('\t', page.stats, '\n')
    else:
        predicted_line_class = line_classifier.classify_page_lines(page)
    return predicted_line_class


def sort_lines_by_class(page, line_classifier: NeuralLineClassifier, debug: int = 0):
    class_lines = defaultdict(list)
    predicted_line_class = get_predicted_line_classes(page, line_classifier)
    for col in sorted(page.columns, key=lambda c: c.coords.left):
        for tr in sorted(col.text_regions, key=lambda t: t.coords.top):
            if debug > 1:
                print('sort_lines_by_class - tr.type:', tr.type)
            for line in tr.lines:
                if debug > 1:
                    print(f"sort_lines_by_class - line_class line.text: "
                          f"{line.metadata['line_class']: <12}\t{line.text}")
                if 'marginalia' in tr.type:
                    class_lines['marginalia'].append(line)
                    line.metadata['line_class'] = 'marginalia'
                    line.metadata['line_classifier'] = 'loghi'
                elif line.id in predicted_line_class:
                    if debug > 1:
                        print('sort_lines_by_class - line.id in predicted_line_class', line.id)
                    pred_class = predicted_line_class[line.id]
                    if 'date' in tr.type and pred_class != 'date':
                        line.metadata['line_class'] = 'date'
                        line.metadata['line_classifier'] = 'loghi'
                        if tr.stats['words'] >= 4:
                            # print('DISAGREEMENT', line.text)
                            class_lines['date'].append(line)
                            continue
                        elif tr.coords.bottom < 500:
                            if debug > 1:
                                print('DISAGREEMENT DATE HEADER')
                                print(f'\tpage.top: {page.coords.top}\ttr.bottom: {tr.coords.bottom}')
                            class_lines['date_header'].append(line)
                            continue
                    if 'attendance' in tr.type and pred_class != 'attendance':
                        line.metadata['line_class'] = 'attendance'
                        line.metadata['line_classifier'] = 'loghi'
                        if tr.coords.left - page.coords.left < 200:
                            if debug > 1:
                                print('DISAGREEMENT ATTENDANCE')
                                print(f'\tpage.left: {page.coords.left}\ttr.left: {tr.coords.left}')
                            class_lines['attendance'].append(line)
                            continue
                    if 'resolution' in tr.type and pred_class == 'attendance':
                        line.metadata['line_class'] = 'para_mid'
                        line.metadata['line_classifier'] = 'loghi'
                        if page.coords.right - tr.coords.right < 400:
                            if debug > 1:
                                print('DISAGREEMENT ATTENDANCE')
                                print(f'\tpage.left: {page.coords.left}\ttr.left: {tr.coords.left}')
                            class_lines['para'].append(line)
                            continue
                    # elif 'date' not in tr.type and pred_class == 'date':
                        # print('DISAGREEMENT', line.text)
                        # print('NLC predicts date')
                    if pred_class.startswith('para_'):
                        if debug > 3:
                            print('PARA INDENT')
                            print(f'\tpage.left: {page.coords.left}\ttr.left: {tr.coords.left}')
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


def split_above_below_overlap_groups(para_line_group: List[pdm.PageXMLTextLine],
                                     date_line_group: List[pdm.PageXMLTextLine],
                                     debug: int = 0):
    above_group = []
    below_group = []
    overlap_group = []
    para_top = para_line_group[0].coords.top
    para_bottom = para_line_group[-1].coords.bottom
    date_top = date_line_group[0].coords.top
    date_bottom = date_line_group[-1].coords.bottom
    if debug > 0:
        print('split_para_lines_on_date_gaps - para_top:', para_top)
        print('split_para_lines_on_date_gaps - para_bottom:', para_bottom)
        print('split_para_lines_on_date_gaps - date_top:', date_top)
        print('split_para_lines_on_date_gaps - date_bottom:', date_bottom)
        for line in date_line_group:
            print(f"\tdate line: {line.coords.top: >4}-{line.coords.bottom: <4}\t{line.text}")
    for line in para_line_group:
        if line.coords.bottom < date_top:
            if debug > 1:
                print('adding to above group, line', line.text)
            above_group.append(line)
        elif line.coords.top > date_bottom:
            if debug > 1:
                print('adding to below group, line', line.text)
            below_group.append(line)
        else:
            if debug > 1:
                print('adding to overlap group, line', line.text)
            overlap_group.append(line)
    # print(len(above_group), len(overlap_group), len(below_group), len(para_line_group))
    assert sum([len(above_group), len(overlap_group), len(below_group)]) == len(para_line_group)
    return above_group, overlap_group, below_group


def split_para_lines_on_date_gaps(line_groups: Dict[str, List[List[pdm.PageXMLTextLine]]],
                                  debug: int = 0) -> List[List[pdm.PageXMLTextLine]]:
    sum_before = sum([len(group) for group in line_groups['para']])
    para_line_groups = []
    for para_line_group in line_groups['para']:
        overlapping_date_group = []
        for date_line_group in line_groups['date']:
            para_top = para_line_group[0].coords.top
            para_bottom = para_line_group[-1].coords.bottom
            date_top = date_line_group[0].coords.top
            date_bottom = date_line_group[-1].coords.bottom
            if para_top < date_top and para_bottom > date_bottom:
                overlapping_date_group.append(date_line_group)
        if len(overlapping_date_group) == 0:
            if debug > 0:
                print('split_para_lines_on_date_gaps - no overlapping date text_region:')
                for line in para_line_group:
                    print('\t', line.text)
            para_line_groups.append(para_line_group)
            continue
        while len(overlapping_date_group) > 0 and len(para_line_group) > 0:
            if debug > 0:
                print('number of overlapping date_groups:', len(overlapping_date_group))
            date_line_group = overlapping_date_group.pop(0)
            above_group, overlap_group, below_group = split_above_below_overlap_groups(para_line_group, date_line_group)
            if debug > 0:
                print(f"\tabove: {len(above_group)}\toverlap: {len(overlap_group)}\tbelow: {len(below_group)}")
            if len(above_group) > 0:
                if debug > 0:
                    for line in above_group:
                        print(f"\tabove date line: {line.coords.top: >4}-{line.coords.bottom: <4}\t{line.text}")
                para_line_groups.append(above_group)
            if len(overlap_group) > 0:
                if debug > 0:
                    for line in overlap_group:
                        print(f"\toverlap with date line: {line.coords.top: >4}-{line.coords.bottom: <4}\t{line.text}")
                para_line_groups.append(overlap_group)
            para_line_group = below_group
        if len(para_line_group) > 0:
            para_line_groups.append(para_line_group)
            if debug > 0:
                for line in para_line_group:
                    print(f"\tbelow date line: {line.coords.top: >4}-{line.coords.bottom: <4}\t{line.text}")
    sum_after = sum([len(group) for group in para_line_groups])
    assert sum_after == sum_before, f"unequal number of lines before split {sum_before} and after split {sum_after}"
    return para_line_groups


def make_classified_text_regions(class_lines: Dict[str, List[pdm.PageXMLTextLine]],
                                 page: pdm.PageXMLPage, debug: int = 0) -> Dict[str, List[pdm.PageXMLTextRegion]]:
    class_trs = defaultdict(list)
    line_groups: Dict[str, List[List[pdm.PageXMLTextLine]]] = defaultdict(list)
    for line_class in class_lines:
        line_groups[line_class] = split_lines_on_vertical_gaps(class_lines[line_class], debug=debug)
    for line_class in line_groups:
        if line_class == 'para' and 'date' in class_lines and len(class_lines['date']) > 0:
            line_groups[line_class] = split_para_lines_on_date_gaps(line_groups, debug=debug)
        for line_group in line_groups[line_class]:
            try:
                group_coords = pdm.parse_derived_coords(line_group)
            except Exception:
                print('Cannot derive coords from line_group:')
                lines_coords = [line.coords for line in line_group if line.coords]
                points = [point for coords in lines_coords for point in coords.points]
                if len(points) == 0:
                    group_coords = None
                else:
                    group_coords = pdm.Coords(points)
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
        main_trs = sorted(class_trs['date'] + class_trs['para'], key=lambda t: t.coords.top)
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


def split_lines_on_vertical_gaps(lines: List[pdm.PageXMLTextLine],
                                 debug: int = 0) -> List[List[pdm.PageXMLTextLine]]:
    lines = sorted(lines)
    line_groups = []
    if len(lines) == 0:
        return line_groups
    line_group = [lines[0]]
    if len(lines) == 1:
        return [line_group]
    if debug > 2:
        print('split_lines_on_vertical_gaps - first line_group:')
        for line in line_group:
            print(f"\t{line.coords.top: >4}-{line.coords.bottom: <4}    {line.text}")
    for curr_line in lines[1:]:
        prev_line = line_group[-1]
        base_dist = get_line_base_dist(prev_line, curr_line)
        if debug > 2:
            print('split_lines_on_vertical_gaps - curr_line:')
            print(f"\t{curr_line.coords.top: >4}-{curr_line.coords.bottom: <4}    {curr_line.text}")
            if 'height' in curr_line.metadata:
                print(f"\tbase_dist: {base_dist}\tcurr_line.height: {curr_line.metadata['height']['mean']}")
            else:
                print(f"\tbase_dist: {base_dist}\tcurr_line base - top + 50: "
                      f"{curr_line.baseline.top - curr_line.coords.top + 50}")
        split = False
        if 'height' in curr_line.metadata and 'height' in prev_line.metadata:
            if base_dist > curr_line.metadata['height']['mean'] * 2:
                split = True
        elif base_dist > (curr_line.baseline.top - curr_line.coords.top + 50):
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


def find_session_dates(pages, inv_start_date, neural_line_classifier, date_mapper: DateNameMapper,
                       ignorecase: bool = True, debug: int = 0):
    date_strings = get_next_date_strings(inv_start_date, date_mapper, num_dates=7, include_year=False)
    config = {'ngram_size': 2, 'skip_size': 2, 'ignorecase': ignorecase}
    date_searcher = FuzzyPhraseSearcher(phrase_model=date_strings, config=config)
    session_dates = {}
    session_trs = defaultdict(list)
    current_date = None
    for pi, page in enumerate(pages):
        if page.stats['words'] == 0:
            continue
        try:
            if pi > 1 and is_duplicate(page, pages[pi - 2]):
                print('FOUND duplicate page', page.id)
                continue
        except ZeroDivisionError:
            print(pi, page.id, pages[pi - 2].id)
            print(page.stats, pages[pi - 2].stats)
            raise
        if debug > 0:
            print('\n\n---------------------------------------')
            print('find_session_dates - page:', page.id)
        if 'inventory_id' not in page.metadata:
            page.metadata['inventory_id'] = f"{page.metadata['series_name']}_{page.metadata['inventory_num']}"
        class_lines = sort_lines_by_class(page, neural_line_classifier, debug=debug)
        class_trs = make_classified_text_regions(class_lines, page, debug=debug)
        has_attendance = link_date_attendance(class_trs)
        has_marginalia = link_para_marginalia(class_trs)
        unlinked_att_trs, unlinked_marg_trs = link_classified_text_regions(class_trs)
        if len(unlinked_att_trs) > 0:
            print('find_session_dates - unlinked_att_trs:', len(unlinked_att_trs), page.id)
        if len(unlinked_marg_trs) > 0:
            print('find_session_dates - unlinked_marg_trs:', len(unlinked_marg_trs), page.id)
        main_trs = sorted(class_trs['date'] + class_trs['para'], key=lambda tr: tr.coords.top)

        for main_tr in main_trs:
            if debug > 0:
                print('\nfind_session_dates - main_tr:', main_tr.coords.box)
                if current_date:
                    print('find_session_dates - current_date:', current_date.isoformat())
                else:
                    print('find_session_dates - no current_date')
            if current_date and main_tr.metadata['text_region_class'] == 'para':
                if debug > 0:
                    print('find_session_dates - adding para to session with date', current_date.isoformat())
                session_trs[current_date.isoformat()].append(main_tr)
                for line in main_tr.lines:
                    if debug > 0:
                        print(f"\tPARA_LINE: {line.coords.top: >4}-{line.coords.bottom: <4} "
                              f"{line.metadata['line_class']: <12}    {line.text}")
                if main_tr in has_marginalia:
                    for marg_tr in has_marginalia[main_tr]:
                        session_trs[current_date.isoformat()].append(marg_tr)
                continue
            for line in main_tr.lines:
                if line.text is None:
                    continue
                if debug > 0:
                    print(f"\t{line.metadata['line_class']: <12}    {line.text}")
                line_matches = date_searcher.find_matches({'id': line.id, 'text': line.text})
                filtered_matches = [match for match in line_matches if match.offset < 50]
                filtered_matches = [match for match in filtered_matches if
                                    abs(len(match.string) - len(line.text)) < 50]
                best_match = extract_best_date_match(filtered_matches)
                if best_match:
                    # print('\t', best_match.phrase.phrase_string)
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
                    if debug > 0:
                        print('find_session_dates - found date:', current_date, best_match.string, page.id)
                    date_strings = get_next_date_strings(current_date, date_mapper, num_dates=7, include_year=False)
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


def get_sessions(inv_id: str, pages, neural_line_classifier, ignorecase: bool = True,
                 debug: int = 0):
    print('get_sessions - num pages:', len(pages))
    inv_metadata = get_inventory_by_id(inv_id)
    period_start = inv_metadata['period_start']
    pages.sort(key=lambda page: page.id)
    date_token_cat = get_date_token_cat(inv_num=inv_metadata['inventory_num'], ignorecase=ignorecase)
    session_date_lines = get_session_date_lines_from_pages(pages)
    if len(session_date_lines) == 0:
        print(f"WARNING - No session date lines found for "
              f"inventory {inv_metadata['inventory_num']} with {len(pages)} pages")
        return None
    date_line_structure = get_session_date_line_structure(session_date_lines, date_token_cat, inv_id)
    if 'week_day_name' not in [element[0] for element in date_line_structure]:
        print('WARNING - missing week_day_name in date_line_structure for inventory', inv_metadata['inventory_num'])
        return None

    date_mapper = DateNameMapper(inv_metadata, date_line_structure)

    # year_start_date = RepublicDate(date_string=inv_metadata['period_start'], date_mapper=date_mapper)
    # date_strings = get_next_date_strings(year_start_date, date_mapper, num_dates=7)

    # period_start = "1616-01-01"
    inv_start_date = RepublicDate(date_string=period_start, date_mapper=date_mapper)
    resolution_type = pages[0].metadata['resolution_type']
    text_type = pages[0].metadata['text_type']
    session_num = 0
    for session_date, session_trs in find_session_dates(pages, inv_start_date,
                                                        neural_line_classifier, date_mapper,
                                                        ignorecase=ignorecase, debug=debug):
        # print('-------------')
        session_num += 1
        '''
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
        '''
        session_metadata = {
            'id': f'session-{inv_metadata["inventory_num"]}-num-{session_num}',
            'session_id': f'session-{inv_metadata["inventory_num"]}-num-{session_num}',
            'session_num': session_num,
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
            'id': f'session-{inv_metadata["inventory_num"]}-num-{session_num}',
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
    return None


def make_paragraph_text(lines: List[pdm.PageXMLTextLine]) -> Tuple[str, List[Dict[str, any]]]:
    text, line_ranges = make_text_region_text(lines, word_break_chars='-„')
    return text, line_ranges


def make_session_paragraphs(session_metadata, session_trs, debug: int = 0):
    paras = get_session_paragraph_line_groups(session_trs, debug=debug)
    # print('make_session_paragraphs - len(paras):', len(paras))
    doc_text_offset = 0
    for pi, para in enumerate(paras):
        para_type, para_lines = para
        paragraph_id = f"{session_metadata['id']}-para-{pi+1}"
        metadata = copy.deepcopy(session_metadata)
        metadata['id'] = paragraph_id
        metadata['type'] = "paragraph"
        text_region_ids = []
        for line in para_lines:
            if line.metadata["parent_id"] not in text_region_ids:
                text_region_ids.append(line.metadata["parent_id"])
                if line.metadata['page_id'] not in metadata['page_ids']:
                    metadata['page_ids'].append(line.metadata['page_id'])
        text, line_ranges = make_paragraph_text(para_lines)
        paragraph = rdm.RepublicParagraph(lines=para_lines, metadata=metadata,
                                          text=text, line_ranges=line_ranges)
        paragraph.metadata["start_offset"] = doc_text_offset
        paragraph.metadata["para_type"] = para_type
        paragraph.add_type(para_type)
        doc_text_offset += len(paragraph.text)
        yield paragraph
    return None


def check_lines_have_boundary_signals(lines: List[pdm.PageXMLTextLine], curr_index: int,
                                      prev_line: pdm.PageXMLTextLine, debug: int = 0) -> bool:
    if debug > 0:
        print('check_lines_have_boundary_signals - curr_index:', curr_index)
    if curr_index == -1:
        curr_line = prev_line
    else:
        curr_line = lines[curr_index]
    if curr_line is None:
        return True
    if debug > 0:
        print('check_lines_have_boundary_signals - curr_line:', curr_line.metadata['line_class'], curr_line.text)
    if curr_line.metadata['line_class'].startswith('para') is False:
        if debug > 0:
            print('\tno para line:', True)
        return True
    if curr_line.text is None:
        if debug > 0:
            print('\tno text:', True)
        return True
    if len(lines) == curr_index+1:
        if debug > 0:
            print('\tno next line:', True)
        return True
    if curr_line.text and curr_line.text[-1] == '.':
        if debug > 0:
            print('\tends with period:', True)
        return True
    next_line = lines[curr_index+1]
    if debug > 0:
        print('check_lines_have_boundary_signals - next_line:', next_line.metadata['line_class'], next_line.text)
    if next_line.text is None:
        if debug > 0:
            print('\tno text:', True)
        return True
    if curr_line.text[-1] in '-„':
        if debug > 0:
            print('\tcurr line has word break:', False)
        return False
    if next_line.text[0].isalpha() and next_line.text[0].islower():
        if debug > 0:
            print('\tnext line starts with lower alpha:', False)
        return False
    if debug > 0:
        print('\telse:', True)
    return True


def get_next_line(session_trs: List[pdm.PageXMLTextRegion], si: int, li: int) -> Union[pdm.PageXMLTextLine, None]:
    curr_tr = session_trs[si]
    if len(curr_tr.lines) > li+1:
        return curr_tr.lines[li+1]
    elif len(session_trs) > si+1:
        next_tr = session_trs[si+1]
        next_text_lines = [line for line in next_tr.lines if line.text]
        return next_text_lines[0]
    else:
        return None


def get_session_paragraph_line_groups(session_trs: List[pdm.PageXMLTextRegion],
                                      debug: int = 0):
    paras = []
    para = []
    prev_line = None
    para_trs = [tr for tr in session_trs if tr.has_type('para')]
    other_trs = [tr for tr in session_trs if tr.has_type('para') is False]
    para_lines = [line for tr in para_trs for line in tr.lines]
    for si, session_tr in enumerate(other_trs):
        paras.append((session_tr.metadata['text_region_class'], session_tr.lines))
    for li, line in enumerate(para_lines):
        if line.metadata['line_class'] == 'para_start':
            if check_lines_have_boundary_signals(para_lines, li-1, prev_line, debug=debug):
                if len(para) > 0:
                    if debug > 0:
                        print('reached para_start, adding previous as number', len(paras)+1)
                    paras.append(('para', para))
                para = []
        if debug > 0:
            print(f"{line.coords.top: >4}-{line.coords.bottom: <4}\t{line.metadata['line_class']: <20}\t{line.text}")
        para.append(line)
        if debug > 0:
            print(f"current paragraph has {len(para)} lines")
        if line.metadata['line_class'] == 'para_end':
            if check_lines_have_boundary_signals(para_lines, li, prev_line, debug=debug):
                if len(para) > 0:
                    if debug > 0:
                        print('reached para_end, adding current as number', len(paras)+1)
                    paras.append(('para', para))
                para = []
        prev_line = line
    if len(para) > 0:
        paras.append(('para', para))
    return paras
