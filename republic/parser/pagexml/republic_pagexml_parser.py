from typing import Dict, List, Union
from collections import Counter
import copy
import re

import numpy as np

from republic.helper.metadata_helper import make_iiif_region_url
import republic.parser.republic_file_parser as file_parser
import republic.parser.pagexml.generic_pagexml_parser as pagexml_parser
import republic.model.physical_document_model as pdm


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
    # print('Parsing file', pagexml_file)
    try:
        scan_doc = pagexml_parser.parse_pagexml_file(pagexml_file, pagexml_data=pagexml_data)
        scan_doc.reading_order = {}
    except (AssertionError, KeyError, TypeError):
        print('Error parsing file', pagexml_file)
        raise
    if not scan_doc.coords and scan_doc.text_regions:
        # add scan coordinates if they're not in the XML
        scan_doc.coords = pdm.parse_derived_coords(scan_doc.text_regions)
    for text_region in scan_doc.text_regions:
        if text_region.types.intersection({'date', 'page-number'}):
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
    if scan_doc.coords.right == 0:
        scan_doc.metadata['scan_type'] = ['empty_scan']
    elif scan_doc.coords.right < 2500:
        scan_doc.metadata['scan_type'] = ['single_page']
    elif scan_doc.coords.right < 4900:
        scan_doc.metadata['scan_type'] = ['double_page']
    else:
        scan_doc.metadata['scan_type'] = ['special_page']
    set_document_children_derived_ids(scan_doc, scan_doc.id)
    return scan_doc


def is_even_side(item: pdm.PhysicalStructureDoc) -> bool:
    return item.coords.right < 2500


def is_odd_side(item: pdm.PhysicalStructureDoc) -> bool:
    return item.coords.left > 2200 and item.coords.right > 2500


def is_extra_side(item: pdm.PhysicalStructureDoc) -> bool:
    return item.coords.right > 4900 and item.coords.left > 4700


def initialize_pagexml_page(scan_doc: pdm.PageXMLScan, side: str) -> pdm.PageXMLPage:
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
    return page_doc


def split_scan_pages(scan_doc: pdm.PageXMLScan) -> List[pdm.PageXMLPage]:
    pages: List[pdm.PageXMLPage] = []
    if not scan_doc.text_regions:
        return pages
    page_odd = initialize_pagexml_page(scan_doc, 'odd')
    page_even = initialize_pagexml_page(scan_doc, 'even')
    # page_extra = initialize_pagexml_page(scan_doc, 'extra')
    for text_region in scan_doc.text_regions:
        text_region.metadata['scan_id'] = scan_doc.id
        if text_region.metadata and 'type' in text_region.metadata:
            if is_even_side(text_region):
                page_even.add_child(text_region)
                # print("stats after adding child", page_even.stats)
            elif is_odd_side(text_region):
                page_odd.add_child(text_region)
                # print("stats after adding child", page_odd.stats)
        elif text_region.lines:
            even_lines = [line for line in text_region.lines if is_even_side(line)]
            odd_lines = [line for line in text_region.lines if is_odd_side(line)]
            if len(even_lines) == 0:
                page_odd.add_child(text_region)
                # print("stats after adding child", page_odd.stats)
            elif len(odd_lines) == 0:
                page_even.add_child(text_region)
                # print("stats after adding child", page_even.stats)
            else:
                # The text region crosses the page boundary. Split the lines into new text regions per
                # page, and create new text regions
                odd_region = pdm.PageXMLTextRegion(lines=odd_lines, coords=pdm.parse_derived_coords(odd_lines),
                                                   metadata=text_region.metadata)
                even_region = pdm.PageXMLTextRegion(lines=even_lines, coords=pdm.parse_derived_coords(even_lines),
                                                    metadata=text_region.metadata)
                page_even.add_child(even_region)
                # print("stats after adding child", page_even.stats)
                page_odd.add_child(odd_region)
                # print("stats after adding child", page_odd.stats)
        elif text_region.text_regions:
            even_text_regions = [text_region for text_region in text_region.text_regions if is_even_side(text_region)]
            odd_text_regions = [text_region for text_region in text_region.text_regions if is_odd_side(text_region)]
            if len(even_text_regions) == 0:
                page_odd.add_child(text_region)
                # print("stats after adding child", page_odd.stats)
            elif len(odd_text_regions) == 0:
                page_even.add_child(text_region)
                # print("stats after adding child", page_even.stats)
            else:
                # The text region crosses the page boundary. Split the text_regions into new text regions per
                # page, and create new text regions
                odd_region = pdm.PageXMLTextRegion(text_regions=odd_text_regions, metadata=text_region.metadata,
                                                   coords=pdm.parse_derived_coords(odd_text_regions))
                even_region = pdm.PageXMLTextRegion(text_regions=even_text_regions, metadata=text_region.metadata,
                                                    coords=pdm.parse_derived_coords(even_text_regions))
                page_even.add_child(even_region)
                # print("stats after adding child", page_even.stats)
                page_odd.add_child(odd_region)
                # print("stats after adding child", page_odd.stats)
    for page_doc in [page_even, page_odd]:
        if not page_doc.coords:
            if len(page_doc.columns):
                page_doc.coords = pdm.parse_derived_coords(page_doc.columns)
            elif len(page_doc.text_regions):
                page_doc.coords = pdm.parse_derived_coords(page_doc.text_regions)
            if page_doc.coords:
                page_doc.metadata['iiif_url'] = derive_pagexml_page_iiif_url(page_doc.metadata['jpg_url'],
                                                                             page_doc.coords)
            else:
                page_doc.metadata['iiif_url'] = scan_doc.metadata['iiif_url']
        pages += [page_doc]
    return pages


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
    lines = [line for text_region in column.text_regions for line in text_region.lines]
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
        pixel_dist.update([pixel for pixel in range(line.coords.left, line.coords.right+1)])
    return pixel_dist


