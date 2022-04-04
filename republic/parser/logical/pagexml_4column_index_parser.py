import copy
from typing import Dict, List, Tuple, Union
from collections import defaultdict
import re

import republic.parser.pagexml.republic_pagexml_parser as page_parser
import republic.model.physical_document_model as pdm


day_month_pattern = r"^(\d+) (Jan|Feb|Maa|Apr|Mey|Jun|Jul|Aug|Sep|Oct|Okt|Nov|Dec)\S{,3}$"
month_pattern = r"^(Jan|Feb|Maa|Apr|Mey|Jun|Jul|Aug|Sep|Oct|Okt|Nov|Dec)\S{,3}$"
day_month_dito_pattern = r"^(\d+) (dito|ditto|Jan|Feb|Maa|Apr|Mey|Jun|Jul|Aug|Sep|Oct|Okt|Nov|Dec)\S{,3}$"
day_dito_pattern = r"^(\d+) (dito|ditto)\S{,2}$"


def move_lines(line_types: Dict[str, List[pdm.PageXMLTextLine]], target_type: str,
               target_docs: pdm.List[pdm.PageXMLTextRegion], debug: bool = False) -> None:
    print("MOVING LINES")
    for target_doc in target_docs:
        print(target_type, target_doc.coords.left, target_doc.coords.right)
    for line_type in line_types:
        if line_type == target_type or line_type == "header" or line_type == "double_col":
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
                if pdm.is_horizontally_overlapping(line, target_doc): # and line.coords.top > target_doc.coords.top:
                    # pdm.is_vertically_overlapping(line, target_doc):
                    if debug:
                        print(f"{li} moving line from {line_type} to {target_type}: {line.coords.x: >6}{line.coords.y: >6}\t{line.text}")
                    line_types[target_type].append(line)
                    if line not in line_types[line_type]:
                        print("trying to remove line", li, line.text)
                    line_types[line_type].remove(line)
                    has_moved = True
                if has_moved:
                    break
            # if has_moved is False and line_type == "main_term" and target_type == "sub_lemma":
            #     print(f"{li} keeping line in {line_type}: {line.coords.x: >6}{line.coords.y: >6}\t{line.text}")


def filter_header_lines(line_types: Dict[str, List[pdm.PageXMLTextLine]], debug: bool = False) -> None:
    # Step 1a: make header box
    coords = pdm.parse_derived_coords(line_types["header"])
    header = pdm.PageXMLTextRegion("header", coords=coords)
    # print("HEADER BOTTOM:", header.coords.bottom)
    # Step 1b: move lines from other to header box
    for line_type in line_types:
        if line_type == "header":
            continue
        lines = sorted(line_types[line_type], key=lambda x: x.coords.y)
        for line in lines:
            # print(line_type, line.coords.x, line.coords.y, line.coords.bottom, line.text)
            if pdm.is_vertically_overlapping(line, header) or line.coords.bottom < header.coords.bottom:
                line_types["header"].append(line)
                line_types[line_type].remove(line)
                if debug:
                    print(f"moving line from {line_type} to header: {line.coords.x: >6}{line.coords.y: >6}\t{line.text}")


def filter_target_type_lines(page_id: str, target_type: str,
                             line_types: Dict[str, List[pdm.PageXMLTextLine]],
                             config: Dict[str, any], overlap_threshold: float = 0.1,
                             debug: bool = False) -> None:
    # print("FILTERING FOR TARGET", target_type)
    try:
        temp_coords = pdm.parse_derived_coords(line_types[target_type])
    except IndexError as err:
        config = copy.deepcopy(config)
        config["column_gap"]["gap_pixel_freq_ratio"] = 0.25
        temp_coords = pdm.parse_derived_coords(line_types[target_type])

    temp_tr = pdm.PageXMLTextRegion(coords=temp_coords, lines=line_types[target_type])
    temp_tr.set_derived_id(page_id)
    # print("temp tr:", temp_tr.id, temp_tr.stats)
    # Step 2a: split sub_lemma lines in columns
    columns, extra_tr = page_parser.split_lines_on_column_gaps(temp_tr, config,
                                                               overlap_threshold=overlap_threshold)
    # print("filter split columns:", len(columns))
    if extra_tr is not None:
        if len(columns) == 2:
            for line in extra_tr.lines:
                print("extra as third column", line.coords.left, line.coords.right, line.text)
        else:
            columns.append(extra_tr)
    # for column in columns:
    #     print(f"\t{target_type}:", column.id, column.stats)
    # Step 2b: move lines from main_term to sub_lemma boxes
    move_lines(line_types, target_type, columns, debug=debug)


