from typing import Dict, List, Tuple, Union
from collections import Counter
from collections import defaultdict
import copy
import re

import numpy as np

from republic.helper.metadata_helper import make_iiif_region_url
import republic.parser.republic_file_parser as file_parser
import republic.parser.pagexml.generic_pagexml_parser as pagexml_parser
import republic.model.physical_document_model as pdm
from republic.config.republic_config import base_config


def parse_republic_pagexml_file(pagexml_file: str) -> pdm.PageXMLScan:
    try:
        scan_doc = pagexml_parser.parse_pagexml_file(pagexml_file)
        metadata = file_parser.get_republic_scan_metadata(pagexml_file)
        for field in metadata:
            scan_doc.metadata[field] = metadata[field]
        if 'coords' not in scan_doc:
            scan_doc.coords = pdm.parse_derived_coords(scan_doc.text_regions)
        return scan_doc
    except (AssertionError, KeyError, TypeError, ValueError):
        print(f"Error parsing file {pagexml_file}")
        raise


def get_scan_pagexml(pagexml_file: str,
                     pagexml_data: Union[str, None] = None) -> pdm.PageXMLScan:
    try:
        scan_doc = pagexml_parser.parse_pagexml_file(pagexml_file, pagexml_data=pagexml_data)
    except (AssertionError, KeyError, TypeError):
        print('Error parsing file', pagexml_file)
        raise
    if not scan_doc.coords and scan_doc.text_regions:
        # add scan coordinates if they're not in the XML
        scan_doc.coords = pdm.parse_derived_coords(scan_doc.text_regions)
    for text_region in scan_doc.text_regions:
        if "text_type" in scan_doc.metadata \
                and scan_doc.metadata["text_type"] == "handwritten" \
                and text_region.has_type('date') \
                and len(' '.join([line.text for line in text_region.lines])) > 15:
            text_region.add_type(['main'])
        elif text_region.types.intersection({'date', 'page-number'}):
            text_region.add_type(['header', 'extra'])
        elif text_region.types.intersection({'catch-word', 'signature-mark'}):
            text_region.add_type(['footer', 'extra'])
        elif text_region.types.intersection({'separator'}):
            text_region.add_type(['extra'])
        elif text_region.types.intersection({'index', 'respect', 'resolution'}):
            text_region.add_type(['main'])
    metadata = file_parser.get_republic_scan_metadata(pagexml_file)
    scan_doc.id = metadata['id']
    for field in metadata:
        scan_doc.metadata[field] = metadata[field]
    set_scan_type(scan_doc)
    set_document_children_derived_ids(scan_doc, scan_doc.id)
    return scan_doc


def set_scan_type(scan: pdm.PageXMLDoc) -> None:
    inv_num = scan.metadata["inventory_num"]
    if 3096 <= inv_num <= 3348:
        scan.metadata["resolution_type"] = "ordinaris"
        scan.metadata["text_type"] = "handwritten"
        scan.metadata["normal_odd_end"] = 5500
        scan.metadata["normal_even_end"] = 2800
    elif 3760 <= inv_num <= 3864:
        scan.metadata["resolution_type"] = "ordinaris"
        scan.metadata["text_type"] = "printed"
        scan.metadata["normal_odd_end"] = 4900
        scan.metadata["normal_even_end"] = 2500
    elif 4542 <= inv_num <= 4797:
        scan.metadata["resolution_type"] = "secreet"
        scan.metadata["text_type"] = "handwritten"
        scan.metadata["normal_odd_end"] = 5500
        scan.metadata["normal_even_end"] = 2800
    else:
        raise ValueError(f'Unknown REPUBLIC inventory number: {inv_num}')
    if scan.coords.right == 0:
        scan.metadata['scan_type'] = ['empty_scan']
    elif scan.coords.right <= scan.metadata["normal_even_end"]:
        scan.metadata['scan_type'] = ['single_page']
    elif scan.coords.right <= scan.metadata["normal_odd_end"]:
        scan.metadata['scan_type'] = ['double_page']
    else:
        scan.metadata['scan_type'] = ['special_page']


def get_page_split_widths(item: pdm.PhysicalStructureDoc) -> Tuple[int, int]:
    odd_end, even_end = 4900, 2500
    if "scan_width" in item.metadata:
        # use scan width if it's available
        odd_end = item.metadata["scan_width"]
    elif "scan_width" in item.parent.metadata:
        # check if scan width is available on parent
        odd_end = item.parent.metadata["scan_width"]
    elif "normal_odd_end" in item.metadata:
        # otherwise, default to expected size
        odd_end = item.metadata["normal_odd_end"]
    elif item.parent and "normal_odd_end" in item.parent.metadata:
        # if this item has no normal info, check its parent
        odd_end = item.parent.metadata["normal_odd_end"]
    if "scan_width" in item.metadata:
        # use half of scan width (plus a small margin) if it's available
        even_end = item.metadata["scan_width"] / 2 + 100
    elif "scan_width" in item.parent.metadata:
        # check if scan width is available on parent
        even_end = item.parent.metadata["scan_width"] / 2 + 100
    elif "normal_even_end" in item.metadata:
        # otherwise, default to expected size
        even_end = item.metadata["normal_even_end"]
    elif item.parent and "normal_even_end" in item.parent.metadata:
        # if this item has no normal info, check its parent
        even_end = item.parent.metadata["normal_even_end"]
    return odd_end, even_end


def is_even_side(item: pdm.PhysicalStructureDoc) -> bool:
    odd_end, even_end = get_page_split_widths(item)
    return item.coords.left < even_end - 100 and item.coords.right < even_end


def is_odd_side(item: pdm.PhysicalStructureDoc) -> bool:
    odd_end, even_end = get_page_split_widths(item)
    return item.coords.left > even_end - 300 and item.coords.right > even_end


