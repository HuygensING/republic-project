from __future__ import annotations

import copy
from typing import Dict, List, Tuple, Union
from collections import defaultdict
from itertools import combinations
import re

import numpy as np
import pagexml.model.physical_document_model as pdm

import republic.parser.pagexml.republic_column_parser as column_parser
# import republic.model.physical_document_model as pdm
# from republic.model.physical_document_model import PageXMLTextLine
from republic.helper.metadata_helper import parse_scan_id
from republic.helper.pagexml_helper import make_baseline_string as mbs

day_month_pattern = r"^(\d+) (Jan|Feb|Maa|Apr|Mey|Jun|Jul|Aug|Sep|Oct|Okt|Nov|Dec)\S{,3}$"
month_pattern = r"^(Jan|Feb|Maa|Apr|Mey|Jun|Jul|Aug|Sep|Oct|Okt|Nov|Dec)\S{,3}$"
day_month_dito_pattern = r"^(\d+) (dito|ditto|Jan|Feb|Maa|Apr|Mey|Jun|Jul|Aug|Sep|Oct|Okt|Nov|Dec)\S{,3}$"
day_month_dito_end_pattern = r".*(\d+) (dito|ditto|Jan|Feb|Maa|Apr|Mey|Jun|Jul|Aug|Sep|Oct|Okt|Nov|Dec)\S{,3}$"
day_dito_pattern = r"^(\d+) (dito|ditto)\S{,2}$"


def move_lines(line_types: Dict[str, List[pdm.PageXMLTextLine]], target_type: str,
               target_docs: pdm.List[pdm.PageXMLTextRegion], debug: int = 0) -> None:
    if debug > 1:
        print("move_lines - MOVING LINES")
        if debug > 2:
            for target_doc in target_docs:
                print(f'\ttarget_type: {target_type}\ttarget_doc.coords.left: {target_doc.coords.left}'
                      f'\t.right: {target_doc.coords.right}')
    for line_type in line_types:
        if line_type == target_type or line_type in {"header", "double_col", "finis_lines", "title", "empty"}:
            continue
        # if line_type == "main_term":
        #     continue
        # print(line_type, len(line_types[line_type]))
        lines = [line for line in line_types[line_type]]
        # for li, line in enumerate(lines):
        #     print("before:", line.coords.x, line.coords.y, line.text)
        for li, line in enumerate(lines):
            has_moved = False
            for target_doc in target_docs:
                # if line_type == "main_term" and target_type == "page_locator":
                #     print("target type:", target_type, "doc:", target_doc.id)
                threshold = 0.5
                if line_type in {'date_locator', 'page_locator'}:
                    threshold = 0.7
                if pdm.is_horizontally_overlapping(line, target_doc, threshold=threshold):
                    # pdm.is_vertically_overlapping(line, target_doc):
                    if debug > 1:
                        print(f"move_lines - {li} moving line from {line_type} to {target_type}: {line.coords.x}-{line.coords.right}"
                              f"\t{line.coords.y: >6}\t{line.text}")
                    line_types[target_type].append(line)
                    if line not in line_types[line_type]:
                        print("trying to remove line", li, line.text)
                    line_types[line_type].remove(line)
                    has_moved = True
                if has_moved:
                    break
            # if has_moved is False and line_type == "main_term" and target_type == "sub_lemma":
            #     print(f"{li} keeping line in {line_type}: {line.coords.x: >6}{line.coords.y: >6}\t{line.text}")


def filter_header_lines(line_types: Dict[str, List[pdm.PageXMLTextLine]], debug: int = 0) -> None:
    # Step 1a: make header box
    coords = pdm.parse_derived_coords(line_types["header"])
    header = pdm.PageXMLTextRegion("header", coords=coords)
    if debug > 1:
        print("filter_header_lines - HEADER BOTTOM:", header.coords.bottom)
    # Step 1b: move lines from other to header box
    for line_type in line_types:
        if line_type in {"header", "finis_lines", "title", "empty"}:
            continue
        lines = sorted(line_types[line_type], key=lambda x: x.coords.y)
        for line in lines:
            # print(line_type, line.coords.x, line.coords.y, line.coords.bottom, line.text)
            if pdm.is_vertically_overlapping(line, header) or line.coords.bottom < header.coords.bottom:
                move = True
                # check if line horizontally overlaps because of page skew
                if len(line.text) >= 5 and line.coords.bottom > header.coords.bottom - 20:
                    h_overlap = []
                    for header_line in line_types["header"]:
                        if pdm.is_horizontally_overlapping(header_line, line, threshold=0.01) \
                                and line.is_below(header_line):
                            move = False
                        elif pdm.is_vertically_overlapping(line, header_line, threshold=0.5):
                            h_overlap.append(header_line)
                        # print([pdm.horizontal_distance(line, h_line) for h_line in h_overlap])
                    h_overlap.sort(key=lambda x: pdm.horizontal_distance(line, x))
                    if len(h_overlap) > 0:
                        if min([pdm.horizontal_distance(line, h_line) for h_line in h_overlap]) > 500:
                            move = False
                        elif len(line.text) > 6 and line.coords.bottom > h_overlap[0].coords.bottom + 10:
                            move = False
                if move:
                    line_types["header"].append(line)
                    line_types[line_type].remove(line)
                    if debug > 1:
                        print(f"filter_header_lines - moving line from {line_type} to header: {line.coords.left: >4}-{line.coords.right: <4}"
                              f"\t{line.coords.top}-{line.coords.bottom}\t{line.text}")
    if debug > 0:
        print('filter_header_lines - returning line_types and number of lines:')
        print_line_type_stats(line_types)


def print_line_type_stats(line_types, debug: int = 0):
    for line_type in line_types:
        print('\t', line_type, len(line_types[line_type]))
        if debug > 2:
            for line in sorted(line_types[line_type], key=lambda x: x.coords.y):
                print(f"\t{line_type}\t{line.coords.left: >4}-{line.coords.right: <4}"
                      f"\twidth: {line.coords.width}\ttop: {line.coords.top}, bottom: {line.coords.bottom}"
                      f"\t{line.text}")
    print('\ttotal: ', sum([len(line_types[line_type]) for line_type in line_types]))


def get_line_parent_metadata(line: pdm.PageXMLTextLine) -> Dict[str, any]:
    if line.parent is None:
        print(f"line with id {line.id} has no parent")
        raise AttributeError(f"line with id {line.id} has no parent")
    return copy.deepcopy(line.parent.metadata)


def make_line_type_text_region(lines: List[pdm.PageXMLTextLine], line_type: str = None) -> pdm.PageXMLTextRegion:
    try:
        temp_coords = pdm.parse_derived_coords(lines)
    except Exception:
        print(f'make_index_page_text_regions - Error creating coords for {len(lines)} column lines'
              f' for line_type {line_type}')
        for line in lines:
            print('\t', line.coords.box, line.text)
        raise
    metadata = get_line_parent_metadata(lines[0])

    temp_tr = pdm.PageXMLTextRegion(metadata=metadata, coords=temp_coords, lines=lines)
    if 'column_id' in metadata:
        temp_tr.set_derived_id(metadata['column_id'])
    elif 'page_id' in metadata:
        temp_tr.set_derived_id(metadata['page_id'])
    elif 'scan_id' in metadata:
        temp_tr.set_derived_id(metadata['scan_id'])
    else:
        raise KeyError(f"no 'scan_id' in metadata: {metadata} for parent of line {lines[0].id}")
    return temp_tr


