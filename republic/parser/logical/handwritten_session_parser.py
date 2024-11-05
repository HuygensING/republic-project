import copy
import datetime
import re
from collections import defaultdict
from typing import Dict, List, Tuple, Union

import pagexml.model.physical_document_model as pdm
from fuzzy_search import PhraseMatch
from fuzzy_search.search.phrase_searcher import FuzzyPhraseSearcher
from fuzzy_search.search.token_searcher import FuzzyTokenSearcher

import republic.helper.pagexml_helper as pagexml_helper
import republic.model.republic_document_model as rdm
from republic.classification.page_features import get_line_base_dist
from republic.helper.text_helper import is_duplicate
from republic.helper.metadata_helper import coords_to_iiif_url
from republic.helper.metadata_helper import doc_id_to_iiif_url
from republic.helper.pagexml_helper import print_line_class_dist
from republic.helper.pagexml_helper import get_content_type
from republic.model.inventory_mapping import get_inventory_by_id
from republic.model.republic_date import DateNameMapper
from republic.model.republic_date import RepublicDate
from republic.model.republic_date import get_next_date_strings
from republic.parser.pagexml.page_date_parser import process_handwritten_page, process_handwritten_pages
from republic.parser.pagexml.page_date_parser import get_inventory_date_mapper
from republic.parser.pagexml.page_date_parser import classify_page_date_regions
from republic.parser.pagexml.page_date_parser import load_date_region_classifier
from republic.parser.pagexml.page_date_parser import find_date_region_record_lines
from republic.parser.logical.generic_session_parser import make_session_date_metadata
from republic.parser.logical.generic_session_parser import make_session
from republic.parser.logical.generic_session_parser import make_session_metadata
from republic.parser.logical.date_parser import get_date_token_cat
# from republic.parser.logical.date_parser import get_session_date_line_structure
from republic.parser.logical.date_parser import get_session_date_line_structures
from republic.parser.logical.date_parser import get_session_date_lines_from_pages
from republic.parser.logical.date_parser import make_weekday_name_searcher
from republic.parser.logical.date_parser import extract_best_date_match


DATE_JUMPS = {
    ("4560", "1602-11-10"): [-250],
    ("4562", "1617-08-09"): [365],
    ("4562", "1632-12-22"): [-250],
    ("4562", "1632-05-04"): [0, 365],
    ("4566", "1632-05-04"): [0, 365],
    ("4610", "1701-02-16"): [-10],
}


def calculate_date_jump(inventory_num: Union[int, str], current_date: RepublicDate,
                        date_jumps: Dict[Tuple[str, str], any]) -> int:
    if (str(inventory_num), current_date.isoformat()) in date_jumps:
        return date_jumps[(str(inventory_num), current_date.isoformat())].pop(0)
    else:
        return 0


def generate_date_string(curr_date: RepublicDate, date_mapper: DateNameMapper):
    return get_next_date_strings(curr_date, date_mapper=date_mapper, num_dates=7)


def get_predicted_line_classes(page: pdm.PageXMLPage, debug: int = 0):
    predicted_line_class = {}
    for line in page.get_lines():
        if 'line_class' not in line.metadata:
            if line.text and len(line.text) < 3:
                line.metadata['line_class'] = 'noise'
            else:
                line.metadata['line_class'] = 'unknown'
                if debug > 1:
                    print('\nMISSING LINE_CLASS:', line.text)
                    print('\t', line.parent.type)
        else:
            predicted_line_class[line.id] = line.metadata['line_class']
    return predicted_line_class


def line_introduces_insertion(line: pdm.PageXMLTextLine) -> bool:
    if re.match(r"Extract [Uu](y|ij|i)t het Register", line.text):
        return True
    if re.search(r"geinsereer[dt]", line.text):
        return True
    else:
        return False