def is_extra_side(item: pdm.PhysicalStructureDoc) -> bool:
    odd_end, even_end = get_page_split_widths(item)
    return item.coords.right > odd_end and item.coords.left > odd_end - 200


def initialize_pagexml_page(scan_doc: pdm.PageXMLScan, side: str,
                            page_type_index: Dict[int, any]) -> pdm.PageXMLPage:
    """Initialize a pagexml page type document based on the scan metadata."""
    metadata = copy.copy(scan_doc.metadata)
    if 'doc_type' in metadata:
        del metadata['doc_type']
    metadata['type'] = 'page'
    metadata['page_side'] = side
    if side == 'odd':
        metadata['page_num'] = scan_doc.metadata['scan_num'] * 2 - 1
        metadata['id'] = f"{scan_doc.metadata['id']}-page-{metadata['page_num']}"
    elif side == 'even':
        metadata['page_num'] = scan_doc.metadata['scan_num'] * 2 - 2
        metadata['id'] = f"{scan_doc.metadata['id']}-page-{metadata['page_num']}"
    else:
        metadata['page_num'] = scan_doc.metadata['scan_num'] * 2 - 2
        metadata['id'] = f"{scan_doc.metadata['id']}-page-{metadata['page_num']}-extra"
    metadata['scan_id'] = scan_doc.metadata['id']
    page_doc = pdm.PageXMLPage(doc_id=metadata['id'], metadata=metadata, text_regions=[])
    page_doc.set_parent(scan_doc)
    if page_type_index and metadata['page_num'] in page_type_index:
        page_type = page_type_index[metadata['page_num']]
        page_doc.add_type(page_type)
    return page_doc


