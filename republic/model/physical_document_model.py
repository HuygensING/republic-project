from __future__ import annotations
from typing import Dict, List, Set, Tuple, Union
from collections import defaultdict
from collections import Counter
import copy
import string
import re

import numpy as np
from scipy.spatial import ConvexHull

from republic.helper.metadata_helper import make_iiif_region_url


def parse_points(points: Union[str, List[Tuple[int, int]]]) -> List[Tuple[int, int]]:
    """Parse a string of PageXML image coordinates into a list of coordinates."""
    if isinstance(points, str):
        points = [point.split(',') for point in points.split(' ')]
        return [(int(point[0]), int(point[1])) for point in points]
    elif isinstance(points, list):
        if len(points) == 0:
            raise IndexError("point list cannot be empty")
        for point in points:
            if not isinstance(point, list) and not isinstance(point, tuple):
                print(point)
                print(type(point))
                raise TypeError("List of points must be list of tuples with (int, int)")
            if not isinstance(point[0], int) or not isinstance(point[1], int):
                raise TypeError("List of points must be list of tuples with (int, int)")
        return points


class Coords:

    def __init__(self, points: Union[str, List[Tuple[int, int]]]):
        self.points: List[Tuple[int, int]] = parse_points(points)
        self.point_string = " ".join([",".join([str(point[0]), str(point[1])]) for point in self.points])
        self.x = min([point[0] for point in self.points])
        self.y = min([point[1] for point in self.points])
        self.w = max([point[0] for point in self.points]) - self.x
        self.h = max([point[1] for point in self.points]) - self.y
        self.type = "coords"

    def __repr__(self):
        return f'{self.__class__.__name__}(points="{self.point_string}")'

    def __str__(self):
        return self.__repr__()

    @property
    def json(self):
        return {
            'type': self.type,
            'points': self.points
        }

    @property
    def left(self):
        return self.x

    @property
    def right(self):
        return self.x + self.w

    @property
    def top(self):
        return self.y

    @property
    def bottom(self):
        return self.y + self.h

    @property
    def height(self):
        return self.h

    @property
    def width(self):
        return self.w

    @property
    def box(self):
        return {"x": self.x, "y": self.y, "w": self.w, "h": self.h}


class Baseline(Coords):

    def __init__(self, points: Union[str, List[Tuple[int, int]]]):
        super().__init__(points)
        self.type = "baseline"


def parse_derived_coords(document_list: list) -> Coords:
    """Derive scan coordinates for a composite document based on the list of documents it contains.
    A convex hull is drawn around all points of all contained documents."""
    return coords_list_to_hull_coords([document.coords for document in document_list])


def coords_list_to_hull_coords(coords_list):
    points = np.array([point for coords in coords_list for point in coords.points])
    edges = points_to_hull_edges(points)
    hull_points = edges_to_hull_points(edges)
    return Coords(hull_points)


def points_to_hull_edges(points):
    hull = ConvexHull(points)
    edges = defaultdict(dict)
    for simplex in hull.simplices:
        p1 = (int(points[simplex, 0][0]), int(points[simplex, 1][0]))
        p2 = (int(points[simplex, 0][1]), int(points[simplex, 1][1]))
        edges[p2][p1] = 1
        edges[p1][p2] = 1
    return edges


def edges_to_hull_points(edges):
    nodes = list(edges.keys())
    curr_point = sorted(nodes)[0]
    sorted_nodes = [curr_point]
    while len(sorted_nodes) < len(nodes):
        for next_point in edges[curr_point]:
            if next_point not in sorted_nodes:
                sorted_nodes.append(next_point)
                curr_point = next_point
                break
    return sorted_nodes


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

    def __init__(self, doc_id: Union[None, str] = None, doc_type: Union[None, str, List[str]] = None,
                 metadata: Union[None, Dict[str, any]] = None):
        self.id = doc_id
        self.type = doc_type
        self.metadata = metadata

    def add_type(self, doc_type: Union[str, List[str]]) -> None:
        doc_types = [doc_type] if isinstance(doc_type, str) else doc_type
        if isinstance(self.type, str):
            self.type = [self.type]
        for doc_type in doc_types:
            if doc_type not in self.type:
                self.type.append(doc_type)

    def remove_type(self, doc_type: Union[str, List[str]]) -> None:
        doc_types = [doc_type] if isinstance(doc_type, str) else doc_type
        if isinstance(self.type, str):
            self.type = [self.type]
        for doc_type in doc_types:
            if doc_type not in self.type:
                self.type.append(doc_type)
        if len(self.type) == 1:
            self.type = self.type[0]

    def has_type(self, doc_type: str) -> bool:
        if isinstance(self.type, str):
            return doc_type == self.type
        else:
            return doc_type in self.type

    @property
    def types(self) -> Set[str]:
        if isinstance(self.type, str):
            return {self.type}
        else:
            return set(self.type)

    @property
    def json(self) -> Dict[str, any]:
        return {
            'id': self.id,
            'type': self.type,
            'metadata': self.metadata
        }


