from typing import Dict, Generator, List, Set
from collections import Counter
from itertools import combinations
import string
import re

import numpy as np
import pagexml.model.physical_document_model as pdm
from pagexml.helper.pagexml_helper import elements_overlap
# import republic.model.physical_document_model as pdm


def coords_overlap(item1: pdm.PhysicalStructureDoc, item2: pdm.PhysicalStructureDoc) -> int:
    left = max([item1.coords.left, item2.coords.left])
    right = min([item1.coords.right, item2.coords.right])
    # overlap must be positive, else there is no overlap
    return right - left if right - left > 0 else 0


def make_baseline_string(line: pdm.PageXMLTextLine):
    b = line.baseline
    return f"{b.left: >4}-{b.right: <4}\t{b.top: >4}-{b.bottom: <4}"


def make_coords_string(line: pdm.PageXMLTextLine):
    c = line.coords
    return f"{c.left: >4}-{c.right: <4}\t{c.top: >4}-{c.bottom: <4}"


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


def merge_columns(columns: List[pdm.PageXMLColumn],
                  doc_id: str, metadata: dict, lines_only: bool = False) -> pdm.PageXMLColumn:
    """Merge two columns into one, sorting lines by baseline height."""
    if lines_only is True:
        merged_lines = [line for col in columns for line in col.get_lines()]
        merged_lines = list(set(merged_lines))
        sorted_lines = sorted(merged_lines, key=lambda x: x.baseline.y)
        merged_coords = pdm.parse_derived_coords(sorted_lines)
        merged_col = pdm.PageXMLColumn(doc_id=doc_id,
                                       metadata=metadata, coords=merged_coords,
                                       lines=merged_lines)
    else:
        merged_trs = [tr for col in columns for tr in col.text_regions]
        sorted_trs = sorted(merged_trs, key=lambda  x: x.coords.y)
        merged_lines = [line for col in columns for line in col.lines]
        sorted_lines = sorted(merged_lines, key=lambda x: x.baseline.y)
        merged_coords = pdm.parse_derived_coords(sorted_trs + sorted_lines)
        merged_col = pdm.PageXMLColumn(doc_id=doc_id,
                                       metadata=metadata, coords=merged_coords,
                                       text_regions=sorted_trs, lines=sorted_lines)

    for col in columns:
        for col_type in col.types:
            if col_type not in merged_col.type:
                merged_col.add_type(col_type)
    return merged_col


def get_overlapping_text_regions(text_regions: List[pdm.PageXMLTextRegion],
                                 overlap_threshold: float = 0.3) -> List[Set[pdm.PageXMLTextRegion]]:
    tr_sets = []
    in_overlapping = set()
    for tr1, tr2 in combinations(text_regions, 2):
        if elements_overlap(tr1, tr2, threshold=overlap_threshold) is False:
            continue
        tr_sets.append({tr1, tr2})
        in_overlapping.update({tr1, tr2})
    tr_sets.extend([{tr} for tr in text_regions if tr not in in_overlapping])
    return tr_sets


def copy_reading_order(super_doc: pdm.PageXMLDoc, sub_doc: pdm.PageXMLDoc,
                       tr_id_map: Dict[str, str] = None):
    order_number = {}
    if hasattr(sub_doc, "text_regions"):
        for tr in sub_doc.text_regions:
            if tr_id_map and tr.id in tr_id_map:
                order_number[tr.id] = int(super_doc.reading_order_number[tr_id_map[tr.id]])
            elif tr.id in super_doc.reading_order_number:
                order_number[tr.id] = int(super_doc.reading_order_number[tr.id])
            else:
                # If for some reason a text region is not in the reading order list
                # just add it to the end of the reading order
                super_doc.reading_order_number[tr.id] = len(super_doc.reading_order_number) + 1
                order_number[tr.id] = super_doc.reading_order_number[tr.id]
    try:
        for ti, tr_id in enumerate(sorted(order_number, key=lambda t: order_number[t])):
            sub_doc.reading_order_number[tr_id] = ti + 1
            sub_doc.reading_order[ti + 1] = tr_id
    except TypeError:
        print(f"ERROR - copy_reading_order - non-integer in reading order number: {order_number}")
        raise