def sort_lines_by_class(page, debug: int = 0, near_extract_intro: bool = False,
                        date_start_lines: List[pdm.PageXMLTextLine] = None):
    class_lines = defaultdict(list)
    predicted_line_class = get_predicted_line_classes(page)
    if date_start_lines is None:
        date_start_lines = []
    # check that date_start_lines are in page
    page_lines = page.get_lines()
    for line in date_start_lines:
        if line not in page_lines:
            print(f"handwritten_session_parser.sort_lines_by_class - missing date_start_line")
            print(f"    page {page.id} has no line {line.id}")
            raise ValueError(f"date_start_line {line.id} not in page {page.id}")
    for col in sorted(page.columns, key=lambda c: c.coords.left):
        for tr in sorted(col.text_regions, key=lambda t: t.coords.top):
            if debug > 1:
                print('sort_lines_by_class - tr.type:', tr.type)
            for line in tr.lines:
                if line in date_start_lines:
                    line.metadata['line_class'] = 'date'
                    line.metadata['line_classifier'] = 'manual'
                    class_lines['date'].append(line)
                    continue
                if debug > 1:
                    print(f"sort_lines_by_class - line_class line.text: "
                          f"{line.metadata['line_class']: <12}\t{line.text}")
                if line.text is None:
                    continue
                if line_introduces_insertion(line):
                    near_extract_intro = True
                    line.metadata['line_class'] = f"{line.metadata['line_class']}_extract_intro"
                    line.metadata['line_classifier'] = 'handwritten_session_parser'
                    if debug > 0:
                        print(f"handwritten_session_parser.sort_lines_by_class - "
                              f"line introduces insertion: {line.text}")
                        print(f"\tline_class: {line.metadata['line_class']}")
                if 'marginalia' in tr.type:
                    class_lines['marginalia'].append(line)
                    line.metadata['line_class'] = 'marginalia'
                    line.metadata['line_classifier'] = 'loghi'
                elif line.id in predicted_line_class:
                    if debug > 1:
                        print('sort_lines_by_class - line.id in predicted_line_class', line.id)
                    pred_class = predicted_line_class[line.id]
                    if 'date' in tr.type and pred_class != 'date':
                        if near_extract_intro is True:
                            line.metadata['line_class'] = 'extract_date'
                            line.metadata['line_classifier'] = 'handwritten_session_parser'
                        else:
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
                    if debug > 1:
                        print(f"line {line.id} not in predicted_line_class, setting class to 'unknown'")
                    line.metadata['line_class'] = 'unknown'
                    line.metadata['line_classifier'] = 'nlc_classifier'
                    class_lines['unknown'].append(line)
                if near_extract_intro and line.metadata['line_class'] == 'date':
                    line.metadata['line_class'] = 'extract_date'
    return class_lines, near_extract_intro


def merge_line_class_trs(class_trs, line_class: str, page: pdm.PageXMLPage, distance_threshold: int = 400,
                         debug: int = 0):
    """Check if pairs of text regions of the same class should be merged.
    This is only for attendance lists and session date references."""
    pagexml_helper.check_parentage(page)
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
                merge_tr.parent = prev_tr.parent
                merge_tr.set_as_parent(merge_lines)
                merge_tr.metadata['text_region_class'] = curr_tr.metadata['text_region_class']
                merge_tr.metadata['text_region_links'] = []
                prev_tr.lines = []
                curr_tr.lines = []
                if debug > 2:
                    print(f'created merge_tr: {merge_tr.id} from prev_tr {prev_tr.id} and curr_tr {curr_tr}')
                    for col in page.columns:
                        print(f'  tr.id: {col.id}\tpage.id: {page.id}')
                        for tr in col.text_regions:
                            print(f'    tr.id: {tr.id}\tcol.id: {col.id}')
                            for line in tr.lines:
                                print(f'\tline.id: {line.id}\ttr.id: {tr.id}')
                prev_tr = merge_tr
            else:
                # print('ADDING MERGED TR')
                merged_trs.append(prev_tr)
                # if curr_tr == class_trs[line_class][-1]:
                #     merged_trs.append(curr_tr)
                prev_tr = curr_tr
        # print('ADDING FINAL TR')
        merged_trs.append(prev_tr)
        pagexml_helper.check_parentage(page)
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


