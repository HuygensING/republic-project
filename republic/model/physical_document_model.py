from __future__ import annotations
from typing import Dict, Generator, List, Set, Tuple, Union
from collections import defaultdict
from collections import Counter
import string
import re

import numpy as np
from scipy.spatial import ConvexHull


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


def get_baseline_y(line: PageXMLTextLine) -> List[int]:
    """Return the Y/vertical coordinates of a text line's baseline."""
    if line_starts_with_big_capital(line):
        return [point[1] for point in line.baseline.points if point[1] < line.baseline.bottom - 20]
    else:
        return [point[1] for point in line.baseline.points]


def line_starts_with_big_capital(line: PageXMLTextLine) -> bool:
    """Determine is a line start with a capital in a larger font than the rest,
    which is aligned at the top, so sticks out at the bottom."""
    # The vertical distance between the lowest and highest baseline point (height) should be large
    if line.baseline.h < 30:
        return False
    lowest_point = find_lowest_point(line)
    # The lowest point should be left-aligned with the sentence.
    if lowest_point[0] - line.baseline.left > 100:
        return False
    return True


def find_lowest_point(line: PageXMLTextLine) -> Tuple[int, int]:
    """Find the first baseline point that corresponds to the lowest vertical point."""
    for point in line.baseline.points:
        if point[1] == line.baseline.bottom:
            return point


def interpolate_points(p1: Tuple[int, int], p2: Tuple[int, int],
                       step: int = 50) -> Generator[Dict[int, int], None, None]:
    """Determine the x coordinates between a pair of points on a baseline
    and calculate their corresponding y coordinates.
    :param p1: a 2D point
    :type p1: Tuple[int, int]
    :param p2: a 2D point
    :type p2: Tuple[int, int]
    :param step: the step size in pixels for interpolation
    :type step: int
    :return: a generator of interpolated points based on step size
    :rtype: Generator[Dict[int, int], None, None]
    """
    if p1[0] > p2[0]:
        # p2 should be to the right of p1
        p1, p2 = p2, p1
    start_x = p1[0] + step - (p1[0] % step)
    end_x = p2[0] - (p2[0] % step)
    delta_y = (p1[1] - p2[1]) / (p2[0] - p1[0])
    for int_x in range(start_x, end_x + 1, step):
        int_y = p1[1] - int((int_x - p1[0]) * delta_y)
        yield int_x, int_y


def interpolate_baseline_points(points: List[Tuple[int, int]],
                                step: int = 50) -> Dict[int, int]:
    """Determine the x coordinates between each pair of subsequent
    points on a baseline and calculate their corresponding y coordinates.

    :param points: the list of points of a baseline object
    :type points: List[Tuple[int, int]]
    :param step: the step size in pixels for interpolation
    :type step: int
    :return: a dictionary of interpolated points based on step size
    :rtype: Dict[int, int]
    """
    interpolated_baseline_points = {}
    # iterate over each subsequent pair of baseline points
    for ci, curr_point in enumerate(points[:-1]):
        next_point = points[ci + 1]
        # interpolate points between the current and next points using step as size
        for int_x, int_y in interpolate_points(curr_point, next_point, step=step):
            interpolated_baseline_points[int_x] = int_y
    return interpolated_baseline_points


def compute_baseline_distances(baseline1: Baseline, baseline2: Baseline,
                               step: int = 50) -> List[int]:
    """Compute the vertical distance between two baselines, based on
    their horizontal overlap, using a fixed step size. Interpolated
    points will be generated at fixed increments of step size for
    both baselines, so they have points with corresponding x
    coordinates to calculate the distance.

    :param baseline1: the first Baseline object to compare
    :type baseline1: Baseline
    :param baseline2: the second Baseline object to compare
    :type baseline2: Baseline
    :param step: the step size in pixels for interpolation
    :type step: int
    :return: a list of vertical distances based on horizontal overlap
    :rtype: List[int]
    """
    b1_points = interpolate_baseline_points(baseline1.points, step=step)
    b2_points = interpolate_baseline_points(baseline2.points, step=step)
    return [abs(b2_points[curr_x] - b1_points[curr_x]) for curr_x in b1_points
            if curr_x in b2_points]


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


