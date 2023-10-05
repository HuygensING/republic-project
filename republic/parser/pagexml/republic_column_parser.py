import copy
import re
from collections import Counter
from typing import Dict, List

import pagexml.model.physical_document_model as pdm
import pagexml.helper.pagexml_helper as pagexml_helper

# import republic.model.physical_document_model as pdm
from republic.helper.pagexml_helper import merge_columns


def within_column(line, column_range, overlap_threshold: float = 0.5):
    start = max([line.coords.left, column_range["start"]])
    end = min([line.coords.right, column_range["end"]])
    overlap = end - start if end > start else 0
    return overlap / line.coords.width > overlap_threshold


def find_overlapping_columns(columns: List[pdm.PageXMLColumn]):
    columns.sort()
    merge_sets = []
    for ci, curr_col in enumerate(columns[:-1]):
        next_col = columns[ci+1]
        if pdm.is_horizontally_overlapping(curr_col, next_col):
            for merge_set in merge_sets:
                if curr_col in merge_set:
                    merge_set.append(next_col)
                    break
            else:
                merge_sets.append([curr_col, next_col])
    return merge_sets


#################################################
# Identifying columns using pixel distributions #
#################################################


def compute_pixel_dist(lines: List[pdm.PageXMLTextLine]) -> Counter:
    """Count how many lines are above each horizontal pixel coordinate."""
    pixel_dist = Counter()
    for line in lines:
        if line.baseline:
            pixel_dist.update([pixel for pixel in range(line.baseline.left, line.baseline.right + 1)])
        else:
            pixel_dist.update([pixel for pixel in range(line.coords.left, line.coords.right + 1)])
    return pixel_dist


def new_gap_pixel_interval(pixel: int) -> dict:
    return {"start": pixel, "end": pixel}


def determine_freq_gap_interval(pixel_dist: Counter, freq_threshold: int, config: dict, debug: int = 0) -> list:
    common_pixels = sorted([pixel for pixel, freq in pixel_dist.items() if freq >= freq_threshold])
    if debug > 0:
        print("determine_freq_gap_interval - common_pixels:", common_pixels)
    gap_pixel_intervals = []
    if len(common_pixels) == 0:
        return gap_pixel_intervals
    curr_interval = new_gap_pixel_interval(common_pixels[0])
    if debug > 0:
        print("determine_freq_gap_interval - curr_interval:", curr_interval)
    prev_interval_end = 0
    for curr_index, curr_pixel in enumerate(common_pixels[:-1]):
        next_pixel = common_pixels[curr_index + 1]
        if debug > 0:
            print("determine_freq_gap_interval - curr:", curr_pixel, "next:", next_pixel, "start:",
                  curr_interval["start"], "end:", curr_interval["end"], "prev_end:", prev_interval_end)
        if next_pixel - curr_pixel < config["column_gap"]["gap_threshold"]:
            curr_interval["end"] = next_pixel
        else:
            # if curr_interval["end"] - curr_interval["start"] < config["column_gap"]["gap_threshold"]:
            if curr_interval["start"] - prev_interval_end < config["column_gap"]["gap_threshold"]:
                if debug > 0:
                    print("determine_freq_gap_interval - skipping interval:", curr_interval, "\tcurr_pixel:",
                          curr_pixel, "next_pixel:", next_pixel)
                continue
            if debug > 0:
                print("determine_freq_gap_interval - adding interval:", curr_interval, "\tcurr_pixel:",
                      curr_pixel, "next_pixel:", next_pixel)
            gap_pixel_intervals += [curr_interval]
            prev_interval_end = curr_interval["end"]
            curr_interval = new_gap_pixel_interval(next_pixel)
    gap_pixel_intervals += [curr_interval]
    return gap_pixel_intervals


def find_column_gaps(lines: List[pdm.PageXMLTextLine], config: Dict[str, any],
                     debug: int = 0):
    num_column_lines = len(lines) / 2 if len(lines) < 140 else 60
    gap_pixel_freq_threshold = int(num_column_lines * config["column_gap"]["gap_pixel_freq_ratio"])
    if debug > 0:
        print("find_column_gaps - lines:", len(lines), "gap_pixel_freq_ratio:", config["column_gap"]["gap_pixel_freq_ratio"])
        print("find_column_gaps - freq_threshold:", gap_pixel_freq_threshold)
    gap_pixel_dist = compute_pixel_dist(lines)
    if debug > 0:
        print("find_column_gaps - gap_pixel_dist:", gap_pixel_dist)
    gap_pixel_intervals = determine_freq_gap_interval(gap_pixel_dist, gap_pixel_freq_threshold, config, debug=debug)
    return gap_pixel_intervals