class PhysicalStructureDoc(StructureDoc):

    def __init__(self, doc_id: str = None, doc_type: Union[str, List[str]] = None,
                 metadata: Dict[str, any] = None, coords: Coords = None):
        super().__init__(doc_id, doc_type, metadata)
        self.coords: Union[None, Coords] = coords
        self.main_type = 'doc'

    @property
    def json(self) -> Dict[str, any]:
        doc_json = super().json
        if self.coords:
            doc_json['coords'] = self.coords.points
        return doc_json

    def set_derived_id(self, parent_id: str):
        box_string = f"{self.coords.x}-{self.coords.y}-{self.coords.w}-{self.coords.h}"
        self.id = f"{parent_id}-{self.main_type}-{box_string}"


class PageXMLDoc(PhysicalStructureDoc):

    def __init__(self, doc_id: str = None, doc_type: Union[str, List[str]] = None,
                 metadata: Dict[str, any] = None, coords: Coords = None):
        super().__init__(doc_id, "pagexml_doc", metadata)
        self.coords: Union[None, Coords] = coords
        self.add_type(doc_type)
        self.main_type = 'pagexml_doc'


class PageXMLWord(PageXMLDoc):

    def __init__(self, doc_id: str = None, doc_type: Union[str, List[str]] = None,
                 metadata: Dict[str, any] = None, coords: Coords = None,
                 conf: float = None, text: str = None):
        super().__init__(doc_id, "word", metadata, coords)
        self.conf = conf
        self.text = text
        self.main_type = 'word'
        if doc_type:
            self.add_type(doc_type)

    @property
    def json(self) -> Dict[str, any]:
        doc_json = super().json
        doc_json['text'] = self.text
        if self.conf:
            doc_json['conf'] = self.conf
        return doc_json


class PageXMLTextLine(PageXMLDoc):

    def __init__(self, doc_id: str = None, doc_type: Union[str, List[str]] = None,
                 metadata: Dict[str, any] = None, coords: Coords = None,
                 baseline: Baseline = None, xheight: int = None,
                 text: str = None, words: List[PageXMLWord] = None):
        super().__init__(doc_id, "line", metadata, coords)
        self.main_type = 'line'
        self.text: Union[None, str] = text
        self.xheight: Union[None, int] = xheight
        self.baseline: Union[None, Baseline] = baseline
        self.words: List[PageXMLWord] = words if words else []
        if doc_type:
            self.add_type(doc_type)

    @property
    def json(self) -> Dict[str, any]:
        doc_json = super().json
        doc_json['text'] = self.text
        if self.baseline:
            doc_json['baseline'] = self.baseline.json
        if self.words:
            doc_json['words'] = [word.json for word in self.words]
        if self.xheight:
            doc_json['xheight'] = self.xheight
        return doc_json

    def get_words(self):
        if self.words:
            return self.words
        elif self.text:
            return self.text.split(' ')
        else:
            return []

    @property
    def num_words(self):
        return len(self.get_words())


