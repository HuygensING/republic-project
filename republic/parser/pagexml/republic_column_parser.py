import copy
import re
from collections import Counter
from typing import Dict, List, Set, Union

import numpy as np
import pagexml.analysis.layout_stats as page_layout
import pagexml.model.physical_document_model as pdm
import pagexml.helper.pagexml_helper as pagexml_helper

# import republic.model.physical_document_model as pdm
import republic.helper.metadata_helper as meta_helper
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
    if debug > 2:
        print("determine_freq_gap_interval - common_pixels:", common_pixels)
    gap_pixel_intervals = []
    if len(common_pixels) == 0:
        return gap_pixel_intervals
    curr_interval = new_gap_pixel_interval(common_pixels[0])
    if debug > 2:
        print("determine_freq_gap_interval - curr_interval:", curr_interval)
    prev_interval_end = 0
    for curr_index, curr_pixel in enumerate(common_pixels[:-1]):
        next_pixel = common_pixels[curr_index + 1]
        if debug > 2:
            print("determine_freq_gap_interval - curr:", curr_pixel, "next:", next_pixel, "start:",
                  curr_interval["start"], "end:", curr_interval["end"], "prev_end:", prev_interval_end)
        if next_pixel - curr_pixel < config["column_gap"]["gap_threshold"]:
            curr_interval["end"] = next_pixel
        else:
            # if curr_interval["end"] - curr_interval["start"] < config["column_gap"]["gap_threshold"]:
            if curr_interval["start"] - prev_interval_end < config["column_gap"]["gap_threshold"]:
                if debug > 2:
                    print("determine_freq_gap_interval - skipping interval:", curr_interval, "\tcurr_pixel:",
                          curr_pixel, "next_pixel:", next_pixel)
                continue
            if debug > 2:
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
    if debug > 2:
        print("find_column_gaps - lines:", len(lines), "gap_pixel_freq_ratio:", config["column_gap"]["gap_pixel_freq_ratio"])
        print("find_column_gaps - freq_threshold:", gap_pixel_freq_threshold)
    gap_pixel_dist = compute_pixel_dist(lines)
    if debug > 2:
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
    tr = pdm.PageXMLTextRegion(metadata=copy.deepcopy(metadata), coords=coords, lines=lines)
    column = pdm.PageXMLColumn(metadata=copy.deepcopy(metadata), coords=coords, text_regions=[tr])
    column.set_derived_id(page_id)
    return column


def add_line_to_column(line: pdm.PageXMLTextLine, column: pdm.PageXMLColumn) -> None:
    for tr in column.text_regions:
        if pdm.is_horizontally_overlapping(line, tr, threshold=0.1) and \
                pdm.is_vertically_overlapping(line, tr, threshold=0.1):
            tr.lines.append(line)
            tr.lines.sort()
            return None
    new_tr = pdm.PageXMLTextRegion(metadata=copy.deepcopy(column.metadata),
                                   coords=pdm.parse_derived_coords([line]),
                                   lines=[line])
    column.text_regions.append(new_tr)
    column.text_regions.sort()


