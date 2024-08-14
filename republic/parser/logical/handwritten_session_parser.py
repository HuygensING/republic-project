import copy
import datetime
import re
from collections import defaultdict
from typing import Dict, List, Tuple, Union

import pagexml.model.physical_document_model as pdm
from fuzzy_search.match.phrase_match import PhraseMatch
from fuzzy_search.search.phrase_searcher import FuzzyPhraseSearcher
from fuzzy_search.search.token_searcher import FuzzyTokenSearcher

import republic.helper.pagexml_helper as pagexml_helper
import republic.model.republic_document_model as rdm
import republic.parser.pagexml.republic_column_parser as column_parser
from republic.classification.page_features import get_line_base_dist
from republic.helper.text_helper import is_duplicate
from republic.helper.metadata_helper import coords_to_iiif_url
from republic.helper.metadata_helper import doc_id_to_iiif_url
from republic.model.inventory_mapping import get_inventory_by_id
from republic.model.inventory_mapping import get_inventory_by_num
from republic.model.republic_date import DateNameMapper
from republic.model.republic_date import RepublicDate
from republic.model.republic_date import get_next_date_strings
from republic.parser.pagexml.republic_page_parser import split_page_column_text_regions
from republic.parser.logical.generic_session_parser import make_session_date_metadata
from republic.parser.logical.generic_session_parser import make_session
from republic.parser.logical.generic_session_parser import make_session_metadata
from republic.parser.logical.date_parser import get_date_token_cat
from republic.parser.logical.date_parser import get_session_date_line_structure
from republic.parser.logical.date_parser import get_session_date_lines_from_pages
from republic.parser.logical.date_parser import make_week_day_name_searcher
from republic.parser.logical.date_parser import extract_best_date_match


