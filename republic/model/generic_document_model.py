from typing import Dict, List, Union
from collections import defaultdict
from collections import Counter
import copy
import string
import re

from republic.helper.metadata_helper import make_iiif_region_url


def parse_derived_coords(item_list: list) -> Dict[str, int]:
    """Return the coordinates of a box around a given list of items that each have their own coordinates."""
    for item in item_list:
        if 'coords' not in item:
            raise KeyError("items in list should have a 'coords' property")
    if len(item_list) == 0:
        left, right, top, bottom = 0, 0, 0, 0
    else:
        left = item_list[0]['coords']['left']
        right = item_list[0]['coords']['right']
        top = item_list[0]['coords']['top']
        bottom = item_list[0]['coords']['bottom']
    for item in item_list:
        if item['coords']['left'] < left:
            left = item['coords']['left']
        if item['coords']['right'] > right:
            right = item['coords']['right']
        if item['coords']['top'] < top:
            top = item['coords']['top']
        if item['coords']['bottom'] > bottom:
            bottom = item['coords']['bottom']
    return {
        'left': left,
        'right': right,
        'top': top,
        'bottom': bottom,
        'height': bottom - top,
        'width': right - left
    }


def order_lines(lines):
    ordered_lines = []
    for li, curr_line in enumerate(lines[:-1]):
        if curr_line in ordered_lines:
            continue
        next_line = lines[li+1]
        min_bottom = min(curr_line['coords']['bottom'], next_line['coords']['bottom'])
        max_top = max(curr_line['coords']['top'], next_line['coords']['top'])
        overlap = min_bottom - max_top
        if overlap > curr_line["coords"]["height"] / 2:
            if curr_line['coords']['left'] > next_line['coords']['right']:
                ordered_lines.append(next_line)
        ordered_lines.append(curr_line)
    if lines[-1] not in ordered_lines:
        ordered_lines.append(lines[-1])
    return ordered_lines


class StructureDoc:

    def __init__(self,
                 metadata: Union[None, Dict] = None,
                 coords: Union[None, Dict] = None,
                 lines: Union[None, List[Dict[str, Union[str, int, Dict[str, int]]]]] = None,
                 columns: Union[None, List[Dict[str, Union[dict, list]]]] = None):
        """This is a generic class for gathering lines that belong to the same logical structural element,
        even though they appear across different columns and pages."""
        self.metadata = copy.deepcopy(metadata) if metadata is not None else {}
        self.coords = coords
        self.type = "structure_doc"
        self.lines: List[Dict[str, Union[str, int, Dict[str, int]]]] = lines if lines else []
        self.column_ids = defaultdict(list)
        self.columns: List[Dict[str, Union[dict, list]]] = columns if columns else []
        if lines:
            self.add_lines_as_columns()
        elif columns:
            self.add_columns_as_lines()

    def add_columns_as_lines(self):
        """Add the lines from the columns as list, keeping track which column each line belongs to."""
        self.lines = self.generate_lines_from_columns()
        # for line in self.lines:
        #     self.column_ids[line['column_id']].append(line)

    def add_lines_as_columns(self):
        """Generate columns from the lines, keeping track which column each line belongs to."""
        for line in self.lines:
            self.column_ids[line['metadata']['column_id']].append(line)
        self.columns = self.generate_columns_from_lines()

    def get_lines(self) -> List[Dict[str, Union[str, int, dict]]]:
        """Return all the lines of the document."""
        return self.lines

    def get_columns(self) -> List[Dict[str, Union[list, dict]]]:
        """Return all the columns of the document."""
        return self.columns

    def generate_lines_from_columns(self):
        """Generate a list of lines from the columns."""
        textregions = [textregion for column in self.columns for textregion in column['textregions']]
        return [line for textregion in textregions for line in textregion['lines']]

    def generate_columns_from_lines(self) -> List[Dict[str, Union[dict, list]]]:
        """Return all the columns and lines belonging to this document.
        The coordinates of the columns are derived from the coordinates of the lines they contain."""
        columns = []
        for column_id in self.column_ids:
            line = self.column_ids[column_id][0]
            textregion_lines = defaultdict(list)
            for line in self.column_ids[column_id]:
                textregion_lines[line['metadata']['textregion_id']] += [line]
            column = {
                'metadata': {
                    'id': column_id,
                    'scan_id': line['metadata']['scan_id'],
                    'doc_id': line['metadata']['doc_id'],
                },
                'coords': parse_derived_coords(self.column_ids[column_id]),
                'textregions': []
            }
            for textregion_id in textregion_lines:
                textregion = {
                    'metadata': {'textregion_id': textregion_id},
                    'coords': parse_derived_coords(textregion_lines[textregion_id]),
                    'lines': textregion_lines[textregion_id]
                }
                column['textregions'] += [textregion]
            columns += [column]
        return columns

    def add_iiif_urls(self, scan_urls: dict):
        for column in self.columns:
            scan_url = scan_urls[column["scan_id"]]
            region_url = make_iiif_region_url(scan_url, column["coords"], add_margin=50)
            column["metadata"]["iiif_url"] = region_url

    def bounding_box_match(self, other):
        for key in self.coords:
            if self.coords[key] != other.coords[key]:
                return False
        return True

    def bounding_box_overlap(self, other) -> dict:
        overlap_box = {"left": 0, "right": 0, "top": 0, "bottom": 0, "width": 0, "height": 0}
        # self is to the left or to the right of other
        if self.coords["right"] <= other.coords["left"] or self.coords["left"] >= other.coords["right"]:
            return overlap_box
        # self is above or below other
        if self.coords["bottom"] <= other.coords["top"] or self.coords["top"] >= other.coords["bottom"]:
            return overlap_box
        # self overlaps with other
        max_left = max(self.coords["left"], other.coords["left"])
        min_right = min(self.coords["right"], other.coords["right"])
        max_top = max(self.coords["top"], other.coords["top"])
        min_bottom = min(self.coords["bottom"], other.coords["bottom"])
        return {
            "left": max_left,
            "right": min_right,
            "top": max_top,
            "bottom": min_bottom,
            "width": min_right - max_left,
            "height": min_bottom - max_top
        }

    def transpose(self, other):
        return {
            "left": other.coords["left"] - self.coords["left"],
            "right": other.coords["right"] - self.coords["right"],
            "top": other.coords["top"] - self.coords["top"],
            "bottom": other.coords["bottom"] - self.coords["bottom"],
        }

    def sort_columns(self):
        merge = {}
        columns = copy.copy(self.columns)
        for ci1, column1 in enumerate(columns):
            for ci2, column2 in enumerate(columns):
                if column1["metadata"]["scan_id"] != column2["metadata"]["scan_id"]:
                    continue
                if ci1 == ci2:
                    continue
                if column1['coords']['left'] >= column2['coords']['left'] and \
                        column1['coords']['right'] <= column2['coords']['right']:
                    # print(f'MERGE COLUMN {ci1} INTO COLUMN {ci2}')
                    merge[ci1] = ci2
        for merge_column in merge:
            # merge contained column in container column
            columns[merge[merge_column]]['textregions'] += columns[merge_column]['textregions']
        return [(ci, column) for ci, column in enumerate(columns) if ci not in merge]

    def stream_ordered_lines(self):
        columns = self.sort_columns()
        for column_index, column in columns:
            for ti, text_region in enumerate(column["textregions"]):
                for line in order_lines(text_region["lines"]):
                    line["metadata"]["inventory_num"] = self.metadata["inventory_num"]
                    line["metadata"]["doc_id"] = self.metadata["id"]
                    line["metadata"]["column_index"] = column_index
                    line["metadata"]["textregion_index"] = ti
                    yield line