def classify_lines(page_doc: pdm.PageXMLTextRegion, debug: bool = False) -> Dict[str, List[pdm.PageXMLTextLine]]:
    trs = page_doc.text_regions
    if hasattr(page_doc, "columns"):
        trs += page_doc.columns
    if hasattr(page_doc, "extra"):
        trs += page_doc.extra
    lines = [line for tr_outer in trs for tr_inner in tr_outer.text_regions for line in tr_inner.lines]
    lines += [line for tr in trs for line in tr.lines if line not in lines]
    lines += [line for line in page_doc.lines if line not in lines]
    print(f"classifying {len(set(lines))} lines")
    line_types = {
        "header": [],
        "main_term": [],
        "sub_lemma": [],
        "date_locator": [],
        "page_locator": [],
        "double_col": [],
        "unknown": []
    }
    for line in set(lines):
        if line.text is None:
            # print("SKIPPING NONE-TEXT LINE")
            continue
        if re.match(r"^[A-Z]\.$", line.text) and line.coords.y < 450:
            line_types["header"].append(line)
        elif re.match(r"^(datums|pag)[,\.]$", line.text, re.IGNORECASE):
            line_types["header"].append(line)
        elif m := re.search(day_month_dito_pattern, line.text):
            line_types["date_locator"].append(line)
        elif m := re.search(r"^dito", line.text):
            line_types["date_locator"].append(line)
        elif m := re.search(r"^\d+$", line.text):
            line_types["page_locator"].append(line)
        elif len(line.text) > 25:
            line_types["double_col"].append(line)
        elif len(line.text) >= 15 or re.match("Item", line.text):
            line_types["sub_lemma"].append(line)
        else:
            line_types["main_term"].append(line)
    if debug:
        for line_type in line_types:
            print(line_type, len(line_types[line_type]))
            for line in sorted(line_types[line_type], key=lambda x: x.coords.y):
                print(line_type, line.coords.left, line.coords.right, line.coords.bottom, line.text)
    return line_types


def split_double_col_lines(line_types, config):
    trs = []
    print("SPLITTING DOUBLE COL LINES")
    for line_type in line_types:
        if line_type in {"header", "double_col", "unknown"}:
            continue
        coords = pdm.parse_derived_coords(line_types[line_type])
        temp_tr = pdm.PageXMLTextRegion(coords=coords, lines=line_types[line_type])
        temp_tr.set_derived_id("temp_tr")
        # print(line_type, "temp_tr:", temp_tr.id)
        columns, temp_extra = page_parser.split_lines_on_column_gaps(temp_tr, config, overlap_threshold=0.1)
        # print("\tnum cols:", len(columns), "temp_extra:", temp_extra.id if temp_extra else None)
        for col in columns:
            # print("ADDING COL\t", line_type, col.coords.left, col.coords.right)
            trs.append((col, line_type))
        if temp_extra:
            # print("ADDING EXTRA COL\t", line_type, temp_extra.coords.left, temp_extra.coords.right)
            # for line in temp_extra.lines:
            #     print("\t\t", line.coords.left, line.coords.right, line.text)
            trs.append((temp_extra, line_type))
    trs.sort(key=lambda x: x[0].coords.left)
    for line in line_types["double_col"]:
        print("Double column line:", line.coords.left, line.coords.right, line.text)
        overlapping_trs = []
        for tr, col_type in trs:
            left = max(line.coords.left, tr.coords.left)
            right = min(line.coords.right, tr.coords.right)
            if right - left <= 0:
                # no overlap, skip
                continue
            # print(line.coords.left, left, line.coords.right, right)
            # print(tr.coords.left, left, tr.coords.right, right)
            overlapping_trs.append((tr, col_type))
        print("Overlapping trs:")
        for tr, col_type in overlapping_trs:
            print("\t", col_type, tr.id)
        num_chars = len(line.text)
        char_width = line.coords.width / num_chars
        left = line.coords.left
        text = line.text
        points = line.coords.points
        # print("START:", points)
        for tr, col_type in overlapping_trs[:-1]:
            overlap_width = tr.coords.right - left
            overlap_num_chars = int(overlap_width / char_width)
            overlap_text = text[:overlap_num_chars]
            text = text[overlap_num_chars:]
            if len(overlap_text) == 0:
                continue
            overlap_points = [point for point in points if point[0] <= tr.coords.right]
            overlap_points += [(tr.coords.right, overlap_points[-1][1])]
            # print("PARTIAL:", overlap_points)
            overlap_coords = pdm.Coords(overlap_points)
            points = [point for point in points if point[0] > tr.coords.right]
            # print("REMAINING:", points)
            overlap_line = pdm.PageXMLTextLine(coords=overlap_coords, text = overlap_text)
            print("Partial line:", overlap_line.coords.left, overlap_line.coords.right, overlap_line.text)
            # print("Adding partial line to tr:", tr.id)
            line_types[col_type].append(overlap_line)
            # print("REMAINING TEXT:", text)
        # print("TEXT:", text)
        if len(points) > 1 and len(text) > 0:
            overlap_coords = pdm.Coords(points)
            overlap_line = pdm.PageXMLTextLine(coords=overlap_coords, text = text)
            tr, col_type = overlapping_trs[-1]
            # print("Partial line:", overlap_line.coords.left, overlap_line.coords.right, overlap_line.text)
            # print("Adding partial line to line_type:", col_type)
            line_types[col_type].append(overlap_line)