def new_gap_pixel_interval(pixel: int) -> dict:
    return {"start": pixel, "end": pixel}


def determine_freq_gap_interval(pixel_dist: Counter, freq_threshold: int, config: dict) -> list:
    common_pixels = sorted([pixel for pixel, freq in pixel_dist.items() if freq > freq_threshold])
    gap_pixel_intervals = []
    if len(common_pixels) == 0:
        return gap_pixel_intervals
    curr_interval = new_gap_pixel_interval(common_pixels[0])
    for curr_index, curr_pixel in enumerate(common_pixels[:-1]):
        next_pixel = common_pixels[curr_index+1]
        if next_pixel - curr_pixel < 100:
            curr_interval["end"] = next_pixel
        else:
            if curr_interval["end"] - curr_interval["start"] < config["column_gap"]["gap_threshold"]:
                # print("skipping interval:", curr_interval, "\tcurr_pixel:", curr_pixel, "next_pixel:", next_pixel)
                continue
            # print("adding interval:", curr_interval, "\tcurr_pixel:", curr_pixel, "next_pixel:", next_pixel)
            gap_pixel_intervals += [curr_interval]
            curr_interval = new_gap_pixel_interval(next_pixel)
    gap_pixel_intervals += [curr_interval]
    return gap_pixel_intervals


def find_column_gaps(lines: List[pdm.PageXMLTextLine], config: Dict[str, any]):
    gap_pixel_freq_threshold = int(len(lines) / 2 * config["column_gap"]["gap_pixel_freq_ratio"])
    gap_pixel_dist = compute_pixel_dist(lines)
    gap_pixel_intervals = determine_freq_gap_interval(gap_pixel_dist, gap_pixel_freq_threshold, config)
    return gap_pixel_intervals


def within_column(line, column_range):
    start = max([line.coords.left, column_range["start"]])
    end = min([line.coords.right, column_range["end"]])
    overlap = end - start if end > start else 0
    return overlap / line.coords.width > 0.5


def split_lines_on_column_gaps(page_doc, config: Dict[str, any]):
    column_ranges = find_column_gaps(page_doc.extra[0].lines, config)
    columns = [[] for _ in range(len(column_ranges)+1)]
    extra = []
    for line in page_doc.extra[0].lines:
        print(line.coords.left, line.coords.right)
        index = None
        for column_range in column_ranges:
            if within_column(line, column_range):
                index = column_ranges.index(column_range)
                print("column:", index)
                columns[index].append(line)
        if index is None:
            extra.append(line)
            print(line.text)
        print()
    return columns, extra