def split_scan_pages(scan_doc: pdm.PageXMLScan, page_type_index: Dict[int, any] = None,
                     debug: bool = False) -> List[pdm.PageXMLPage]:
    pages: List[pdm.PageXMLPage] = []
    if not scan_doc.text_regions:
        return pages
    page_odd = initialize_pagexml_page(scan_doc, 'odd', page_type_index)
    page_even = initialize_pagexml_page(scan_doc, 'even', page_type_index)
    config = copy.deepcopy(base_config)
    if 3760 <= scan_doc.metadata['inventory_num'] <= 3864:
        max_col_width = 1000
        if scan_doc.metadata['inventory_num'] >= 3804:
            if page_even.has_type('index_page') or page_odd.has_type('index_page'):
                max_col_width = 500
                config['column_gap']['gap_pixel_freq_ratio'] = 0.2
                config['column_gap']['gap_threshold'] = 10
    else:
        max_col_width = 2200
    # print("INITIAL EVEN:", page_even.stats)
    # print(page_even.type)
    # print("INITIAL ODD:", page_odd.stats)
    # print(page_odd.type)
    # page_extra = initialize_pagexml_page(scan_doc, 'extra')
    tr_id_map = {}
    undecided = []
    trs = []
    for tr in scan_doc.text_regions:
        if tr.parent is None:
            print('MISSING PARENT:', tr.id)
        if tr.coords.width > max_col_width:
            # print("SPLITTING COLUMN BECAUSE IT IS TOO WIDE")
            cols, extra = split_lines_on_column_gaps(tr, config, debug=debug)
            if debug:
                for col in cols:
                    print("COLUMN:", col.id)
                    for line in col.lines:
                        print(f"\tLINE {line.coords.left}-{line.coords.right}\t{line.coords.y}\t{line.text}")
            trs += cols
            if extra:
                if debug:
                    print("EXTRA:", extra.id)
                    for line in extra.lines:
                        print(f"\tLINE {line.coords.left}-{line.coords.right}\t{line.coords.y}\t{line.text}")
                trs.append(extra)
        elif is_even_side(tr) or is_odd_side(tr):
            trs.append(tr)
        else:
            cols, extra = split_lines_on_column_gaps(tr, config)
            if debug:
                for col in cols:
                    print("COLUMN:", col.id)
                    for line in col.lines:
                        print(f"\tLINE {line.coords.left}-{line.coords.right}\t{line.coords.y}\t{line.text}")
            trs += cols
            if extra:
                if debug:
                    print("EXTRA:", extra.id)
                    for line in col.lines:
                        print(f"\tLINE {line.coords.left}-{line.coords.right}\t{line.coords.y}\t{line.text}")
                trs.append(extra)
    for text_region in trs:
        if text_region.has_type('main') and text_region.has_type('extra'):
            text_region.remove_type('extra')
        text_region.metadata['scan_id'] = scan_doc.id
        if text_region.metadata and 'type' in text_region.metadata:
            # print("DECIDING EVEN/ODD SIDE")
            if is_even_side(text_region):
                # print("\tEVEN:", text_region.id, text_region.type)
                page_even.add_child(text_region)
            elif is_odd_side(text_region):
                # print("\tODD:", text_region.id, text_region.type)
                page_odd.add_child(text_region)
            else:
                if text_region.coords is None:
                    lines = text_region.get_lines()
                    text_region.coords = pdm.parse_derived_coords(lines)
                print('\tSPLITTING PAGE BOUNDARY OVERLAPPING REGION:', text_region.id, text_region.type)
                # print(config)
                sub_trs, extra = split_lines_on_column_gaps(text_region, config=config, debug=False)
                if extra:
                    sub_trs += [extra]
                print('\t\tnumber of sub text regions:', len(sub_trs))
                for sub_tr in sub_trs:
                    if is_even_side(sub_tr):
                        sub_tr.set_derived_id(page_even.id)
                        sub_tr.set_parent(page_even)
                        # print("BEFORE:", page_even.stats)
                        page_even.add_child(sub_tr)
                        # print("AFTER:", page_even.stats)
                        print('\tSPLIT SUB TR EVEN:', sub_tr.id)
                        # print(sub_tr.type)
                        # print(sub_tr.stats)
                    elif is_odd_side(sub_tr):
                        # print("BEFORE:", page_odd.stats)
                        page_odd.add_child(sub_tr)
                        # print("AFTER:", page_odd.stats)
                        sub_tr.set_derived_id(page_odd.id)
                        sub_tr.set_parent(page_odd)
                        print('\tSPLIT SUB TR ODD:', sub_tr.id)
                        # print(sub_tr.type)
                        # print(sub_tr.stats)
                    else:
                        print('\tUNDECIDED:', sub_tr.id, sub_tr.type)
                        undecided.append(sub_tr)
                # undecided.append(text_region)
        elif text_region.lines:
            # print("TEXTREGION HAS NO TYPE BUT HAS LINES:", text_region.id)
            even_lines = [line for line in text_region.lines if is_even_side(line)]
            odd_lines = [line for line in text_region.lines if is_odd_side(line)]
            if len(even_lines) == 0:
                # print("NO EVEN, MOVE TR TO ODD")
                page_odd.add_child(text_region)
            elif len(odd_lines) == 0:
                # print("NO ODD, MOVE TR TO EVEN")
                page_even.add_child(text_region)
            else:
                # The text region crosses the page boundary. Split the lines into new text regions per
                # page, and create new text regions
                # print("SPLIT LINES")
                odd_region = pdm.PageXMLTextRegion(lines=odd_lines, coords=pdm.parse_derived_coords(odd_lines),
                                                   metadata=text_region.metadata)
                even_region = pdm.PageXMLTextRegion(lines=even_lines, coords=pdm.parse_derived_coords(even_lines),
                                                    metadata=text_region.metadata)
                # print("ODD REGION", odd_region.id, odd_region.stats)
                # print("EVEN REGION", even_region.id, even_region.stats)
                even_region.set_parent(page_even)
                even_region.set_derived_id(page_even.id)
                odd_region.set_parent(page_odd)
                odd_region.set_derived_id(page_odd.id)
                tr_id_map[even_region.id] = text_region.id
                tr_id_map[odd_region.id] = text_region.id
                page_even.add_child(even_region)
                page_odd.add_child(odd_region)
        elif text_region.text_regions:
            # print("TEXTREGION HAS TEXTREGIONS:", text_region.id)
            even_text_regions = [text_region for text_region in text_region.text_regions if is_even_side(text_region)]
            odd_text_regions = [text_region for text_region in text_region.text_regions if is_odd_side(text_region)]
            if len(even_text_regions) == 0:
                # print("NO EVEN, MOVE TR TO ODD")
                page_odd.add_child(text_region)
            elif len(odd_text_regions) == 0:
                # print("NO ODD, MOVE TR TO EVEN")
                page_even.add_child(text_region)
            else:
                # The text region crosses the page boundary. Split the text_regions into new text regions per
                # page, and create new text regions
                # print("SPLIT TEXTREGION")
                odd_region = pdm.PageXMLTextRegion(text_regions=odd_text_regions, metadata=text_region.metadata,
                                                   coords=pdm.parse_derived_coords(odd_text_regions))
                even_region = pdm.PageXMLTextRegion(text_regions=even_text_regions, metadata=text_region.metadata,
                                                    coords=pdm.parse_derived_coords(even_text_regions))
                # print("ODD REGION", odd_region.id, odd_region.stats)
                # print("EVEN REGION", even_region.id, even_region.stats)
                tr_id_map[even_region.id] = text_region.id
                tr_id_map[odd_region.id] = text_region.id
                page_even.add_child(even_region)
                page_odd.add_child(odd_region)
    for page_doc in [page_even, page_odd]:
        if not page_doc.coords:
            if len(page_doc.columns):
                page_doc.coords = pdm.parse_derived_coords(page_doc.columns)
            elif len(page_doc.text_regions):
                page_doc.coords = pdm.parse_derived_coords(page_doc.text_regions)
            else:
                print("Empty page, no coords")
        decided = []
        if page_doc.coords is None:
            continue
        for undecided_tr in undecided:
            if undecided_tr.coords is None:
                print("Skipping undecided textregion without coords", page_doc.id)
                decided.append(undecided_tr)
            if pdm.is_horizontally_overlapping(undecided_tr, page_doc):
                # print("Adding undecided textregion to page", page_doc.id)
                # print("\tundecided textregion coords:", undecided_tr.coords.box)
                # print("\tundecided textregion stats:", undecided_tr.stats)
                page_doc.add_child(undecided_tr)
                decided.append(undecided_tr)
        undecided = [tr for tr in undecided if tr not in decided]
        if page_doc.coords:
            page_doc.metadata['iiif_url'] = derive_pagexml_page_iiif_url(page_doc.metadata['jpg_url'],
                                                                         page_doc.coords)
        else:
            page_doc.metadata['iiif_url'] = scan_doc.metadata['iiif_url']
        if scan_doc.reading_order:
            # if the scan has a reading order, adopt it for the individual pages
            copy_reading_order(scan_doc, page_doc, tr_id_map)
        pages += [page_doc]
    for undecided_tr in undecided:
        if debug:
            print("UNKNOWN:", undecided_tr.id, undecided_tr.stats)
            odd_end, even_end = get_page_split_widths(undecided_tr)
            # print(undecided_tr.parent.metadata)
            print("odd end:", odd_end, "\teven end:", even_end)
            print(undecided_tr.coords.box)
            for line in undecided_tr.lines:
                print(line.coords.x, line.coords.y, line.text)
    return pages