def move_double_col_lines(line_types: Dict[str, List[pdm.PageXMLTextLine]],
                          config: Dict[str, any], overlap_threshold: float = 0.7,
                          debug: int = 0):
    # print("MOVING DOUBLE COL LINES")
    target_type = "sub_lemma"
    config = copy.deepcopy(config)
    config["column_gap"]["gap_pixel_freq_ratio"] = 0.25
    # print("move_double_col_lines - line.metadata:", line_types[target_type][0].metadata)
    # print("move_double_col_lines - line.parent.metadata:", line_types[target_type][0].metadata)

    # print("temp tr:", temp_tr.id, temp_tr.stats)
    # Assumption 2024-05-07: there is at least one sub_lemma line, probably an incorrect assumption
    check_line_parent_metadata([line for lt in line_types for line in line_types[lt]])
    temp_tr = make_line_type_text_region(line_types[target_type], line_type=target_type)
    columns = column_parser.split_lines_on_column_gaps(temp_tr, config,
                                                       overlap_threshold=overlap_threshold)
    main_tr = make_line_type_text_region(line_types['main_term'], line_type='main_term')
    main_columns = column_parser.split_lines_on_column_gaps(main_tr, config,
                                                            overlap_threshold=overlap_threshold)
    if debug > 0:
        print(f"move_double_col_lines - sub_lemma columns:")
        for col in columns:
            print(f"\tleft-right: {col.coords.left}-{col.coords.right}"
                  f"\ttop-bottom: {col.coords.top}-{col.coords.bottom}"
                  f"\tlines: {col.stats['lines']}")
        print(f"move_double_col_lines - main_term columns:")
        for col in main_columns:
            print(f"\tleft-right: {col.coords.left}-{col.coords.right}"
                  f"\ttop-bottom: {col.coords.top}-{col.coords.bottom}"
                  f"\tlines: {col.stats['lines']}")
    if len(columns) > 2:
        columns.sort(key=lambda x: x.coords.left)
        for ci, left_col in enumerate(columns[:-1]):
            right_col = columns[ci+1]
            if not pdm.is_horizontally_overlapping(left_col, right_col, threshold=0.2):
                continue
            # sub lemma column is typically around 450-470 pixels wide
            # much narrower columns to the left of them that partially
            # overlap with them probably around merged lines from two
            # columns.
            if right_col.coords.width > 400 and left_col.coords.width < 350:
                for line in left_col.get_lines():
                    if debug > 0:
                        print(f"\tMOVING SUB_LEMMA LINE TO DOUBLE_COL: {mbs(line)}\t{line.text}")
                    # print(f"\t{line.coords.left}-{line.coords.right}\t{line.coords.width}\t{line.text}")
                    line_types["double_col"].append(line)
                    line_types["sub_lemma"].remove(line)


def filter_target_type_lines(target_type: str,
                             line_types: Dict[str, List[pdm.PageXMLTextLine]],
                             config: Dict[str, any], overlap_threshold: float = 0.1,
                             debug: int = 0) -> None:
    if debug > 0:
        print("filter_target_type_lines - check line_type stats BEGIN")
        print_line_type_stats(line_types, debug=debug)
    if debug > 1:
        print("filter_target_type_lines - FILTERING FOR TARGET", target_type)

    temp_tr = make_line_type_text_region(line_types[target_type], line_type=target_type)
    if 'column_id' in temp_tr.metadata:
        temp_tr.set_derived_id(temp_tr.metadata['column_id'])
    elif 'scan_id' in temp_tr.metadata:
        temp_tr.set_derived_id(temp_tr.metadata['scan_id'])
    elif 'page_id' in temp_tr.metadata:
        temp_tr.set_derived_id(temp_tr.metadata['page_id'].split('-page-')[0])
    else:
        raise KeyError('no column_id, scan_id nor page_id in metadata of temp_tr')

    # print("temp tr:", temp_tr.id, temp_tr.stats)
    columns = column_parser.split_lines_on_column_gaps(temp_tr, config,
                                                       overlap_threshold=overlap_threshold, debug=debug)
    # sometimes the gap_pixel_freq_ratio select column ranges that exclude all lines and
    # they all end up in an extra text_region (so a single column is returned that is
    # actually a TextRegion). In that case, redo the split with a lower gap_pixel_freq_ratio
    if len(columns) == 1 and isinstance(columns[0], pdm.PageXMLColumn) is False:
        if debug > 0:
            print(f"filter_target_type_lines - re-splitting columns with lower gap_pixel_freq_ratio for {target_type}")
        temp_config = copy.deepcopy(config)
        temp_config['column_gap']['gap_pixel_freq_ratio'] = 0.4
        # print("\tnew config:", temp_config['column_gap'])
        columns = column_parser.split_lines_on_column_gaps(temp_tr, temp_config,
                                                           overlap_threshold=overlap_threshold, debug=debug)
    real_columns = []
    for column in columns:
        # print(f"filter_target_type_lines - checking column width - column.width: {column.coords.width}")
        if not isinstance(column, pdm.PageXMLColumn):
            column = pdm.PageXMLColumn(metadata=copy.deepcopy(column.metadata),
                                       coords=copy.deepcopy(column.coords),
                                       text_regions=[column])
            column.set_derived_id(column.metadata['scan_id'])
            # print(f"filter_target_type_lines - checking real column width - column.width: {column.coords.width}")
        real_columns.append(column)
    columns = real_columns
    # if debug > 0:
    #     print("BEFORE MOVING TO SUB LEMMA")
    #     for line_type in line_types:
    #         print(f'\t{line_type}: {len(line_types[line_type])} lines')
    # print("filter split columns:", len(columns))
    # if extra_tr is not None:
    #     if len(columns) == 2:
    #         for line in extra_tr.lines:
    #             print("extra as third column", line.coords.left, line.coords.right, line.text)
    #     else:
    #         columns.append(extra_tr)
    columns.sort(key=lambda x: x.coords.left)
    if debug > 1:
        print('\tnumber of columns:', len(columns))
        print(f"filter_target_type_lines - BEFORE MOVING LINES: ")
        for column in columns:
            print(f"\t{target_type}\t{column.coords.left}-{column.coords.right}"
                  f"\t{column.coords.top}-{column.coords.bottom}"
                  f"\tWidth: {column.coords.width}\tLines: {len(column.get_lines())}")
            # for line in column.get_lines():
            #     print('\t', line.coords.left, line.coords.right, line.text)
    if len(columns) > 2:
        # normal distance between two columns of the same type
        if debug > 0:
            print(f"filter_target_type_lines - computing normal distance between columns")
        norm_dist = set()
        for c1, c2 in combinations(columns, 2):
            dist = c2.coords.left - c1.coords.left
            if debug > 0:
                print(f"\tc1.coords.left: {c1.coords.left}\tc2.coords.left: {c2.coords.left}\tdist: {dist}")
            # print(c1.coords.left, c2.coords.left, dist)
            if 800 < dist < 1000:
                norm_dist.add(c1)
                norm_dist.add(c2)
        for col in columns:
            if col not in norm_dist:
                for line in col.get_lines():
                    line_types[target_type].remove(line)
                    line_types["unknown"].append(line)
                    if debug > 0:
                        print(f"\tmoving line to unknown: {mbs(line)}\t{line.text}")
                # print(f"NOISE COLUMN: {col.coords.left}-{col.coords.right}\tLines: {len(col.get_lines())}")
        columns = norm_dist
    for column in columns:
        if debug > 0:
            print(f"filter_target_type_lines - checking col width below 600 - col.width: {column.coords.width}")
        if target_type == "sub_lemma" and column.coords.width > 600:
            # check for double column lines
            new_double_col_lines = []
            for li, curr_line in enumerate(column.get_lines()):
                start = li - 5 if li > 5 else 0
                end = li + 6 if li + 6 <= len(column.get_lines()) else len(column.get_lines())
                neighbour_lines = [line for line in column.get_lines()[start:end] if line != curr_line]
                median_left = np.median([line.coords.x for line in neighbour_lines])
                if median_left - curr_line.coords.left > 100:
                    if debug > 0:
                        print(f"filter_target_type_lines - SUB LEMMA HAS DOUBLE COL LINE: {mbs(curr_line)}",
                              curr_line.text)
                    new_double_col_lines.append(curr_line)
            if len(new_double_col_lines) > 0:
                for line in new_double_col_lines:
                    if debug > 0:
                        print(f"filter_target_type_lines - moving line from sub_lemma to double_col: {mbs(line)}",
                              line.text)
                    line_types["double_col"].append(line)
                    line_types["sub_lemma"].remove(line)
                    # print('LINE IN COL.get_lines():', line in column.get_lines())
                    # print('LINE IN COL.lines:', line in column.lines)
                    for tr in column.text_regions:
                        # print('LINE IN TR.get_lines():', line in tr.get_lines())
                        # print('LINE IN TR.lines:', line in tr.lines)
                        if line in tr.lines:
                            if debug > 0:
                                print(f"filter_target_type_lines - removing line from sub_lemma tr: {mbs(line)}",
                                      line.text)
                            tr.lines.remove(line)
                            if len(tr.lines) == 0:
                                if debug > 0:
                                    print(f"filter_target_type_lines - removing empty tr coords")
                                column.text_regions.remove(tr)
                            else:
                                tr.coords = pdm.parse_derived_coords(tr.lines)
                                if debug > 0:
                                    print(f"filter_target_type_lines - updating tr coords: {tr.coords.box}")
                    if len(column.text_regions) > 0:
                        column.coords = pdm.parse_derived_coords(column.text_regions)
                        if debug > 0:
                            print(f"filter_target_type_lines - updating column coords: {column.coords.box}")
    #     print(f"\t{target_type}:", column.id, column.stats)
    # Step 2b: move lines from main_term to sub_lemma boxes
    if debug > 0:
        print("filter_target_type_lines - check line_type stats END")
        print_line_type_stats(line_types, debug=debug)
        for col in columns:
            print('\tcol', col.stats)
    if debug > 1:
        print(f"filter_target_type_lines - calling move_lines with target_type {target_type}")
        print("\tcolumn coords are now:")
        for col in columns:
            print(f"\t\t{col.coords.box}")
    move_lines(line_types, target_type, columns, debug=debug)