def split_column_regions(page_doc: pdm.PageXMLPage) -> pdm.PageXMLPage:
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
    for text_region in page_doc.text_regions:
        text_regions += [text_region] if text_region.lines else text_region.text_regions
    text_regions.sort(key=lambda x: x.coords.top)
    for text_region in text_regions:
        if text_region.lines and text_region.coords.width > 1200:
            # Wide text_regions are part of the header
            extra_text_regions += [text_region]
            text_region.main_type = 'extra'
            text_region.add_type('extra')
            continue
        # check if this text region overlaps with an existing column
        overlapping_column = None
        for column in columns:
            overlap = coords_overlap(column, text_region)
            #      column['coords']['left'], column['coords']['right'])
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
        column.metadata['iiif_url'] = derive_pagexml_page_iiif_url(page_doc.metadata['jpg_url'], column.coords)
    if extra_text_regions:
        extra_coords = pdm.parse_derived_coords(extra_text_regions)
        extra = pdm.PageXMLTextRegion(metadata=extra_metadata, coords=extra_coords, text_regions=extra_text_regions)
        extra.main_type = 'extra'
        extra.metadata['iiif_url'] = derive_pagexml_page_iiif_url(page_doc.metadata['jpg_url'], extra.coords)
        extra.set_derived_id(extra.metadata['scan_id'])
    new_page = pdm.PageXMLPage(doc_id=page_doc.id, doc_type=page_doc.type, coords=page_doc.coords,
                               metadata=page_doc.metadata, columns=columns, extra=extra_text_regions)
    new_page.set_parent(page_doc.parent)
    return new_page


def set_document_children_derived_ids(doc: pdm.PageXMLDoc, scan_id: str):
    doc.set_parentage()
    doc_text_regions: List[pdm.PageXMLDoc] = []
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
        # print('\tcolumn id:', text_region.id)
        # print('\tparent id:', text_region.parent.id)
        text_region.set_derived_id(scan_id)
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


def split_pagexml_scan(scan_doc: pdm.PageXMLScan) -> List[pdm.PageXMLPage]:
    split_columns = True
    for text_region in scan_doc.text_regions:
        if text_region.has_type('main'):
            split_columns = False
    pages = split_scan_pages(scan_doc)
    if split_columns:
        pages = [split_column_regions(page_doc) for page_doc in pages]
    else:
        for page in pages:
            for text_region in page.text_regions:
                if not text_region.type or text_region.has_type('extra'):
                    text_region.metadata['iiif_url'] = derive_pagexml_page_iiif_url(page.metadata['jpg_url'],
                                                                                    text_region.coords)
                    page.add_child(text_region, as_extra=True)
                else:
                    # turn the text region into a column
                    column = pdm.PageXMLColumn(metadata=text_region.metadata, coords=text_region.coords,
                                               text_regions=text_region.text_regions,
                                               lines=text_region.lines)
                    column.set_derived_id(scan_doc.id)
                    column.metadata['iiif_url'] = derive_pagexml_page_iiif_url(page.metadata['jpg_url'],
                                                                               column.coords)
                    page.add_child(column)
            page.text_regions = []
    for page in pages:
        for text_region in page.columns + page.extra:
            text_region.set_derived_id(scan_doc.id)
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
    # print([column.parent.id for page in pages for column in page.columns])
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
        for next_column in page.columns[ci+1:]:
            if elements_overlap(curr_column, next_column, threshold=0.8):
                print('Overlapping columns!')
                print('\t', curr_column.coords.box)
                print('\t', next_column.coords.box)
    return False


def merge_columns(column1: pdm.PageXMLColumn, column2: pdm.PageXMLColumn,
                  doc_id: str, metadata: dict) -> pdm.PageXMLColumn:
    """Merge two columns into one, sorting lines by baseline height."""
    merged_lines = column1.get_lines() + column2.get_lines()
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
        # print('column:', column.id)
        # print('column:', column.coords.box)
        # print('column:', column.stats)
        lines = sorted(column.get_lines(), key=lambda line: line.coords.y)
        last_title_line_index = -1
        for li, line in enumerate(lines):
            # print(f"{line.coords.y}\t{line.coords.left}, {line.coords.right}\t{line.text}")
            if line.coords.left < 3400 and line.coords.right > 3600:
                # print(f"TITLE: {line.coords.y}\t{line.coords.left}, {line.coords.right}\t{line.text}")
                last_title_line_index = li
        title_lines = lines[:last_title_line_index+1]
        if len(title_lines) > 0:
            title_column = make_derived_column(title_lines, column.metadata, page.id)
            extra_columns.append(title_column)
        body_lines = lines[last_title_line_index+1:]
        # print('total lines:', len(lines))
        # print('title lines:', len(title_lines))
        # print('body lines:', len(body_lines))
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
        # print('left_col lines:', len(left_col_lines))
        # print('right_col lines:', len(right_col_lines))
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
    # print(new_page.stats)
    # print('num extra:', len(new_page.extra), len(extra_columns))
    # print('num text_regions:', len(page.text_regions))
    # print('num columns:', len(new_page.columns), len(text_columns))
    # for col in text_columns:
    #     print('text col:', col.id)
    # for col in new_page.columns:
    #     print('page col:', col.id, col.stats)
    return new_page