def column_bounding_box_surrounds_lines(column: pdm.PageXMLColumn) -> bool:
    """Check if the column coordinates contain the coordinate
    boxes of the column lines."""
    for line in column.get_lines():
        if not pagexml_helper.elements_overlap(column, line, threshold=0.6):
            return False
    return True


def is_text_column(column: pdm.PageXMLColumn) -> bool:
    """Check if there is at least one alpha-numeric word on the page."""
    # num_chars = 0
    num_alpha_words = 0
    for line in column.get_lines():
        if line.text:
            try:
                words = [word for word in re.split(r'\W+', line.text.strip()) if len(word) > 1]
            except re.error:
                print(line.text)
                raise
            num_alpha_words += len(words)
            # num_chars += len(line.text)
    # return num_chars >= 20
    return num_alpha_words > 0


def is_full_text_column(column: pdm.PageXMLColumn, num_page_cols: int = 2) -> bool:
    """Check if a page column is a full-text column (running from top to bottom of page)."""
    between_cols_margin = 300 * (num_page_cols - 1)
    page_text_width = 2000
    full_column_text_width = (page_text_width - between_cols_margin) / num_page_cols
    if column.coords.width < full_column_text_width - 80:
        # narrow column is not a normal text column
        return False
    if column.coords.height > 2500:
        # full page-height column
        return True
    if column.coords.height / column.stats['lines'] > 100:
        # lines are far apart, probably something wrong
        return False
    if column.coords.width > 700 and column.stats['lines'] > 30:
        return True


def is_noise_column(column: pdm.PageXMLColumn) -> bool:
    """Check if columns contains only very short lines."""
    for line in column.get_lines():
        if line.text and len(line.text) > 3:
            return False
    return True


def is_header_footer_column(column: pdm.PageXMLColumn) -> bool:
    """Check if a column is a header or footer."""
    if column.coords.top <= 600:
        if column.coords.bottom > 600:
            # column is too low for top margin header
            return False
    if column.coords.bottom >= 3200:
        if column.coords.top < 3200:
            # column is too high for bottom margin footer
            return False
    if is_text_column(column):
        return False
    if column.stats['lines'] > 4:
        return False
    if column.coords.width > 500 and column.coords.height > 150:
        return False
    return True


def determine_column_type(column: pdm.PageXMLColumn) -> str:
    """Determine whether a column is a full-text column, margin column
    or extra text column."""
    if is_full_text_column(column):
        return 'full_text'
    elif is_text_column(column):
        return 'extra_text'
    elif is_header_footer_column(column):
        return 'header_footer'
    elif is_noise_column(column):
        return 'noise_column'
    else:
        print('Bounding box:', column.coords.box)
        print('Stats:', column.stats)
        num_chars = 0
        for line in column.get_lines():
            print(line.coords.box, line.text)
            num_chars += len(line.text)
        print('num_chars:', num_chars)
        raise TypeError('unknown column type')


def make_derived_column(lines: List[pdm.PageXMLTextLine], metadata: dict, page_id: str) -> pdm.PageXMLColumn:
    """Make a new PageXMLColumn based on a set of lines, column metadata and a page_id."""
    coords = pdm.parse_derived_coords(lines)
    column = pdm.PageXMLColumn(metadata=metadata, coords=coords, lines=lines)
    column.set_derived_id(page_id)
    return column