DATE_JUMPS = {
    ("4560", "1602-11-10"): [-250],
    ("4562", "1617-08-09"): [365],
    ("4562", "1632-12-22"): [-250],
    ("4562", "1632-05-04"): [0, 365],
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
    if re.match(r"geinsereer[dt]", line.text):
        return True
    else:
        return False


def sort_lines_by_class(page, debug: int = 0, near_extract_intro: bool = False):
    class_lines = defaultdict(list)
    predicted_line_class = get_predicted_line_classes(page)
    for col in sorted(page.columns, key=lambda c: c.coords.left):
        for tr in sorted(col.text_regions, key=lambda t: t.coords.top):
            if debug > 1:
                print('sort_lines_by_class - tr.type:', tr.type)
            for line in tr.lines:
                if debug > 1:
                    print(f"sort_lines_by_class - line_class line.text: "
                          f"{line.metadata['line_class']: <12}\t{line.text}")
                if line.text is None:
                    continue
                if line_introduces_insertion(line):
                    near_extract_intro = True
                    line.metadata['line_class'] = f"{line.metadata['line_class']}_extract_intro"
                    line.metadata['line_classifier'] = 'handwritten_session_parser'
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
    check_parentage(page)
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
        check_parentage(page)
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
                if debug > 0:
                    print(f'marginalia link from para {para_tr.id} to marg {marg_tr.id}')
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
    check_page_parentage(page)
    class_trs = defaultdict(list)
    line_groups: Dict[str, List[List[pdm.PageXMLTextLine]]] = defaultdict(list)
    for line_class in class_lines:
        line_groups[line_class] = split_lines_on_vertical_gaps(class_lines[line_class], debug=debug)
    check_page_parentage(page)
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
        check_page_parentage(page)
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


def process_handwritten_columns(columns: List[pdm.PageXMLColumn], page: pdm.PageXMLPage):
    """Process all columns of a page and merge columns that are horizontally overlapping."""
    merge_sets = column_parser.find_overlapping_columns(columns)
    # print(merge_sets)
    merge_cols = {col for merge_set in merge_sets for col in merge_set}
    non_overlapping_cols = [col for col in columns if col not in merge_cols]
    for merge_set in merge_sets:
        # print("MERGING OVERLAPPING COLUMNS:", [col.id for col in merge_set])
        merged_col = pagexml_helper.merge_columns(merge_set, "temp_id", merge_set[0].metadata)
        merged_col.set_derived_id(page.id)
        merged_col.set_parent(page)
        non_overlapping_cols.append(merged_col)
    return non_overlapping_cols


def process_handwritten_text_regions(text_regions: List[pdm.PageXMLTextRegion], column: pdm.PageXMLColumn,
                                     debug: int = 0):
    """Process all text regions of a columns and merge regions that are overlapping."""
    if debug > 3:
        print(f'process_handwritten_text_regions - start with {len(text_regions)} trs')
    non_overlapping_trs = []
    for tr in text_regions:
        check_parentage(tr)
    merge_sets = pagexml_helper.get_overlapping_text_regions(text_regions, overlap_threshold=0.5)
    assert sum(len(ms) for ms in merge_sets) == len(text_regions), "merge_sets contain more text regions that given"
    if debug > 3:
        for merge_set in merge_sets:
            print('process_handwritten_text_regions - merge_set size:', len(merge_set))
    for merge_set in merge_sets:
        if len(merge_set) == 1:
            tr = merge_set.pop()
            if debug > 3:
                print(f'process_handwritten_text_regions - adding tr at index {len(non_overlapping_trs)}:', tr.id)
            check_parentage(tr)
            non_overlapping_trs.append(tr)
            continue
        # print("MERGING OVERLAPPING TEXTREGION:", [tr.id for tr in merge_set])
        lines = [line for tr in merge_set for line in tr.lines]
        if len(lines) == 0:
            if debug > 3:
                print('process_handwritten_text_regions - no lines for merge_set of text regions with ids:',
                      [tr.id for tr in text_regions])
            coords = pdm.parse_derived_coords(list(merge_set))
        else:
            coords = pdm.parse_derived_coords(lines)
        merged_tr = pdm.PageXMLTextRegion(doc_id="temp_id", metadata=merge_set.pop().metadata,
                                          coords=coords, lines=lines)
        # print(merged_tr)
        merged_tr.set_derived_id(column.metadata['scan_id'])
        merged_tr.set_parent(column)
        merged_tr.set_as_parent(lines)
        check_parentage(merged_tr)
        if debug > 3:
            print(f'process_handwritten_text_regions - adding merged tr at index {len(non_overlapping_trs)}:',
                  merged_tr.id)
            for line in merged_tr.lines:
                print('\t', line.id, line.parent.id)
        non_overlapping_trs.append(merged_tr)
    if debug > 3:
        print(f'process_handwritten_text_regions - end with {len(non_overlapping_trs)} trs')
    for ti, tr in enumerate(non_overlapping_trs):
        try:
            check_parentage(tr)
        except ValueError:
            print(ti, tr.id)
            raise
    return non_overlapping_trs


def process_handwritten_page(page, week_day_name_searcher: FuzzyPhraseSearcher = None, debug: int = 0):
    """Split and/or merge columns and overlapping text regions of handwritten
    resolution pages and correct line classes for session dates, attendance
    lists, date headers and paragraphs. """
    check_parentage(page)
    page = copy.deepcopy(page)
    page.columns = process_handwritten_columns(page.columns, page)
    check_parentage(page)
    for col in page.columns:
        # print(f'\n{col.id}\n')
        col.text_regions = process_handwritten_text_regions(col.text_regions, col)
    check_parentage(page)
    page = split_page_column_text_regions(page, week_day_name_searcher=week_day_name_searcher,
                                          update_type=True, copy_page=False, debug=debug)
    check_parentage(page)
    return page


def make_inventory_date_name_mapper(inv_num: int, pages: List[pdm.PageXMLPage], debug: int = 0):
    """Return a date name mapper for a given inventory that returns likely date representations
    for a given date, based on the date format found in the pages of the inventory."""
    inv_meta = get_inventory_by_num(inv_num)
    date_token_cat = get_date_token_cat(inv_num=inv_meta['inventory_num'], ignorecase=True)
    session_date_lines = get_session_date_lines_from_pages(pages, debug=debug)
    date_line_structure = get_session_date_line_structure(session_date_lines, date_token_cat,
                                                          inv_meta['inventory_id'])
    try:
        date_mapper = DateNameMapper(inv_meta, date_line_structure)
    except Exception:
        print(f'Error creating DateNameMapper for inventory {inv_num}')
        print(f'with date_line_structure:', date_line_structure)
        print(f'with session_date_lines:', [line.text for line in session_date_lines])
        raise
    return date_mapper


def process_handwritten_pages(inv, pages, ignorecase: bool = True, debug: int = 0):
    date_mapper = make_inventory_date_name_mapper(inv, pages, debug=debug)
    config = {'ngram_size': 3, 'skip_size': 1, 'ignorecase': ignorecase, 'levenshtein_threshold': 0.8}
    week_day_name_searcher = make_week_day_name_searcher(date_mapper, config)
    new_pages = [process_handwritten_page(page, week_day_name_searcher=week_day_name_searcher,
                                          debug=0) for page in pages]
    return new_pages


def check_parentage(doc: pdm.PageXMLDoc):
    """Check that a documents descendants have proper parentage set."""
    # print('doc.id:', doc.id)
    if isinstance(doc, pdm.PageXMLPage):
        for column in doc.columns:
            if column.parent is None:
                raise ValueError(f"no parent set for column {column.id} in page {doc.id}")
            if column.parent != doc:
                raise ValueError(f"wrong parent set for column {column.id} in page {doc.id}")
            check_parentage(column)
        for tr in doc.extra:
            if tr.parent is None:
                raise ValueError(f"no parent set for text_region {tr.id} in page {doc.id}")
            if tr.parent != doc:
                raise ValueError(f"wrong parent set for text_region {tr.id} in page {doc.id}")
            check_parentage(tr)
    elif isinstance(doc, pdm.PageXMLColumn):
        for tr in doc.text_regions:
            if tr.parent is None:
                raise ValueError(f"no parent set for tr {tr.id} in column {doc.id}")
            if tr.parent != doc:
                raise ValueError(f"wrong parent set for tr {tr.id} in column {doc.id}")
            check_parentage(tr)
    elif isinstance(doc, pdm.PageXMLTextRegion):
        for line in doc.lines:
            if line.parent is None:
                raise ValueError(f"no parent set for line {line.id} in text_region {doc.id}")
            if line.parent != doc:
                print('line parent:', line.parent.id)
                raise ValueError(f"wrong parent set for line {line.id} in text_region {doc.id}")


def check_page_parentage(page: pdm.PageXMLPage):
    for col in page.columns:
        if col.parent != page:
            raise ValueError(f"no parent set for column {col.id} in page {page.id}")
        for tr in col.text_regions:
            if tr.parent != col:
                raise ValueError(f"no parent set for text_region {tr.id} in page {page.id}")
            for line in tr.lines:
                if line.parent != tr:
                    raise ValueError(f"no parent set for line {line.id} in page {page.id}")
    return None


def find_session_dates(pages, inv_start_date, date_mapper: DateNameMapper,
                       ignorecase: bool = True, near_extract_intro: bool = False,
                       num_past_dates: int = 5, num_future_dates: int = 31, debug: int = 0):
    date_strings = get_next_date_strings(inv_start_date, date_mapper, num_dates=num_future_dates, include_year=False)
    # for dt in date_strings:
    #     print(dt, date_strings[dt])
    date_jumps = copy.deepcopy(DATE_JUMPS)
    if 3096 <= pages[0].metadata['inventory_num'] <= 3350:
        config = {'ngram_size': 2, 'skip_size': 1, 'ignorecase': ignorecase, 'levenshtein_threshold': 0.8}
        date_searcher = FuzzyPhraseSearcher(phrase_model=date_strings, config=config)
    else:
        config = {'ngram_size': 3, 'skip_size': 1, 'ignorecase': ignorecase, 'levenshtein_threshold': 0.8}
        date_searcher = FuzzyTokenSearcher(phrase_model=date_strings, config=config)
    if debug > 0:
        print('find_session_dates - initial date_strings:', date_strings.keys())
    print(date_searcher.phrase_model.token_in_phrase)
    if debug > 0:
        print(f"{pages[0].metadata['inventory_num']}\tstart_date: {inv_start_date}\tnumber of pages: {len(pages)}")

    session_dates = defaultdict(list)
    session_trs = defaultdict(list)
    current_date = None
    jump_days = 0
    num_lines_since_extract_intro = 0
    for pi, page in enumerate(pages):
        page = copy.deepcopy(page)
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
        check_page_parentage(page)
        # print('find_session_dates - page:', page.id)
        if 'inventory_id' not in page.metadata:
            page.metadata['inventory_id'] = f"{page.metadata['series_name']}_{page.metadata['inventory_num']}"
        class_lines, near_extract_intro = sort_lines_by_class(page, near_extract_intro=near_extract_intro,
                                                              debug=debug)
        if debug > 0:
            print(f'page: {page.id}\tnear_extract_intro: {near_extract_intro}\n')
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
        check_page_parentage(page)
        if debug > 0:
            print(f'\tAFTER - near_extract_intro: {near_extract_intro}')
            print(f'\tAFTER - num_lines_since_extract_intro: {num_lines_since_extract_intro}\n')
        check_page_parentage(page)
        class_trs = make_classified_text_regions(class_lines, page, debug=debug)
        check_page_parentage(page)
        has_attendance = link_date_attendance(class_trs)
        check_page_parentage(page)
        has_marginalia = link_para_marginalia(class_trs, debug=debug)
        check_page_parentage(page)
        unlinked_att_trs, unlinked_marg_trs = link_classified_text_regions(class_trs, debug=debug)
        check_page_parentage(page)
        if debug > 0:
            if len(unlinked_att_trs) > 0:
                print('find_session_dates - unlinked_att_trs:', len(unlinked_att_trs), page.id)
            if len(unlinked_marg_trs) > 0:
                print('find_session_dates - unlinked_marg_trs:', len(unlinked_marg_trs), page.id)
        main_trs = sorted(class_trs['date'] + class_trs['para'], key=lambda tr: tr.coords.top)

        check_page_parentage(page)
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
                line_matches = date_searcher.find_matches({'id': line.id, 'text': line.text}, debug=0)
                # for match in line_matches:
                #     print(match)
                filtered_matches = [match for match in line_matches if match.offset < 50]
                filtered_matches = [match for match in filtered_matches if
                                    abs(len(match.string) - len(line.text)) < 50]
                best_match = extract_best_date_match(filtered_matches, current_date if current_date else inv_start_date,
                                                     jump_days, date_strings)
                if best_match:
                    current_date_string = current_date.date.isoformat() if current_date else None
                    current_date = date_strings[best_match.phrase.phrase_string]
                    if debug > 1:
                        print('\tbest_match', best_match.phrase.phrase_string, '\t', best_match.string, '\t',
                              best_match.levenshtein_similarity)
                    # print('\n--------------------------------\n')
                    if debug > 0:
                        print('\tbest_match', best_match.phrase.phrase_string, '\t', best_match.string, '\t',
                              best_match.levenshtein_similarity)
                    print(f'\tdate: {current_date.isoformat()}\tpage: {page.id}')
                    # print('\n--------------------------------\n')
                    if debug > 2:
                        print(f'UPDATING CURRENT DATE from {current_date_string} to '
                              f'{date_strings[best_match.phrase.phrase_string].date.isoformat()}')
                    date_metadata = make_session_date_metadata(current_date, best_match, line)
                    session_dates[current_date.isoformat()].append(date_metadata)
                    session_trs[current_date.isoformat()].append(main_tr)
                    if debug > 2:
                        print(f'\tADDING main_tr to {current_date.date.isoformat()}')
                    if debug > 0:
                        print('find_session_dates - found date:', current_date, best_match.string, page.id)
                    jump_days = calculate_date_jump(page.metadata['inventory_num'], current_date, date_jumps)
                    delta = datetime.timedelta(days=-num_past_dates + jump_days)
                    start_day = current_date.date + delta
                    start_day = RepublicDate(start_day.year, start_day.month, start_day.day, date_mapper=date_mapper)
                    if debug > 0:
                        print(f"jump: {jump_days}\tdelta: {delta}\tstart_day: {start_day}")
                    if debug > 1:
                        print(f'current_date: {current_date.date.isoformat()}\tstart_day: {start_day.date.isoformat()}')
                    date_strings = get_next_date_strings(start_day, date_mapper,
                                                         num_dates=num_past_dates + num_future_dates + 1,
                                                         include_year=False)
                    # for date_string in date_strings:
                    #     print(f'DATE STRING {date_string}\t{date_strings[date_string]}')
                    # print('date_strings:', date_strings.keys())
                    date_searcher = FuzzyPhraseSearcher(phrase_model=date_strings, config=config)
            if current_date and main_tr in has_attendance:
                for att_tr in has_attendance[main_tr]:
                    session_trs[current_date.isoformat()].append(att_tr)
        prev_dates = [session_date for session_date in session_trs if session_date != current_date.isoformat()]
        if debug > 0:
            print(f'\nprev_dates:', prev_dates)
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
    date_line_structure = get_session_date_line_structure(session_date_lines, date_token_cat,
                                                          inv_metadata['inventory_id'])

    date_mapper = DateNameMapper(inv_metadata, date_line_structure)
    config = {'ngram_size': 3, 'skip_size': 1, 'ignorecase': ignorecase, 'levenshtein_threshold': 0.8}
    week_day_name_searcher = make_week_day_name_searcher(date_mapper, config)
    return [process_handwritten_page(page, week_day_name_searcher=week_day_name_searcher,
                                     debug=0) for page in processed_pages]


def get_inventory_date_mapper(inv_metadata: Dict[str, any], pages: List[pdm.PageXMLPage],
                              ignorecase: bool = True, debug: int = 0):
    date_token_cat = get_date_token_cat(inv_num=inv_metadata['inventory_num'], ignorecase=ignorecase)
    session_date_lines = get_session_date_lines_from_pages(pages, debug=debug)
    if len(session_date_lines) == 0:
        print(f"WARNING - No session date lines found for "
              f"inventory {inv_metadata['inventory_num']} with {len(pages)} pages")
        return None
    date_line_structure = get_session_date_line_structure(session_date_lines,
                                                          date_token_cat, inv_metadata['inventory_id'])
    if 'week_day_name' not in [element[0] for element in date_line_structure]:
        print('WARNING - missing week_day_name in date_line_structure for inventory', inv_metadata['inventory_num'])
        return None

    return DateNameMapper(inv_metadata, date_line_structure)


def get_handwritten_sessions(inv_id: str, pages, ignorecase: bool = True,
                             session_starts: List[Dict[str, any]] = None,
                             num_past_dates: int = 5, num_future_dates: int = 31, debug: int = 0):
    print('get_sessions - num pages:', len(pages))
    inv_metadata = get_inventory_by_id(inv_id)
    period_start = inv_metadata['period_start']
    pages.sort(key=lambda page: page.id)
    pages = process_handwritten_pages(inv_metadata, pages, ignorecase)
    # pages = process_handwritten_pages(inv_metadata, pages[start_index:end_index], ignorecase)
    date_mapper = get_inventory_date_mapper(inv_metadata, pages, ignorecase=ignorecase, debug=debug)
    config = {'ngram_size': 3, 'skip_size': 1, 'ignorecase': ignorecase, 'levenshtein_threshold': 0.8}
    week_day_name_searcher = make_week_day_name_searcher(date_mapper, config)
    pages = [process_handwritten_page(page, week_day_name_searcher=week_day_name_searcher,
                                      debug=0) for page in pages]

    # year_start_date = RepublicDate(date_string=inv_metadata['period_start'], date_mapper=date_mapper)
    # date_strings = get_next_date_strings(year_start_date, date_mapper, num_dates=7)

    # period_start = "1616-01-01"
    inv_start_date = RepublicDate(date_string=period_start, date_mapper=date_mapper)
    resolution_type = pages[0].metadata['resolution_type']
    text_type = pages[0].metadata['text_type']
    session_num = 0
    session_finder = find_session_dates(pages, inv_start_date, date_mapper, ignorecase=ignorecase,
                                        num_past_dates=num_past_dates, num_future_dates=num_future_dates,
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
        session = rdm.Session(metadata=session_metadata, date_metadata=session_date_metadata,
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