def check_main_sub_lemma_overlap(line_types: Dict[str, List[pdm.PageXMLTextLine]],
                                 config: Dict[str, any]):
    print("CHECKING MAIN AND SUB OVERLAP")
    main_coords = pdm.parse_derived_coords(line_types["main_term"])
    main_tr = pdm.PageXMLTextRegion(coords=main_coords, lines=line_types["main_term"])
    main_cols, main_extra = page_parser.split_lines_on_column_gaps(main_tr, config)
    print("MAIN COLS:", len(main_cols), "EXTRA:", main_extra is not None)
    for main_col in main_cols:
        print("\tCOL", main_col.coords.left, main_col.coords.right)
    if main_extra:
        print("\tEXTRA", main_extra.coords.left, main_extra.coords.right)
        for line in main_extra.lines:
            print(line.coords.left, line.coords.right, line.text)
    sub_coords = pdm.parse_derived_coords(line_types["sub_lemma"])
    sub_tr = pdm.PageXMLTextRegion(coords=sub_coords, lines=line_types["sub_lemma"])
    sub_cols, sub_extra = page_parser.split_lines_on_column_gaps(sub_tr, config)
    print("SUB COLS:", len(sub_cols), "EXTRA:", sub_extra is not None)
    for sub_col in sub_cols:
        print("\tCOL", sub_col.coords.left, sub_col.coords.right)
    if sub_extra:
        print("\tCOL", sub_extra.coords.left, sub_extra.coords.right)
    # check if sub overlaps with main
    for main_col, sub_col in zip(main_cols, sub_cols):
        print(main_col.coords.left, main_col.coords.right, sub_col.coords.left, sub_col.coords.right)
        print(pdm.horizontal_overlap(main_col.coords, sub_col.coords))


def move_unknowns_from_page(line_types: Dict[str, List[pdm.PageXMLTextLine]],
                            config: Dict[str, any], debug: bool = False):
    if debug:
        print("MOVING UNKNOWS FROM PAGE")
    all_cols = []
    main_coords = pdm.parse_derived_coords(line_types["main_term"])
    main_tr = pdm.PageXMLTextRegion(coords=main_coords, lines=line_types["main_term"])
    main_cols, main_extra = page_parser.split_lines_on_column_gaps(main_tr, config)
    # for col in main_cols:
    #     col.add_type('main_term')
    #     all_cols.append(col)
    # if main_extra:
    #     main_extra.add_type('main_term')
    #     all_cols.append(main_extra)
    sub_coords = pdm.parse_derived_coords(line_types["sub_lemma"])
    sub_tr = pdm.PageXMLTextRegion(coords=sub_coords, lines=line_types["sub_lemma"])
    sub_cols, sub_extra = page_parser.split_lines_on_column_gaps(sub_tr, config)
    for col in sub_cols:
        col.add_type('sub_lemma')
        all_cols.append(col)
    if sub_extra:
        sub_extra.add_type('sub_lemma')
        all_cols.append(sub_extra)
    date_coords = pdm.parse_derived_coords(line_types["date_locator"])
    date_tr = pdm.PageXMLTextRegion(coords=date_coords, lines=line_types["date_locator"])
    date_cols, date_extra = page_parser.split_lines_on_column_gaps(date_tr, config)
    for col in date_cols:
        col.add_type('date_locator')
        all_cols.append(col)
    if date_extra:
        date_extra.add_type('date_locator')
        all_cols.append(date_extra)
    page_coords = pdm.parse_derived_coords(line_types["page_locator"])
    page_tr = pdm.PageXMLTextRegion(coords=page_coords, lines=line_types["page_locator"])
    page_cols, page_extra = page_parser.split_lines_on_column_gaps(page_tr, config, debug=False)
    for col in page_cols:
        col.add_type('page_locator')
        # print("PAGE COL:", col.id)
        all_cols.append(col)
    if page_extra:
        page_extra.add_type('page_locator')
        # print("PAGE EXTRA:", page_extra.id)
        all_cols.append(page_extra)
    all_cols = sorted(all_cols, key=lambda x: x.coords.left)
    if debug:
        for ci, col in enumerate(all_cols):
            print("\t", ci, "of", len(all_cols), col.id, col.type)
    first_col = all_cols[0]
    if 'sub_lemma' not in first_col.type:
        print("FIRST COLUMN IS NOT SUB_LEMMA:", first_col.type)
        # remove the first column from the list
        all_cols = all_cols[1:]
        if 'page_locator' in first_col.type:
            line_types["unknown"] = first_col.lines
            for line in first_col.lines:
                line_types["page_locator"].remove(line)
                print("\tMOVING LINE FROM PAGE TO UNKNOWN:", line.coords.left, line.coords.right, line.text)