class PageXMLTextRegion(PageXMLDoc):

    def __init__(self, doc_id: str = None, doc_type: Union[str, List[str]] = None,
                 metadata: Dict[str, any] = None, coords: Coords = None,
                 text_regions: List[PageXMLTextRegion] = None,
                 lines: List[PageXMLTextLine] = None, orientation: float = None):
        super().__init__(doc_id, "text_region", metadata, coords)
        self.main_type = 'text_region'
        self.text_regions: List[PageXMLTextRegion] = text_regions if text_regions else []
        self.lines: List[PageXMLTextLine] = lines if lines else []
        self.orientation: Union[None, float] = orientation
        if doc_type:
            self.add_type(doc_type)

    @property
    def json(self) -> Dict[str, any]:
        doc_json = super().json
        if self.lines:
            doc_json['lines'] = [line.json for line in self.lines]
        if self.text_regions:
            doc_json['text_regions'] = [text_region.json for text_region in self.text_regions]
        if self.orientation:
            doc_json['orientation'] = self.orientation
        doc_json['stats'] = self.stats
        return doc_json

    def get_inner_text_regions(self) -> List[PageXMLTextRegion]:
        text_regions: List[PageXMLTextRegion] = []
        for text_region in self.text_regions:
            if text_region.text_regions:
                text_regions += text_region.get_inner_text_regions()
            elif text_region.lines:
                text_regions.append(text_region)
        if not self.text_regions and self.lines:
            text_regions.append(self)
        return text_regions

    def get_lines(self) -> List[PageXMLTextLine]:
        lines: List[PageXMLTextLine] = []
        if self.text_regions:
            for text_region in self.text_regions:
                lines += text_region.get_lines()
        if self.lines:
            lines += self.lines
        return lines

    def get_words(self):
        words: List[PageXMLWord] = []
        if self.text_regions:
            for text_region in self.text_regions:
                words += text_region.get_words()
        if self.lines:
            for line in self.lines:
                if line.words:
                    words += line.words
                elif line.text:
                    words += line.text.split(' ')
        return words

    @property
    def num_lines(self):
        return len(self.get_lines())

    @property
    def num_words(self):
        return len(self.get_words())

    @property
    def num_text_regions(self):
        return len(self.text_regions)

    @property
    def stats(self):
        return {
            'lines': self.num_lines,
            'words': self.num_words,
            'text_regions': self.num_text_regions
        }


class PageXMLColumn(PageXMLTextRegion):

    def __init__(self, doc_id: str = None, doc_type: Union[str, List[str]] = None,
                 metadata: Dict[str, any] = None, coords: Coords = None,
                 text_regions: List[PageXMLTextRegion] = None, lines: List[PageXMLTextLine] = None):
        super().__init__(doc_id=doc_id, doc_type="column", metadata=metadata, coords=coords)
        self.main_type = 'column'
        self.text_regions: List[PageXMLTextRegion] = text_regions if text_regions else []
        self.lines: List[PageXMLTextLine] = lines if lines else []
        if doc_type:
            self.add_type(doc_type)

    @property
    def json(self) -> Dict[str, any]:
        doc_json = super().json
        if self.lines:
            doc_json['lines'] = [line.json for line in self.lines]
        if self.text_regions:
            doc_json['text_regions'] = [text_region.json for text_region in self.text_regions]
        doc_json['stats'] = self.stats
        return doc_json

    @property
    def stats(self):
        stats = super().stats
        return stats


class PageXMLPage(PageXMLTextRegion):

    def __init__(self, doc_id: str = None, doc_type: Union[str, List[str]] = None,
                 metadata: Dict[str, any] = None, coords: Coords = None,
                 columns: List[PageXMLColumn] = None, text_regions: List[PageXMLTextRegion] = None,
                 extra: List[PageXMLTextRegion] = None,
                 lines: List[PageXMLTextLine] = None):
        super().__init__(doc_id=doc_id, doc_type="page", metadata=metadata, coords=coords)
        self.main_type = 'page'
        self.columns: List[PageXMLColumn] = columns if columns else []
        self.text_regions: List[PageXMLTextRegion] = text_regions if text_regions else []
        self.lines: List[PageXMLTextLine] = lines if lines else []
        self.extra: List[PageXMLTextRegion] = extra if extra else []
        if doc_type:
            self.add_type(doc_type)

    @property
    def json(self) -> Dict[str, any]:
        doc_json = super().json
        if self.lines:
            doc_json['lines'] = [line.json for line in self.lines]
        if self.text_regions:
            doc_json['text_regions'] = [text_region.json for text_region in self.text_regions]
        if self.columns:
            doc_json['columns'] = [column.json for column in self.columns]
        if self.extra:
            doc_json['extra'] = [text_region.json for text_region in self.extra]
        doc_json['stats'] = self.stats
        return doc_json

    @property
    def stats(self):
        stats = super().stats
        for column in self.columns:
            column_stats = column.stats
            for field in ['lines', 'words']:
                stats[field] += column_stats[field]
        stats['columns'] = len(self.columns)
        stats['extra'] = len(self.extra)
        return stats