def copy_reading_order(super_doc: pdm.PageXMLDoc, sub_doc: pdm.PageXMLDoc,
                       tr_id_map: Dict[str, str] = None):
    order_number = {}
    extra_trs = 0
    if hasattr(sub_doc, "text_regions"):
        for tr in sub_doc.text_regions:
            if tr_id_map and tr.id in tr_id_map:
                order_number[tr.id] = super_doc.reading_order_number[tr_id_map[tr.id]]
            elif tr.id in super_doc.reading_order_number:
                order_number[tr.id] = super_doc.reading_order_number[tr.id]
            else:
                # If for some reason a text region is not in the reading order list
                # just add it to the end of the reading order
                super_doc.reading_order_number[tr.id] = len(super_doc.reading_order_number) + 1
                order_number[tr.id] = super_doc.reading_order_number[tr.id]
        for ti, tr_id in enumerate(sorted(order_number, key=lambda t: order_number[t])):
            sub_doc.reading_order_number[tr_id] = ti + 1
            sub_doc.reading_order[ti + 1] = tr_id


def derive_pagexml_page_iiif_url(jpg_url: str, coords: pdm.Coords) -> str:
    region = {
        'left': coords.left - 100,
        'top': coords.top - 100,
        'width': coords.width + 200,
        'height': coords.height + 200,
    }
    return make_iiif_region_url(jpg_url, region)


def coords_overlap(item1: pdm.PhysicalStructureDoc, item2: pdm.PhysicalStructureDoc) -> int:
    left = item1.coords.left if item1.coords.left > item2.coords.left else item2.coords.left
    right = item1.coords.right if item1.coords.right < item2.coords.right else item2.coords.right
    # overlap must be positive, else there is no overlap
    return right - left if right - left > 0 else 0


def get_median_normal_line_score(scores, default):
    median_score = np.median(scores)
    normal_scores = [score for score in scores if abs(score - median_score) < 50]
    if len(normal_scores) == 0:
        if default == "min":
            return min(scores)
        else:
            return max(scores)
    try:
        return int(np.median(normal_scores))
    except ValueError:
        print(scores)
        print(median_score)
        print(normal_scores)
        raise


def set_line_alignment(column: pdm.PageXMLColumn):
    if column.stats['lines'] == 0:
        return None
    if len(column.lines) == 0:
        lines = [line for text_region in column.text_regions for line in text_region.lines]
    else:
        lines = column.lines
    lefts = [line.coords.left for line in lines]
    rights = [line.coords.right for line in lines]
    widths = [line.coords.width for line in lines]
    lengths = [len(line.text) if line.text else 0 for line in lines]
    column.metadata["median_normal_left"] = get_median_normal_line_score(lefts, "min")
    column.metadata["median_normal_right"] = get_median_normal_line_score(rights, "max")
    column.metadata["median_normal_width"] = get_median_normal_line_score(widths, "max")
    column.metadata["median_normal_length"] = get_median_normal_line_score(lengths, "max")
    for ti, tr in enumerate(column.text_regions):
        for li, line in enumerate(tr.lines):
            # line.metadata = {"id": column.metadata["id"] + f"-tr-{ti}-line-{li}"}
            if line.coords.width < column.metadata["median_normal_width"] - 40:
                line.metadata["line_width"] = "short"
            else:
                line.metadata["line_width"] = "full"
            if line.coords.left > column.metadata["median_normal_left"] + 40:
                line.metadata["left_alignment"] = "indent"
            elif line.coords.left > column.metadata["median_normal_left"] + 20 \
                    and line.metadata["line_width"] == "short":
                line.metadata["left_alignment"] = "indent"
            else:
                line.metadata["left_alignment"] = "column"
            if line.coords.right < column.metadata["median_normal_right"] - 40:
                line.metadata["right_alignment"] = "indent"
            else:
                line.metadata["right_alignment"] = "column"


#################################################
# Identifying columns using pixel distributions #
#################################################


def compute_pixel_dist(lines: List[pdm.PageXMLTextLine]) -> Counter:
    """Count how many lines are above each horizontal pixel coordinate."""
    pixel_dist = Counter()
    for line in lines:
        pixel_dist.update([pixel for pixel in range(line.coords.left, line.coords.right + 1)])
    return pixel_dist


def new_gap_pixel_interval(pixel: int) -> dict:
    return {"start": pixel, "end": pixel}


def determine_freq_gap_interval(pixel_dist: Counter, freq_threshold: int, config: dict) -> list:
    common_pixels = sorted([pixel for pixel, freq in pixel_dist.items() if freq >= freq_threshold])
    # print("common_pixels:", common_pixels)
    gap_pixel_intervals = []
    if len(common_pixels) == 0:
        return gap_pixel_intervals
    curr_interval = new_gap_pixel_interval(common_pixels[0])
    # print("curr_interval:", curr_interval)
    prev_interval_end = 0
    for curr_index, curr_pixel in enumerate(common_pixels[:-1]):
        next_pixel = common_pixels[curr_index + 1]
        # print("curr:", curr_pixel, "next:", next_pixel, "start:", curr_interval["start"], "end:", curr_interval["end"], "prev_end:", prev_interval_end)
        if next_pixel - curr_pixel < config["column_gap"]["gap_threshold"]:
            curr_interval["end"] = next_pixel
        else:
            # if curr_interval["end"] - curr_interval["start"] < config["column_gap"]["gap_threshold"]:
            if curr_interval["start"] - prev_interval_end < config["column_gap"]["gap_threshold"]:
                # print("skipping interval:", curr_interval, "\tcurr_pixel:", curr_pixel, "next_pixel:", next_pixel)
                continue
            # print("adding interval:", curr_interval, "\tcurr_pixel:", curr_pixel, "next_pixel:", next_pixel)
            gap_pixel_intervals += [curr_interval]
            prev_interval_end = curr_interval["end"]
            curr_interval = new_gap_pixel_interval(next_pixel)
    gap_pixel_intervals += [curr_interval]
    return gap_pixel_intervals