class PhysicalStructureDoc(StructureDoc):

    def __init__(self, metadata: Union[None, Dict] = None,
                 coords: Union[None, Dict] = None,
                 version: Union[None, dict] = None,
                 lines: Union[None, List[Dict[str, Union[str, int, Dict[str, int]]]]] = None,
                 columns: Union[None, List[Dict[str, Union[dict, list]]]] = None):
        """A physical structure doc is an element from the scan hierarchy, where the scan
        is the top level in the hierarchy, and is itself a physical structure document.
        Other typical physical structure document levels are pages, columns, text regions
        and lines. A physical structure doc can have a single version, based on the version
        of the scan."""
        super().__init__(metadata=metadata, coords=coords, lines=lines, columns=columns)
        self.version = version
        self.type = "physical_structure_doc"


class LogicalStructureDoc(StructureDoc):

    def __init__(self, metadata: Union[None, Dict] = None,
                 coords: Dict = None,
                 versions: List[dict] = None,
                 lines: List[Dict[str, Union[str, int, Dict[str, int]]]] = None,
                 columns: List[Dict[str, Union[dict, list]]] = None):
        """A logical structure document is an element from the logical hierarchy of a digitised
        resource, where a resource can be any coherent object, like a book, newspaper or letter.
        A logical structure document has a correspondence to a physical structure document, e.g.
        can be carried on multiple scans, pages, etc., therefore can be linked to versions of
        multiple physical structure documents.
        Logical structure documents can have text regions and lines (the basic elements
        of the text recognition process), as well as columns as post-interpreted elements."""
        super().__init__(metadata=metadata, coords=coords, lines=lines, columns=columns)
        self.scan_versions: List[dict] = versions
        self.type = "logical_structure_doc"


class PageDoc(PhysicalStructureDoc):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.type = "page"
        # make sure page has scan id in metadata
        if "scan_id" not in self.metadata:
            self.metadata["scan_id"] = self.metadata["id"].split("-page")[0]
        # make sure each column has a scan_id
        for column in self.columns:
            if "scan_id" not in column["metadata"]:
                column["metadata"]["scan_id"] = self.metadata["scan_id"]