def split_lines_on_column_gaps(text_region: pdm.PageXMLTextRegion,
                               config: Dict[str, any],
                               overlap_threshold: float = 0.5,
                               ignore_bad_coordinate_lines: bool = True,
                               debug: int = 0) -> List[pdm.PageXMLColumn]:
    lines = [line for line in text_region.get_lines()]
    if 'scan_id' not in text_region.metadata:
        raise KeyError(f'no "scan_id" in text_region {text_region.id}')
    column_ranges = find_column_gaps(lines, config, debug=debug-1)
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
        tr = pdm.PageXMLTextRegion(doc_type=copy.deepcopy(text_region.type),
                                   metadata=copy.deepcopy(text_region.metadata),
                                   coords=coords, lines=lines)
        column = pdm.PageXMLColumn(doc_type=copy.deepcopy(text_region.type),
                                   metadata=copy.deepcopy(text_region.metadata),
                                   coords=coords, text_regions=[tr])
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
            add_line_to_column(line, best_column)
            append_count += 1
            best_column.coords = pdm.parse_derived_coords(best_column.text_regions)
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
                print('\tproblem with coords of extra line:', line.id, line.coords.box, line.text)
                print('\tcoords:', line.coords)
                print('\tin text_region', text_region.id)
            coord_points = [point for line in extra_lines for point in line.coords.points]
            coords = pdm.Coords(coord_points)
            if ignore_bad_coordinate_lines is False:
                raise ValueError('Cannot generate column coords for extra lines')
        if coords is not None:
            extra = pdm.PageXMLTextRegion(metadata=copy.deepcopy(text_region.metadata), coords=coords,
                                          lines=extra_lines)
            if text_region.parent and text_region.parent.id:
                extra.set_derived_id(text_region.parent.id)
                extra.set_parent(text_region.parent)
            else:
                extra.set_derived_id(text_region.metadata['scan_id'])
            # for line in extra.lines:
            #     print(f"RETURNING EXTRA LINE: {line.coords.left}-{line.coords.right}\t{line.coords.y}\t{line.text}")
            config = copy.deepcopy(config)
            config["column_gap"]["gap_pixel_freq_ratio"] = 0.01
            if debug > 0:
                print('split_lines_on_column_gaps - SPLITTING EXTRA')
            if extra.id == text_region.id and len(columns) == 0:
                if debug > 0:
                    print('split_lines_on_column_gaps - extra equals text_region:')
                    print('\t', text_region.id, text_region.stats)
                    print('\t', extra.id, extra.stats)
                    print('split_lines_on_column_gaps - cannot split text_region, returning text_region')
                extra_cols = [extra]
            elif all([extra_stat == tr_stat for extra_stat, tr_stat in zip(extra.stats, text_region.stats)]):
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
    if debug > 3:
        print('\n------------\n')
        for col in columns:
            print(f"split_lines_on_column_gaps - number of lines directly under column {col.id}: {len(col.lines)}")
        print('\n------------\n')
    return columns


def make_new_tr(tr_lines: List[pdm.PageXMLTextLine], original_tr: pdm.PageXMLTextRegion,
                update_type: bool = False, debug: int = 0) -> pdm.PageXMLTextRegion:
    """Generate a new PageXMLTextRegion instance for a give set of lines. Update its type based on
    the line_classes of the lines."""
    tr_coords = pdm.parse_derived_coords(tr_lines)
    tr_lines.sort()
    new_tr = pdm.PageXMLTextRegion(metadata=copy.deepcopy(original_tr.metadata),
                                   coords=tr_coords, lines=tr_lines)
    new_tr.type = {t for t in original_tr.type}
    if update_type:
        new_tr.type = update_text_region_type(new_tr, debug=debug)
    new_tr.set_derived_id(original_tr.metadata['scan_id'])
    return new_tr


def get_main_line_types(lines: List[pdm.PageXMLTextLine]) -> List[str]:
    line_types = [line.metadata['line_class'] for line in lines if 'line_class' in line.metadata and line.metadata['line_class']
                  not in {'empty', 'noise'}]
    return [lt[:4] if lt.startswith('para_') else lt for lt in line_types]


def update_text_region_type(text_region: pdm.PageXMLTextRegion, debug: int = 0) -> Set[str]:
    """Determine the type of text region based on the line_classes of its lines."""
    tr_type = {'text_region', 'structure_doc', 'physical_structure_doc', 'main', 'pagexml_doc'}
    line_types = get_main_line_types(text_region.lines)
    type_freq = Counter(line_types)
    if len(line_types) == 0:
        main_type = 'empty'
    elif len(type_freq) == 1:
        main_type = list(type_freq.keys())[0]
    else:
        main_type, freq = type_freq.most_common(1)[0]
        if main_type in {'para', 'date', 'attendance', 'marginalia'} and freq / sum(type_freq.values()) > 0.5:
            main_type = main_type
        elif main_type != 'date' and 'date' in type_freq and type_freq['date'] == type_freq[main_type]:
            main_type = 'date'
        elif main_type == 'date':
            main_type = 'date'
        else:
            main_type = 'mix'
    if main_type == 'para':
        main_type = 'resolution'
    tr_type.add(main_type)
    if debug > 0:
        print(f"republic_column_parser.update_text_region_type - main_type: {main_type}")
        print(f"republic_column_parser.update_text_region_type - type_freq: {type_freq}")
    return tr_type


def split_text_region_by_line_type(tr: pdm.PageXMLTextRegion) -> List[pdm.PageXMLTextRegion]:
    split_trs = []
    for line in tr.lines:
        tr_class = meta_helper.map_line_class_to_tr_class(line.metadata['line_class'])

    return split_trs