def link_para_marginalia(class_trs, debug: int = 0):
    has_marginalia = defaultdict(list)
    if 'para' not in class_trs or 'marginalia' not in class_trs:
        return has_marginalia
    for para_tr in class_trs['para']:
        # print('ITERATING OVER PARA:', para_tr.id)
        for marg_tr in class_trs['marginalia']:
            # print('ITERATING OVER MARG:', marg_tr.id)
            if pdm.is_vertically_overlapping(para_tr, marg_tr, threshold=0.5):
                if debug > 1:
                    print(f'handwritten_session_parser.link_para_marginalia - marginalia link '
                          f'from para {para_tr.id} to marg {marg_tr.id}')
                has_marginalia[para_tr].append(marg_tr)
    for para_tr in has_marginalia:
        if 'text_region_links' not in para_tr.metadata:
            para_tr.metadata['text_region_links'] = []
        for marg_tr in has_marginalia[para_tr]:
            if 'text_region_links' not in marg_tr.metadata:
                marg_tr.metadata['text_region_links'] = []
            linked_ids = [link['text_region_id'] for link in para_tr.metadata['text_region_links']]
            # print('LINKED_IDS:', linked_ids)
            if marg_tr.id in linked_ids:
                # raise ValueError(f'DOUBLE MARGINALIA LINK: para_tr: {para_tr.id}\tmarg_tr: {marg_tr.id}')
                continue
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
    if debug > 1:
        print('handwritten_session_parser.split_above_below_overlap_groups - para_top:', para_top)
        print('handwritten_session_parser.split_above_below_overlap_groups - para_bottom:', para_bottom)
        print('handwritten_session_parser.split_above_below_overlap_groups - date_top:', date_top)
        print('handwritten_session_parser.split_above_below_overlap_groups - date_bottom:', date_bottom)
        for line in date_line_group:
            print(f"\tdate line: {line.coords.top: >4}-{line.coords.bottom: <4}\t{line.text}")
    for line in para_line_group:
        if line.coords.bottom < date_top:
            if debug > 1:
                print('    adding to above group, line', line.text)
            above_group.append(line)
        elif line.coords.top > date_bottom:
            if debug > 1:
                print('    adding to below group, line', line.text)
            below_group.append(line)
        else:
            if debug > 1:
                print('    adding to overlap group, line', line.text)
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
            if debug > 1:
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
    pagexml_helper.check_page_parentage(page)
    class_trs = defaultdict(list)
    line_groups: Dict[str, List[List[pdm.PageXMLTextLine]]] = defaultdict(list)
    for line_class in class_lines:
        line_groups[line_class] = split_lines_on_vertical_gaps(class_lines[line_class], debug=debug)
    pagexml_helper.check_page_parentage(page)
    for line_class in line_groups:
        if debug > 2:
            print('line_class:', line_class)
        if line_class == 'para' and 'date' in class_lines and len(class_lines['date']) > 0:
            line_groups[line_class] = split_para_lines_on_date_gaps(line_groups, debug=debug)
        for line_group in line_groups[line_class]:
            try:
                group_coords = pdm.parse_derived_coords(line_group)
            except BaseException:
                print('Cannot derive coords from line_group:')
                lines_coords = [line.coords for line in line_group if line.coords]
                points = [point for coords in lines_coords for point in coords.points]
                if len(points) == 0:
                    group_coords = None
                else:
                    group_coords = pdm.Coords(points)
            col = line_group[0].parent.parent
            for line in line_group:
                if line.parent is None:
                    print('MISSING PARENT FOR LINE:', line.id)
                parent_tr = line.parent
                if isinstance(parent_tr, pdm.PageXMLTextRegion):
                    parent_tr.lines.remove(line)
            group_metadata = make_text_region_metadata(line_class, group_coords, page)
            group_tr = pdm.PageXMLTextRegion(coords=group_coords, lines=line_group, metadata=group_metadata)
            group_tr.add_type(line_class)
            group_tr.set_derived_id(line_group[0].metadata['scan_id'])
            group_tr.set_as_parent(line_group)
            if isinstance(col, pdm.PageXMLColumn):
                group_tr.parent = col
            else:
                raise ValueError(f'parent {col.id} of text region is not of type PageXMLColumn')
            class_trs[line_class].append(group_tr)
        pagexml_helper.check_page_parentage(page)
    for line_class in ['date', 'attendance']:
        class_trs[line_class] = merge_line_class_trs(class_trs[line_class], line_class, page)
    return class_trs


def link_classified_text_regions(class_trs, debug: int = 0):
    has_attendance = link_date_attendance(class_trs)
    has_marginalia = link_para_marginalia(class_trs, debug=debug)
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