def find_column_gaps(lines: List[pdm.PageXMLTextLine], config: Dict[str, any],
                     debug: bool = False):
    num_column_lines = len(lines) / 2 if len(lines) < 140 else 60
    gap_pixel_freq_threshold = int(num_column_lines * config["column_gap"]["gap_pixel_freq_ratio"])
    if debug:
        print("lines:", len(lines), "gap_pixel_freq_ratio:", config["column_gap"]["gap_pixel_freq_ratio"])
        print("freq_threshold:", gap_pixel_freq_threshold)
    gap_pixel_dist = compute_pixel_dist(lines)
    # if debug:
    #     print("gap_pixel_dist:", gap_pixel_dist)
    gap_pixel_intervals = determine_freq_gap_interval(gap_pixel_dist, gap_pixel_freq_threshold, config)
    return gap_pixel_intervals


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



def split_lines_on_column_gaps(text_region: pdm.PageXMLTextRegion, config: Dict[str, any],
                               overlap_threshold: float = 0.5, debug: bool = False):
    column_ranges = find_column_gaps(text_region.lines, config, debug=debug)
    if debug:
        print("COLUMN RANGES:", column_ranges)
    column_ranges = [col_range for col_range in column_ranges if col_range["end"] - col_range["start"] >= 20]
    column_lines = [[] for _ in range(len(column_ranges) + 1)]
    extra_lines = []
    for line in text_region.lines:
        index = None
        for column_range in column_ranges:
            if line.coords.width == 0:
                print("ZERO WIDTH LINE:", line.coords.x, line.coords.y, line.text)
            if within_column(line, column_range, overlap_threshold=overlap_threshold):
                index = column_ranges.index(column_range)
                column_lines[index].append(line)
        if index is None:
            extra_lines.append(line)
            # print(f"APPENDING EXTRA LINE: {line.coords.left}-{line.coords.right}\t{line.coords.y}\t{line.text}")
    columns = []
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
        if debug:
            print("MERGING OVERLAPPING COLUMNS:", [col.id for col in merge_set])
        merged_col = merge_columns(merge_set, "temp_id", merge_set[0].metadata)
        if text_region.parent and text_region.parent.id:
            merged_col.set_derived_id(text_region.parent.id)
            merged_col.set_parent(text_region.parent)
        else:
            merged_col.set_derived_id(text_region.id)
        non_overlapping_cols.append(merged_col)
    columns = non_overlapping_cols
    if debug:
        print("NUM COLUMNS:", len(columns))
        print("EXTRA LINES BEFORE:", len(extra_lines))
    for line in extra_lines:
        is_column_line = False
        for column in columns:
            # print("EXTRA LINE CHECKING OVERLAP:", line.coords.left, line.coords.right, column.coords.left, column.coords.right)
            if pdm.is_horizontally_overlapping(line, column):
                column.lines.append(line)
                is_column_line = True
        if is_column_line is False:
            # print(f"APPENDING NON-COL LINE: {line.coords.left}-{line.coords.right}\t{line.coords.y}\t{line.text}")
            non_col_lines.append(line)
    extra_lines = non_col_lines
    # print("EXTRA LINES AFTER:", len(extra_lines))
    extra = None
    if len(extra_lines) > 0:
        coords = pdm.parse_derived_coords(extra_lines)
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
        extra_cols, extra_extra = split_lines_on_column_gaps(extra, config)
        if extra_extra:
            extra_cols += [extra_extra]
        for extra_col in extra_cols:
            extra_col.set_parent(text_region.parent)
            if text_region.parent:
                extra_col.set_derived_id(text_region.parent.id)
        columns += extra_cols
        extra = None
    return columns, extra


def get_column_separator(text_region: pdm.PageXMLTextRegion,
                         separators: List[pdm.PageXMLTextRegion]) -> Union[pdm.PageXMLTextRegion, None]:
    column_separator = None
    for separator in separators:
        sep_left = separator.coords.left - 20
        sep_right = separator.coords.right + 20
        if text_region.coords.left < sep_left and text_region.coords.right > sep_right:
            bottom = min(text_region.coords.bottom, separator.coords.bottom)
            top = max(text_region.coords.top, separator.coords.top)
            overlap = bottom - top
            if overlap / text_region.coords.height > 0.7:
                column_separator = separator
                break
    return column_separator


def split_merged_regions(text_regions: List[pdm.PageXMLTextRegion]) -> List[pdm.PageXMLTextRegion]:
    # ignore really short vertical separators as they are probably not real separators
    separators = [tr for tr in text_regions if tr.has_type('separator') if tr.coords.h > 100]
    split_regions = []
    for tr in text_regions:
        if tr.has_type('extra'):
            split_regions.append(tr)
            continue
        column_separator = get_column_separator(tr, separators)
        if column_separator is not None:
            left_lines, right_lines, extra_lines = [], [], []
            for line in tr.lines:
                if line.coords.right < column_separator.coords.right + 20:
                    left_lines.append(line)
                elif line.coords.left > column_separator.coords.left - 20:
                    right_lines.append(line)
                elif line.coords.bottom < column_separator.coords.top:
                    extra_lines.append(line)
                elif line.coords.top > column_separator.coords.bottom:
                    extra_lines.append(line)
                elif line.coords.bottom < 450 and line.coords.top < column_separator.coords.top:
                    # header line with box overlapping separator box
                    extra_lines.append(line)
                elif line.coords.top > 3150 and line.coords.bottom > column_separator.coords.bottom:
                    # section closing line with box overlapping separator box
                    extra_lines.append(line)
                else:
                    extra_lines.append(line)
                    print('MOVING TO EXTRA', line.id, '\t', line.text)
                    # print('ERROR SEPARATING LINES:')
                    # print('column separator box:', column_separator.coords.box)
                    # print('line box:', line.coords.box)
                    # raise ValueError('cannot sort line to left or right of separator')
            if len(left_lines) > 0:
                left_coords = pdm.parse_derived_coords(left_lines)
                left_tr = pdm.PageXMLTextRegion(lines=left_lines, coords=left_coords, metadata=tr.metadata)
                left_tr.set_derived_id(tr.parent.id)
                split_regions.append(left_tr)
                left_tr.type = tr.type
            if len(right_lines) > 0:
                right_coords = pdm.parse_derived_coords(right_lines)
                right_tr = pdm.PageXMLTextRegion(lines=right_lines, coords=right_coords, metadata=tr.metadata)
                right_tr.set_derived_id(tr.parent.id)
                right_tr.type = tr.type
                split_regions.append(right_tr)
            if len(extra_lines) > 0:
                extra_coords = pdm.parse_derived_coords(extra_lines)
                extra_tr = pdm.PageXMLTextRegion(lines=extra_lines, coords=extra_coords, metadata=tr.metadata)
                extra_tr.set_derived_id(tr.parent.id)
                split_regions.append(extra_tr)
                extra_tr.add_type('extra')
                if extra_tr.has_type('main'):
                    extra_tr.remove_type('main')
                split_regions.append(extra_tr)
        else:
            split_regions.append(tr)
    return split_regions