class Paragraph:

    def __init__(self, para_lines: list, word_freq: Counter = None):
        self.lines = copy.deepcopy(para_lines)
        self.metadata = {
            "inventory_num": para_lines[0]["metadata"]["inventory_num"]
        }
        self.text = ""
        self.line_ranges = []
        self.set_text(word_freq)

    def __repr__(self):
        return f"Paragraph(lines={[line['metadata']['id'] for line in self.lines]}, text={self.text})"

    def json(self):
        return {
            "metadata": self.metadata,
            "lines": [line['metadata']['id'] for line in self.lines],
            "text": self.text,
            "line_ranges": self.line_ranges
        }

    def set_text(self, word_freq: Counter = None):
        for li, line in enumerate(self.lines):
            if line["text"] is None:
                continue
            elif 'is_bleed_through' in line['metadata'] and line['metadata']['is_bleed_through']:
                continue
            elif len(line['text']) == 1:
                continue
            next_line = self.lines[li+1] if len(self.lines) > li+1 else {'text': None}
            if len(line["text"]) > 2 and line["text"][-2] == "-" and not line["text"][-1].isalpha():
                line_text = line["text"][:-2]
            elif line["text"][-1] == "-":
                line_text = line["text"][:-1]
            elif line_ends_with_word_break(line, next_line, word_freq):
                line_text = re.split(r'\W+$', line["text"])[0]
            elif (li + 1) == len(self.lines):
                line_text = line["text"]
            else:
                line_text = line["text"] + " "
            line_range = {"start": len(self.text), "end": len(self.text + line_text)}
            self.text += line_text
            self.line_ranges.append(line_range)

    def get_match_lines(self, match):
        part_of_match = False
        match_lines = []
        for li, line_range in enumerate(self.line_ranges):
            if line_range["start"] <= match.offset < line_range["end"]:
                part_of_match = True
            if line_range["start"] <= match.end:
                part_of_match = False
            if part_of_match:
                match_lines.append(self.lines[li])
        return match_lines


class ColumnDoc:

    def __init__(self, metadata: dict, coords: dict, textregions: List[dict]):
        self.metadata = metadata
        self.coords = coords
        self.textregions = textregions


class PageLine:

    def __init__(self, line: dict):
        assert 'xheight' in line
        assert 'text' in line
        self.xheight = line['xheight']
        self.text = line['text']
        self.metadata = line['metadata']


def line_ends_with_word_break(curr_line: Dict[str, any], next_line: Dict[str, any],
                              word_freq: Counter = None) -> bool:
    if not next_line['text']:
        # if the next line has no text, it has no first word to join with the last word of the current line
        return False
    if not curr_line['text'][-1] in string.punctuation:
        # if the current line does not end with punctuation, we assume, the last word is not hyphenated
        return False
    match = re.search(r'(\w+)\W+$', curr_line['text'])
    if not match:
        # if the current line has no word immediately before the punctuation, we assume there is no word break
        return False
    last_word = match.group(1)
    match = re.search(r'^(\w+)', next_line['text'])
    if not match:
        # if the next line does not start with a word, we assume it should not be joined to the last word
        # on the current line
        return False
    next_word = match.group(1)
    if curr_line['text'][-1] == '-':
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
        print('last word:', last_word, word_freq[last_word])
        print('next word:', next_word, word_freq[next_word])
        print('joint word:', joint_word, word_freq[joint_word])
        return True
    else:
        return False


def doc_from_json(self, doc_json):
    if doc_json["metadata"]["doc_type"] == "page":
        return PageDoc(metadata=doc_json["metadata"],
                       coords=doc_json["coords"],
                       columns=doc_json["columns"],
                       version=doc_json["version"])
    if isinstance(doc_json["version"], list):
        return LogicalStructureDoc(metadata=doc_json["metadata"],
                                   coords=doc_json["coords"],
                                   columns=doc_json["columns"],
                                   versions=doc_json["version"])


def same_height(line1: Dict[str, any], line2: Dict[str, any]) -> bool:
    max_top = max(line1['coords']['top'], line2['coords']['top'])
    min_bottom = min(line1['coords']['bottom'], line2['coords']['bottom'])
    min_height = min(line1['coords']['height'], line2['coords']['height'])
    overlap = min_bottom - max_top
    return overlap > (min_height/2)


def same_column(line1, line2):
    if line1["metadata"]["scan_id"] != line2["metadata"]["scan_id"]:
        return False
    return line1["metadata"]["column_index"] == line2["metadata"]["column_index"]


def stream_ordered_lines_multi_doc(docs: List[StructureDoc]):
    for doc in docs:
        for line in doc.stream_ordered_lines():
            yield line