def move_unknowns_to_correct_column(line_types: Dict[str, List[pdm.PageXMLTextLine]],
                                    config: Dict[str, any], debug: bool = False):
    cols = defaultdict(list)
    for line_type in ['main_term', 'sub_lemma', 'date_locator', 'page_locator']:
        type_coords = pdm.parse_derived_coords(line_types[line_type])
        type_tr = pdm.PageXMLTextRegion(coords=type_coords, lines=line_types[line_type])
        type_cols, type_extra = page_parser.split_lines_on_column_gaps(type_tr, config)
        cols[line_type] = type_cols
        if type_extra:
            cols[line_type].append(type_extra)
    unknown_lines = line_types["unknown"]
    for line in unknown_lines:
        found_col = False
        for line_type in cols:
            for col in cols[line_type]:
                if pdm.is_horizontally_overlapping(line, col):
                    if debug:
                        print("MOVING LINE FROM UNKNOWN TO", line_type.upper())
                    line_types[line_type].append(line)
                    line_types["unknown"].remove(line)
                    found_col = True
                break
        if found_col is False:
            print("NO CORRECT COLUMN FOUND FOR UNKNOWN:", line.coords.left, line.coords.right, line.text)


def classify_and_filter_lines(page: pdm.PageXMLPage,
                              config: Dict[str, any],
                              debug: bool = False) -> Dict[str, List[pdm.PageXMLTextLine]]:
    line_types = classify_lines(page, debug=debug)
    if debug:
        print(f"PAGE HAS {len(page.get_lines())} LINES")
        print(f"LINE_TYPES HAS {len([l for t in line_types for l in line_types[t]])} LINES")
    filter_header_lines(line_types, debug=debug)
    config = copy.deepcopy(config)
    config["column_gap"]["gap_pixel_freq_ratio"] = 0.25
    filter_target_type_lines(page.id, "sub_lemma", line_types, config, overlap_threshold=0.7, debug=debug)
    # check for lines incorrectly moved to page col
    move_unknowns_from_page(line_types, config, debug=debug)
    # First, filter page and date, so main_term has only overlap with
    # sub_lemma left
    config["column_gap"]["gap_pixel_freq_ratio"] = 0.75
    filter_target_type_lines(page.id, "page_locator", line_types, config, debug=debug)
    filter_target_type_lines(page.id, "date_locator", line_types, config, debug=debug)
    filter_target_type_lines(page.id, "sub_lemma", line_types, config, overlap_threshold=0.5, debug=debug)
    # Second, check if there are merged lines overlapping main_term and sub_lemma
    # check_main_sub_lemma_overlap(line_types, config)
    # for line_type in line_types:
    #     print(line_type, len(line_types[line_type]))
    #     for line in sorted(line_types[line_type], key=lambda x: x.coords.y):
    #         print(line_type, line.coords.bottom, line.coords.left, line.coords.right, line.text)
    split_double_col_lines(line_types, config)
    # print("after filtering:")
    # for line_type in line_types:
    #     print(line_type, len(line_types[line_type]))
    move_unknowns_to_correct_column(line_types, config, debug=debug)
    return line_types