def filter_finis_lines(lines: List[pdm.PageXMLTextLine],
                       debug: int = 0) -> Tuple[List[pdm.PageXMLTextLine], List[pdm.PageXMLTextLine]]:
    filtered_lines = []
    long_lines = [line for line in lines if line.text and len(line.text) > 5]
    temp_coords = pdm.parse_derived_coords(long_lines)
    if debug > 0:
        print("filter_target_type_lines - REMOVING FINIS LINES")
        print("\tpage text bottom:", temp_coords.bottom)
        print(f"\tpage has {len(lines)} lines")
    finis_lines = []
    for line in lines:
        if temp_coords.bottom - line.coords.bottom < 20:
            if debug > 0:
                print("\tclose to page text bottom:", line.coords.x, line.coords.y, line.text)
            if line.text is None or len(line.text) < 3:
                finis_lines.append(line)
    for line in lines:
        overlapping = [finis_line for finis_line in finis_lines if pdm.is_vertically_overlapping(line, finis_line)]
        if line in finis_lines:
            continue
        elif len(overlapping) > 0:
            if debug > 0:
                print("\t\tline overlapping with FINIS lines:", line.coords.x, line.coords.y, line.text)
            finis_lines.append(line)
        else:
            filtered_lines.append(line)
    return filtered_lines, finis_lines


def classify_lines(page_doc: pdm.PageXMLTextRegion, last_page: bool = False,
                   debug: int = 0) -> Dict[str, List[pdm.PageXMLTextLine]]:
    if debug > 0:
        print(f"classify_lines - BEFORE COLLECTING TRS - PAGE HAS {page_doc.stats['words']} WORDS, "
              f"{page_doc.stats['lines']} LINES")
    trs = [tr for tr in page_doc.text_regions]
    title_trs = []
    if hasattr(page_doc, "columns"):
        trs += [tr for tr in page_doc.columns if tr not in trs]
    if hasattr(page_doc, "extra"):
        trs += [tr for tr in page_doc.extra if tr not in trs and tr.has_type('title') is False]
        title_trs += [tr for tr in page_doc.extra if tr not in trs and tr.has_type('title')]
    if debug > 0:
        num_words = sum([tr.stats['words'] for tr in trs + title_trs])
        num_lines = sum([tr.stats['lines'] for tr in trs + title_trs])
        print(f"classify_lines - BEFORE COLLECTING LINES - TRS HAVE {num_words} WORDS, {num_lines} LINES")
    lines = [line for tr_outer in trs for tr_inner in tr_outer.text_regions for line in tr_inner.lines]
    lines += [line for tr in trs for line in tr.lines if line not in lines]
    lines += [line for line in page_doc.lines if line not in lines]
    lines = list(set(lines))
    if debug > 0:
        num_words = sum([line.stats['words'] for line in lines])
        num_words += sum([line.stats['words'] for tr in title_trs for line in tr.lines])
        num_lines = len(lines) + sum([tr.stats['lines'] for tr in title_trs])
        print(f"classify_lines - AFTER COLLECTING LINES - LINES HAVE {num_words} WORDS, {num_lines} LINES")
    # print(f"AFTER COLLECTING LINES - PAGE HAS {page_doc.stats['words']} WORDS, {page_doc.stats['lines']} LINES")
    if last_page:
        lines, finis_lines = filter_finis_lines(lines, debug=debug)
    else:
        finis_lines = []
    # print(f"classifying {len(set(lines))} lines")
    line_types = {
        "header": [],
        "main_term": [],
        "sub_lemma": [],
        "date_locator": [],
        "page_locator": [],
        "double_col": [],
        "finis_lines": finis_lines,
        "unknown": [],
        'title': [line for tr in title_trs for line in tr.lines],
        'empty': [],
    }
    check_line_parent_metadata(lines)
    for line in set(lines):
        if line.text is None:
            if debug > 0:
                print("classify_lines - SKIPPING NONE-TEXT LINE")
            line_types['empty'].append(line)
            continue
        if re.match(r"^[A-Z]\.?$", line.text) and line.coords.y < 420:
            line_types["header"].append(line)
        elif re.match(r"^(datums|pag)[,.]*$", line.text, re.IGNORECASE):
            line_types["header"].append(line)
        elif re.search(day_month_dito_pattern, line.text, re.IGNORECASE):
            line_types["date_locator"].append(line)
        elif re.search(r"^dito.{,2}$", line.text):
            line_types["date_locator"].append(line)
        elif re.search(r"^dito.{3,}$", line.text):
            line_types["double_col"].append(line)
        elif re.search(r"^\d+$", line.text):
            line_types["page_locator"].append(line)
        elif re.search(day_month_dito_end_pattern, line.text, re.IGNORECASE):
            line_types["double_col"].append(line)
        elif len(line.text) > 25 or line.coords.width > 550:
            line_types["double_col"].append(line)
        elif len(line.text) >= 15 or re.match("Item", line.text):
            line_types["sub_lemma"].append(line)
        else:
            line_types["main_term"].append(line)
    # print(f"AFTER SORTING LINES - PAGE HAS {page_doc.stats['words']} WORDS, {page_doc.stats['lines']} LINES")
    if debug > 0:
        print('classify_lines - returning line_types and number of lines:')
        print_line_type_stats(line_types, debug=debug)
    return line_types


def extract_overlapping_text(line: pdm.PageXMLTextLine, tr: pdm.PageXMLTextRegion,
                             debug: int = 0) -> tuple[pdm.PageXMLTextLine | None, pdm.PageXMLTextLine | None]:
    num_chars = len(line.text)
    char_width = line.coords.width / num_chars
    overlap_width = tr.coords.right - line.coords.left
    overlap_num_chars = int(overlap_width / char_width)
    if overlap_num_chars == 0:
        # the overlap is too small for a single character,
        # skip this column
        return None, line
    left = line.coords.left
    text = line.text
    points = line.coords.points
    bases = line.baseline.points
    best_dist = num_chars
    best_end = 0
    best_tail_start = 0
    for m in re.finditer(r"(\S+)\s*", text):
        end = m.start() + len(m.group(1))
        dist = abs(end - overlap_num_chars)
        if dist < best_dist:
            best_dist = dist
            best_end = end
            best_tail_start = m.end()
        if debug > 0:
            print(m.start(), m.end(), m.group(1), len(m.group(1)), "num_chars:",
                  overlap_num_chars, "best_end:", best_end)

    overlap_text = text[:best_end]
    overlap_width = int(char_width * len(overlap_text))
    overlap_right = left + overlap_width
    remaining_text = text[best_tail_start:]
    remaining_left = left + int(char_width * best_tail_start)
    if debug > 0:
        print("OVERLAP TEXT:", overlap_text)
        print("REMAINING TEXT:", remaining_text)

        print(
            f"char width: {char_width}\t{left} - {tr.coords.right}\toverlap width: {overlap_width}"
            f"\tnum_chars: {best_end}")
    overlap_points = [point for point in points if point[0] <= tr.coords.right]
    overlap_bases = [point for point in bases if point[0] <= tr.coords.right]
    if debug and len(overlap_bases) == 0:
        print("overlapping text region, coords right:", tr.coords.right)
        print("line baseline points:", bases)
    overlap_points += [(overlap_right, overlap_points[-1][1])]
    overlap_bases += [(overlap_right, overlap_bases[-1][1])]
    if len(overlap_text) == 0:
        overlap_line = None
    else:
        # print("PARTIAL:", overlap_points)
        overlap_coords = pdm.Coords(overlap_points)
        overlap_baseline = pdm.Baseline(overlap_bases)
        overlap_line = pdm.PageXMLTextLine(metadata=copy.deepcopy(line.metadata),
                                           coords=overlap_coords,
                                           baseline=overlap_baseline,
                                           text=overlap_text)
        if debug > 0:
            print("OVERLAP LINE:", overlap_line.coords.left, overlap_line.coords.right, overlap_line.text)
    if len(remaining_text) == 0:
        remaining_line = None
    else:
        remaining_points = [point for point in points if point[0] > tr.coords.right]
        remaining_bases = [point for point in bases if point[0] > tr.coords.right]
        remaining_points += [(remaining_left, overlap_points[-1][1])]
        remaining_bases += [(remaining_left, overlap_bases[-1][1])]
        # print("REMAINING:", points)
        remaining_coords = pdm.Coords(remaining_points)
        remaining_baseline = pdm.Baseline(remaining_bases)
        remaining_line = pdm.PageXMLTextLine(metadata=copy.deepcopy(line.metadata),
                                             coords=remaining_coords,
                                             baseline=remaining_baseline,
                                             text=remaining_text)
        if debug > 0:
            print("REMAINING LINE:", remaining_line.coords.left, remaining_line.coords.right, remaining_line.text)
    return overlap_line, remaining_line