def sort_regions_in_reading_order(doc: pdm.PageXMLDoc) -> List[pdm.PageXMLTextRegion]:
    doc_text_regions: List[pdm.PageXMLTextRegion] = []
    if doc.reading_order and hasattr(doc, 'text_regions') and doc.text_regions:
        text_region_ids = [region for _index, region in sorted(doc.reading_order.items(), key=lambda x: x[0])]
        return [tr for tr in sorted(doc.text_regions, key=lambda x: text_region_ids.index(x.id))]
    if hasattr(doc, 'columns') and sorted(doc.columns):
        doc_text_regions = doc.columns
    elif hasattr(doc, 'text_regions') and doc.text_regions:
        doc_text_regions = doc.text_regions
    if doc_text_regions:
        sub_text_regions = []
        for text_region in sorted(doc_text_regions, key=lambda x: x.coords.left):
            sub_text_regions += sort_regions_in_reading_order(text_region)
        return sub_text_regions
    elif isinstance(doc, pdm.PageXMLTextRegion):
        return [doc]
    else:
        return []


def horizontal_group_lines(lines: List[pdm.PageXMLTextLine]) -> List[List[pdm.PageXMLTextLine]]:
    """Sort lines of a text region vertically as a list of lists,
    with adjacent lines grouped in inner lists."""
    if len(lines) == 0:
        return []
    # First, sort lines vertically
    # Important: include ALL lines with coords, including empty ones
    vertically_sorted = [line for line in sorted(lines, key=lambda line: line.coords.top)]
    if len(vertically_sorted) == 0:
        for line in lines:
            print(line.coords.box, line.text)
        return []
    # Second, group adjacent lines in vertical line stack
    horizontally_grouped_lines = [[vertically_sorted[0]]]
    rest_lines = vertically_sorted[1:]
    if len(vertically_sorted) > 1:
        for li, curr_line in enumerate(rest_lines):
            prev_line = horizontally_grouped_lines[-1][-1]
            if curr_line.is_below(prev_line):
                horizontally_grouped_lines.append([curr_line])
            elif curr_line.is_next_to(prev_line):
                horizontally_grouped_lines[-1].append(curr_line)
            else:
                horizontally_grouped_lines.append([curr_line])
    # Third, sort adjecent lines horizontally
    for line_group in horizontally_grouped_lines:
        line_group.sort(key=lambda line: line.coords.left)
    return horizontally_grouped_lines


def horizontally_merge_lines(lines: List[pdm.PageXMLTextLine]) -> List[pdm.PageXMLTextLine]:
    """Sort lines vertically and merge horizontally adjacent lines."""
    horizontally_grouped_lines = horizontal_group_lines(lines)
    horizontally_merged_lines = []
    for line_group in horizontally_grouped_lines:
        coords = pdm.parse_derived_coords(line_group)
        baseline = pdm.Baseline([point for line in line_group for point in line.baseline.points])
        line = pdm.PageXMLTextLine(metadata=line_group[0].metadata, coords=coords, baseline=baseline,
                                   text=' '.join([line.text for line in line_group]))
        line.set_derived_id(line_group[0].metadata['parent_id'])
        horizontally_merged_lines.append(line)
    return horizontally_merged_lines