def make_index_page_text_regions(page: pdm.PageXMLPage,
                                 line_types: Dict[str, List[pdm.PageXMLTextLine]],
                                 config: Dict[str, any]) -> Tuple[List[pdm.PageXMLColumn], List[pdm.PageXMLTextRegion]]:
    extra = []
    index_columns = []
    # Add test: count lines and words in new columns to make sure
    # All content of page is copied to new columns
    lines, words = 0, 0
    for line_type in line_types:
        if line_type == "double_col" or line_type == "unknown":
            continue
        if line_type == "header":
            coords = pdm.parse_derived_coords(line_types[line_type])
            tr = pdm.PageXMLTextRegion(coords=coords, lines=line_types[line_type])
            tr.lines.sort(key=lambda x: x.coords.y)
            tr.set_derived_id(page.id)
            tr.add_type("index_header")
            extra.append(tr)
            lines += tr.stats["lines"]
            words += tr.stats["words"]
            # print(f"HEADER HAS {tr.stats['words']} WORDS")
        else:
            temp_coords = pdm.parse_derived_coords(line_types[line_type])
            temp_tr = pdm.PageXMLTextRegion(coords=temp_coords, lines=line_types[line_type])
            # print("splitting lines into columns for type:", line_type)
            columns, temp_extra = page_parser.split_lines_on_column_gaps(temp_tr, config, overlap_threshold=0.1)
            if len(columns) > 2 or len(columns) == 2 and temp_extra is not None:
                for column in columns:
                    print("column:", line_type, column.coords.box, column.stats)
                    if len(columns) > 2:
                        print("col:", line_type, column.coords.box, column.stats)
                        for line in column.lines:
                            print("\t", line.coords.left, line.coords.right, line.text)
                if temp_extra is not None:
                    print("extra:", line_type, temp_extra.coords.box, temp_extra.stats)
                    for line in temp_extra.lines:
                        print("\t", line.coords.left, line.coords.right, line.text)
                raise ValueError(f"More columns of type {line_type} than expected")
            if temp_extra is not None:
                columns += [temp_extra]
            for column in columns:
                # print(line_type, column.coords.box)
                column.set_derived_id(page.id)
                column.lines.sort(key=lambda x: x.coords.y)
                column.add_type("index_column")
                column.add_type(f"{line_type}_column")
                lines += column.stats["lines"]
                words += column.stats["words"]
                # print(f"COLUMN HAS {column.stats['words']} WORDS", column.type)
                index_columns.append(column)
            if temp_extra is not None:
                # print(temp_tr.stats)
                # print("col_type:", line_type, "columns:", len(columns))
                # for column in columns:
                #     print(column.id, column.coords.box)
                # print("temp_extra:", temp_extra.stats)
                # for line in temp_extra.lines:
                #     print(f"\t{line_type}\t{line.coords.x: >6}{line.coords.y: >6}{line.coords.w: >6}\t{line.text}")
                pass
    if abs(words - page.stats["words"]) > 5 and len(line_types["double_col"]) > 0:
        print(f"page {page.id} has {page.stats['words']} words, while columns have {words} words")
        raise ValueError("Not all content from page is copied to index columns and header")
    if words != page.stats["words"] and len(line_types["double_col"]) == 0:
        print(f"page {page.id} has {page.stats['words']} words, while columns have {words} words")
        raise ValueError("Not all content from page is copied to index columns and header")
    return index_columns, extra


def get_col_type_order(columns: List[pdm.PageXMLColumn]) -> List[str]:
    if len(columns) % 4 == 0:
        return ["main_term", "sub_lemma", "date_locator", "page_locator"]
    elif len(columns) % 3 == 0:
        return ["main_term", "sub_lemma", "page_locator"]
    else:
        for column in columns:
            print(column.type, column.coords.x)

        raise ValueError(f"Unexpected number of columns: {len(columns)}")


def group_index_columns(columns: List[pdm.PageXMLColumn]) -> List[List[pdm.PageXMLColumn]]:
    column_groups = []
    columns.sort(key=lambda col: col.coords.x)
    col_type_order = get_col_type_order(columns)
    group_size = len(col_type_order)
    for index in range(0, group_size*2, group_size):
        group = columns[index:index+group_size]
        for ci, column in enumerate(group):
            expected_type = f"{col_type_order[ci]}_column"
            if column.has_type(expected_type) is False:
                col_types = f"[{', '.join(column.type)}]"
                raise TypeError(f"column at index {ci} should have type {expected_type} but has types: {col_types}")
        column_groups.append(group)
    return column_groups