def split_column_text_regions(column: pdm.PageXMLColumn, update_type: bool = False,
                              debug: int = 0) -> pdm.PageXMLColumn:
    """Split the text regions of a column into multiple regions if they contain large vertical gaps.
    If update_type is set to True, the text regions type will also be updated based on the line_classes
    of their lines."""
    col_trs = []
    if len(column.text_regions) == 0 and len(column.lines) > 0:
        # make sure column has only text_regions as children
        # all lines should be part of text regions
        tr = make_new_tr(column.lines, column, debug=debug)
        tr.set_parent(column)
        column.text_regions.append(tr)
        column.lines = []
    if debug > 0:
        print('republic_column_parser.split_column_text_regions\tCOL STATS:', column.stats)
    for tr in column.text_regions:
        new_trs = split_text_region_on_vertical_gap(tr, update_type=update_type, debug=debug)
        if debug > 0:
            print(f'republic_column_parser.split_column_text_regions - received {len(new_trs)} new trs from tr {tr.id}')
            for new_tr in new_trs:
                print(f'\tnew id:{new_tr.id}\tcoords.points: {new_tr.coords.points}')
                print(f"\t{Counter([line.metadata['line_class'] for line in new_tr.lines])}")
                print(f"\t{new_tr.type}")
        col_trs.extend(new_trs)
    col_trs.sort()
    new_coords = pdm.parse_derived_coords(col_trs)
    new_column = pdm.PageXMLColumn(doc_id=column.id, metadata=copy.deepcopy(column.metadata),
                                   coords=new_coords, text_regions=col_trs)
    new_column.type = {col_type for col_type in column.type}
    new_column.set_parent(column.parent)
    if debug > 0:
        print(f'republic_column_parser.split_column_text_regions - new_column.id: {new_column.id}')
        print(f'republic_column_parser.split_column_text_regions - '
              f'new_column.coords.points: {new_column.coords.points}')
        print('\n\n')
    return new_column


def is_line_class_boundary(prev_line: pdm.PageXMLTextLine, curr_line: pdm.PageXMLTextLine) -> bool:
    if 'line_class' not in prev_line.metadata or 'line_class' not in curr_line.metadata:
        return False
    prev_class, curr_class = prev_line.metadata['line_class'], curr_line.metadata['line_class']
    if prev_class in {'noise', 'empty', 'insert_omitted'} or curr_class in {'noise', 'empty', 'insert_omitted'}:
        return False
    if prev_class in {'date', 'attendance'} and curr_class.startswith('para_'):
        return True
    if prev_class.startswith('para_') and curr_class in {'date', 'attendance'}:
        return True
    return False


def get_previous_content_line(line_index: int, lines: List[pdm.PageXMLTextLine]) -> Union[pdm.PageXMLTextLine, None]:
    for prev_index in range(line_index - 1, 0, -1):
        prev_line = lines[prev_index]
        if is_noise_linse(prev_line) is False:
            return prev_line
    return None


def get_next_content_line(line_index: int, lines: List[pdm.PageXMLTextLine]) -> Union[pdm.PageXMLTextLine, None]:
    for next_index in range(line_index + 1, len(lines)):
        next_line = lines[next_index]
        if is_noise_linse(next_line) is False:
            return next_line
    return None


def is_noise_linse(line: pdm.PageXMLTextLine) -> bool:
    if 'line_class' not in line.metadata:
        return False
    return line.metadata['line_class'] in {'noise', 'empty'}


def separate_noise_lines(text_region: pdm.PageXMLTextRegion, debug: int = 0) -> Dict[str, any]:
    lines = {
        'content': [],
        'noise': []
    }
    sorted_lines = sorted(text_region.lines)
    noise_lines = [line for line in sorted_lines if is_noise_linse(line)]
    lines['content'] = [line for line in sorted_lines if line not in noise_lines]
    for li, line in enumerate(sorted_lines):
        if is_noise_linse(line) is False:
            continue
        prev_line = get_previous_content_line(li, sorted_lines)
        next_line = get_next_content_line(li, sorted_lines)
        if prev_line:
            assert prev_line.id != line.id, "current line and prev_line are the same"
        if next_line:
            assert next_line.id != line.id, "current line and next_line are the same"
        if prev_line and next_line:
            closest = prev_line if pdm.vertical_distance(line, prev_line) < pdm.vertical_distance(line, next_line) \
                else next_line
            if debug > 2:
                print(f"linking noise line {line.id} to closest {closest.id}")
            lines['noise'].append((line, closest))
        elif prev_line:
            if debug > 2:
                print(f"linking noise line {line.id} to prev {prev_line.id}")
            lines['noise'].append((line, prev_line))
        elif next_line:
            if debug > 2:
                print(f"linking noise line {line.id} to next {next_line.id}")
            lines['noise'].append((line, next_line))
        else:
            if debug > 2:
                print(f"linking noise line {line.id} to None")
            lines['noise'].append((line, None))
    return lines