def split_column_regions(page_doc: pdm.PageXMLPage, config: Dict[str, any] = base_config) -> pdm.PageXMLPage:
    column_metadata = {
        'page_id': page_doc.metadata['id'],
        'scan_id': page_doc.metadata['scan_id'],
        'type': ['column', 'pagexml_doc', 'text_region']
    }
    extra_metadata = copy.deepcopy(column_metadata)
    extra_metadata['type'] = 'header'
    columns: List[pdm.PageXMLColumn] = []
    extra_text_regions: List[pdm.PageXMLTextRegion] = []
    text_regions: List[pdm.PageXMLTextRegion] = []
    if "text_type" not in page_doc.metadata:
        set_scan_type(page_doc)
    if page_doc.metadata["text_type"] == "printed":
        max_column_width = 1200
    else:
        max_column_width = 2200
    trs = page_doc.text_regions + page_doc.columns
    for text_region in trs:
        if len(text_region.text_regions) > 0:
            text_regions += text_region.text_regions
        elif text_region.lines and text_region.coords.width > max_column_width:
            config = copy.deepcopy(config)
            config["column_gap"]["gap_pixel_freq_ratio"] = 0.5
            cols, extra = split_lines_on_column_gaps(text_region, config, debug=False)
            text_regions += cols
            for col in cols:
                col.set_parent(page_doc)
                col.set_derived_id(page_doc.id)
            if extra:
                extra.set_parent(page_doc)
                extra.set_derived_id(page_doc.id)
                text_regions.append(extra)
        else:
            text_regions.append(text_region)
        # text_regions += [text_region] if text_region.lines else text_region.text_regions
    text_regions.sort(key=lambda x: x.coords.top)
    text_regions = split_merged_regions(text_regions)
    # remove the text_regions as direct descendants of page
    page_doc.text_regions = []
    for text_region in text_regions:
        if text_region.lines and text_region.coords.width > max_column_width:
            # Wide text_regions are part of the header
            text_region.main_type = 'extra'
            text_region.add_type('extra')
        if text_region.has_type('extra'):
            extra_text_regions += [text_region]
            continue
        # check if this text region overlaps with an existing column
        overlapping_column = None
        for column in columns:
            overlap = coords_overlap(column, text_region)
            tr_overlap_frac = overlap / text_region.coords.width
            cl_overlap_frac = overlap / column.coords.width
            if min(tr_overlap_frac, cl_overlap_frac) > 0.5 and max(tr_overlap_frac, cl_overlap_frac) > 0.75:
                overlapping_column = column
                break
        # if there is an overlapping column, add this text region
        if overlapping_column:
            overlapping_column.text_regions += [text_region]
            overlapping_column.coords = pdm.parse_derived_coords(overlapping_column.text_regions)
        # if no, create a new column for this text region
        else:
            column = pdm.PageXMLColumn(coords=pdm.parse_derived_coords([text_region]), metadata=column_metadata,
                                       text_regions=[text_region])
            columns += [column]
    for column in columns:
        if not column.coords:
            print('COLUMN NO COORDS:', column)
            raise KeyError('Column has no "coords" property.')
    columns.sort(key=lambda x: x.coords.left)
    for ci, column in enumerate(columns):
        column.text_regions.sort(key=lambda x: x.coords.top)
        column.metadata = column_metadata
        column.set_derived_id(column.metadata['scan_id'])
        set_line_alignment(column)
        copy_reading_order(page_doc, column)
        column.metadata['iiif_url'] = derive_pagexml_page_iiif_url(page_doc.metadata['jpg_url'], column.coords)
    if extra_text_regions:
        extra_coords = pdm.parse_derived_coords(extra_text_regions)
        extra = pdm.PageXMLTextRegion(metadata=extra_metadata, coords=extra_coords, text_regions=extra_text_regions)
        extra.main_type = 'extra'
        extra.metadata['iiif_url'] = derive_pagexml_page_iiif_url(page_doc.metadata['jpg_url'], extra.coords)
        extra.set_derived_id(extra.metadata['scan_id'])
    new_page = pdm.PageXMLPage(doc_id=page_doc.id, doc_type=page_doc.type, coords=page_doc.coords,
                               metadata=page_doc.metadata, columns=columns, extra=extra_text_regions,
                               reading_order=page_doc.reading_order)
    new_page.set_parent(page_doc.parent)
    return new_page


def swap_reading_order_ids(doc: pdm.PageXMLDoc, text_region: pdm.PageXMLTextRegion,
                           old_id: str) -> None:
    doc.reading_order_number[text_region.id] = doc.reading_order_number[old_id]
    del doc.reading_order_number[old_id]
    doc.reading_order[doc.reading_order_number[text_region.id]] = text_region.id