class PageXMLScan(PageXMLTextRegion):

    def __init__(self, doc_id: str = None, doc_type: Union[str, List[str]] = None,
                 metadata: Dict[str, any] = None, coords: Coords = None,
                 pages: List[PageXMLPage] = None,
                 columns: List[PageXMLColumn] = None,
                 text_regions: List[PageXMLTextRegion] = None,
                 lines: List[PageXMLTextLine] = None):
        super().__init__(doc_id=doc_id, doc_type="scan", metadata=metadata, coords=coords)
        self.main_type = 'scan'
        self.pages: List[PageXMLPage] = pages if pages else []
        self.columns: List[PageXMLColumn] = columns if columns else []
        self.text_regions: List[PageXMLTextRegion] = text_regions if text_regions else []
        self.lines: List[PageXMLTextLine] = lines if lines else []
        if doc_type:
            self.add_type(doc_type)

    @property
    def json(self) -> Dict[str, any]:
        doc_json = super().json
        if self.lines:
            doc_json['lines'] = [line.json for line in self.lines]
        if self.text_regions:
            doc_json['text_regions'] = [text_region.json for text_region in self.text_regions]
        if self.columns:
            doc_json['columns'] = [line.json for line in self.columns]
        if self.pages:
            doc_json['pages'] = [line.json for line in self.pages]
        doc_json['stats'] = self.stats
        return doc_json

    @property
    def stats(self):
        stats = super().stats
        stats['columns'] = len([column for page in self.pages for column in page.columns])
        stats['extra'] = len([text_region for page in self.pages for text_region in page.extra])
        stats['pages'] = len(self.pages)
        return stats


