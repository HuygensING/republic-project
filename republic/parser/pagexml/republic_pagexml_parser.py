from typing import Dict, List, Union
from collections import Counter
import copy

import numpy as np

from republic.helper.metadata_helper import make_iiif_region_url
import republic.parser.republic_file_parser as file_parser
import republic.parser.pagexml.generic_pagexml_parser as pagexml_parser
from republic.parser.pagexml.test_republic_pagexml_assertions import test_republic_pagexml_assertions
from republic.model.physical_document_model import Coords, parse_derived_coords, PhysicalStructureDoc
from republic.model.physical_document_model import PageXMLTextRegion, PageXMLColumn, PageXMLScan, PageXMLPage
from republic.model.physical_document_model import PageXMLTextLine, PageXMLDoc


def parse_republic_pagexml_file(pagexml_file: str) -> PageXMLScan:
    try:
        scan_doc = pagexml_parser.parse_pagexml_file(pagexml_file)
        metadata = file_parser.get_republic_scan_metadata(pagexml_file)
        for field in metadata:
            scan_doc.metadata[field] = metadata[field]
        if 'coords' not in scan_doc:
            scan_doc.coords = parse_derived_coords(scan_doc.text_regions)
        return scan_doc
    except (AssertionError, KeyError, TypeError, ValueError):
        print(f"Error parsing file {pagexml_file}")
        raise


def get_scan_pagexml(pagexml_file: str, inventory_config: dict,
                     pagexml_data: Union[str, None] = None) -> PageXMLScan:
    # print('Parsing file', pagexml_file)
    try:
        scan_json = pagexml_parser.read_pagexml_file(pagexml_file, pagexml_data=pagexml_data)
        test_republic_pagexml_assertions(scan_json)
        scan_doc = pagexml_parser.parse_pagexml_json(scan_json)
    except (AssertionError, KeyError, TypeError):
        print('Error parsing file', pagexml_file)
        raise
    if not scan_doc.coords and scan_doc.text_regions:
        # add scan coordinates if they're not in the XML
        scan_doc.coords = parse_derived_coords(scan_doc.text_regions)
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


def is_even_side(item: PhysicalStructureDoc) -> bool:
    return item.coords.right < 2500


def is_odd_side(item: PhysicalStructureDoc) -> bool:
    return item.coords.left > 2200 and item.coords.right > 2500


def is_extra_side(item: PhysicalStructureDoc) -> bool:
    return item.coords.right > 4900 and item.coords.left > 4700


def initialize_pagexml_page(scan_doc: PageXMLScan, side: str) -> PageXMLPage:
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
    page_doc = PageXMLPage(doc_id=metadata['id'], metadata=metadata, text_regions=[])
    page_doc.set_parent(scan_doc)
    return page_doc


def split_scan_pages(scan_doc: PageXMLScan) -> List[PageXMLPage]:
    pages: List[PageXMLPage] = []
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
                odd_region = PageXMLTextRegion(lines=odd_lines, coords=parse_derived_coords(odd_lines),
                                               metadata=text_region.metadata)
                even_region = PageXMLTextRegion(lines=even_lines, coords=parse_derived_coords(even_lines),
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
                odd_region = PageXMLTextRegion(text_regions=odd_text_regions, metadata=text_region.metadata,
                                               coords=parse_derived_coords(odd_text_regions))
                even_region = PageXMLTextRegion(text_regions=even_text_regions, metadata=text_region.metadata,
                                                coords=parse_derived_coords(even_text_regions))
                page_even.add_child(even_region)
                # print("stats after adding child", page_even.stats)
                page_odd.add_child(odd_region)
                # print("stats after adding child", page_odd.stats)
    for page_doc in [page_even, page_odd]:
        if not page_doc.coords:
            if len(page_doc.columns):
                page_doc.coords = parse_derived_coords(page_doc.columns)
            elif len(page_doc.text_regions):
                page_doc.coords = parse_derived_coords(page_doc.text_regions)
            if page_doc.coords:
                page_doc.metadata['iiif_url'] = derive_pagexml_page_iiif_url(page_doc.metadata['jpg_url'],
                                                                             page_doc.coords)
            else:
                page_doc.metadata['iiif_url'] = scan_doc.metadata['iiif_url']
        pages += [page_doc]
    return pages


def derive_pagexml_page_iiif_url(jpg_url: str, coords: Coords) -> str:
    region = {
        'left': coords.left - 100,
        'top': coords.top - 100,
        'width': coords.width + 200,
        'height': coords.height + 200,
    }
    return make_iiif_region_url(jpg_url, region)


def coords_overlap(item1: PhysicalStructureDoc, item2: PhysicalStructureDoc) -> int:
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


def set_line_alignment(column: PageXMLColumn):
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


def compute_pixel_dist(lines: List[PageXMLTextLine]) -> Counter:
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


def find_column_gaps(lines: List[PageXMLTextLine], config: Dict[str, any]):
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
    columns = [[] for i in range(len(column_ranges)+1)]
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


def split_column_regions(page_doc: PageXMLPage) -> PageXMLPage:
    column_metadata = {
        'page_id': page_doc.metadata['id'],
        'scan_id': page_doc.metadata['scan_id'],
        'type': ['column', 'pagexml_doc', 'text_region']
    }
    extra_metadata = copy.deepcopy(column_metadata)
    extra_metadata['type'] = 'header'
    columns: List[PageXMLColumn] = []
    extra_text_regions: List[PageXMLTextRegion] = []
    text_regions: List[PageXMLTextRegion] = []
    for text_region in page_doc.text_regions:
        text_regions += [text_region] if text_region.lines else text_region.text_regions
    text_regions.sort(key=lambda x: x.coords.top)
    for text_region in text_regions:
        if text_region.lines and text_region.coords.width > 1200:
            # Wide text_regions are part of the header
            extra_text_regions += [text_region]
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
            overlapping_column.coords = parse_derived_coords(overlapping_column.text_regions)
        # if no, create a new column for this text region
        else:
            column = PageXMLColumn(coords=parse_derived_coords([text_region]), metadata=column_metadata,
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
        extra_coords = parse_derived_coords(extra_text_regions)
        extra = PageXMLTextRegion(metadata=extra_metadata, coords=extra_coords, text_regions=extra_text_regions)
        extra.main_type = 'extra'
        extra.metadata['iiif_url'] = derive_pagexml_page_iiif_url(page_doc.metadata['jpg_url'], extra.coords)
        extra.set_derived_id(extra.metadata['scan_id'])
    else:
        extra = None
    new_page = PageXMLPage(doc_id=page_doc.id, doc_type=page_doc.type, coords=page_doc.coords,
                           metadata=page_doc.metadata, columns=columns, extra=extra_text_regions)
    new_page.set_parent(page_doc.parent)
    return new_page


def set_document_children_derived_ids(doc: PageXMLDoc, scan_id: str):
    doc.set_parentage()
    doc_text_regions: List[PageXMLDoc] = []
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


def split_pagexml_scan(scan_doc: PageXMLScan) -> List[PageXMLPage]:
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
                    column = PageXMLColumn(metadata=text_region.metadata, coords=text_region.coords,
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