def make_dummy_line(left: int, right: int, top: int, bottom: int,
                    metadata: Dict[str, any]) -> pdm.PageXMLTextLine:
    dummy_points = [(left, top), (left, bottom), (right, top), (right, bottom)]
    dummy_coords = pdm.Coords(dummy_points)
    return pdm.PageXMLTextLine(metadata=copy.deepcopy(metadata), coords=dummy_coords, text=None)


def make_dummy_column(left: int, right: int, top: int, bottom: int,
                      metadata: Dict[str, any]) -> pdm.PageXMLColumn:
    dummy_line = make_dummy_line(left, right, top, bottom, metadata)
    dummy_coords = pdm.parse_derived_coords([dummy_line])
    return pdm.PageXMLColumn(metadata=metadata, coords=dummy_coords, lines=[dummy_line])


def check_missing_columns(columns: List[Tuple[pdm.PageXMLColumn, str]],
                          metadata: Dict[str, any],
                          debug: int = 0) -> List[Tuple[pdm.PageXMLColumn, str]]:
    col_order = ["main_term", "sub_lemma", "date_locator", "page_locator"] * 2
    if debug > 0:
        print('check_missing_column - CHECKING FOR MISSING COLUMNS')
        print('\tnum columns:', len(columns))
    if len(columns) < len(col_order):
        col_order_copy = copy.copy(col_order)
        for ci, col_info in enumerate(columns):
            col, col_type = col_info
            col_order_copy.remove(col_type)
        if debug > 0:
            print('check_missing_column - MISSING COLUMNS:', col_order_copy)
        for ci, col_type in enumerate(col_order):
            if debug > 0:
                print('check_missing_column - column index:', ci, '\tnumber of columns:', len(columns))
            if ci >= len(columns):
                # missing columns are at the last of the expected columns
                missing_type = col_type
                curr_col = columns[ci - 1][0]
                missing_left = curr_col.coords.right + 20
                # TO DO: determine width by missing column type
                missing_right = missing_left + 120
                missing_col = make_dummy_column(missing_left, missing_right, 500, 550, metadata)
                columns += [(missing_col, missing_type)]
            elif columns[ci][1] == col_type:
                # The ci column has the expected type
                continue
            else:
                # The missing column comes before the current column
                missing_type = col_type
                next_col = columns[ci][0]
                missing_right = next_col.coords.left - 20
                if ci == 0:
                    # main_term column is missing
                    # main_term column is around 200 pixels
                    missing_left = missing_right - 200
                else:
                    curr_col = columns[ci-1][0]
                    missing_left = curr_col.coords.right + 20
                missing_col = make_dummy_column(missing_left, missing_right, 500, 550, metadata)
                columns = columns[:ci] + [(missing_col, missing_type)] + columns[ci:]
    if len(columns) == len(col_order):
        for ci, col_info in enumerate(columns):
            col, col_type = col_info
            if col_order[ci] != col_type:
                raise ValueError(f'Columns out of order: {[col[1] for col in columns]}')
        return columns
    elif len(columns) > len(col_order):
        raise ValueError(f'Too many columns: {[col[1] for col in columns]}')
    else:
        raise ValueError(f'Not enough columns: {[col[1] for col in columns]}')


def split_double_col_lines(line_types, config, debug: int = 0):
    cols = []
    if debug > 0:
        print("split_double_col_lines - SPLITTING DOUBLE COL LINES")
    # lines = [line for line_type in line_types for line in line_types[line_type] if line.text]
    # char_width = sum([line.coords.w for line in lines]) / sum([len(line.text) for line in lines])
    for line_type in line_types:
        if line_type in {"header", "double_col", "unknown", "finis_lines", "title", "empty"}:
            continue
        elif len(line_types[line_type]) == 0:
            print(f"split_double_col_lines - no lines for line_type {line_type}")
        try:
            coords = pdm.parse_derived_coords(line_types[line_type])
        except IndexError:
            print(f'split_double_col_lines - ERROR GENERATING DERIVED COORDS FROM THE '
                  f'FOLLOWING {line_type} LINES:')
            for line in line_types[line_type]:
                print(f'{line_type} line:', line.coords)
            raise
        temp_tr = make_line_type_text_region(line_types[line_type], line_type=line_type)
        columns = column_parser.split_lines_on_column_gaps(temp_tr, config, overlap_threshold=0.1)
        if debug > 0:
            print("split_double_col_lines - line_type:", line_type, "temp_tr:", temp_tr.id)
            # print("\tnum cols:", len(columns), "temp_extra:", temp_extra.id if temp_extra else None)
            print("\tnum cols:", len(columns))
        for col in columns:
            col.add_type(line_type)
            if debug > 0:
                print("split_double_col_lines - ADDING COL with type\t", line_type, col.coords.left, col.coords.right)
            cols.append((col, line_type))
        # if temp_extra:
        #     if debug > 0:
        #         print("ADDING EXTRA COL\t", line_type, temp_extra.coords.left, temp_extra.coords.right)
        #         for line in temp_extra.lines:
        #             print("\t\t", line.coords.left, line.coords.right, line.text)
        #     cols.append((temp_extra, line_type))
    cols.sort(key=lambda x: x[0].coords.left)
    if debug > 0:
        print("split_double_col_lines - cols:\n", [col[1] for col in cols])
    if debug > 0:
        print(f"make_index_page_text_regions - checking missing columns with cols[0][0].metadata:")
        print(f"\t{cols[0][0].metadata}\n\n")
    cols = check_missing_columns(cols, cols[0][0].metadata, debug=debug)
    for line in line_types["double_col"]:
        if debug > 0:
            print("split_double_col_lines - Double column line:", line.coords.left, line.coords.right, line.text)
        overlapping_cols = []
        for col, col_type in cols:
            if debug > 0:
                print(f"split_double_col_lines - col_type: {col_type}")
                print("\t", col.stats)
            nearest_col_line = None
            nearest_col_line_dist = 100000
            for col_line in col.get_lines():
                dist = pdm.vertical_distance(line, col_line)
                if dist < nearest_col_line_dist:
                    nearest_col_line_dist = dist
                    nearest_col_line = col_line
            left = max(line.coords.left, nearest_col_line.coords.left)
            right = min(line.coords.right, nearest_col_line.coords.right)
            if right - left <= 0:
                # no overlap, skip
                continue
            if debug > 0:
                print(f"double_col line.left: {line.coords.left}\tmax left: {left}"
                      f"\tline.right: {line.coords.right}\tmin right: {right}")
                print(f"nearest_col_line.left: {nearest_col_line.coords.left}\tmax left: {left}"
                      f"\tnearest_col_line.right: {nearest_col_line.coords.right}\tmin right: {right}")
            overlapping_cols.append((col, col_type))
        if debug > 0:
            print("split_double_col_lines - Overlapping trs:")
            for col, col_type in overlapping_cols:
                print("\t", col_type, col.id)
        # print("START:", points)
        remaining_line = line
        for col, col_type in overlapping_cols[:-1]:
            if debug > 0:
                print("split_double_col_lines - EXTRACTING FROM REMAINING LINE:", remaining_line.text)
            overlap_line, remaining_line = extract_overlapping_text(remaining_line, col)
            if overlap_line:
                if debug > 0:
                    print(f"split_double_col_lines - Adding overlapping line to {col_type}:", overlap_line.text)
                    print(f"\tbaseline: {overlap_line.baseline.points}")
                    if remaining_line is not None:
                        print(f"split_double_col_lines - Remaining line: "
                              f"{remaining_line.coords.left}-{remaining_line.coords.right}"
                              f"\t{remaining_line.text}")
                        print(f"\tbaseline: {remaining_line.baseline.points}")
                line_types[col_type].append(overlap_line)
            text = remaining_line.text if remaining_line else ''
            if len(text) == 0:
                break
            continue
        # print("TEXT:", text)
        if remaining_line and len(remaining_line.text) > 0:
            tr, col_type = overlapping_cols[-1]
            if debug > 0:
                print(f"split_double_col_lines - Adding remaining line to {col_type}:", remaining_line.text)
                print(f"\tbaseline: {remaining_line.baseline.points}")
            line_types[col_type].append(remaining_line)
        continue


