import copy
from collections import Counter
from typing import Dict, List, Tuple, Union

import pagexml.model.physical_document_model as pdm
from fuzzy_search import FuzzyPhraseSearcher
from pagexml.helper.pagexml_helper import regions_overlap

import republic.helper.pagexml_helper as pagexml_helper
import republic.parser.pagexml.republic_column_parser as column_parser
# import republic.model.physical_document_model as pdm
from republic.helper.metadata_helper import make_iiif_region_url
from republic.config.republic_config import base_config
from republic.parser.logical.date_parser import check_line_starts_with_week_day_name
# from republic.parser.pagexml.republic_column_parser import split_lines_on_column_gaps
# from republic.parser.pagexml.republic_column_parser import determine_column_type
# from republic.parser.pagexml.republic_column_parser import split_column_text_regions


def derive_pagexml_page_iiif_url(jpg_url: str, coords: pdm.Coords, margin: int = 100) -> str:
    region = {
        'left': coords.left - margin if coords.left > margin else 0,
        'top': coords.top - margin if coords.top > margin else 0,
        'width': coords.width + 2 * margin,
        'height': coords.height + 2 * margin,
    }
    return make_iiif_region_url(jpg_url, region)


def split_column_regions(page_doc: pdm.PageXMLPage, config: Dict[str, any] = base_config,
                         debug: int = 0) -> pdm.PageXMLPage:
    if debug > 0:
        print('split_column_regions - SPLITTING PAGE INTO COLUMN REGIONS', page_doc.id)
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
        raise KeyError(f"missing 'text_type' in page {page_doc.id}")
    if page_doc.metadata["text_type"] == "printed":
        max_column_width = 1200
    else:
        max_column_width = 2400
    trs = page_doc.text_regions + page_doc.columns
    if debug > 0:
        print('split_column_regions - NUMBER OF TRS', len(trs))
    for text_region in trs:
        if debug > 0:
            print('split_column_regions - tr', text_region.id, text_region.stats)
        if len(text_region.text_regions) > 0:
            text_regions += text_region.text_regions
        elif text_region.lines and text_region.coords.width > max_column_width:
            if debug > 0:
                print(f'\tWIDE TEXT REGION {text_region.id}, SPLITTING')
            config = copy.deepcopy(config)
            config["column_gap"]["gap_pixel_freq_ratio"] = 0.5
            # print('split_column_regions - column_gap:', config['column_gap'])
            cols = column_parser.split_lines_on_column_gaps(text_region, config, debug=debug)
            text_regions += cols
            for col in cols:
                col.set_parent(page_doc)
                col.set_derived_id(page_doc.id)
            if debug > 0:
                print(f'\tAFTER SPLITTING REGION IS {len(cols)} COLUMNS')
        else:
            if debug > 0:
                print(f'\tREGULAR TEXT REGION {text_region.id}, NOT SPLITTING')
            text_regions.append(text_region)
        # text_regions += [text_region] if text_region.lines else text_region.text_regions
    text_regions.sort(key=lambda x: x.coords.top)
    text_regions = split_merged_regions(text_regions)
    # remove the text_regions as direct descendants of page
    page_doc.text_regions = []
    for text_region in text_regions:
        # for zero width textregions, assume a single pixel width
        tr_width = text_region.coords.width
        if tr_width == 0:
            tr_width = 1
        text_region.set_as_parent(text_region.lines)
        if text_region.lines and text_region.coords.width > max_column_width:
            # Wide text_regions are part of the header
            if debug > 0:
                print('split_column_regions - WIDE TR', text_region.id, text_region.stats)
            text_region.main_type = 'extra'
            text_region.add_type('extra')
        if text_region.has_type('extra'):
            extra_text_regions += [text_region]
            continue
        # check if this text region overlaps with an existing column
        overlapping_column = None
        for column in columns:
            if debug > 0:
                print('COLUMN BOX:', page_doc.id, column.id, column.coords.box)
            overlap = pdm.get_horizontal_overlap(column, text_region)
            tr_overlap_frac = overlap / tr_width
            cl_overlap_frac = overlap / column.coords.width if column.coords.width > 0 else 0
            if min(tr_overlap_frac, cl_overlap_frac) > 0.5 and max(tr_overlap_frac, cl_overlap_frac) > 0.75:
                overlapping_column = column
                break
        # if there is an overlapping column, add this text region
        if overlapping_column:
            overlapping_column.text_regions += [text_region]
            overlapping_column.coords = pdm.parse_derived_coords(overlapping_column.text_regions)
        # if no, create a new column for this text region
        else:
            if text_region.coords.width > 0 and text_region.coords.height > 0:
                coords = pdm.parse_derived_coords([text_region])
            else:
                coords = pdm.Coords([point for point in text_region.coords.points])
            column = pdm.PageXMLColumn(coords=coords, metadata=column_metadata,
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
        column.set_as_parent(column.text_regions)
        pagexml_helper.set_line_alignment(column)
        pagexml_helper.copy_reading_order(page_doc, column)
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


def get_page_split_widths(scan: pdm.PageXMLScan, debug: int = 0) -> Tuple[int, int]:
    if hasattr(scan, 'coords') is False or scan.coords is None or scan.coords.points is None:
        print(f'ERROR determining scan width in get_page_split_widths for scan {scan.id}')
    scan_width = scan.coords.width
    scan_width_norm_ratio = scan.coords.width / scan.metadata['normal_odd_end']
    odd_end = scan_width
    if 0.8 <= scan_width_norm_ratio <= 1.25:
        even_end = scan_width / 2 + 100
    else:
        even_end = scan.metadata['normal_odd_end'] / 2 + 100
    return int(even_end), int(odd_end)


def is_even_side(item: pdm.PhysicalStructureDoc, scan: pdm.PageXMLScan = None, debug: int = 0) -> bool:
    even_end, odd_end = get_page_split_widths(scan)
    if item.coords.right < even_end:
        return True
    elif item.coords.left > even_end:
        return False
    even_width = even_end - item.coords.left if item.coords.left < even_end else 0
    even_ratio = even_width / item.coords.width
    if even_ratio > 0.7:
        return True
    elif even_ratio < 0.3:
        return False
    if debug > 2:
        print(f'is_even_side - odd_end: {odd_end}\t\teven_end: {even_end}')
        print(f'is_even_side - even_width: {even_width}')
        print(f'is_even_side - even_ratio: {even_width / item.coords.width}')
    return item.coords.left < even_end - 100 and item.coords.right < even_end


def is_odd_side(item: pdm.PhysicalStructureDoc, scan: pdm.PageXMLScan = None) -> bool:
    even_end, odd_end = get_page_split_widths(scan)
    if item.coords.right < even_end:
        return False
    elif item.coords.left > even_end:
        return True
    even_width = even_end - item.coords.left if item.coords.left < even_end else 0
    even_ratio = even_width / item.coords.width
    if even_ratio > 0.7:
        return False
    elif even_ratio < 0.3:
        return True
    return item.coords.left > even_end - 300 and item.coords.right > even_end


def is_extra_side(item: pdm.PhysicalStructureDoc, scan: pdm.PageXMLScan = None) -> bool:
    even_end, odd_end = get_page_split_widths(scan)
    return item.coords.right > odd_end and item.coords.left > odd_end - 200


def initialize_pagexml_page(scan_doc: pdm.PageXMLScan, side: str,
                            page_type_index: Dict[int, any]) -> pdm.PageXMLPage:
    """Initialize a pagexml page type document based on the scan metadata."""
    metadata = copy.copy(scan_doc.metadata)
    even_end, odd_end = get_page_split_widths(scan_doc)
    if 'doc_type' in metadata:
        del metadata['doc_type']
    metadata['type'] = 'page'
    metadata['page_side'] = side
    if side == 'odd':
        metadata['page_num'] = scan_doc.metadata['scan_num'] * 2 - 1
        metadata['id'] = f"{scan_doc.metadata['id']}-page-{metadata['page_num']}"
        region = [even_end, scan_doc.coords.top, odd_end, scan_doc.coords.bottom]
    elif side == 'even':
        metadata['page_num'] = scan_doc.metadata['scan_num'] * 2 - 2
        metadata['id'] = f"{scan_doc.metadata['id']}-page-{metadata['page_num']}"
        region = [scan_doc.coords.left, scan_doc.coords.top, even_end, scan_doc.coords.bottom]
    else:
        metadata['page_num'] = scan_doc.metadata['scan_num'] * 2 - 2
        metadata['id'] = f"{scan_doc.metadata['id']}-page-{metadata['page_num']}-extra"
        region = [odd_end, scan_doc.coords.top, scan_doc.coords.right, scan_doc.coords.bottom]
    metadata['scan_id'] = scan_doc.metadata['id']
    points = [
        (region[0], region[1]), (region[0], region[3]),
        (region[2], region[3]), (region[2], region[1])
    ]
    coords = pdm.Coords(points)
    page_doc = pdm.PageXMLPage(doc_id=metadata['id'], metadata=metadata, coords=coords, text_regions=[])
    page_doc.set_parent(scan_doc)
    if page_type_index and metadata['page_num'] in page_type_index:
        page_type = page_type_index[metadata['page_num']]
        page_doc.add_type(page_type)
    assert 'page_num' in page_doc.metadata, f"page {page_doc.id} is missing 'page_num'"
    return page_doc


def combine_stats(text_regions: List[pdm.PageXMLTextRegion]) -> Dict[str, int]:
    combined_stats = {
        'words': 0,
        'lines': 0,
        'text_regions': 0,
        'columns': 0
    }
    for tr in text_regions:
        tr_stats = tr.stats
        for field in combined_stats:
            combined_stats[field] += tr_stats[field] if field in tr_stats else 0
        if hasattr(tr, 'extra'):
            if 'extra' not in combined_stats:
                combined_stats['extra'] = 0
            combined_stats['extra'] += len(tr.extra)
    return combined_stats


def get_column_text_regions(scan_doc: pdm.PageXMLScan, max_col_width: int, config: Dict[str, any],
                            debug: int = 0) -> List[Union[pdm.PageXMLTextRegion, pdm.PageXMLColumn]]:
    trs = []
    for ti, tr in enumerate(scan_doc.text_regions):
        if tr.parent is None:
            print('MISSING PARENT:', tr.id)
        if tr.coords.width <= max_col_width and is_even_side(tr, scan_doc) or is_odd_side(tr, scan_doc):
            if 'main' in tr.type or 'attendance' in tr.type:
                col = None
                for col_tr in trs:
                    if 'column' not in col_tr.type:
                        continue
                    if pdm.is_horizontally_overlapping(tr, col_tr):
                        col = col_tr
                        text_regions = [tr] if len(tr.text_regions) == 0 else tr.text_regions
                        for text_region in text_regions:
                            if debug > 0:
                                print(f'get_column_text_regions - adding tr {text_region.id} to col {col.id}')
                                print('\t', text_region.stats)
                            col.add_child(text_region)

                        col.set_derived_id(scan_doc.id)
                        if debug > 0:
                            print(f'get_column_text_regions - updating col id to {col.id}')
                        break
                if col is None:
                    metadata = copy.deepcopy(tr.metadata)
                    coords = copy.deepcopy(tr.coords)
                    text_regions = [tr] if len(tr.text_regions) == 0 else tr.text_regions
                    if debug > 0:
                        print(f'get_column_text_regions - creating new column for trs {[t.id for t in text_regions]}')
                    col = pdm.PageXMLColumn(metadata=metadata, coords=coords,
                                            text_regions=text_regions)
                    col.set_derived_id(scan_doc.id)
                    col.set_parent(scan_doc)
                    for tr_type in tr.type:
                        if tr_type not in {'text_region'} and tr_type not in col.type:
                            col.add_type(tr_type)
                    trs.append(col)
                if debug > 0:
                    print('get_column_text_regions - MAIN TEXT REGION', tr.id)
                    print('\t', tr.type)
                    print('becomes part of col', col.id, col.stats, len(col.text_regions))
            else:
                if debug > 0:
                    print('get_column_text_regions - NON-MAIN TEXT REGION', tr.id)
                    print('\t', tr.type)
                trs.append(tr)
        else:
            if debug > 0:
                if tr.coords.width > max_col_width:
                    print("get_column_text_regions - SPLITTING COLUMN BECAUSE IT IS TOO WIDE", tr.id)
                else:
                    print("get_column_text_regions - SPLITTING COLUMN FOR SOME OTHER REASON", tr.id)
                print(tr.stats)
            config = copy.deepcopy(config)
            config['column_gap']['gap_threshold'] = 20
            config['column_gap']['gap_pixel_freq_ratio'] = 0.5
            cols = column_parser.split_lines_on_column_gaps(tr, config, debug=debug)
            if debug > 0:
                for col in cols:
                    print("get_column_text_regions - after tr split -> COLUMN:", col.id)
                    for line in col.lines:
                        print(f"\tget_column_text_regions - LINE {line.coords.left}-{line.coords.right}\t{line.coords.y}\t{line.text}")
            trs += cols
        if debug > 0:
            print('\nADDED TRS:')
            for added_tr in trs:
                print('\tIN TRS:', added_tr.id, added_tr.stats)
            print('\n')
        # tr_stats = combine_stats(trs)
        # print(ti, tr_stats)
        if debug > 0:
            print('\n')
    if debug > 1:
        print('\nget_column_text_regions - column text_regions:')
        for tr in trs:
            print('\t', tr.id, tr.stats)
        print('\n')
    return trs


def assign_trs_to_odd_even_pages(scan_doc: pdm.PageXMLScan, page_even: pdm.PageXMLPage,
                                 page_odd: pdm.PageXMLPage, trs: List[pdm.PageXMLTextRegion],
                                 page_type_index: Dict[int, any], config: Dict[str, any],
                                 debug: int = 0) -> List[pdm.PageXMLPage]:
    tr_id_map = {}
    undecided = []
    append_count = 0
    if debug > 0:
        print(f'assign_trs_to_odd_even_pages - STARTING WITH {len(trs)} TRS\n')
    for text_region in sorted(trs, key=lambda x: x.coords.x):
        if text_region.has_type('main') and text_region.has_type('extra'):
            text_region.remove_type('extra')
        if scan_doc.metadata['inventory_num'] < 3700 or scan_doc.metadata['inventory_num'] > 4500:
            if text_region.has_type('date') and text_region.has_type('extra'):
                text_region.add_type('main')
                text_region.remove_type('extra')
        as_extra = 'extra' in text_region.type
        text_region.metadata['scan_id'] = scan_doc.id
        if text_region.metadata and 'type' in text_region.metadata:
            if debug > 0:
                print("assign_trs_to_odd_even_pages - DECIDING EVEN/ODD SIDE", text_region.id)
            if is_even_side(text_region, scan_doc) or is_odd_side(text_region, scan_doc):
                side = 'EVEN' if is_even_side(text_region, scan_doc) else 'ODD'
                page = page_even if is_even_side(text_region, scan_doc) else page_odd
                before_stats = page.stats
                if debug > 0:
                    print(f"\tPAGE {side} STATS BEFORE ADDING DERIVED TR:", page.stats)
                    print(f"\t{side}:", text_region.id, text_region.type)
                    print('\t\t', text_region.stats)
                try:
                    page.add_child(text_region, as_extra=as_extra)
                except BaseException:
                    print(f'Error add text_region {text_region.id} as child to page {page.id}, '
                          f'text_region.coords.points: {text_region.coords.points}')
                    raise
                after_stats = page.stats
                if text_region.stats['lines'] + before_stats['lines'] != after_stats['lines']:
                    print('assign_trs_to_odd_even_pages - BEFORE:', before_stats)
                    print('assign_trs_to_odd_even_pages - text_region:', text_region.stats)
                    print('assign_trs_to_odd_even_pages - AFTER:', after_stats)
                    raise ValueError('Line missing in page line count after adding text_region')
                if debug > 0:
                    print(f"\tPAGE {side} STATS AFTER ADDING DERIVED TR:", page.stats)
                append_count += 1
            else:
                if text_region.coords is None:
                    lines = text_region.get_lines()
                    text_region.coords = pdm.parse_derived_coords(lines)
                if debug > 0:
                    print('\tSPLITTING PAGE BOUNDARY OVERLAPPING REGION:', text_region.id, text_region.type)
                    print('\t', text_region.stats)
                    # print(config)
                sub_trs = column_parser.split_lines_on_column_gaps(text_region, config=config, debug=debug)
                if debug > 0:
                    print('\t\tnumber of sub text regions:', len(sub_trs))
                for sub_tr in sub_trs:
                    if debug > 0:
                        print('\t\t\tdeciding on side for sub_tr', sub_tr.id)
                        print('\t\t\t', sub_tr.stats)
                    if is_even_side(sub_tr, scan_doc):
                        side = 'even'
                        page = page_even
                        if debug > 0:
                            print('\t\t\t\tadding sub_tr to even')
                    elif is_odd_side(sub_tr, scan_doc):
                        side = 'odd'
                        page = page_odd
                        if debug > 0:
                            print('\t\t\t\tadding sub_tr to odd')
                    else:
                        if debug > 0:
                            print('\tUNDECIDED:', sub_tr.id, sub_tr.type)
                        undecided.append(sub_tr)
                        append_count += 1
                        continue
                    sub_tr.set_derived_id(page.id)
                    sub_tr.set_parent(page)
                    if debug > 0:
                        print(f"assign_trs_to_odd_even_pages - PAGE {side} STATS BEFORE ADDING DERIVED TR:", page.stats)
                    page.add_child(sub_tr, as_extra=as_extra)
                    append_count += 1
                    if debug > 0:
                        print(f"assign_trs_to_odd_even_pages - PAGE {side} STATS AFTER ADDING DERIVED TR:", page.stats)
                    if debug > 0:
                        print(f'\tSPLIT SUB TR {side}:', sub_tr.id)
                        print('\t', sub_tr.type)
                        print('\t', sub_tr.stats)
                # undecided.append(text_region)
        elif text_region.lines:
            if debug > 0:
                print("assign_trs_to_odd_even_pages - TEXTREGION HAS NO TYPE BUT HAS LINES:", text_region.id)
            even_lines = [line for line in text_region.lines if is_even_side(line, scan_doc)]
            odd_lines = [line for line in text_region.lines if is_odd_side(line, scan_doc)]
            if len(even_lines) == 0:
                if debug > 0:
                    print("assign_trs_to_odd_even_pages - NO EVEN, MOVE TR TO ODD")
                page_odd.add_child(text_region, as_extra=as_extra)
            elif len(odd_lines) == 0:
                if debug > 0:
                    print("assign_trs_to_odd_even_pages - NO ODD, MOVE TR TO EVEN")
                page_even.add_child(text_region, as_extra=as_extra)
            else:
                # The text region crosses the page boundary. Split the lines into new text regions per
                # page, and create new text regions
                if debug > 0:
                    print("assign_trs_to_odd_even_pages - SPLIT LINES")
                odd_region = pdm.PageXMLTextRegion(lines=odd_lines, coords=pdm.parse_derived_coords(odd_lines),
                                                   metadata=text_region.metadata)
                even_region = pdm.PageXMLTextRegion(lines=even_lines, coords=pdm.parse_derived_coords(even_lines),
                                                    metadata=text_region.metadata)
                if debug > 0:
                    print("assign_trs_to_odd_even_pages - ODD REGION", odd_region.id, odd_region.stats)
                    print("assign_trs_to_odd_even_pages - EVEN REGION", even_region.id, even_region.stats)
                even_region.set_parent(page_even)
                even_region.set_derived_id(page_even.id)
                odd_region.set_parent(page_odd)
                odd_region.set_derived_id(page_odd.id)
                tr_id_map[even_region.id] = text_region.id
                tr_id_map[odd_region.id] = text_region.id
                page_even.add_child(even_region, as_extra=as_extra)
                page_odd.add_child(odd_region, as_extra=as_extra)
        elif text_region.text_regions:
            if debug > 1:
                print("assign_trs_to_odd_even_pages - TEXTREGION HAS TEXTREGIONS:", text_region.id)
            even_text_regions = []
            odd_text_regions = []
            for tr in text_region.text_regions:
                if is_even_side(tr, scan_doc):
                    even_text_regions.append(tr)
                elif is_odd_side(tr, scan_doc):
                    odd_text_regions.append(tr)
                else:
                    pass
            if len(even_text_regions) == 0:
                if debug > 1:
                    print("assign_trs_to_odd_even_pages - NO EVEN, MOVE TR TO ODD")
                page_odd.add_child(text_region, as_extra=as_extra)
            elif len(odd_text_regions) == 0:
                if debug > 1:
                    print("assign_trs_to_odd_even_pages - NO ODD, MOVE TR TO EVEN")
                page_even.add_child(text_region, as_extra=as_extra)
            else:
                # The text region crosses the page boundary. Split the text_regions into new text regions per
                # page, and create new text regions
                if debug > 1:
                    print("assign_trs_to_odd_even_pages - SPLIT TEXTREGION")
                odd_region = pdm.PageXMLTextRegion(text_regions=odd_text_regions, metadata=text_region.metadata,
                                                   coords=pdm.parse_derived_coords(odd_text_regions))
                even_region = pdm.PageXMLTextRegion(text_regions=even_text_regions, metadata=text_region.metadata,
                                                    coords=pdm.parse_derived_coords(even_text_regions))
                if debug > 1:
                    print("assign_trs_to_odd_even_pages - ODD REGION", odd_region.id, odd_region.stats)
                    print("assign_trs_to_odd_even_pages - EVEN REGION", even_region.id, even_region.stats)
                tr_id_map[even_region.id] = text_region.id
                tr_id_map[odd_region.id] = text_region.id
                page_even.add_child(even_region, as_extra=as_extra)
                page_odd.add_child(odd_region, as_extra=as_extra)
        else:
            print('assign_trs_to_odd_even_pages - SKIPPING TR', text_region.id)
            # undecided.append(text_region)
            # append_count += 1
        if debug > 1:
            print('assign_trs_to_odd_even_pages - APPEND_COUNT:', append_count)
            print('assign_trs_to_odd_even_pages - EVEN PAGE STATS:', page_even.stats)
            print('assign_trs_to_odd_even_pages - ODD PAGE STATS:', page_odd.stats)
        if debug > 0:
            print('\n')
    if debug > 1:
        print('assign_trs_to_odd_even_pages - NUM UNDECIDED:', len(undecided))
        for tr in undecided:
            print('\t', tr.id, tr.stats)
    assign_undecided(scan_doc, page_even, page_odd, undecided, page_type_index, debug=debug)
    pages = []
    for page_doc in [page_even, page_odd]:
        if page_doc.coords:
            page_doc.metadata['iiif_url'] = derive_pagexml_page_iiif_url(page_doc.metadata['jpg_url'],
                                                                         page_doc.coords)
        else:
            page_doc.metadata['iiif_url'] = scan_doc.metadata['iiif_url']
        if scan_doc.reading_order:
            # if the scan has a reading order, adopt it for the individual pages
            pagexml_helper.copy_reading_order(scan_doc, page_doc, tr_id_map)
        pages += [page_doc]
    return pages


def assign_undecided(scan: pdm.PageXMLScan, page_even: pdm.PageXMLPage, page_odd: pdm.PageXMLPage,
                     undecided: List[pdm.PageXMLTextRegion],
                     page_type_index: Dict[int, any], debug: int = 0):
    if 'normal_odd_end' in page_odd.metadata:
        for undecided_tr in undecided:
            undecided_tr.metadata['normal_odd_end'] = page_odd.metadata['normal_odd_end']
            undecided_tr.metadata['normal_even_end'] = page_odd.metadata['normal_even_end']
    for page_doc in [page_even, page_odd]:
        if page_doc.metadata['page_num'] not in page_type_index:
            print('missing page_type for page', page_doc.id)
        elif 'title_page' in page_type_index[page_doc.metadata['page_num']]:
            separate_title_lines(page_doc, debug=debug)
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
            elif undecided_tr.coords.left > page_odd.metadata['normal_even_end']:
                page_odd.add_child(undecided_tr)
                decided.append(undecided_tr)
            elif page_odd.metadata['normal_even_end'] - undecided_tr.coords.left < undecided_tr.coords.w:
                page_odd.add_child(undecided_tr)
                decided.append(undecided_tr)
            else:
                page_even.add_child(undecided_tr)
                decided.append(undecided_tr)
        undecided = [tr for tr in undecided if tr not in decided]
    for undecided_tr in undecided:
        if debug > 1:
            print("UNKNOWN:", undecided_tr.id, undecided_tr.stats)
            # print('\tpage_even metadata:', page_even.metadata)
            # print('\tpage_odd metadata:', page_odd.metadata)
            # print('\tundecided metadata:', undecided_tr.metadata)
            undecided_tr.metadata['normal_odd_end'] = page_odd.metadata['normal_odd_end']
            undecided_tr.metadata['normal_even_end'] = page_even.metadata['normal_even_end']
            even_end, odd_end = get_page_split_widths(scan)
            # print(undecided_tr.parent.metadata)
            print("odd end:", odd_end, "\teven end:", even_end)
            print(undecided_tr.coords.box)
            for line in undecided_tr.lines:
                print(line.coords.x, line.coords.y, line.text)


def split_scan_pages(scan_doc: pdm.PageXMLScan, page_type_index: Dict[int, any] = None,
                     debug: int = 0) -> List[pdm.PageXMLPage]:
    scan_stats = combine_stats([scan_doc])
    if 'scan_width' not in scan_doc.metadata:
        scan_doc.metadata['scan_width'] = scan_doc.coords.width
    page_even = initialize_pagexml_page(scan_doc, 'even', page_type_index)
    page_odd = initialize_pagexml_page(scan_doc, 'odd', page_type_index)
    if not scan_doc.text_regions:
        return [page_even, page_odd]
    config = copy.deepcopy(base_config)
    if 3760 <= scan_doc.metadata['inventory_num'] <= 3864:
        max_col_width = 1000
        if scan_doc.metadata['inventory_num'] >= 3804:
            even_page_num = scan_doc.metadata['scan_num'] * 2 - 2
            odd_page_num = scan_doc.metadata['scan_num'] * 2 - 1
            if even_page_num not in page_type_index:
                print(f'split_scan_page - missing page_num for page {scan_doc.id}-page-{even_page_num}')
                raise KeyError(f'missing page_type for page {scan_doc.id}-page-{even_page_num}')
            if odd_page_num not in page_type_index:
                print(f'split_scan_page - missing page_num for page {scan_doc.id}-page-{odd_page_num}')
                raise KeyError(f'missing page_type for page {scan_doc.id}-page-{odd_page_num}')
            if 'index_page' in page_type_index[even_page_num] or 'index_page' in page_type_index[odd_page_num]:
                max_col_width = 500
                config['column_gap']['gap_pixel_freq_ratio'] = 0.2
                config['column_gap']['gap_threshold'] = 10
    else:
        max_col_width = 2200
    if debug > 1:
        print(f"split_scan_pages - max_col_width: {max_col_width}")
    # page_extra = initialize_pagexml_page(scan_doc, 'extra')
    trs = get_column_text_regions(scan_doc, max_col_width, config, debug=debug)
    tr_stats = combine_stats(trs)
    if tr_stats['words'] != scan_stats['words']:
        print('split_scan_page - Unequal number of words')
        for tr in trs:
            print('split_scan_page - trs:', tr.id, tr.stats)
            for li, line in enumerate(tr.lines):
                print('\t', li, line.id)
            for sub_tr in tr.text_regions:
                print('\tSUB_TR:', sub_tr.id, sub_tr.stats)
                for line in sub_tr.lines:
                    print('\t\t', line.id, line.text)
        print('split_scan_page - scan_stats:', scan_stats)
        raise ValueError(f'split_scan_page - Unequal number of words in trs ({tr_stats["words"]}) '
                         f'and scan ({scan_stats["words"]}) for scan {scan_doc.id}')
    if debug > 0:
        print('split_scan_page - scan_stats:', scan_stats)
        print('split_scan_page - tr_stats:', tr_stats)
    pages = assign_trs_to_odd_even_pages(scan_doc, page_even, page_odd, trs,
                                         page_type_index, config, debug=debug)
    page_stats = combine_stats(pages)
    if debug > 0:
        print('split_scan_page - page_stats:', page_stats)
        for page in pages:
            print('\tPER PAGE STATS:', page.id, page.stats)
    if page_stats['words'] != scan_stats['words']:
        print('split_scan_page - Unequal number of words')
        print('split_scan_page - scan stats:', scan_stats)
        print('split_scan_page - trs')
        for tr in trs:
            print('\tsplit_scan_page - tr', tr.id, tr.stats)
        for page in pages:
            print('split_scan_page - stats for page', page.id, page.stats)
        raise ValueError(f'Unequal number of words in pages ({page_stats["words"]}) '
                         f'and scan ({scan_stats["words"]}) for scan {scan_doc.id}')
    return pages


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


def separate_title_lines(page: pdm.PageXMLPage, debug: int = 0) -> pdm.PageXMLPage:
    outer: List[pdm.PageXMLDoc] = page.columns + page.text_regions + page.extra
    if 3760 <= page.metadata['inventory_num'] <= 3864:
        max_col_width = 1000
    else:
        max_col_width = 1500
    for tr in outer:
        if debug > 0:
            print('\tseparate_title_lines - TEXT REGION', tr.id, tr.type)
        if tr.coords.width > max_col_width:
            if debug > 0:
                print('separate_title_lines - HAS TITLE LINES:', tr.id)
            last_title_line_top = 0
            for line in tr.lines:
                if line.coords.width < max_col_width:
                    continue
                if line.coords.top > 2000:
                    continue
                if debug > 0:
                    print('\tTITLE LINE:', line.coords.width, line.coords.top, line.text)
                if line.coords.top > last_title_line_top:
                    last_title_line_top = line.coords.top
                    if debug > 0:
                        print('\tLAST TITLE LINE:', line.coords.width, line.coords.top, line.text)
            title_lines = [line for line in tr.lines if line.coords.top <= last_title_line_top]
            col_lines = [line for line in tr.lines if line.coords.top > last_title_line_top]
            if len(title_lines) > 0 and len(col_lines) > 0:
                tr.lines = col_lines
                tr.set_derived_id(page.metadata['scan_id'])
                title_tr_coords = pdm.parse_derived_coords(title_lines)
                title_tr = pdm.PageXMLTextRegion(coords=title_tr_coords, lines=title_lines)
                title_tr.set_derived_id(page.metadata['scan_id'])
                page.extra.append(title_tr)
                if debug > 0:
                    print('separate_title_lines - BELOW TITLE:')
                    for line in tr.lines:
                        print(f'\t{line.coords.left: >4}-{line.coords.right: <4}\t{line.coords.top}\t{line.text}')
    return page


def get_page_full_text_columns(page: pdm.PageXMLPage) -> List[pdm.PageXMLColumn]:
    """Return the full-text columns of a page. Merge any overlapping extra
    columns into the full-text columns."""
    full_text_columns = []
    extra_columns = []
    for column in page.columns:
        try:
            column_type = column_parser.determine_column_type(column)
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
            if regions_overlap(extra_col, full_text_col):
                # merge columns into new full_text_col
                # make sure multiple merges into the same full text
                # columns are cumulative
                full_text_col = pagexml_helper.merge_columns([extra_col, full_text_col],
                                                             full_text_col.id, full_text_col.metadata)
        # keep tracked of the new merged columns
        merged_columns.append(full_text_col)
    return merged_columns


def is_paragraph_line(line: pdm.PageXMLTextLine) -> bool:
    if 'line_class' not in line.metadata:
        return False
    return line.metadata['line_class'].startswith('para_')


def update_line_types(page: pdm.PageXMLPage, week_day_name_searcher: FuzzyPhraseSearcher,
                      copy_page: bool = True, debug: int = 0) -> pdm.PageXMLPage:
    """Update line class types when they are in conflict with the type of
    their corresponding text region.

    This is particularly for text regions labelled as attendance but with
    lines classified as paragraph lines.
    """
    default_types = {'text_region', 'structure_doc', 'physical_structure_doc', 'pagexml_doc'}
    para_trs = []
    para_lines = []
    indent_trs = []
    new_page = copy.deepcopy(page) if copy_page is True else page
    for col in new_page.columns:
        for tr in col.text_regions:
            if tr.has_type('resolution'):
                para_trs.append(tr)
                para_lines.extend([line for line in tr.lines if is_paragraph_line(line)])
                line_types = column_parser.get_main_line_types(tr.lines)
                type_freq = Counter(line_types)
                if 'attendance' in type_freq:
                    para_lefts = [line.coords.left for line in tr.lines
                                  if line.metadata['line_class'].startswith('para_')]
                    for line in tr.lines:
                        if line.metadata['line_class'] == 'attendance':
                            indented = [left for left in para_lefts if left - line.coords.left > 100]
                            if len(indented) == 0:
                                line.metadata['line_class'] = 'para_mid'
                                if debug > 0:
                                    print(f"republic_page_parser.update_line_types - resolution tr {tr.id} "
                                          f"has attendance line types but not left indented, updating to 'para_mid'")
            elif tr.has_type('attendance') or tr.has_type('header'):
                indent_trs.append(tr)
    if len(para_lines) == 0:
        return new_page
    for indent_tr in indent_trs:
        if indent_tr.has_type('attendance') or indent_tr.has_type('header'):
            line_types = column_parser.get_main_line_types(indent_tr.lines)
            if len(line_types) == 0:
                if debug > 0:
                    print(f"republic_page_parser.update_line_types - attendance tr {indent_tr.id} "
                          f"has no main line types, updating to 'empty'")
                indent_tr.type = {t for t in default_types}
                indent_tr.add_type('empty')
                continue
            type_freq = Counter(line_types)
            if 'date' in type_freq:
                for line in indent_tr.lines:
                    if line.metadata['line_class'] == 'date' and len(line.text) > 40:
                        print('CUT LINE:', len(line.text), line.text)
            if 'attendance' in type_freq and 'para' not in type_freq and indent_tr.has_type('attendance'):
                if debug > 0:
                    print(f"republic_page_parser.update_line_types - attendance tr {indent_tr.id} "
                          f"has attendance lines, not updating line types")
                continue
            if 'para' not in type_freq and indent_tr.has_type('header'):
                if debug > 0:
                    print(f"republic_page_parser.update_line_types - header tr {indent_tr.id} "
                          f"has no para lines, not updating line types")
                continue
            if 'para' in type_freq:
                indent_lines = [para_line for para_line in para_lines
                                if para_line.coords.left - indent_tr.coords.left > 100]
                if indent_tr.has_type('attendance') and \
                        (len(indent_lines) > 10 or len(indent_lines) / len(para_lines) > 0.5):
                    if debug > 0:
                        print(f"republic_page_parser.update_line_types - attendance tr {indent_tr.id} "
                              f"has para lines and is to the left of other para lines, updating line "
                              f"types to 'attendance'")
                    for indent_line in indent_tr.lines:
                        if indent_line.metadata['line_class'].startswith('para_'):
                            indent_line.metadata['line_class'] = 'attendance'
                if indent_tr.has_type('header') and indent_tr.has_type('date'):
                    update_type = 'date_header'
                    for indent_line in indent_tr.lines:
                        if check_line_starts_with_week_day_name(indent_line, week_day_name_searcher):
                            if debug > 0:
                                print(f"republic_page_parser.update_line_types - header date tr {indent_tr.id} "
                                      f"has week day date lines, updating line types to 'date'")
                            update_type = 'date'
                            indent_tr.remove_type('header')
                            indent_tr.add_type('main')
                            break
                    else:
                        if debug > 0:
                            print(f"republic_page_parser.update_line_types - header date tr {indent_tr.id} "
                                  f"has para lines, updating line types to '{update_type}'")
                    for indent_line in indent_tr.lines:
                        indent_line.metadata['line_class'] = update_type
    return new_page


def split_page_column_text_regions(page: pdm.PageXMLPage, update_type: bool = False,
                                   week_day_name_searcher: FuzzyPhraseSearcher = None,
                                   copy_page: bool = True, debug: int = 0) -> pdm.PageXMLPage:
    if update_type is True:
        page = update_line_types(page, week_day_name_searcher=week_day_name_searcher,
                                 copy_page=copy_page, debug=debug)
    new_extra = [tr for tr in page.extra] if page.extra else []
    if debug > 0:
        print(f"split_page_column_text_regions - new_extra: {new_extra}")
    new_cols = [column_parser.split_column_text_regions(col, update_type=update_type, debug=debug)
                for col in page.columns]
    if debug > 0:
        print(f"split_page_column_text_regions - new_cols: {new_cols}")
    if page.coords:
        new_coords = pdm.Coords([point for point in page.coords.points])
    elif len(new_cols + new_extra) > 0:
        new_coords = pdm.parse_derived_coords(new_extra + new_cols)
    else:
        new_coords = None
    new_page = pdm.PageXMLPage(doc_id=page.id, metadata=copy.deepcopy(page.metadata),
                               coords=new_coords, columns=new_cols, extra=new_extra)
    return new_page