def set_document_children_derived_ids(doc: pdm.PageXMLDoc, scan_id: str):
    pdm.set_parentage(doc)
    doc_text_regions: List[pdm.PageXMLTextRegion] = []
    if hasattr(doc, 'text_regions'):
        doc_text_regions += doc.text_regions
    if hasattr(doc, 'columns'):
        doc_text_regions += doc.columns
    if hasattr(doc, 'extra'):
        doc_text_regions += doc.extra
    for text_region in doc_text_regions:
        if text_region.id is None:
            text_region.set_derived_id(scan_id)
        if 'scan_id' not in text_region.metadata:
            text_region.metadata['scan_id'] = scan_id
        old_id = text_region.id
        text_region.set_derived_id(scan_id)
        if doc.reading_order and old_id in doc.reading_order_number:
            if old_id == text_region.id:
                continue
            swap_reading_order_ids(doc, text_region, old_id)
        if text_region.has_type('column'):
            id_field = 'column_id'
        elif text_region.has_type('header'):
            id_field = 'header_id'
        elif text_region.has_type('footer'):
            id_field = 'footer_id'
        elif doc.has_type('page'):
            id_field = 'extra_id'
        else:
            id_field = 'text_region_id'
        id_value = text_region.id
        if hasattr(text_region, 'text_regions'):
            for inner_region in text_region.text_regions:
                if inner_region.id is None:
                    inner_region.set_derived_id(scan_id)
                if 'scan_id' not in inner_region.metadata:
                    inner_region.metadata['scan_id'] = scan_id
                inner_region.metadata[id_field] = id_value
                inner_region.set_derived_id(scan_id)
                for line in inner_region.lines:
                    if line.id is None:
                        line.set_derived_id(scan_id)
                    line.metadata[id_field] = id_value
                    if 'scan_id' in text_region.metadata:
                        line.metadata['scan_id'] = text_region.metadata['scan_id']
                    if 'page_id' in text_region.metadata:
                        line.metadata['page_id'] = text_region.metadata['page_id']
                    line.set_derived_id(scan_id)
        if hasattr(text_region, 'lines'):
            for line in text_region.lines:
                if line.id is None:
                    line.set_derived_id(scan_id)
                line.metadata[id_field] = id_value
                if 'scan_id' in text_region.metadata:
                    line.metadata['scan_id'] = text_region.metadata['scan_id']
                if 'page_id' in text_region.metadata:
                    line.metadata['page_id'] = text_region.metadata['page_id']
                line.set_derived_id(scan_id)


def split_pagexml_scan(scan_doc: pdm.PageXMLScan, page_type_index: Dict[int, any],
                       debug: bool = False) -> List[pdm.PageXMLPage]:
    split_columns = True
    has_wide_main = False
    # print("SCAN TYPE:", scan_doc.type)
    for text_region in scan_doc.text_regions:
        if text_region.has_type('main') and text_region.coords.width > 1100:
            if debug:
                print('WIDE TEXT REGION:', text_region.id)
            has_wide_main = True
        if text_region.has_type('main'):
            split_columns = False
    if has_wide_main:
        split_columns = True
    pages = split_scan_pages(scan_doc, page_type_index, debug=debug)
    if debug:
        print('\n')
        for page in pages:
            print(page.id)
            for tr in page.columns + page.extra + page.text_regions:
                print(f"{tr.coords.x: >4}-{tr.coords.y: >4}\t{tr.coords.w}\t{tr.type}")
        print('\n')
    if split_columns:
        if debug:
            print('Splitting page columns into narrower sub columns')
        pages = [split_column_regions(page_doc) for page_doc in pages]
    else:
        for page in pages:
            for text_region in page.text_regions:
                if text_region.has_type('main') and text_region.has_type('extra'):
                    text_region.remove_type('extra')
                if not text_region.type or not text_region.has_type('main') or text_region.has_type('extra'):
                    text_region.metadata['iiif_url'] = derive_pagexml_page_iiif_url(page.metadata['jpg_url'],
                                                                                    text_region.coords)
                    page.add_child(text_region, as_extra=True)
                    if debug:
                        print('adding tr as extra:', text_region.id)
                else:
                    # turn the text region into a column
                    column = pdm.PageXMLColumn(metadata=text_region.metadata, coords=text_region.coords,
                                               text_regions=text_region.text_regions,
                                               lines=text_region.lines)
                    column.set_derived_id(scan_doc.id)
                    column.metadata['iiif_url'] = derive_pagexml_page_iiif_url(page.metadata['jpg_url'],
                                                                               column.coords)
                    if debug:
                        print('adding tr as column:', text_region.id)
                    page.add_child(column)
            page.text_regions = []
    for page in pages:
        for text_region in page.columns + page.extra:
            text_region.set_derived_id(scan_doc.id)
            if debug:
                print('setting derived ID:', text_region.id, 'with parent', scan_doc.id)
            if text_region.has_type('column'):
                id_field = 'column_id'
            elif text_region.has_type('header'):
                id_field = 'header_id'
            elif text_region.has_type('footer'):
                id_field = 'footer_id'
            else:
                id_field = 'extra_id'
            id_value = text_region.id
            for inner_region in text_region.text_regions:
                inner_region.metadata[id_field] = id_value
                inner_region.set_derived_id(scan_doc.id)
                inner_region.metadata['iiif_url'] = derive_pagexml_page_iiif_url(page.metadata['jpg_url'],
                                                                                 inner_region.coords)
                for line in inner_region.lines:
                    line.metadata[id_field] = id_value
                    line.metadata['scan_id'] = text_region.metadata['scan_id']
                    line.metadata['page_id'] = text_region.metadata['page_id']
                    line.set_derived_id(scan_doc.id)
            for line in text_region.lines:
                line.metadata[id_field] = id_value
                line.metadata['scan_id'] = text_region.metadata['scan_id']
                line.metadata['page_id'] = text_region.metadata['page_id']
                line.set_derived_id(scan_doc.id)
    return pages


def column_bounding_box_surrounds_lines(column: pdm.PageXMLColumn) -> bool:
    """Check if the column coordinates contain the coordinate
    boxes of the column lines."""
    for line in column.get_lines():
        if not elements_overlap(column, line, threshold=0.6):
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