def update_date_strings(page: pdm.PageXMLPage, current_date: RepublicDate, date_mapper: DateNameMapper,
                        num_past_dates: int, num_future_dates: int, date_jumps,
                        date_metadata: Dict[str, any],
                        debug: int = 0):
    """Update the date strings that are expected for the next session by shifting the current date,
    based on a fuzzy date match or a manual start date record. """
    if debug > 2:
        print(f'\tADDING main_tr to {current_date.date.isoformat()}')
    if debug > 0:
        evidence = date_metadata['evidence']
        if evidence['type'] == 'PhraseMatch':
            date_string = date_metadata['date_match_string']
        else:
            date_string = evidence['date']
        print(f"handwritten_session_parser.update_date_strings - found date via {evidence['type']}:",
              current_date, date_string, page.id)
    jump_days = calculate_date_jump(page.metadata['inventory_num'], current_date, date_jumps)
    delta = datetime.timedelta(days=-num_past_dates + jump_days)
    start_day = current_date.date + delta
    start_day = RepublicDate(start_day.year, start_day.month, start_day.day, date_mapper=date_mapper)
    if debug > 0:
        print(f"    jump: {jump_days}\tdelta: {delta}\tstart_day: {start_day}")
    if debug > 1:
        print(f'    current_date: {current_date.date.isoformat()}\tstart_day: {start_day.date.isoformat()}')
    date_strings = get_next_date_strings(start_day, date_mapper,
                                         num_dates=num_past_dates + num_future_dates + 1,
                                         include_year=False)
    return date_strings, jump_days


def check_extract(class_lines: Dict[str, List[pdm.PageXMLTextLine]], near_extract_intro: bool,
                  num_lines_since_extract_intro: int):
    # check if a previous page started an inserted extract
    # with a distractor date
    if 'para' in class_lines:
        for li, line in enumerate(class_lines['para']):
            if line.metadata['line_class'].endswith('_extract_intro'):
                line.metadata['line_class'] = line.metadata['line_class'].replace('_extract_intro', '')
                num_lines_since_extract_intro = 0
            if near_extract_intro:
                num_lines_since_extract_intro += 1
            if num_lines_since_extract_intro > 10:
                near_extract_intro = False
                num_lines_since_extract_intro = 0
    return near_extract_intro, num_lines_since_extract_intro


def get_date_searcher(pages: List[pdm.PageXMLPage], inv_start_date: RepublicDate,
                      date_strings: Dict[str, RepublicDate], config: Dict[str, any],
                      debug: int = 0):
    if 3096 <= pages[0].metadata['inventory_num'] <= 3350:
        date_searcher = FuzzyPhraseSearcher(phrase_model=date_strings, config=config)
    else:
        date_searcher = FuzzyPhraseSearcher(phrase_model=date_strings, config=config)
    if debug > 1:
        print('handwritten_session_parser.get_date_searcher - initial date_strings:', date_strings.keys())
    if debug > 1:
        print(f"handwritten_session_parser.get_date_searcher - date_searcher.phrase_model.token_in_phrase:",
              date_searcher.phrase_model.token_in_phrase)
    if debug > 0:
        print(f"{pages[0].metadata['inventory_num']}\tstart_date: {inv_start_date}\tnumber of pages: {len(pages)}")
    return date_searcher


def map_date_starts(page: pdm.PageXMLPage, session_starts: List[Dict[str, any]], debug: int = 0):
    date_start_lines = []
    date_start_map = {}
    if session_starts is not None:
        page_records = [record for record in session_starts if page.metadata['page_num'] == record['page_num']]
        print(f"{page.id}\t{len(page_records)}")
        for record in page_records:
            record_lines = find_date_region_record_lines(page, record, debug=debug)
            date_start_lines.extend(record_lines)
            for line in record_lines:
                date_start_map[line] = record
    return date_start_map, date_start_lines