def split_lines_on_column_gaps(text_region: pdm.PageXMLTextRegion,
                               config: Dict[str, any],
                               overlap_threshold: float = 0.5,
                               debug: int = 0) -> List[pdm.PageXMLColumn]:
    lines = [line for line in text_region.get_lines()]
    column_ranges = find_column_gaps(lines, config, debug=debug)
    if debug > 0:
        print('split_lines_on_column_gaps - text_region:', text_region.id, text_region.stats)
        print('split_lines_on_column_gaps - column_gap:', config['column_gap'])
        print("COLUMN RANGES:", column_ranges)
    column_ranges = [col_range for col_range in column_ranges if col_range["end"] - col_range["start"] >= 20]
    column_lines = [[] for _ in range(len(column_ranges))]
    extra_lines = []
    num_lines = text_region.stats['lines']
    append_count = 0
    for line in lines:
        index = None
        for column_range in column_ranges:
            if line.coords.width == 0:
                if debug:
                    print("ZERO WIDTH LINE:", line.coords.box, line.text)
                continue

            if within_column(line, column_range, overlap_threshold=overlap_threshold):
                index = column_ranges.index(column_range)
                column_lines[index].append(line)
                append_count += 1
        if index is None:
            extra_lines.append(line)
            append_count += 1
            # print(f"APPENDING EXTRA LINE: {line.coords.left}-{line.coords.right}\t{line.coords.y}\t{line.text}")
    columns = []
    if debug > 0:
        print('RANGE SPLIT num_lines:', num_lines, 'append_count:', append_count)
        for ci, lines in enumerate(column_lines):
            print('\tcolumn', ci, '\tlines:', len(lines))
        print('\textra lines:', len(extra_lines))
    for lines in column_lines:
        if len(lines) == 0:
            continue
        coords = pdm.parse_derived_coords(lines)
        column = pdm.PageXMLColumn(doc_type=copy.deepcopy(text_region.type),
                                   metadata=copy.deepcopy(text_region.metadata),
                                   coords=coords, lines=lines)
        if text_region.parent and text_region.parent.id:
            column.set_derived_id(text_region.parent.id)
            column.set_parent(text_region.parent)
        else:
            column.set_derived_id(text_region.id)
        columns.append(column)
    # column range may have expanded with lines partially overlapping initial range
    # check which extra lines should be added to columns
    non_col_lines = []
    merge_sets = find_overlapping_columns(columns)
    merge_cols = {col for merge_set in merge_sets for col in merge_set}
    non_overlapping_cols = [col for col in columns if col not in merge_cols]
    for merge_set in merge_sets:
        if debug > 0:
            print("MERGING OVERLAPPING COLUMNS:", [col.id for col in merge_set])
        merged_col = merge_columns(merge_set, "temp_id", merge_set[0].metadata)
        if text_region.parent and text_region.parent.id:
            merged_col.set_derived_id(text_region.parent.id)
            merged_col.set_parent(text_region.parent)
        else:
            merged_col.set_derived_id(text_region.id)
        non_overlapping_cols.append(merged_col)
    columns = non_overlapping_cols
    if debug > 0:
        print("NUM COLUMNS:", len(columns))
        print("EXTRA LINES BEFORE:", len(extra_lines))
        for line in extra_lines:
            print('\tEXTRA LINE:', line.text)
    append_count = 0
    for line in extra_lines:
        best_overlap = 0
        best_column = None
        for column in columns:
            # print("EXTRA LINE CHECKING OVERLAP:", line.coords.left, line.coords.right,
            #       column.coords.left, column.coords.right)
            overlap = pdm.get_horizontal_overlap(line, column)
            # print('\tOVERLAP', overlap)
            if overlap > best_overlap:
                if best_column is None or column.coords.width < best_column.coords.width:
                    best_column = column
                    best_overlap = overlap
                    # print('\t\tBEST', best_column)
        if best_column is not None and pdm.is_horizontally_overlapping(line, best_column):
            best_column.lines.append(line)
            append_count += 1
            best_column.coords = pdm.parse_derived_coords(best_column.lines)
            if text_region.parent:
                best_column.set_derived_id(text_region.parent.id)
        else:
            # print(f"APPENDING NON-COL LINE: {line.coords.left}-{line.coords.right}\t{line.coords.y}\t{line.text}")
            non_col_lines.append(line)
            append_count += 1
    if debug > 0:
        print('append_count:', append_count)
    extra_lines = non_col_lines
    if debug > 0:
        print("EXTRA LINES AFTER:", len(extra_lines))
    extra = None
    if len(extra_lines) > 0:
        try:
            coords = pdm.parse_derived_coords(extra_lines)
        except BaseException:
            for line in extra_lines:
                print(line.coords.box, line.text)
            raise ValueError('Cannot generate column coords for extra lines')
        extra = pdm.PageXMLTextRegion(metadata=text_region.metadata, coords=coords,
                                      lines=extra_lines)
        if text_region.parent and text_region.parent.id:
            extra.set_derived_id(text_region.parent.id)
            extra.set_parent(text_region.parent)
        else:
            extra.set_derived_id(text_region.id)
        # for line in extra.lines:
        #     print(f"RETURNING EXTRA LINE: {line.coords.left}-{line.coords.right}\t{line.coords.y}\t{line.text}")
        config = copy.deepcopy(config)
        config["column_gap"]["gap_pixel_freq_ratio"] = 0.01
        if debug > 0:
            print('SPLITTING EXTRA')
        if extra.id == text_region.id and len(columns) == 0:
            if debug > 0:
                print('split_lines_on_column_gaps - extra equals text_region:')
                print('\t', text_region.id, text_region.stats)
                print('\t', extra.id, extra.stats)
                print('split_lines_on_column_gaps - cannot split text_region, returning text_region')
            extra_cols = [extra]
        else:
            extra_cols = split_lines_on_column_gaps(extra, config, debug=debug)
        for extra_col in extra_cols:
            if debug > 0:
                print('\tEXTRA COL AFTER EXTRA SPLIT:', extra_col.stats)
            extra_col.set_parent(text_region.parent)
            if text_region.parent:
                extra_col.set_derived_id(text_region.parent.id)
        columns += extra_cols
        extra = None
    if extra is not None:
        print('source doc:', text_region.id)
        print(extra)
        raise TypeError(f'Extra is not None but {type(extra)}')
    return columns