def find_baseline_overlap_start_indexes(baseline1: Baseline, baseline2: Baseline) -> Tuple[int, int]:
    """Find the first point in each baseline where the two start to horizontally overlap."""
    baseline1_start_index = 0
    baseline2_start_index = 0
    for bi1, p1 in enumerate(baseline1.points):
        if bi1 < len(baseline1.points) - 1 and baseline1.points[bi1 + 1][0] < baseline2.points[0][0]:
            continue
        baseline1_start_index = bi1
        break
    for bi2, p2 in enumerate(baseline2.points):
        if bi2 < len(baseline2.points) - 1 and baseline2.points[bi2 + 1][0] < baseline1.points[0][0]:
            continue
        baseline2_start_index = bi2
        break
    return baseline1_start_index, baseline2_start_index


def baseline_is_below(baseline1: Baseline, baseline2: Baseline) -> bool:
    """Test if baseline 1 is directly below baseline 2"""
    num_below = 0
    num_overlap = 0
    # find the indexes of the first baseline points where the two lines horizontally overlap
    index1, index2 = find_baseline_overlap_start_indexes(baseline1, baseline2)
    while True:
        # check if the current baseline point of line 1 is below that of the one of line 2
        if baseline1.points[index1][1] > baseline2.points[index2][1]:
            num_below += 1
        num_overlap += 1
        # Check which baseline index to move forward for the next test
        if baseline1.points[index1][0] <= baseline2.points[index2][0]:
            # if current point of baseline 1 is to the left of the current point of baseline 2
            # move to the next point of baseline 1
            index1 += 1
        else:
            # otherwise, move to the next points of baseline 2
            index2 += 1
        if len(baseline1.points) == index1 or len(baseline2.points) == index2:
            # if the end of one of the baselines is reached, counting is done
            break
    # baseline 1 is below baseline 2 if the majority of
    # the horizontally overlapping points is below
    return num_below / num_overlap > 0.5


def horizontal_overlap(coords1: Coords, coords2: Coords) -> int:
    right = min(coords1.right, coords2.right)
    left = max(coords1.left, coords2.left)
    return right - left if right > left else 0


def vertical_overlap(coords1: Coords, coords2: Coords) -> int:
    bottom = min(coords1.bottom, coords2.bottom)
    top = max(coords1.top, coords2.top)
    return bottom - top if bottom > top else 0


def same_column(line1: PageXMLTextLine, line2: PageXMLTextLine) -> bool:
    if 'column_id' in line1.metadata and 'column_id' in line2.metadata:
        return True
    else:
        # check if the two lines have a horizontal overlap that is more than 50% of the width of line 1
        # Note: this doesn't work for short adjacent lines within the same column
        return horizontal_overlap(line1.coords, line2.coords) > (line1.coords.w / 2)


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


class StructureDoc:

    def __init__(self, doc_id: Union[None, str] = None, doc_type: Union[None, str, List[str]] = None,
                 metadata: Dict[str, any] = None):
        self.id = doc_id
        self.type = doc_type
        self.main_type = 'doc'
        self.metadata = metadata if metadata else {}
        self.parent: Union[StructureDoc, None] = None

    def set_parent(self, parent: StructureDoc):
        """Set parent document and add metadata of parent to this document's metadata"""
        self.parent = parent
        self.add_parent_id_to_metadata()

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

    def set_as_parent(self, children: List[StructureDoc]):
        """Set this document as parent of a list of child documents"""
        for child in children:
            child.set_parent(self)

    def add_parent_id_to_metadata(self):
        if self.parent:
            self.metadata['parent_type'] = self.parent.main_type
            self.metadata['parent_id'] = self.parent.id
            if hasattr(self.parent, 'main_type'):
                self.metadata[f'{self.parent.main_type}_id'] = self.parent.id

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
        self.main_type = 'physical_structure_doc'

    @property
    def json(self) -> Dict[str, any]:
        doc_json = super().json
        if self.coords:
            doc_json['coords'] = self.coords.points
        return doc_json

    def set_parentage(self):
        if hasattr(self, 'pages') and self.pages:
            self.set_as_parent(self.pages)
        if hasattr(self, 'columns') and self.columns:
            self.set_as_parent(self.columns)
        if hasattr(self, 'text_regions') and self.text_regions:
            self.set_as_parent(self.text_regions)
        if hasattr(self, 'lines') and self.lines:
            self.set_as_parent(self.lines)

    def set_derived_id(self, parent_id: str):
        box_string = f"{self.coords.x}-{self.coords.y}-{self.coords.w}-{self.coords.h}"
        self.id = f"{parent_id}-{self.main_type}-{box_string}"
        self.set_parentage()