def prepare_text_regions(class_lines: Dict[str, List[pdm.PageXMLTextLine]], page: pdm.PageXMLPage,
                         debug: int = 0):
    pagexml_helper.check_page_parentage(page)
    class_trs = make_classified_text_regions(class_lines, page, debug=debug)
    pagexml_helper.check_page_parentage(page)
    has_attendance = link_date_attendance(class_trs)
    pagexml_helper.check_page_parentage(page)
    has_marginalia = link_para_marginalia(class_trs, debug=debug)
    pagexml_helper.check_page_parentage(page)
    unlinked_att_trs, unlinked_marg_trs = link_classified_text_regions(class_trs, debug=debug)
    pagexml_helper.check_page_parentage(page)
    if debug > 0:
        if len(unlinked_att_trs) > 0:
            print('handwritten_session_parser.get_date_searcher - unlinked_att_trs:', len(unlinked_att_trs), page.id)
        if len(unlinked_marg_trs) > 0:
            print('handwritten_session_parser.get_date_searcher - unlinked_marg_trs:', len(unlinked_marg_trs), page.id)
    main_trs = sorted(class_trs['date'] + class_trs['para'], key=lambda tr: tr.coords.top)
    return main_trs, has_marginalia, has_attendance


def fuzzy_search_date(line: pdm.PageXMLTextLine, main_tr: pdm.PageXMLTextRegion,
                      date_searcher: FuzzyPhraseSearcher,
                      date_name_mapper: DateNameMapper,
                      current_date: RepublicDate, inv_start_date: RepublicDate, jump_days: int,
                      date_strings: Dict[str, RepublicDate], debug: int = 0):
    line_matches = date_searcher.find_matches({'id': line.id, 'text': line.text}, debug=0)
    if debug > 0 and main_tr.has_type('date'):
        print(f"handwritten_session_parser.fuzzy_search_date - date line: {line.text}")
        print(f"    number of date matches: {len(line_matches)}")
        for match in line_matches:
            print(f"\tmatch: {match}")
    filtered_matches = [match for match in line_matches if match.offset < 50]
    filtered_matches = [match for match in filtered_matches if
                        abs(len(match.string) - len(line.text)) < 50]
    best_match = extract_best_date_match(date_name_mapper, filtered_matches, current_date if current_date else inv_start_date,
                                         jump_days, date_strings)
    return best_match


def check_date_update(page: pdm.PageXMLPage, line: pdm.PageXMLTextLine, main_tr: pdm.PageXMLTextRegion,
                      date_searcher: FuzzyPhraseSearcher, date_start_map: Dict[pdm.PageXMLTextLine, dict],
                      date_mapper: DateNameMapper,
                      current_date: RepublicDate, inv_start_date: RepublicDate, jump_days: int,
                      date_strings: Dict[str, RepublicDate],
                      suspicious_jump: int = None, debug: int = 0):
    """Check if the current line is the start of a session, and if so, update the date
    and generate date metadata with the line as evidence."""
    update_date = None
    date_metadata = None
    if line.text is None:
        return update_date, date_metadata
    if current_date is None:
        current_date = inv_start_date
    if debug > 2:
        print(f"handwritten_session_parser.check_date_update - line {line.id}")
        print(f"\t{line.metadata['line_class']: <12}    {line.text}")
    if line in date_start_map:
        # if the line appears in the date_start_map, it means we know that it is
        # either a date start line, or a distractor (a date header or something
        # that looks like a start date but is not).
        # If it is a start date, update the date, else, ignore the line and don't
        # do a fuzzy match.
        record = date_start_map[line]
        print(f"line in date_start_map: {line.id}\t{line.text}\t{record['date_type']}")
        if record['date_type'] == 'start':
            update_date = RepublicDate(record['year'], record['month_num'], record['day_num'],
                                       date_mapper=date_mapper)
            date_metadata = make_session_date_metadata(current_date, line, start_record=record)
        else:
            # IMPORTANT!
            # if date_type is not date, the line is not a start date and should be ignored
            pass
        best_match = None
    else:
        best_match = fuzzy_search_date(line, main_tr, date_searcher, date_mapper,
                                       current_date, inv_start_date,
                                       jump_days, date_strings, debug=debug)
    if best_match:
        current_date_string = current_date.date.isoformat() if current_date else None
        update_date = date_strings[best_match.phrase.phrase_string]
        if debug > 1:
            print('\tbest_match', best_match.phrase.phrase_string, '\t', best_match.string, '\t',
                  best_match.levenshtein_similarity)
        # print('\n--------------------------------\n')
        if debug > 0:
            print('\tbest_match', best_match.phrase.phrase_string, '\t', best_match.string, '\t',
                  best_match.levenshtein_similarity)
        print(f'\tdate: {update_date.isoformat()}  {best_match.phrase.phrase_string}\t{best_match.string}\tline: {line.id}\tpage: {page.id}')
        # print('\n--------------------------------\n')
        if debug > 2:
            print(f'UPDATING CURRENT DATE from {current_date_string} to '
                  f'{date_strings[best_match.phrase.phrase_string].date.isoformat()}')
        date_metadata = make_session_date_metadata(current_date, line, fuzzy_date_match=best_match)
    return update_date, date_metadata