class StructureDocOld:

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
        self.lines: List[Dict[str, Union[str, int, Dict[str, int]]]] = copy.deepcopy(lines) if lines else []
        self.column_ids = defaultdict(list)
        self.columns: List[Dict[str, Union[dict, list]]] = copy.deepcopy(columns) if columns else []
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
                textregion_lines[line['metadata']['id']] += [line]
            column = {
                'metadata': {
                    'id': column_id,
                    'scan_id': line['metadata']['scan_id'],
                    'doc_id': line['metadata']['doc_id'],
                },
                'coords': parse_derived_coords_old(self.column_ids[column_id]),
                'textregions': []
            }
            if 'page_column_id' in line['metadata']:
                column['metadata']['page_column_id'] = line['metadata']['page_column_id']
            for textregion_id in textregion_lines:
                textregion = {
                    'metadata': {'id': textregion_id},
                    'coords': parse_derived_coords_old(textregion_lines[textregion_id]),
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


class PhysicalStructureDocOld(StructureDocOld):

    def __init__(self, metadata: Union[None, Dict] = None,
                 coords: Union[None, Dict] = None,
                 scan_version: Union[None, dict] = None,
                 lines: Union[None, List[Dict[str, Union[str, int, Dict[str, int]]]]] = None,
                 columns: Union[None, List[Dict[str, Union[dict, list]]]] = None):
        """A physical structure doc is an element from the scan hierarchy, where the scan
        is the top level in the hierarchy, and is itself a physical structure document.
        Other typical physical structure document levels are pages, columns, text regions
        and lines. A physical structure doc can have a single version, based on the version
        of the scan."""
        super().__init__(metadata=metadata, coords=coords, lines=lines, columns=columns)
        self.scan_version = scan_version
        self.type = "physical_structure_doc"


class LogicalStructureDocOld(StructureDocOld):

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


class PageDoc(PhysicalStructureDocOld):

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


def doc_from_json(doc_json):
    if doc_json["metadata"]["doc_type"] == "page":
        return PageDoc(metadata=doc_json["metadata"],
                       coords=doc_json["coords"],
                       columns=doc_json["columns"],
                       version=doc_json["version"])
    if isinstance(doc_json["version"], list):
        return LogicalStructureDocOld(metadata=doc_json["metadata"],
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


def stream_ordered_lines_multi_doc(docs: List[StructureDocOld]):
    for doc in docs:
        for line in doc.stream_ordered_lines():
            yield line


def json_to_pagexml_word(json_doc: dict) -> PageXMLWord:
    word = PageXMLWord(doc_id=json_doc['id'], doc_type=json_doc['type'], metadata=json_doc['metadata'],
                       text=json_doc['text'])
    return word


def json_to_pagexml_line(json_doc: dict) -> PageXMLTextLine:
    words = [json_to_pagexml_word(word) for word in json_doc['words']] if 'words' in json_doc else []
    line = PageXMLTextLine(doc_id=json_doc['id'], doc_type=json_doc['type'], metadata=json_doc['metadata'],
                           coords=Coords(json_doc['coords']), text=json_doc['text'], words=words)
    return line


def json_to_pagexml_text_region(json_doc: dict) -> PageXMLTextRegion:
    text_regions = [json_to_pagexml_text_region(text_region) for text_region in json_doc['text_regions']] \
        if 'text_regions' in json_doc else []
    lines = [json_to_pagexml_line(line) for line in json_doc['lines']] if 'lines' in json_doc else []

    text_region = PageXMLTextRegion(doc_id=json_doc['id'], doc_type=json_doc['type'], metadata=json_doc['metadata'],
                                    coords=Coords(json_doc['coords']), text_regions=text_regions, lines=lines)
    return text_region


def json_to_pagexml_column(json_doc: dict) -> PageXMLColumn:
    text_regions = [json_to_pagexml_text_region(text_region) for text_region in json_doc['text_regions']] \
        if 'text_regions' in json_doc else []
    lines = [json_to_pagexml_line(line) for line in json_doc['lines']] if 'lines' in json_doc else []

    column = PageXMLColumn(doc_id=json_doc['id'], doc_type=json_doc['type'], metadata=json_doc['metadata'],
                           coords=Coords(json_doc['coords']), text_regions=text_regions, lines=lines)
    return column


def json_to_pagexml_page(json_doc: dict) -> PageXMLPage:
    extra = [json_to_pagexml_text_region(text_region) for text_region in json_doc['extra']] \
        if 'extra' in json_doc else []
    columns = [json_to_pagexml_column(column) for column in json_doc['columns']] if 'columns' in json_doc else []
    text_regions = [json_to_pagexml_text_region(text_region) for text_region in json_doc['text_regions']] \
        if 'text_regions' in json_doc else []
    lines = [json_to_pagexml_line(line) for line in json_doc['lines']] if 'lines' in json_doc else []

    page = PageXMLPage(doc_id=json_doc['id'], doc_type=json_doc['type'], metadata=json_doc['metadata'],
                       coords=Coords(json_doc['coords']), extra=extra, columns=columns,
                       text_regions=text_regions, lines=lines)
    return page


def json_to_pagexml_scan(json_doc: dict) -> PageXMLScan:
    pages = [json_to_pagexml_page(page) for page in json_doc['pages']] if 'pages' in json_doc else []
    columns = [json_to_pagexml_column(column) for column in json_doc['columns']] if 'columns' in json_doc else []
    text_regions = [json_to_pagexml_text_region(text_region) for text_region in json_doc['text_regions']] \
        if 'text_regions' in json_doc else []
    lines = [json_to_pagexml_line(line) for line in json_doc['lines']] if 'lines' in json_doc else []

    scan = PageXMLScan(doc_id=json_doc['id'], doc_type=json_doc['type'], metadata=json_doc['metadata'],
                       coords=Coords(json_doc['coords']), pages=pages, columns=columns,
                       text_regions=text_regions, lines=lines)
    return scan


def json_to_pagexml_doc(json_doc: dict) -> PageXMLDoc:
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