class LogicalStructureDoc(StructureDoc):

    def __init__(self, doc_id: str = None, doc_type: Union[str, List[str]] = None,
                 metadata: Dict[str, any] = None, lines: List[PageXMLTextLine] = None,
                 text_regions: List[PageXMLTextRegion] = None):
        super().__init__(doc_id, doc_type, metadata)
        self.lines: List[PageXMLTextLine] = lines if lines else []
        self.text_regions: List[PageXMLTextRegion] = text_regions if text_regions else []
        self.logical_parent: Union[StructureDoc, None] = None

    def set_logical_parent(self, parent: StructureDoc):
        """Set parent document and add metadata of parent to this document's metadata"""
        self.logical_parent = parent
        self.add_logical_parent_id_to_metadata()

    def add_logical_parent_id_to_metadata(self):
        if self.logical_parent:
            self.metadata['logical_parent_type'] = self.logical_parent.main_type
            self.metadata['logical_parent_id'] = self.logical_parent.id
            if hasattr(self.logical_parent, 'main_type'):
                self.metadata[f'{self.logical_parent.main_type}_id'] = self.logical_parent.id


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
        self.metadata['type'] = 'line'
        self.set_as_parent(self.words)
        if doc_type:
            self.add_type(doc_type)

    @property
    def json(self) -> Dict[str, any]:
        doc_json = super().json
        doc_json['text'] = self.text
        if self.baseline:
            doc_json['baseline'] = self.baseline.points
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

    def is_below(self, other: PageXMLTextLine) -> bool:
        """Test if the baseline of this line is directly below the baseline of the other line."""
        # if there is no horizontal overlap, this line is not directly below the other
        if not horizontal_overlap(self.baseline, other.baseline):
            # print("NO HORIZONTAL OVERLAP")
            return False
        # if the bottom of this line is above the top of the other line, this line is above the other
        if self.baseline.bottom < other.baseline.top:
            # print("BOTTOM IS ABOVE TOP")
            return False
        # if most of this line's baseline points are not below most the other's baseline points
        # this line is not below the other
        if baseline_is_below(self.baseline, other.baseline):
            # print("BASELINE IS BELOW")
            return True
        return False

    def is_next_to(self, other: PageXMLTextLine) -> bool:
        """Test if this line is vertically aligned with the other line."""
        if vertical_overlap(self.coords, other.coords) == 0:
            # print("NO VERTICAL OVERLAP")
            return False
        if horizontal_overlap(self.coords, other.coords) > 40:
            # print("TOO MUCH HORIZONTAL OVERLAP", horizontal_overlap(self.coords, other.coords))
            return False
        if self.baseline.top > other.baseline.bottom + 10:
            # print("VERTICAL BASELINE GAP TOO BIG")
            return False
        else:
            return True


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
        self.set_parentage()
        if doc_type:
            self.add_type(doc_type)

    def set_parentage(self):
        if self.text_regions:
            self.set_as_parent(self.text_regions)
        if self.lines:
            self.set_as_parent(self.lines)

    def add_child(self, child: PageXMLDoc):
        child.set_parent(self)
        if isinstance(child, PageXMLTextLine):
            self.lines.append(child)
        elif isinstance(child, PageXMLTextRegion):
            self.text_regions.append(child)
        else:
            raise TypeError(f'unknown child type: {child.__class__.__name__}')

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
        super().__init__(doc_id=doc_id, doc_type="column", metadata=metadata, coords=coords, lines=lines,
                         text_regions=text_regions)
        self.main_type = 'column'
        self.set_parentage()
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
        super().__init__(doc_id=doc_id, doc_type="page", metadata=metadata, coords=coords, lines=lines,
                         text_regions=text_regions)
        self.main_type = 'page'
        self.columns: List[PageXMLColumn] = columns if columns else []
        self.extra: List[PageXMLTextRegion] = extra if extra else []
        self.set_parentage()
        self.set_as_parent(self.columns)
        self.set_as_parent(self.extra)
        if doc_type:
            self.add_type(doc_type)

    def add_child(self, child: PageXMLDoc, as_extra: bool = False):
        child.set_parent(self)
        if isinstance(child, PageXMLColumn):
            self.columns.append(child)
        elif isinstance(child, PageXMLTextLine):
            self.lines.append(child)
        elif isinstance(child, PageXMLTextRegion):
            if as_extra:
                self.extra.append(child)
            else:
                self.text_regions.append(child)
        else:
            raise TypeError(f'unknown child type: {child.__class__.__name__}')

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
        super().__init__(doc_id=doc_id, doc_type="scan", metadata=metadata, coords=coords, lines=lines,
                         text_regions=text_regions)
        self.main_type = 'scan'
        self.pages: List[PageXMLPage] = pages if pages else []
        self.columns: List[PageXMLColumn] = columns if columns else []
        self.set_parentage()
        self.set_as_parent(self.pages)
        self.set_as_parent(self.columns)
        if doc_type:
            self.add_type(doc_type)

    def add_child(self, child: PageXMLDoc):
        child.set_parent(self)
        if isinstance(child, PageXMLPage):
            self.pages.append(child)
        elif isinstance(child, PageXMLColumn):
            self.columns.append(child)
        elif isinstance(child, PageXMLTextRegion):
            self.text_regions.append(child)
        elif isinstance(child, PageXMLTextLine):
            self.lines.append(child)

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