def add_date_start_with_no_evidence(current_date: RepublicDate, main_tr: pdm.PageXMLTextRegion,
                                    session_trs: Dict[str, List[pdm.PageXMLTextRegion]],
                                    session_dates: Dict[str, List[Dict[str, any]]]):
    # no date text region was found that precedes the resolution text regions
    # so add date_metadata without session date evidence, using the first
    # line of the first main_tr for the page, scan and inventory metadata
    if current_date.isoformat() in session_trs and len(session_trs[current_date.isoformat()]) > 0:
        first_line = session_trs[current_date.isoformat()][0].lines[0]
    else:
        first_line = main_tr.lines[0]
    no_evidence_metadata = make_session_date_metadata(current_date, first_line)
    return no_evidence_metadata


def find_session_dates(pages, inv_start_date, date_mapper: DateNameMapper,
                       ignorecase: bool = True, near_extract_intro: bool = False,
                       num_past_dates: int = 5, num_future_dates: int = 31,
                       session_starts: List[Dict[str, any]] = None, debug: int = 0):
    date_strings = get_next_date_strings(inv_start_date, date_mapper, num_dates=num_future_dates, include_year=False)
    # for dt in date_strings:
    #     print(dt, date_strings[dt])
    date_jumps = copy.deepcopy(DATE_JUMPS)
    config = {'ngram_size': 2, 'skip_size': 1, 'ignorecase': ignorecase, 'levenshtein_threshold': 0.8}
    date_searcher = get_date_searcher(pages, inv_start_date, date_strings, config=config, debug=debug)

    session_dates = defaultdict(list)
    session_trs = defaultdict(list)
    # current_date = None
    # Assumption 2024-10-22: current_date always starts on start date
    # according to the inventory metadata. Any paragraph text regions
    # before the first found date that is not the same as the start
    # date, belong to the start date.
    current_date = inv_start_date
    jump_days = 0
    num_lines_since_extract_intro = 0
    for pi, page in enumerate(pages):
        page = copy.deepcopy(page)
        tr_assigned_to_date = {}
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
        # page = split_page_column_text_regions(page, debug=0)
        if debug > 0:
            print('\n\n---------------------------------------')
            print('find_session_dates - page:', page.id)
        pagexml_helper.check_page_parentage(page)
        # print('find_session_dates - page:', page.id)
        if 'inventory_id' not in page.metadata:
            page.metadata['inventory_id'] = f"{page.metadata['series_name']}_{page.metadata['inventory_num']}"

        date_start_map, date_start_lines = map_date_starts(page, session_starts=session_starts, debug=debug)
        class_lines, near_extract_intro = sort_lines_by_class(page, near_extract_intro=near_extract_intro,
                                                              date_start_lines=date_start_lines,
                                                              debug=debug)
        if debug > 0:
            print(f'  page: {page.id}\tnear_extract_intro: {near_extract_intro}\n')
            print("  class_lines:", [(lc, len(class_lines[lc])) for lc in class_lines])
        near_extract_intro, num_lines_since_extract_intro = check_extract(class_lines,
                                                                          near_extract_intro,
                                                                          num_lines_since_extract_intro)
        pagexml_helper.check_page_parentage(page)
        if debug > 0:
            print(f'\tAFTER - near_extract_intro: {near_extract_intro}')
            print(f'\tAFTER - num_lines_since_extract_intro: {num_lines_since_extract_intro}\n')
        main_trs, has_marginalia, has_attendance = prepare_text_regions(class_lines, page, debug=debug)

        pagexml_helper.check_page_parentage(page)
        for main_tr in main_trs:
            if debug > 0:
                print('\nfind_session_dates - main_tr:', main_tr.coords.box, get_content_type(main_tr))
                if current_date:
                    print('find_session_dates - current_date:', current_date.isoformat())
                else:
                    print('find_session_dates - no current_date')
            if main_tr.metadata['text_region_class'] == 'para':
                session_trs[current_date.isoformat()].append(main_tr)
                num_trs = len(session_trs[current_date.isoformat()])
                if debug > -1:
                    print(f'find_session_dates - adding tr {num_trs} to session with date {current_date.isoformat()}')
                if debug > 1:
                    for line in main_tr.lines:
                        print(f"\tPARA_LINE: {line.coords.top: >4}-{line.coords.bottom: <4} "
                              f"{line.metadata['line_class']: <12}    {line.text}")
                if main_tr in has_marginalia:
                    for marg_tr in has_marginalia[main_tr]:
                        session_trs[current_date.isoformat()].append(marg_tr)
                if current_date.isoformat() not in session_dates or len(session_dates[current_date.isoformat()]) == 0:
                    no_evidence_metadata = add_date_start_with_no_evidence(current_date, main_tr,
                                                                           session_trs, session_dates)
                    if debug > 0:
                        print('find_session_dates - adding no_evidence_metadata for date', current_date.isoformat())
                    session_dates[current_date.isoformat()].append(no_evidence_metadata)
                continue
            if debug > 2:
                print(f"  iterating over lines of main_tr {main_tr.id}")
            for line in main_tr.lines:
                update_date, date_metadata = check_date_update(page, line, main_tr, date_searcher,
                                                               date_start_map, date_mapper,
                                                               current_date, inv_start_date,
                                                               jump_days, date_strings, debug=debug)
                if update_date is not None:
                    if update_date.isoformat() != current_date.isoformat():
                        # if update_date is different, we need metadata for the new date
                        # if update_date is the same as current_date, it is an extra session
                        # on the same day, so don't update the date_metadata
                        print(f"update_date - current_date: {update_date - current_date}")
                        delta = update_date - current_date
                        current_date = update_date
                        if delta.days > 2:
                            suspicious_jump = delta.days
                            date_strings, jump_days = update_date_strings(page, current_date, date_mapper,
                                                                          num_past_dates + delta.days,
                                                                          num_future_dates, date_jumps, date_metadata,
                                                                          debug=debug)
                        else:
                            date_strings, jump_days = update_date_strings(page, current_date, date_mapper,
                                                                          num_past_dates,
                                                                          num_future_dates, date_jumps, date_metadata,
                                                                          debug=debug)
                        date_searcher = FuzzyPhraseSearcher(phrase_model=date_strings, config=config)
                    else:
                        if debug > 0:
                            print(f"  session start found on same date as current date")
                    session_dates[current_date.isoformat()].append(date_metadata)
                if current_date.isoformat() not in session_dates:
                    no_evidence_metadata = add_date_start_with_no_evidence(current_date, main_tr,
                                                                           session_trs, session_dates)
                    session_dates[current_date.isoformat()].append(no_evidence_metadata)
                if main_tr not in session_trs[current_date.isoformat()]:
                    session_trs[current_date.isoformat()].append(main_tr)
            if current_date and main_tr in has_attendance:
                for att_tr in has_attendance[main_tr]:
                    if att_tr not in session_trs[current_date.isoformat()]:
                        session_trs[current_date.isoformat()].append(att_tr)
        prev_dates = [session_date for session_date in session_trs if session_date != current_date.isoformat()]
        if debug > 0:
            print(f'\ncurrent_date: {current_date.isoformat()}\tprev_dates:', prev_dates)
            for ses_date in session_dates:
                print(f"  date in session_dates dict: {ses_date}")
        for prev_date in prev_dates:
            session_date_metadata = session_dates[prev_date].pop(0)
            yield session_date_metadata, session_trs[prev_date]
            del session_trs[prev_date]
            del session_dates[prev_date]
    yield session_dates[current_date.isoformat()].pop(0), session_trs[current_date.isoformat()]
    return None