def sort_lines_in_reading_order(doc: pdm.PageXMLDoc) -> Generator[pdm.PageXMLTextLine, None, None]:
    """Sort the lines of a pdm.PageXML document in reading order.
    Reading order is: columns from left to right, text regions in columns from top to bottom,
    lines in text regions from top to bottom, and when (roughly) adjacent, from left to right."""
    for text_region in sort_regions_in_reading_order(doc):
        # print('text_region', text_region.id)
        if text_region.main_type == 'column':
            text_region.metadata['column_id'] = text_region.id
        # if 'column_id' not in text_region.metadata:
        #     raise KeyError(f'missing column id: {text_region.metadata}')
        for line in text_region.lines:
            if line.metadata is None:
                line.metadata = {'id': line.id, 'type': ['pagexml', 'line'], 'parent_id': text_region.id}
            if 'column_id' in text_region.metadata and 'column_id' not in line.metadata:
                line.metadata['column_id'] = text_region.metadata['column_id']
            if 'page_id' in text_region.metadata and 'page_id' not in line.metadata:
                line.metadata['page_id'] = text_region.metadata['page_id']
        stacked_lines = horizontal_group_lines(text_region.lines)
        for lines in stacked_lines:
            for line in sorted(lines, key=lambda x: x.coords.left):
                yield line


def line_ends_with_word_break(curr_line: pdm.PageXMLTextLine, next_line: pdm.PageXMLTextLine,
                              word_freq: Counter = None) -> bool:
    if not next_line or not next_line.text:
        # if the next line has no text, it has no first word to join with the last word of the current line
        return False
    if not curr_line.text[-1] in string.punctuation:
        # if the current line does not end with punctuation, we assume, the last word is not hyphenated
        return False
    match = re.search(r"(\w+)\W+$", curr_line.text)
    if not match:
        # if the current line has no word immediately before the punctuation, we assume there is no word break
        return False
    last_word = match.group(1)
    match = re.search(r"^(\w+)", next_line.text)
    if not match:
        # if the next line does not start with a word, we assume it should not be joined to the last word
        # on the current line
        return False
    next_word = match.group(1)
    if curr_line.text[-1] == "-":
        # if the current line ends in a proper hyphen, we assume it should be joined to the first
        # word on the next line
        return True
    if not word_freq:
        # if no word_freq counter is given, we cannot compare frequencies, so assume the words should
        # not be joined
        return False
    joint_word = last_word + next_word
    if word_freq[joint_word] == 0:
        return False
    if word_freq[joint_word] > 0 and word_freq[last_word] * word_freq[next_word] == 0:
        return True
    pmi = word_freq[joint_word] * sum(word_freq.values()) / (word_freq[last_word] * word_freq[next_word])
    if pmi > 1:
        return True
    if word_freq[joint_word] > word_freq[last_word] and word_freq[joint_word] > word_freq[next_word]:
        return True
    elif word_freq[next_word] < word_freq[joint_word] <= word_freq[last_word]:
        print("last word:", last_word, word_freq[last_word])
        print("next word:", next_word, word_freq[next_word])
        print("joint word:", joint_word, word_freq[joint_word])
        return True
    else:
        return False


def json_to_pagexml_word(json_doc: dict) -> pdm.PageXMLWord:
    word = pdm.PageXMLWord(doc_id=json_doc['id'], doc_type=json_doc['type'], metadata=json_doc['metadata'],
                           text=json_doc['text'])
    return word


def json_to_pagexml_line(json_doc: dict) -> pdm.PageXMLTextLine:
    words = [json_to_pagexml_word(word) for word in json_doc['words']] if 'words' in json_doc else []
    reading_order = json_doc['reading_order'] if 'reading_order' in json_doc else {}
    try:
        line = pdm.PageXMLTextLine(doc_id=json_doc['id'], doc_type=json_doc['type'], metadata=json_doc['metadata'],
                                   coords=pdm.Coords(json_doc['coords']), baseline=pdm.Baseline(json_doc['baseline']),
                                   text=json_doc['text'], words=words, reading_order=reading_order)
        return line
    except TypeError:
        print(json_doc['baseline'])
        raise