def elements_overlap(element1: pdm.PageXMLDoc, element2: pdm.PageXMLDoc,
                     threshold: float = 0.5) -> bool:
    """Check if two elements have overlapping coordinates."""
    v_overlap = pdm.vertical_overlap(element1.coords, element2.coords)
    h_overlap = pdm.horizontal_overlap(element1.coords, element2.coords)
    if v_overlap / element1.coords.height > threshold:
        if h_overlap / element1.coords.width > threshold:
            return True
    if v_overlap / element2.coords.height > threshold:
        if h_overlap / element2.coords.width > threshold:
            return True
    else:
        return False


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


def has_overlapping_columns(page: pdm.PageXMLPage) -> bool:
    """Determine whether a page has columns that
    mostly overlap with each other"""
    for ci, curr_column in enumerate(page.columns):
        if ci == len(page.columns) - 1:
            break
        for next_column in page.columns[ci + 1:]:
            if elements_overlap(curr_column, next_column, threshold=0.8):
                print('Overlapping columns!')
                print('\t', curr_column.coords.box)
                print('\t', next_column.coords.box)
    return False


def merge_columns(columns: List[pdm.PageXMLColumn],
                  doc_id: str, metadata: dict) -> pdm.PageXMLColumn:
    """Merge two columns into one, sorting lines by baseline height."""
    merged_lines = [line for col in columns for line in col.get_lines()]
    merged_lines = list(set(merged_lines))
    sorted_lines = sorted(merged_lines, key=lambda x: x.baseline.y)
    merged_coords = pdm.parse_derived_coords(sorted_lines)
    merged_col = pdm.PageXMLColumn(doc_id=doc_id, doc_type='index_column',
                                   metadata=metadata, coords=merged_coords,
                                   lines=merged_lines)
    return merged_col


def has_text_columns(page: pdm.PageXMLPage, num_page_cols: int = 2) -> bool:
    for column in page.columns:
        if is_full_text_column(column, num_page_cols=num_page_cols):
            return True
    return False


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


def get_page_full_text_columns(page: pdm.PageXMLPage) -> List[pdm.PageXMLColumn]:
    """Return the full-text columns of a page. Merge any overlapping extra
    columns into the full-text columns."""
    full_text_columns = []
    extra_columns = []
    for column in page.columns:
        try:
            column_type = determine_column_type(column)
        except TypeError:
            column_type = None
        if column_type == 'full_text':
            full_text_columns.append(column)
        elif column_type == 'margin':
            continue
        elif column_type == 'extra_text':
            extra_columns.append(column)
        else:
            continue
    merged_columns = []
    for full_text_col in full_text_columns:
        for extra_col in extra_columns:
            if elements_overlap(extra_col, full_text_col):
                # merge columns into new full_text_col
                # make sure multiple merges into the same full text
                # columns are cumulative
                full_text_col = merge_columns(extra_col, full_text_col,
                                              full_text_col.id, full_text_col.metadata)
        # keep tracked of the new merged columns
        merged_columns.append(full_text_col)
    return merged_columns


def make_derived_column(lines: List[pdm.PageXMLTextLine], metadata: dict, page_id: str) -> pdm.PageXMLColumn:
    """Make a new PageXMLColumn based on a set of lines, column metadata and a page_id."""
    coords = pdm.parse_derived_coords(lines)
    column = pdm.PageXMLColumn(metadata=metadata, coords=coords, lines=lines)
    column.set_derived_id(page_id)
    return column


def is_title_page(page: pdm.PageXMLPage) -> bool:
    """Check whether a page is a Republic title page."""
    # title pages are always on the right side of the scan
    # and have an uneven page number
    if page.metadata['page_num'] % 2 == 0:
        return False
    num_title_lines = 0
    for line in page.get_lines():
        if line.coords.left < 3500 and line.coords.right > 3600:
            if line.coords.width / len(line.text) > 30:
                num_title_lines += 1
    return num_title_lines > 2


def parse_title_page_columns(page: pdm.PageXMLPage) -> pdm.PageXMLPage:
    extra_columns = page.extra
    text_columns = []
    for column in page.columns:
        if not is_text_column(column):
            extra_columns.append(column)
            continue
        if column.stats['lines'] < 10:
            extra_columns.append(column)
            continue
        if column.coords.width < 1000:
            text_columns.append(column)
            continue
        lines = sorted(column.get_lines(), key=lambda line: line.coords.y)
        last_title_line_index = -1
        for li, line in enumerate(lines):
            if line.coords.left < 3400 and line.coords.right > 3600:
                last_title_line_index = li
        title_lines = lines[:last_title_line_index + 1]
        if len(title_lines) > 0:
            title_column = make_derived_column(title_lines, column.metadata, page.id)
            extra_columns.append(title_column)
        body_lines = lines[last_title_line_index + 1:]
        left_col_lines, right_col_lines = [], []
        for line in body_lines:
            if line.coords.right < 3600:
                left_col_lines.append(line)
            elif line.coords.left > 3400 and line.coords.right >= 3600:
                right_col_lines.append(line)
            else:
                print(line.coords.box)
                print(line.text)
                raise TypeError('cannot select appropriate column')
        if len(left_col_lines) > 0:
            left_column = make_derived_column(left_col_lines, column.metadata, page.metadata['scan_id'])
            text_columns.append(left_column)
        if len(right_col_lines) > 0:
            right_column = make_derived_column(right_col_lines, column.metadata, page.metadata['scan_id'])
            text_columns.append(right_column)
    new_page_coords = pdm.parse_derived_coords(extra_columns + text_columns)
    new_page = pdm.PageXMLPage(metadata=page.metadata, coords=new_page_coords, columns=text_columns,
                               text_regions=page.text_regions, extra=extra_columns)
    new_page.set_derived_id(page.metadata['scan_id'])
    return new_page