def split_text_region_on_vertical_gap(text_region: pdm.PageXMLTextRegion,
                                      update_type: bool = False,
                                      debug: int = 0) -> List[pdm.PageXMLTextRegion]:
    """Split text region into multiple text regions if the lines contain a large vertical gap."""
    new_trs = []
    separated_lines = separate_noise_lines(text_region)
    content_lines = separated_lines['content']
    noise_line_links = separated_lines['noise']
    if debug > 0:
        print(f'\nrepublic_column_parser.split_text_region_on_vertical_gap - tr: {text_region.id}')
    if debug > 2:
        for nl, ll in noise_line_links:
            print('republic_column_parser.split_text_region_on_vertical_gap:')
            print('    noise link:')
            print('\tnoise line:', nl)
            print('\tlink line:', ll)
    line_heights = [page_layout.get_text_heights(line, debug=debug) for line in content_lines]
    # line_heights = [lh for lh in line_heights if lh is not None]
    all_distances = page_layout.get_line_distances(content_lines)
    if debug > 2:
        print('republic_column_parser.split_text_region_on_vertical_gap:')
        for line in content_lines:
            print('\tline:', line.text)
        print('    distances:', all_distances)
    avg_distances = [dists.mean() for dists in all_distances]
    if debug > 1:
        print('republic_column_parser.split_text_region_on_vertical_gap - text_region avg_distances:', avg_distances)
        print('republic_column_parser.split_text_region_on_vertical_gap - text_region line_heights:', line_heights)
    if len(content_lines) == 0:
        return [copy.deepcopy(text_region)]
    prev_line = content_lines[0]
    tr_lines = [prev_line]
    for li, curr_line in enumerate(content_lines[1:]):
        if debug > 2:
            print('\n---------------')
            print('prev_line:', prev_line.text)
            print('curr_line:', curr_line.text)
            print('-----------------')
        avg_dist = avg_distances[li]
        if line_heights[li-1] is None:
            tr_lines.append(curr_line)
            prev_line = curr_line
            continue
        if line_heights[li] is None:
            tr_lines.append(curr_line)
            continue
        if debug > 1:
            print(f"\tmedian line_heights: {np.median(line_heights[li-1])}\t{prev_line.text}")
            print(f"\tmedian line_heights: {np.median(line_heights[li])}\t{curr_line.text}")
        if avg_dist > np.median(line_heights[li]) * 2:
            if debug > 0:
                print(f"\tavg_dist: {avg_dist}\tBOUNDARY")
            new_tr = make_new_tr(tr_lines, text_region, update_type=update_type, debug=debug)
            new_trs.append(new_tr)
            tr_lines = []
        elif is_line_class_boundary(prev_line, curr_line):
            if debug > 0:
                print(f"\tprev_class: {prev_line.metadata['line_class']}"
                      f"\t\tcurr_class: {curr_line.metadata['line_class']}\tBOUNDARY")
            new_tr = make_new_tr(tr_lines, text_region, update_type=update_type, debug=debug)
            new_trs.append(new_tr)
            tr_lines = []
        else:
            if debug > 0:
                print(f"\tavg_dist: {avg_dist}\tno boundary\tmedian line_height: {np.median(line_heights[li])}")
        # print('\t\t', curr_line.text)
        tr_lines.append(curr_line)
        prev_line = curr_line
    if len(tr_lines) > 0:
        new_tr = make_new_tr(tr_lines, text_region, update_type=update_type, debug=debug)
        new_trs.append(new_tr)
    if len(new_trs) == 1:
        if text_region.has_type('date') or text_region.has_type('attendance'):
            new_trs[0].type = text_region.type
    for noise_line, link_line in noise_line_links:
        if link_line is None:
            new_tr = make_new_tr([noise_line], text_region)
            for known_type in meta_helper.KNOWN_TYPES:
                new_tr.remove_type(known_type)
            new_tr.add_type('noise')
            new_trs.append(new_tr)
        else:
            added = False
            for tr in new_trs:
                if link_line in tr.lines:
                    tr.add_child(noise_line)
                    added = True
                    tr.lines.sort()
            assert added is True, (f"no textregion found containing link line {link_line.id} "
                                   f"on page {link_line.metadata['page_id']}")
    return new_trs