def json_to_pagexml_text_region(json_doc: dict) -> pdm.PageXMLTextRegion:
    text_regions = [json_to_pagexml_text_region(text_region) for text_region in json_doc['text_regions']] \
        if 'text_regions' in json_doc else []
    lines = [json_to_pagexml_line(line) for line in json_doc['lines']] if 'lines' in json_doc else []
    reading_order = json_doc['reading_order'] if 'reading_order' in json_doc else {}

    text_region = pdm.PageXMLTextRegion(doc_id=json_doc['id'], doc_type=json_doc['type'], metadata=json_doc['metadata'],
                                        coords=pdm.Coords(json_doc['coords']), text_regions=text_regions, lines=lines,
                                        reading_order=reading_order)
    pdm.set_parentage(text_region)
    return text_region


def json_to_pagexml_column(json_doc: dict) -> pdm.PageXMLColumn:
    text_regions = [json_to_pagexml_text_region(text_region) for text_region in json_doc['text_regions']] \
        if 'text_regions' in json_doc else []
    # for tr in text_regions:
    #     print("IN COLUMN", tr.id, tr.stats)
    lines = [json_to_pagexml_line(line) for line in json_doc['lines']] if 'lines' in json_doc else []
    reading_order = json_doc['reading_order'] if 'reading_order' in json_doc else {}

    column = pdm.PageXMLColumn(doc_id=json_doc['id'], doc_type=json_doc['type'], metadata=json_doc['metadata'],
                               coords=pdm.Coords(json_doc['coords']), text_regions=text_regions, lines=lines,
                               reading_order=reading_order)
    pdm.set_parentage(column)
    # print("IN COLUMN", column.id, column.stats)
    return column


def json_to_base_elements(json_doc: dict):
    columns = [json_to_pagexml_column(column) for column in json_doc['columns']] if 'columns' in json_doc else []
    text_regions = [json_to_pagexml_text_region(text_region) for text_region in json_doc['text_regions']] \
        if 'text_regions' in json_doc else []
    lines = [json_to_pagexml_line(line) for line in json_doc['lines']] if 'lines' in json_doc else []
    reading_order = json_doc['reading_order'] if 'reading_order' in json_doc else {}
    return columns, text_regions, lines, reading_order


def json_to_pagexml_page(json_doc: dict) -> pdm.PageXMLPage:
    extra = [json_to_pagexml_text_region(text_region) for text_region in json_doc['extra']] \
        if 'extra' in json_doc else []
    columns, text_regions, lines, reading_order = json_to_base_elements(json_doc)

    coords = pdm.Coords(json_doc['coords']) if 'coords' in json_doc else None
    page = pdm.PageXMLPage(doc_id=json_doc['id'], doc_type=json_doc['type'], metadata=json_doc['metadata'],
                           coords=coords, extra=extra, columns=columns,
                           text_regions=text_regions, lines=lines,
                           reading_order=reading_order)
    pdm.set_parentage(page)
    return page


def json_to_pagexml_scan(json_doc: dict) -> pdm.PageXMLScan:
    pages = [json_to_pagexml_page(page) for page in json_doc['pages']] if 'pages' in json_doc else []
    columns, text_regions, lines, reading_order = json_to_base_elements(json_doc)

    scan = pdm.PageXMLScan(doc_id=json_doc['id'], doc_type=json_doc['type'], metadata=json_doc['metadata'],
                           coords=pdm.Coords(json_doc['coords']), pages=pages, columns=columns,
                           text_regions=text_regions, lines=lines, reading_order=reading_order)
    pdm.set_parentage(scan)
    return scan


def json_to_pagexml_doc(json_doc: dict) -> pdm.PageXMLDoc:
    if 'pagexml_doc' not in json_doc['type']:
        raise TypeError('json_doc is not of type "pagexml_doc".')
    if 'scan' in json_doc['type']:
        return json_to_pagexml_scan(json_doc)
    if 'page' in json_doc['type']:
        return json_to_pagexml_page(json_doc)
    if 'column' in json_doc['type']:
        return json_to_pagexml_column(json_doc)
    if 'text_region' in json_doc['type']:
        return json_to_pagexml_text_region(json_doc)
    if 'line' in json_doc['type']:
        return json_to_pagexml_line(json_doc)
    if 'word' in json_doc['type']:
        return json_to_pagexml_word(json_doc)