def check_main_sub_lemma_overlap(line_types: Dict[str, List[pdm.PageXMLTextLine]],
                                 config: Dict[str, any]):
    print("CHECKING MAIN AND SUB OVERLAP")
    main_tr = make_line_type_text_region(line_types["main_term"], line_type="main_term")
    main_cols, main_extra = column_parser.split_lines_on_column_gaps(main_tr, config)
    print("MAIN COLS:", len(main_cols), "EXTRA:", main_extra is not None)
    for main_col in main_cols:
        print("\tCOL", main_col.coords.left, main_col.coords.right)
    if main_extra:
        print("\tEXTRA", main_extra.coords.left, main_extra.coords.right)
        for line in main_extra.get_lines():
            print(line.coords.left, line.coords.right, line.text)
    sub_tr = make_line_type_text_region(line_types["sub_lemma"], line_type="sub_lemma")
    sub_cols, sub_extra = column_parser.split_lines_on_column_gaps(sub_tr, config)
    print("SUB COLS:", len(sub_cols), "EXTRA:", sub_extra is not None)
    for sub_col in sub_cols:
        print("\tCOL", sub_col.coords.left, sub_col.coords.right)
    if sub_extra:
        print("\tCOL", sub_extra.coords.left, sub_extra.coords.right)
    # check if sub overlaps with main
    for main_col, sub_col in zip(main_cols, sub_cols):
        print(main_col.coords.left, main_col.coords.right, sub_col.coords.left, sub_col.coords.right)
        print(pdm.get_horizontal_overlap(main_col.coords, sub_col.coords))


def move_unknowns_from_page(line_types: Dict[str, List[pdm.PageXMLTextLine]],
                            config: Dict[str, any], debug: int = 0):
    if debug > 0:
        print("move_unknowns_from_page - MOVING UNKNOWNS FROM PAGE")
    all_cols = []
    # main_coords = pdm.parse_derived_coords(line_types["main_term"])
    # main_tr = pdm.PageXMLTextRegion(coords=main_coords, lines=line_types["main_term"])
    # main_cols, main_extra = column_parser.split_lines_on_column_gaps(main_tr, config)
    # for col in main_cols:
    #     col.add_type('main_term')
    #     all_cols.append(col)
    # if main_extra:
    #     main_extra.add_type('main_term')
    #     all_cols.append(main_extra)
    sub_tr = make_line_type_text_region(line_types["sub_lemma"], line_type="sub_lemma")
    sub_cols = column_parser.split_lines_on_column_gaps(sub_tr, config)
    for col in sub_cols:
        col.add_type('sub_lemma')
        # print('\tMOVING\tSUB_LEMMA COL:', col.coords.left, col.coords.right)
        all_cols.append(col)
    # if sub_extra:
    #     sub_extra.add_type('sub_lemma')
    # print('\tMOVING\tSUB_LEMMA EXTRA:', sub_extra.coords.left, sub_extra.coords.right)
    #     all_cols.append(sub_extra)
    date_tr = make_line_type_text_region(line_types["date_locator"], line_type="date_locator")
    date_cols = column_parser.split_lines_on_column_gaps(date_tr, config)
    for col in date_cols:
        col.add_type('date_locator')
        all_cols.append(col)
    # if date_extra:
    #     date_extra.add_type('date_locator')
    #     all_cols.append(date_extra)
    page_tr = make_line_type_text_region(line_types["page_locator"], line_type="page_locator")
    page_cols = column_parser.split_lines_on_column_gaps(page_tr, config, debug=0)
    for col in page_cols:
        col.add_type('page_locator')
        # print("PAGE COL:", col.id)
        all_cols.append(col)
    # if page_extra:
    #     page_extra.add_type('page_locator')
    # print("PAGE EXTRA:", page_extra.id)
    #     all_cols.append(page_extra)
    all_cols = sorted(all_cols, key=lambda x: x.coords.left)
    if debug > 0:
        print("move_unknowns_from_page - columns are splitting lines on column gaps:")
        for ci, col in enumerate(all_cols):
            print("\t", ci, "of", len(all_cols), col.id, col.type)
    first_col = all_cols[0]
    if 'sub_lemma' not in first_col.type:
        if debug > 0:
            print("move_unknowns_from_page - FIRST COLUMN IS NOT SUB_LEMMA:", first_col.type)
        # remove the first column from the list
        # all_cols = all_cols[1:]
        if 'page_locator' in first_col.type:
            line_types["unknown"] = first_col.get_lines()
            for line in first_col.get_lines():
                line_types["page_locator"].remove(line)
                if debug > 0:
                    print("\tMOVING LINE FROM PAGE TO UNKNOWN:", line.coords.left, line.coords.right, line.text)


def move_unknowns_to_correct_column(line_types: Dict[str, List[pdm.PageXMLTextLine]],
                                    config: Dict[str, any], debug: int = 0):
    cols = defaultdict(list)
    for line_type in ['main_term', 'sub_lemma', 'date_locator', 'page_locator']:
        type_tr = make_line_type_text_region(line_types[line_type], line_type=line_type)
        type_cols = column_parser.split_lines_on_column_gaps(type_tr, config)
        cols[line_type] = type_cols
        # if type_extra:
        #     cols[line_type].append(type_extra)
    unknown_lines = line_types["unknown"]
    for line in unknown_lines:
        found_col = False
        for line_type in cols:
            for col in cols[line_type]:
                if pdm.is_horizontally_overlapping(line, col):
                    if debug > 0:
                        print("move_unknowns_to_correct_column - MOVING LINE FROM UNKNOWN TO", line_type.upper())
                    line_types[line_type].append(line)
                    line_types["unknown"].remove(line)
                    found_col = True
                break
        if found_col is False:
            if debug > 0:
                print("move_unknowns_to_correct_column - NO CORRECT COLUMN FOUND FOR UNKNOWN:",
                      line.coords.left, line.coords.right, line.text)


def check_line_parent_metadata(lines: List[pdm.PageXMLTextLine]) -> None:
    for line in lines:
        if line.parent is None:
            raise AttributeError(f"no parent for line", line.id)
        elif len(line.parent.metadata.keys()) == 0:
            raise AttributeError(f"empty metadata for parent {line.parent.id} of line {line.id}")
        elif 'scan_id' not in line.parent.metadata:
            raise KeyError(f"no 'scan_id' in metadata of parent {line.parent.id} of line {line.id}")