def process_handwritten_page_dates(inv_metadata: Dict[str, any], pages: List[pdm.PageXMLPage],
                                   ignorecase: bool = True):
    processed_pages = process_handwritten_pages(inv_metadata['inventory_num'], pages,
                                                ignorecase=ignorecase)
    date_token_cat = get_date_token_cat(inv_num=inv_metadata['inventory_num'], ignorecase=ignorecase)

    session_date_lines = get_session_date_lines_from_pages(processed_pages, debug=0)
    # date_line_structure = get_session_date_line_structure(session_date_lines, date_token_cat,
    #                                                       inv_metadata['inventory_id'])
    date_line_structures = get_session_date_line_structures(session_date_lines, date_token_cat,
                                                            inv_metadata['inventory_id'])

    date_mapper = DateNameMapper(inv_metadata, date_line_structures)
    config = {'ngram_size': 3, 'skip_size': 1, 'ignorecase': ignorecase, 'levenshtein_threshold': 0.8}
    weekday_name_searcher = make_weekday_name_searcher(date_mapper, config)
    return [process_handwritten_page(page, weekday_name_searcher=weekday_name_searcher,
                                     debug=0) for page in processed_pages]


def get_handwritten_sessions(inv_id: str, pages, ignorecase: bool = True,
                             session_starts: List[Dict[str, any]] = None,
                             do_preprocessing: bool = False,
                             num_past_dates: int = 5, num_future_dates: int = 31, debug: int = 0):
    print('handwritten_session_parser.get_handwritten_sessions - num pages:', len(pages))
    inv_metadata = get_inventory_by_id(inv_id)
    period_start = inv_metadata['period_start']
    pages.sort(key=lambda page: page.id)
    if debug > 1:
        print(f"handwritten_session_parser.get_handwritten_sessions - start:")
        print_line_class_dist(pages)
    if do_preprocessing is True:
        if debug > 1:
            print('handwritten_session_parser.get_handwritten_sessions - getting date_mapper with preprocessing')
        pages = process_handwritten_pages(inv_id, pages, ignorecase)
        # pages = process_handwritten_pages(inv_metadata, pages[start_index:end_index], ignorecase)
        date_mapper = get_inventory_date_mapper(inv_metadata, pages, ignorecase=ignorecase, debug=debug)
        config = {'ngram_size': 3, 'skip_size': 1, 'ignorecase': ignorecase, 'levenshtein_threshold': 0.8}
        weekday_name_searcher = make_weekday_name_searcher(date_mapper, config)
        pages = [process_handwritten_page(page, weekday_name_searcher=weekday_name_searcher,
                                          debug=0) for page in pages]
        if debug > 1:
            print(f"handwritten_session_parser.get_handwritten_sessions - after preprocessing:")
            print_line_class_dist(pages)
    else:
        date_region_classifier = load_date_region_classifier()
        date_tr_type_map = classify_page_date_regions(pages, date_region_classifier)
        if debug > 0:
            print('handwritten_session_parser.get_handwritten_sessions - getting date_mapper without preprocessing')
        date_mapper = get_inventory_date_mapper(inv_metadata, pages, filter_date_starts=True,
                                                date_tr_type_map=date_tr_type_map, ignorecase=ignorecase,
                                                debug=debug)
    # year_start_date = RepublicDate(date_string=inv_metadata['period_start'], date_mapper=date_mapper)
    # date_strings = get_next_date_strings(year_start_date, date_mapper, num_dates=7)

    # period_start = "1616-01-01"
    inv_start_date = RepublicDate(date_string=period_start, date_mapper=date_mapper)
    resolution_type = pages[0].metadata['resolution_type']
    text_type = pages[0].metadata['text_type']
    session_num = 0
    session_finder = find_session_dates(pages, inv_start_date, date_mapper, ignorecase=ignorecase,
                                        num_past_dates=num_past_dates, num_future_dates=num_future_dates,
                                        session_starts=session_starts,
                                        debug=debug)

    for session_date_metadata, session_trs in session_finder:
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
        session_metadata = make_session_metadata(inv_metadata, session_date_metadata, session_num, text_type)
        session = make_session(inv_metadata, session_date_metadata, session_num, text_type, session_trs)
        evidence = session_metadata['evidence']
        for session_tr in session_trs:
            session_tr.metadata['session_id'] = session['id']
            session_tr.metadata['iiif_url'] = doc_id_to_iiif_url(session_tr.id)
        # del session_date_metadata['evidence']
        session = rdm.Session(doc_id=session['id'], metadata=session_metadata,
                              date_metadata=session_date_metadata,
                              text_regions=session_trs,
                              evidence=evidence,
                              date_mapper=date_mapper)
        yield session
    return None


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