class Sublemma:

    def __init__(self, main_term: str, sub_lemma: str, date_locator: str, page_locator: str,
                 lines: Dict[str, List[pdm.PageXMLTextLine]] = None):
        self.main_term = main_term
        self.sub_lemma = sub_lemma
        self.date_locator = date_locator
        self.page_locator = page_locator
        day, month = parse_date_locator(date_locator)
        self.date_locator_day = day
        self.date_locator_month = month
        self.lines = lines if lines is not None else init_sub_lemma_lines()

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
            column_lines[col_type] += column.lines
    return column_lines


def get_sub_lemma_lines(line: pdm.PageXMLTextLine,
                        column_lines: Dict[str, List[pdm.PageXMLTextLine]],
                        remaining_lines: Dict[str, List[pdm.PageXMLTextLine]] = None,
                        prev_bottom: int = 0, threshold: float = 0.5) -> Sublemma:
    sub_lemma_lines = init_sub_lemma_lines(line)
    if remaining_lines:
        for col_type in remaining_lines:
            for remaining_line in remaining_lines[col_type]:
                sub_lemma_lines[col_type].append(remaining_line)
    for col_type in column_lines:
        if col_type == "page_locator":
            continue
        for line in column_lines[col_type]:
            # print('\t', col_type, line.coords.top, line.coords.bottom, line.text)
            if line.coords.top > sub_lemma_lines["page_locator"][-1].coords.bottom:
                # print('\t\tbelow page_locator:', sub_lemma["page_locator"][-1].coords.bottom)
                break
            if line.coords.bottom < prev_bottom:
                # print('\t\tabove current sub lemma:', prev_bottom)
                continue
            top = max(line.coords.top, prev_bottom)
            bottom = min(line.coords.bottom, sub_lemma_lines["page_locator"][-1].coords.bottom)
            overlap = bottom - top
            if overlap <= 0:
                # print('negative overlap:', top, bottom)
                continue
            elif overlap / line.coords.height > threshold:
                # print('\t\tadding to sub_lemma')
                sub_lemma_lines[col_type].append(line)
            else:
                # print('\t\toverlap too small:', overlap, line.coords.height)
                pass
    sub_lemma = parse_sub_lemma_lines(sub_lemma_lines)
    return sub_lemma


def merge_lemma_text_lines(lines: List[pdm.PageXMLTextLine]):
    text = ""
    for line in lines:
        if line.text[-1] == '-':
            text += line.text[:-1]
        else:
            text += line.text + ' '
    return text.strip()


def parse_sub_lemma_lines(sub_lemma_lines: Dict[str, List[pdm.PageXMLTextLine]]) -> Sublemma:
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
    return Sublemma(main_term=main_term, sub_lemma=sub_lemma_text,
                         date_locator=date_locator, page_locator=page_locator,
                         lines=sub_lemma_lines)


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
    elif m:= re.search(r"^(\w+) (\w+)[,\.]?$", date_locator):
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


def split_sub_lemmas(column_lines: Dict[str, List[pdm.PageXMLTextLine]],
                     remaining_lines: Dict[str, List[pdm.PageXMLTextLine]] = None,
                     prev_main_term: str = None) -> Tuple[List[Sublemma],
                                                          Dict[str, List[pdm.PageXMLTextLine]]]:
    sub_lemmas = []
    prev_bottom = 0
    for line in column_lines["page_locator"]:
        if remaining_lines:
            sub_lemma = get_sub_lemma_lines(line, column_lines, remaining_lines, prev_bottom)
            remaining_lines = None
        else:
            sub_lemma = get_sub_lemma_lines(line, column_lines, prev_bottom=prev_bottom)
        if sub_lemma.main_term:
            prev_main_term = sub_lemma.main_term
        elif prev_main_term:
            # copy repeated main term from previous lemma
            sub_lemma.main_term = prev_main_term
        check_date_locator(sub_lemma, sub_lemmas)
        sub_lemmas.append(sub_lemma)
        prev_bottom = sub_lemma.lines["page_locator"][-1].coords.bottom
    remaining_lines = set_column_lines()
    for col_type in column_lines:
        for line in column_lines[col_type]:
            if line.coords.bottom < prev_bottom:
                continue
            elif has_line(sub_lemmas[-1], line):
                continue
            else:
                remaining_lines[col_type].append(line)
    return sub_lemmas, remaining_lines