def classify_and_filter_lines(page: pdm.PageXMLPage,
                              config: Dict[str, any], last_page: bool = False,
                              debug: int = 0) -> Dict[str, List[pdm.PageXMLTextLine]]:
    line_types = classify_lines(page, last_page=last_page, debug=debug)
    if debug > 0:
        print(f"classify_and_filter_lines - PAGE HAS {len(page.get_lines())} LINES")
        print(f"classify_and_filter_lines - LINE_TYPES HAS {len([l for t in line_types for l in line_types[t]])} LINES")
    filter_header_lines(line_types, debug=debug)
    # print_line_type_stats(line_types, debug=3)
    config = copy.deepcopy(config)
    config["column_gap"]["gap_pixel_freq_ratio"] = 0.25
    check_line_parent_metadata([line for line_type in line_types for line in line_types[line_type]])
    move_double_col_lines(line_types, config, debug=debug)
    check_line_parent_metadata([line for line_type in line_types for line in line_types[line_type]])
    if debug > 0:
        print("classify_and_filter_lines - line stats after move_double_col_lines()")
        print_line_type_stats(line_types, debug=debug)
    filter_target_type_lines("sub_lemma", line_types, config, overlap_threshold=0.7, debug=debug)
    # print(f"AFTER FILTERING TARGET LINE TYPES - PAGE HAS {page.stats['words']} WORDS, {page.stats['lines']} LINES")
    # check for lines incorrectly moved to page col
    move_unknowns_from_page(line_types, config, debug=debug)
    # First, filter page and date, so main_term has only overlap with
    # sub_lemma left
    config["column_gap"]["gap_pixel_freq_ratio"] = 0.75
    filter_target_type_lines("date_locator", line_types, config, debug=debug)
    filter_target_type_lines("page_locator", line_types, config, debug=debug)
    move_double_col_lines(line_types, config, debug=debug)
    if debug > 0:
        print("\nclassify_and_filter_lines - calling filter_target_type_lines with 'sub_lemma' "
              "as target for the second time\n")
    # print_line_type_stats(line_types, debug=3)
    filter_target_type_lines("sub_lemma", line_types, config, overlap_threshold=0.5, debug=debug)
    # Second, check if there are merged lines overlapping main_term and sub_lemma
    # check_main_sub_lemma_overlap(line_types, config)
    # for line_type in line_types:
    #     print(line_type, len(line_types[line_type]))
    #     for line in sorted(line_types[line_type], key=lambda x: x.coords.y):
    #         print(line_type, line.coords.bottom, line.coords.left, line.coords.right, line.text)
    if debug > 0:
        print_line_type_stats(line_types, debug=debug)
    split_double_col_lines(line_types, config, debug=debug)
    # print("after filtering:")
    # for line_type in line_types:
    #     print(line_type, len(line_types[line_type]))
    move_unknowns_to_correct_column(line_types, config, debug=debug)
    if debug > 0:
        print_line_type_stats(line_types, debug=debug)
    return line_types


def make_index_page_text_regions(page: pdm.PageXMLPage,
                                 line_types: Dict[str, List[pdm.PageXMLTextLine]],
                                 config: Dict[str, any],
                                 debug: int = 0) -> Tuple[List[pdm.PageXMLColumn], List[pdm.PageXMLTextRegion]]:
    extra = []
    index_columns = []
    # Add test: count lines and words in new columns to make sure
    # All content of page is copied to new columns
    lines, words = 0, 0
    # print('PAGE STATS START:', page.stats)
    for line_type in line_types:
        if line_type in {"double_col", "unknown"}:
            if debug > 0:
                print(f'make_index_page_text_regions - skipping line with type {line_type}:')
                for line in line_types[line_type]:
                    print(f"\t#{line.text}#")
            continue
        if line_type in {"header", 'title', "empty"}:
            if len(line_types[line_type]) == 0:
                continue
            tr = make_line_type_text_region(line_types[line_type], line_type=line_type)
            tr.lines.sort(key=lambda x: x.coords.y)
            tr.set_derived_id(page.id)
            tr.add_type(f"index_{line_type}")
            extra.append(tr)
            lines += tr.stats["lines"]
            words += tr.stats["words"]
            if debug > 0:
                print(f"make_index_page_text_regions - {line_type.upper()} TEXT_REGION HAS "
                      f"{tr.stats['words']} WORDS AND {tr.stats['lines']} LINES")
                for line in tr.lines:
                    print(f"\t{line_type.upper()} LINE", line.coords.x, line.coords.y, line.text)
        elif line_type == "finis_lines":
            if len(line_types[line_type]) == 0:
                continue
            tr = make_line_type_text_region(line_types[line_type], line_type=line_type)
            tr.add_type("index_end")
            extra.append(tr)
            lines += tr.stats["lines"]
            words += tr.stats["words"]
            if debug > 0:
                print(f"make_index_page_text_regions - FINIS TEXT_REGION HAS {tr.stats['words']} WORDS "
                      f"AND {tr.stats['lines']} LINES")
                for line in tr.lines:
                    print("\tFINIS LINE", line.coords.x, line.coords.y, line.text)
        else:
            if len(line_types[line_type]) == 0:
                continue
            temp_tr = make_line_type_text_region(line_types[line_type], line_type=line_type)
            if debug > 0:
                print("\nmake_index_page_text_regions - splitting lines into columns for type:", line_type)
            columns = column_parser.split_lines_on_column_gaps(temp_tr, config,
                                                               overlap_threshold=0.1,
                                                               debug=0)
            if debug > 0:
                print(f"make_index_page_text_regions - splitting returned {len(columns)} columns\n")
            if len(columns) > 2:
                if debug > 0:
                    print(f"make_index_page_text_regions - more than two columns: {len(columns)}")
                    for column in columns:
                        print("\tcolumn:", line_type, column.coords.box, column.stats)
                        if len(columns) > 2:
                            print("\tcol:", line_type, column.coords.left, column.coords.right, column.stats)
                            for line in column.lines:
                                print("\t\t", line.coords.left, line.coords.right, line.text)
                extra += columns[2:]
                columns = columns[:2]
                # if temp_extra is not None:
                #     if debug > 0:
                #         print("extra:", line_type, temp_extra.coords.box, temp_extra.stats)
                #         for line in temp_extra.lines:
                #             print("\t", line.coords.left, line.coords.right, line.text)
                #     extra.append(temp_extra)
                # raise ValueError(f"More columns of type {line_type} than expected")
            # if temp_extra is not None:
            #     columns += [temp_extra]
            for column in columns:
                if debug > 0:
                    print("make_index_page_text_regions - column with line_type", line_type, column.coords.box)
                    print(f"\t{column.id}")
                    for line in sorted(column.get_lines(), key=lambda x: x.coords.y):
                        print(f"\t{line_type.upper()} LINE {mbs(line)}\t{line.text}")
                column.set_derived_id(page.id)
                for tr in column.text_regions:
                    tr.lines.sort(key=lambda x: x.coords.y)
                column.text_regions.sort(key=lambda x: x.coords.y)
                column.add_type("index_column")
                column.add_type(f"{line_type}_column")
                lines += column.stats["lines"]
                words += column.stats["words"]
                if debug > 0:
                    print(f"\tCOLUMN HAS {column.stats['words']} WORDS AND {column.stats['lines']} LINES", column.type)
                    print("\t", column.stats)
                index_columns.append(column)
            # if temp_extra is not None:
            #     if debug > 0:
            #         print(temp_tr.stats)
            #         print("col_type:", line_type, "columns:", len(columns))
            #         for column in columns:
            #             print(column.id, column.coords.box)
            #         print("temp_extra:", temp_extra.stats)
            #         for line in temp_extra.lines:
            #             print(f"\t{line_type}\t{line.coords.x: >6}{line.coords.y: >6}{line.coords.w: >6}"
            #             "\t{line.text}")
            #     pass
        # print(f'PAGE STATS {line_type}:', page.stats)

    # if there are remaining unknown lines, add
    # them as a new extra text region
    if len(line_types["unknown"]) > 0:
        extra_tr = make_line_type_text_region(line_types["unknown"], line_type="unknown")
        extra_tr.set_derived_id(extra_tr.metadata['scan_id'])
        extra.append(extra_tr)
        lines += extra_tr.stats["lines"]
        words += extra_tr.stats["words"]
    if abs(words - page.stats["words"]) > 5 and len(line_types["double_col"]) > 0:
        print(f"make_index_page_text_regions - page {page.id} has {page.stats['words']} words, "
              f"while columns have {words} words")
        print(f"make_index_page_text_regions - page {page.id} has {page.stats['lines']} lines, "
              f"while columns have {lines} lines")
        raise ValueError("Not all content from page is copied to index columns and header")
    if abs(words - page.stats["words"]) > 2 and len(line_types["double_col"]) == 0:
        print(f"make_index_page_text_regions - page {page.id} has {page.stats['words']} words, "
              f"while columns have {words} words")
        print(f"make_index_page_text_regions - page {page.id} has {page.stats['lines']} lines, "
              f"while columns have {lines} lines")
        raise ValueError("Not all content from page is copied to index columns and header")
    index_columns.sort(key=lambda x: x.coords.x)
    col_types = [col.type[-1].replace('_column', '') for col in index_columns]
    typed_columns = [(col, col_type) for col, col_type in zip(index_columns, col_types)]
    if debug > 0:
        print(f"make_index_page_text_regions - checking missing columns with index_columns[0].metadata:")
        print(f"\t{index_columns[0].metadata}\n\n")
    typed_columns = check_missing_columns(typed_columns, index_columns[0].metadata, debug=debug)
    for col, col_type in typed_columns:
        col.add_type(f"{col_type}_column")
    index_columns = [col for col, _ in typed_columns]
    return index_columns, extra