def sort_regions_in_reading_order(doc: PageXMLDoc) -> List[PageXMLTextRegion]:
    doc_text_regions: List[PageXMLTextRegion] = []
    if hasattr(doc, 'columns') and doc.columns:
        doc_text_regions = doc.columns
    elif hasattr(doc, 'text_regions') and doc.text_regions:
        doc_text_regions = doc.text_regions
        for text_region in doc_text_regions:
            if doc.main_type == 'column':
                text_region.metadata['column_id'] = doc.id
            elif 'column_id' in doc.metadata:
                text_region.metadata['column_id'] = doc.metadata['column_id']
    if doc_text_regions:
        sub_text_regions = []
        for text_region in sorted(doc_text_regions, key=lambda x: x.coords.left):
            sub_text_regions += sort_regions_in_reading_order(text_region)
        return sub_text_regions
    elif isinstance(doc, PageXMLTextRegion):
        return [doc]
    else:
        return []


def sort_lines_in_reading_order(doc: PageXMLDoc) -> Generator[PageXMLTextLine]:
    """Sort the lines of a PageXML document in reading order.
    Reading order is: columns from left to right, text regions in columns from top to bottom,
    lines in text regions from top to bottom, and when (roughly) adjacent, from left to right."""
    for text_region in sort_regions_in_reading_order(doc):
        lines = sorted(text_region.lines, key=lambda x: x.coords.top)
        if text_region.main_type == 'column':
            text_region.metadata['column_id'] = text_region.id
        if 'column_id' not in text_region.metadata:
            raise KeyError(f'missing column id: {text_region.metadata}')
        if lines[0].metadata is None:
            lines[0].metadata = {'id': lines[0].id}
        if 'column_id' in text_region.metadata and 'column_id' not in lines[0].metadata:
            lines[0].metadata['column_id'] = text_region.metadata['column_id']
        stacked_lines = [[lines[0]]]
        rest_lines = lines[1:]
        if len(lines) > 1:
            for li, curr_line in enumerate(rest_lines):
                if curr_line.metadata is None:
                    curr_line.metadata = {'id': curr_line.id}
                if 'column_id' in text_region.metadata and 'column_id' not in curr_line.metadata:
                    curr_line.metadata['column_id'] = text_region.metadata['column_id']
                prev_line = stacked_lines[-1][-1]
                if curr_line.is_below(prev_line):
                    stacked_lines.append([curr_line])
                elif curr_line.is_next_to(prev_line):
                    stacked_lines[-1].append(curr_line)
        for lines in stacked_lines:
            for line in sorted(lines, key=lambda x: x.coords.left):
                yield line


def line_ends_with_word_break(curr_line: PageXMLTextLine, next_line: PageXMLTextLine,
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


def json_to_pagexml_word(json_doc: dict) -> PageXMLWord:
    word = PageXMLWord(doc_id=json_doc['id'], doc_type=json_doc['type'], metadata=json_doc['metadata'],
                       text=json_doc['text'])
    return word


def json_to_pagexml_line(json_doc: dict) -> PageXMLTextLine:
    words = [json_to_pagexml_word(word) for word in json_doc['words']] if 'words' in json_doc else []
    try:
        line = PageXMLTextLine(doc_id=json_doc['id'], doc_type=json_doc['type'], metadata=json_doc['metadata'],
                               coords=Coords(json_doc['coords']), baseline=Baseline(json_doc['baseline']),
                               text=json_doc['text'], words=words)
        return line
    except TypeError:
        print(json_doc['baseline'])
        raise


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

    coords = Coords(json_doc['coords']) if 'coords' in json_doc else None
    page = PageXMLPage(doc_id=json_doc['id'], doc_type=json_doc['type'], metadata=json_doc['metadata'],
                       coords=coords, extra=extra, columns=columns,
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