def get_col_type_order(columns: List[pdm.PageXMLColumn], debug: int = 0) -> List[str]:
    if len(columns) % 4 == 0:
        return ["main_term", "sub_lemma", "date_locator", "page_locator"]
    elif len(columns) % 3 == 0:
        return ["main_term", "sub_lemma", "page_locator"]
    else:
        if debug > 0:
            for column in columns:
                print(column.type, column.coords.x)
        raise ValueError(f"Unexpected number of columns: {len(columns)}")


def group_index_columns(columns: List[pdm.PageXMLColumn],
                        debug: int = 0) -> List[List[pdm.PageXMLColumn]]:
    column_groups = []
    columns.sort(key=lambda col: col.coords.x)
    col_type_order = get_col_type_order(columns, debug=debug)
    group_size = len(col_type_order)
    if debug > 0:
        print(f"group_index_columns - col_type_order: {col_type_order}")
        print(f"group_index_columns - group_size: {group_size}")
        print(f"group_index_columns - num columns: {len(columns)}")
    for index in range(0, group_size*2, group_size):
        group = columns[index:index+group_size]
        if debug > 0:
            print(f"group_index_columns - index: {index}")
            print(f"group_index_columns - index+group_size: {index+group_size}")
            print(f"group_index_columns - group columns: {group}")
        for ci, column in enumerate(group):
            expected_type = f"{col_type_order[ci]}_column"
            if column.has_type(expected_type) is False:
                col_types = f"[{', '.join(column.type)}]"
                raise TypeError(f"column at index {ci} should have type {expected_type} but has types: {col_types}")
        column_groups.append(group)
    return column_groups


class Sublemma:

    def __init__(self, main_term: str, sub_lemma: str, date_locator: str, page_locator: str,
                 type_lines: Dict[str, List[pdm.PageXMLTextLine]] = None):
        self.main_term = main_term
        self.sub_lemma = sub_lemma
        self.date_locator = date_locator
        self.page_locator = page_locator
        day, month = parse_date_locator(date_locator)
        self.date_locator_day = day
        self.date_locator_month = month
        self.has_preferred_term: bool = False
        self.lines = type_lines if type_lines is not None else init_sub_lemma_lines()
        lines = [line for line_type in type_lines for line in type_lines[line_type]]
        if len(lines) > 0:
            try:
                self.coords = pdm.parse_derived_coords(lines)
            except IndexError:
                for line_type in type_lines:
                    for line in type_lines[line_type]:
                        print(line.coords.box)
                raise
        else:
            print(f'empty sublemma, main_term: {main_term}\n\tsub_lemma: {sub_lemma}')
        scan_ids = list(set([line.metadata["scan_id"] for line in lines]))
        page_ids = list(set([line.metadata["scan_id"] for line in lines]))
        scan_id_parts = parse_scan_id(scan_ids[0]) if len(scan_ids) > 0 else None
        self.metadata = {
            "scan_id": scan_ids[0] if len(scan_ids) == 1 else scan_ids,
            "page_id": page_ids[0] if len(page_ids) == 1 else page_ids,
            "inventory_num": scan_id_parts["inventory_num"] if scan_id_parts else None
        }

    def __repr__(self):
        return f"Sublemma(main_term={self.main_term}, " \
               f"sub_lemma={self.sub_lemma}, " \
               f"date_locator={self.date_locator}, " \
               f"page_locator={self.page_locator})"


def init_sub_lemma_lines(line: pdm.PageXMLTextLine = None) -> Dict[str, List[pdm.PageXMLTextLine]]:
    return {
        "main_term": [],
        "sub_lemma": [],
        "date_locator": [],
        "page_locator": [line] if line is not None else [],
    }


def set_column_lines(column_group: List[pdm.PageXMLColumn] = None,
                     prev_lines: Dict[str, List[pdm.PageXMLTextLine]] = None) -> Dict[str, List[pdm.PageXMLTextLine]]:
    column_lines = {
        "main_term": prev_lines["main_term"] if prev_lines else [],
        "sub_lemma": prev_lines["sub_lemma"] if prev_lines else [],
        "date_locator": prev_lines["date_locator"] if prev_lines else [],
        "page_locator": prev_lines["page_locator"] if prev_lines else []
    }
    if column_group:
        col_type_order = get_col_type_order(column_group)
        for ci, column in enumerate(column_group):
            col_type = col_type_order[ci]
            column_lines[col_type] += column.get_lines()
    return column_lines


def get_sub_lemma_lines(boundary: Dict[str, int],
                        column_lines: Dict[str, List[pdm.PageXMLTextLine]],
                        remaining_lines: Dict[str, List[pdm.PageXMLTextLine]] = None,
                        threshold: float = 0.5,
                        debug: int = 0) -> Union[Sublemma, None]:
    sub_lemma_lines = init_sub_lemma_lines()
    if debug > 0:
        print('get_sub_lemma_lines - GETTING SUB_LEMMA LINES FOR BOUNDARY:', boundary)
    if remaining_lines:
        for col_type in remaining_lines:
            for remaining_line in remaining_lines[col_type]:
                sub_lemma_lines[col_type].append(remaining_line)
    for col_type in column_lines:
        for line in column_lines[col_type]:
            # if debug > 0:
            #     print('\t', col_type, line.coords.top, line.coords.bottom, line.text)
            if line.coords.top > boundary['bottom']:
                if debug > 1:
                    print('\t', col_type, line.coords.top, line.coords.bottom, line.text)
                    print('\t\tbelow page_locator:', boundary['bottom'])
                    print()
                break
            if line.coords.bottom < boundary['top']:
                if debug > 1:
                    print('\t', col_type, line.coords.top, line.coords.bottom, line.text)
                    print('\t\tabove current sub lemma:', boundary['top'])
                    print()
                continue
            top = max(line.coords.top, boundary['top'])
            bottom = min(line.coords.bottom, boundary['bottom'])
            overlap = bottom - top
            if overlap <= 0:
                if debug > 1:
                    print('\t', col_type, line.coords.top, line.coords.bottom, line.text)
                    print('\t\tnegative overlap:', top, bottom)
                continue
            elif overlap / line.coords.height > threshold:
                if debug > 1:
                    print('\t', col_type, line.coords.top, line.coords.bottom, line.text)
                    print('\t\tadding to sub_lemma')
                if col_type == 'main_term':
                    # main_term lines are already merged per term,
                    # so there should be no more than one per sub_lemma
                    # if there are multiple main terms within range, the earlier
                    # main terms have no page reference but a reference
                    # to a preferred term ('Abbema -> Zie Hamburg')
                    sub_lemma_lines[col_type] = [line]
                    # prev_bottom = line.coords.top
                else:
                    sub_lemma_lines[col_type].append(line)
            else:
                if debug > 1:
                    print('\t\toverlap too small:', overlap, line.coords.height)
                pass
    sub_lemma = parse_sub_lemma_lines(sub_lemma_lines)
    return sub_lemma


def merge_lemma_text_lines(lines: List[pdm.PageXMLTextLine]):
    text = ""
    for line in lines:
        if line.text is None:
            continue
        if line.text == '':
            continue
        if line.text[-1] == '-':
            text += line.text[:-1]
        else:
            text += line.text + ' '
    return text.strip()


def parse_sub_lemma_lines(sub_lemma_lines: Dict[str, List[pdm.PageXMLTextLine]]) -> Union[None, Sublemma]:
    try:
        main_term = merge_lemma_text_lines(sub_lemma_lines["main_term"])
        sub_lemma_text = merge_lemma_text_lines(sub_lemma_lines["sub_lemma"])
        date_locator = merge_lemma_text_lines(sub_lemma_lines["date_locator"])
        page_locator = merge_lemma_text_lines(sub_lemma_lines["page_locator"])
    except IndexError:
        for line_type in sub_lemma_lines:
            for line in sub_lemma_lines[line_type]:
                print(line_type, line.coords.left, line.coords.right, line.text)
        raise
    if len([line for line_type in sub_lemma_lines for line in sub_lemma_lines[line_type]]) == 0:
        return None
    return Sublemma(main_term=main_term, sub_lemma=sub_lemma_text,
                    date_locator=date_locator, page_locator=page_locator,
                    type_lines=sub_lemma_lines)


def has_line(sub_lemma: Sublemma, line: pdm.PageXMLTextLine) -> bool:
    for col_type in sub_lemma.lines:
        if line in sub_lemma.lines[col_type]:
            return True
    return False


def parse_date_locator(date_locator: str) -> Tuple[Union[None, str], Union[None, str]]:
    day, month = None, None
    if m := re.search(day_month_pattern, date_locator):
        day = m.group(1)
        month = m.group(2)
    elif m := re.search(day_dito_pattern, date_locator):
        day = m.group(1)
        month = "dito"
    elif re.match("dito", date_locator):
        day = "dito"
        month = "dito"
    elif m := re.search(r"^(\w+) (\w+)[,.]?$", date_locator):
        day = m.group(1)
        month = m.group(2)
    return day, month


def check_date_locator(sub_lemma: Sublemma, sub_lemmas: List[Sublemma]) -> None:
    if sub_lemma.date_locator_month == "dito":
        if len(sub_lemmas) > 0 and sub_lemmas[-1].date_locator_month:
            sub_lemma.date_locator_month = sub_lemmas[-1].date_locator_month
    if sub_lemma.date_locator_day == "dito":
        if len(sub_lemmas) > 0 and sub_lemmas[-1].date_locator_day:
            sub_lemma.date_locator_day = sub_lemmas[-1].date_locator_day


def group_main_term_lines(lines: List[pdm.PageXMLTextLine], prev_main_term: str = None,
                          debug: int = 0) -> List[pdm.PageXMLTextLine]:
    grouped_lines = []
    main_term = ''
    line_group = []
    non_empty_lines = [line for line in lines if line.text is not None]
    if len(non_empty_lines) == 0:
        non_empty_lines = []
        for line in lines:
            if line.text is None and prev_main_term is not None:
                dummy_line = copy.deepcopy(line)
                dummy_line.text = prev_main_term
                non_empty_lines.append(dummy_line)
    if debug > 0:
        print(f"group_main_term_lines - num lines: {len(lines)}, non-empty: {len(non_empty_lines)}")
    lines = non_empty_lines
    for li, curr_line in enumerate(lines):
        if len(main_term) > 0 and main_term[-1] == '-':
            if curr_line.text[0].islower():
                main_term = main_term[:-1]
        main_term += curr_line.text
        line_group.append(curr_line)
        if debug > 0:
            print('group_main_term_lines - main_term:', main_term)
        if li < len(lines) - 1:
            next_line = lines[li+1]
            if debug > 0:
                print('\t', curr_line.coords.bottom, next_line.coords.top, curr_line.text)
            if next_line.coords.top > curr_line.coords.bottom + 10:
                main_term = ''
                grouped_lines.append(line_group)
                line_group = []
            elif abs(next_line.coords.left - curr_line.coords.left) < 10 and next_line.text[0].isupper():
                main_term = ''
                grouped_lines.append(line_group)
                line_group = []
            else:
                pass
    if len(line_group) > 0:
        grouped_lines.append(line_group)
    for li, line_group in enumerate(grouped_lines):
        grouped_line = merge_lines(line_group)
        if debug > 0:
            print('group_main_term_lines - GROUPED LINE:', grouped_line.text)
        grouped_lines[li] = grouped_line
    return grouped_lines


def merge_lines(lines: List[pdm.PageXMLTextLine]):
    coords = pdm.parse_derived_coords(lines)
    text = ''
    for li, curr_line in enumerate(lines):
        if len(text) > 0 and text[-1] == '-':
            if curr_line.text[0].islower():
                # remove hyphen
                text = text[:-1]
        text += curr_line.text
    return pdm.PageXMLTextLine(metadata=copy.deepcopy(lines[0].metadata),
                               coords=coords, text=text)


def get_lemma_boundaries(column_lines: Dict[str, List[pdm.PageXMLTextLine]],
                         debug: int = 0) -> List[Dict[str, int]]:
    boundaries = []
    if debug > 0:
        print(f"get_lemma_boundaries")
    for li, main_term in enumerate(column_lines['main_term']):
        main_term_top = main_term.coords.top
        main_term_bottom = 10000
        if len(column_lines['main_term']) > li+1:
            next_main_term = column_lines['main_term'][li+1]
            main_term_bottom = next_main_term.coords.top
        in_range_page_locs = []
        for pi, page_loc in enumerate(column_lines['page_locator']):
            if page_loc.coords.bottom < main_term_top:
                continue
            elif page_loc.coords.top > main_term_bottom:
                break
            else:
                in_range_page_locs.append(page_loc)
        if len(in_range_page_locs) == 0:
            boundaries.append({'top': main_term_top, 'bottom': main_term_bottom})
            if debug > 0:
                print(f"get_lemma_boundaries - main_term", main_term.text)
                print('\tNO PAGE LOCATOR, ADDING BOUNDARY', boundaries[-1])
        else:
            boundary_top = main_term_top
            for page_loc in in_range_page_locs:
                boundaries.append({'top': boundary_top, 'bottom': page_loc.coords.bottom})
                if debug > 0:
                    print(f"get_lemma_boundaries - main_term", main_term.text)
                    print('\tPAGE LOCATOR, ADDING BOUNDARY', boundaries[-1])
                boundary_top = page_loc.coords.bottom
    return boundaries


def split_sub_lemmas(column_lines: Dict[str, List[pdm.PageXMLTextLine]],
                     remaining_lines: Dict[str, List[pdm.PageXMLTextLine]] = None,
                     prev_main_term: str = None,
                     debug: int = 0) -> Tuple[List[Sublemma], Dict[str, List[pdm.PageXMLTextLine]]]:
    sub_lemmas = []
    # for line_type in column_lines:
    #     column_lines[line_type] = [line for line in column_lines[line_type] if line.text is not None]
    # prev_bottom = 0
    if debug > 0:
        print(f"split_sub_lemmas - prev_main_term: #{prev_main_term}#")
        print(f"split_sub_lemmas - BEFORE GROUPING column_lines['main_term']:", len(column_lines['main_term']))
    main_term_lines = group_main_term_lines(column_lines['main_term'], prev_main_term, debug=debug)
    if debug > 0:
        print(f"split_sub_lemmas - AFTER GROUPING column_lines['main_term']:", len(column_lines['main_term']))
    column_lines['main_term'] = main_term_lines
    boundaries = get_lemma_boundaries(column_lines, debug=debug)
    if debug > 0:
        print(f"split_sub_lemmas - AFTER BOUNDARIES column_lines['main_term']:", len(column_lines['main_term']))
    if debug > 0:
        print(f"split_sub_lemmas - column_lines['main_term']:", len(column_lines['main_term']))
        print(f"split_sub_lemmas - main_term_lines:", len(main_term_lines))
        print(f"split_sub_lemmas - boundaries:", boundaries)
    for boundary in boundaries:
        # for line in column_lines["page_locator"]:
        if remaining_lines:
            sub_lemma = get_sub_lemma_lines(boundary, column_lines, remaining_lines=remaining_lines,
                                            debug=debug)
            remaining_lines = None
        else:
            sub_lemma = get_sub_lemma_lines(boundary, column_lines, debug=debug)
        if sub_lemma is None:
            continue
        if sub_lemma.main_term:
            prev_main_term = sub_lemma.main_term
        elif prev_main_term:
            # copy repeated main term from previous lemma
            sub_lemma.main_term = prev_main_term
        check_date_locator(sub_lemma, sub_lemmas)
        if debug > 0:
            print('ADDING SUBLEMMA:', sub_lemma)
        sub_lemmas.append(sub_lemma)
        # prev_bottom = sub_lemma.lines["page_locator"][-1].coords.bottom
    remaining_lines = set_column_lines()
    if 'Zie ' not in sub_lemmas[-1].sub_lemma:
        unfinished_lemma = sub_lemmas.pop(-1)
        for col_type in column_lines:
            for line in column_lines[col_type]:
                if line.coords.bottom < unfinished_lemma.coords.top:
                    continue
                elif has_line(unfinished_lemma, line):
                    remaining_lines[col_type].append(line)
                else:
                    remaining_lines[col_type].append(line)
    return sub_lemmas, remaining_lines
