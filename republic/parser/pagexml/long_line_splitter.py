import copy
import re
from typing import List, Tuple, Union

import numpy as np
import pagexml.model.physical_document_model as pdm
from nltk.collocations import BigramCollocationFinder
from pagexml.analysis.layout_stats import sort_coords_above_below_baseline
from pagexml.analysis.layout_stats import compute_baseline_distances

from republic.helper.pagexml_helper import horizontal_group_lines
from republic.parser.pagexml.generic_pagexml_parser import copy_page


def width_in_range(doc: pdm.PageXMLDoc, min_width: int = None, max_width: int = None) -> bool:
    """Check if a PageXMLDoc object has a width within a given range."""
    if min_width is not None and doc.coords.w < min_width:
        return False
    if max_width is not None and doc.coords.w > max_width:
        return False
    return True


def get_line_sequences_in_width_range(lines: List[pdm.PageXMLTextLine],
                                      min_width: int = None,
                                      max_width: int = None) -> List[List[pdm.PageXMLTextLine]]:
    """Return a list of lists of consecutive lines in a text region that have a
    width within a given width range"""
    sequences = []
    sequence = []
    for line in lines:
        if width_in_range(line, min_width=min_width, max_width=max_width) is False:
            if len(sequence) > 0:
                sequences.append(sequence)
            sequence = []
            continue
        sequence.append(line)
    if len(sequence) > 0:
        sequences.append(sequence)
    return sequences


class Word:

    def __init__(self, word: str, index: int, line: pdm.PageXMLTextLine, lg_index: int = None):
        self.word = word
        self.index = index
        self.line = line
        self.lg_index = lg_index

    def __repr__(self):
        return f"'{self.word}'"

    def __len__(self):
        return len(self.word)


def get_words(line: pdm.PageXMLTextLine):
    """Return the word tokens of a line."""
    if line.words is not None and len(line.words) > 0:
        words = [word.text for word in line.words]
    elif line.text is not None:
        words = line.text.split(' ')
    else:
        return None
    return [Word(word, wi, line) for wi, word in enumerate(words)]


def get_split_indexes(words: List[Word], min_offset: int, max_offset: int):
    offset = 0
    split_indexes = []
    for wi, word in enumerate(words):
        word_start, word_end = offset, offset + len(word)
        if min_offset <= word_start <= max_offset:
            split_indexes.append(wi)
        elif min_offset < word_end <= max_offset and word_end - min_offset > min_offset - word_start:
            # most of the word comes after the min offset, so add it too
            split_indexes.append(wi)
        offset = word_end + 1
    return split_indexes


class SplitWord:

    def __init__(self, word: Word, word_pos: str):
        self.word = word.word
        self.index = word.index
        self.line = word.line
        self.word_pos = word_pos

    def __len__(self):
        return len(self.word)

    def __repr__(self):
        attr_string = (f"word='{self.word}', index={self.index}, line_id='{self.line.id}', \n"
                       f"\tword_pos='{self.word_pos}'")
        return f"{self.__class__.__name__}({attr_string})"


class ColumnLines:

    def __init__(self, lines: pdm.PageXMLTextLine, left_first: SplitWord = None,
                 left_last: Union[SplitWord, List[SplitWord]] = None,
                 right_first: Union[SplitWord, List[SplitWord]] = None, right_last: SplitWord = None
                 ):
        self.lines = lines
        self.num_columns = 2
        self.left_first = left_first
        self.left_last = [left_last] if isinstance(left_last, SplitWord) else left_last
        self.right_first = right_first
        self.right_last = right_last


class LineInfo:

    def __init__(self, line_group: List[pdm.PageXMLTextLine],
                 column_sep_width: int, default_line_num_chars: int,
                 dist_to_prev: int, dist_to_next: int, default_line_width: int = None,
                 text_left_boundary: int = None, text_right_boundary: int = None,
                 words: List[Word] = None, split_indexes: List[int] = None):
        self.line_group = line_group
        self.min_left = line_group[0].coords.left
        self.max_right = line_group[-1].coords.right
        self.column_sep_width = column_sep_width
        self.default_line_num_chars = default_line_num_chars
        self.text_left_boundary = text_left_boundary
        self.text_right_boundary = text_right_boundary
        self.default_line_width = default_line_width
        self.width = self.max_right - self.min_left
        self.dist_to_prev = dist_to_prev
        self.dist_to_next = dist_to_next
        self.words = words
        self.split_indexes = split_indexes
        self.split_words = {}
        self.left_col_left = None
        self.left_col_right = None
        self.right_col_left = None
        self.right_col_right = None
        if self.text_left_boundary is not None and self.text_right_boundary is not None:
            self.left_col_left = self.text_left_boundary
            self.left_col_right = self.text_left_boundary + self.default_line_width
            self.right_col_left = self.left_col_right + column_sep_width
            self.right_col_right = self.text_right_boundary

    def update_boundaries(self, text_left_boundary: int, text_right_boundary: int):
        self.text_left_boundary = text_left_boundary
        self.text_right_boundary = text_right_boundary
        self.default_line_width = (self.text_right_boundary - self.text_left_boundary - self.column_sep_width) / 2
        self.left_col_left = self.text_left_boundary
        self.left_col_right = self.text_left_boundary + self.default_line_width
        self.right_col_left = self.left_col_right + self.column_sep_width
        self.right_col_right = self.text_right_boundary


def add_word_info(line_info: LineInfo):
    """Add information about words and word positions in each line and in the line group."""
    line_info.words = [word for line in line_info.line_group for word in get_words(line)]
    for wi, word in enumerate(line_info.words):
        word.lg_index = wi


class MergedLineContext:

    def __init__(self,
                 curr_line_info: LineInfo,
                 prev_line_info: LineInfo,
                 next_line_info: LineInfo,
                 column_sep_width: int,
                 default_line_num_chars: int,
                 default_line_width: int = None,
                 ):
        """A merged line with its surrounding lines (assuming a 2-column layout)
        and the left and right boundaries of the main text on the page. The left
        boundary is the left side of the left-most column, the right boundary is
        the right side of the right-most column.

        :param curr_line_info: the current merged line that is the focus for splitting
        :type: LineInfo
        :param prev_line_info: the previous line in the right-side column
        :type: LineInfo
        :param next_line_info: the next line in the left-side column
        :type: LineInfo
        :param column_sep_width: the width in pixels of the gap between the left
        and right columns
        :type column_sep_width: int
        :param default_line_width: the default width of a text line (if not given,
        it is derived from the text_left_boundary, text_right_boundary and
        column_sep_width
        :type default_line_width: int
        :param default_line_num_chars: the default number of characters of a text
        line.
        """
        # self.curr_group = {'lines': curr_line_group}
        # self.prev_group = {'lines': prev_line_group}
        # self.next_group = {'lines': next_line_group}
        self.curr_info = curr_line_info
        self.prev_info = prev_line_info
        self.next_info = next_line_info
        self.text_left_boundary = curr_line_info.text_left_boundary
        self.text_right_boundary = curr_line_info.text_right_boundary
        self.column_sep_width = column_sep_width
        self.default_line_num_chars = default_line_num_chars
        self.min_offset = default_line_num_chars - 15
        self.max_offset = default_line_num_chars + 15
        if default_line_width is None:
            self.default_line_width = (self.text_right_boundary - self.text_left_boundary - column_sep_width) / 2
        else:
            self.default_line_width = default_line_width
        # self.curr_info.split_indexes = get_split_indexes(self.curr_info.words, self.min_offset, self.max_offset)
        # print(f"long_line_splitter.MergedLineContext - prev_info:")
        # print(self.prev_info)
        # self.prev_info.split_indexes = []
        # self.next_info.split_indexes = []


def get_dist_to_other(line_group1: List[pdm.PageXMLTextLine], line_group2: List[pdm.PageXMLTextLine]) -> int:
    dist_list = compute_baseline_distances(line_group1, line_group2)
    return int(np.median(dist_list))


def extract_left_right_split_from_combination(line_info: LineInfo, combination):
    """Determine the x coordinate at which to split a line given a split combination. """

    left_last = combination['curr_left_last']
    merged_line = [line for line in line_info.line_group if line.id == left_last.line.id][0]
    right_first = combination['curr_right_first']

    left_words = [word for word in line_info.words[:left_last.index + 1] if word.line == merged_line]
    right_words = [word for word in line_info.words[right_first.index:] if word.line == merged_line]

    left_text = ' '.join([word.word for word in left_words])
    right_text = ' '.join([word.word for word in right_words])

    if len(left_text) == 0:
        merged_text = right_text
    elif len(right_text) == 0:
        merged_text = left_text
    else:
        merged_text = left_text + " " + right_text
    if merged_text != merged_line.text:
        print(f"long_line_splitter._extract_left_right_split_from_combination - splitting error:")
        print(f"line.text: {[line.text for line in line_info.line_group]}")
        print(f"merged_line.text: #{merged_line.text}#")
        print(f"\tleft_text: #{left_text}#")
        print(f"\tright_text: #{right_text}#")
        print(f"\tcombined_text: #{left_text + ' ' + right_text}#")
        print(len(left_text + " " + right_text), len(merged_line.text))
        for i in range(len(merged_text)):
            if merged_text[i] == merged_line.text[i]:
                continue
            print(f" discrepancy in index {i}, left+right: {merged_text[i]}\toriginal: {merged_line.text[i]}")
        raise ValueError(f"splits of merged_hyphenated_line do not combine to the original line")
    return left_text, right_text


def extract_left_right_splits_from_regex_match(line: pdm.PageXMLTextLine, match: re.Match, min_offset: int):
    """Determine the x coordinate at which to split a line given a hyphen/word-break
    match. """
    start, end = match.span()
    hyphen_offset = min_offset - 1 + start + len(match.group(1))
    left_text = line.text[:hyphen_offset + 1]
    right_text = line.text[hyphen_offset + 2:]
    if left_text + " " + right_text != line.text:
        print(f"long_line_splitter._extract_left_right_splits - splitting error:")
        print(f"line.text: {line.text}")
        print(f"\tleft_text: #{left_text}#")
        print(f"\tright_text: #{right_text}#")
        print(f"\tcombined_text: #{left_text + ' ' + right_text}#")
        raise ValueError(f"splits of merged_hyphenated_line do not combine to the original line")
    return left_text, right_text


def make_split_lines(line: pdm.PageXMLTextLine, left_line_left: int, left_line_right: int,
                     right_line_left: int, right_line_right: int,
                     left_line_text: str, right_line_text: str, debug: int = 0):
    left_baseline = make_split_baseline(line, left_line_right=left_line_right)
    right_baseline = make_split_baseline(line, right_line_left=right_line_left)
    left_coords = make_split_coords(line, left_line_right=left_line_right, debug=debug)
    right_coords = make_split_coords(line, right_line_left=right_line_left, debug=debug)
    if debug > 0:
        print("long_line_splitter.make_split_lines - ")
        print(f"    line.left: {line.coords.left}\tline.right: {line.coords.right}")
        print(f"    line.baseline: {line.baseline.points}")
        print(f"    line.coords: {line.coords.points}")
        print(f"    left_line_left: {left_line_left}\tleft_line_right: {left_line_right}")
        print(f"    right_line_left: {right_line_left}\tright_line_right: {right_line_right}")
        print(f"    left_baseline: {left_baseline.points}")
        print(f"    right_baseline: {right_baseline.points}")
        print(f"    left_coords: {left_coords.points}")
        print(f"    right_coords: {right_coords.points}")
    if left_baseline is None or left_coords is None:
        return None, line
    elif right_baseline is None or right_coords is None:
        return line, None
    left_line = pdm.PageXMLTextLine(metadata=copy.deepcopy(line.metadata), coords=left_coords,
                                    baseline=left_baseline, text=left_line_text)
    right_line = pdm.PageXMLTextLine(metadata=copy.deepcopy(line.metadata), coords=right_coords,
                                     baseline=right_baseline, text=right_line_text)
    left_line.set_derived_id(line.metadata['scan_id'])
    right_line.set_derived_id(line.metadata['scan_id'])
    return left_line, right_line


def make_split_baseline(line: pdm.PageXMLTextLine, left_line_right: int = None,
                        right_line_left: int = None, debug: int = 0) -> Union[pdm.Baseline, None]:
    """Make baselines for the left and right parts of the merged line."""
    if right_line_left is not None:
        points = [point for point in line.baseline.points if point[0] >= right_line_left]
        if debug > 0:
            print(f"right_line_left: {right_line_left}\tpoints: {points}")
        if len(points) == 0:
            return None
        if min([point[0] for point in points]) > right_line_left:
            # add a left_most point with the same height as the first selected point in the baseline
            right_line_left_point = (right_line_left, points[0][1])
            points = [right_line_left_point] + points
        return pdm.Baseline(points)
    elif left_line_right is not None:
        points = [point for point in line.baseline.points if point[0] <= left_line_right]
        if debug > 0:
            print(f"left_line_right: {left_line_right}\tpoints: {points}")
        if len(points) == 0:
            return None
        if max([point[0] for point in points]) < left_line_right:
            # add a right_most point with the same height as the last selected point in the baseline
            left_line_right_point = (left_line_right, points[0][1])
            points.append(left_line_right_point)
        return pdm.Baseline(points)
    else:
        raise ValueError("one of 'left' and 'right' must be an integer")


def make_split_coords(line: pdm.PageXMLTextLine, left_line_right: int = None,
                      right_line_left: int = None, debug: int = 0) -> Union[pdm.Coords, None]:
    """Make bounding box coordinates for the left and right parts of the merged line."""
    sort_coords_above_below_baseline(line)
    above_points, below_points = sort_coords_above_below_baseline(line)
    if len(above_points) == 0 or len(below_points) == 0:
        # For some reason the bounding box is not covering the baseline.
        # Hack: create a bounding box that is 40 pixels above and below the baseline.
        above_points = [[p[0], p[1] - 40] for p in line.baseline.points]
        below_points = [[p[0], p[1] + 20] for p in line.baseline.points]
    if right_line_left is not None:
        above_right_line_points = [point for point in above_points if point[0] >= right_line_left]
        below_right_line_points = [point for point in below_points if point[0] >= right_line_left]
        if debug > 0:
            print(f"right_line_left: {right_line_left}\tabove_right_line_points: {above_right_line_points}")
            print(f"\tbelow_right_line_points: {below_right_line_points}")
        if len(above_right_line_points) == 0 or len(below_right_line_points) == 0:
            return None
        elif len(above_right_line_points) == 0:
            above_right_line_points = [
                [right_line_left, above_points[0][1]],
                [line.coords.right, above_points[0][1]]
            ]
        elif len(below_right_line_points) == 0:
            below_right_line_points = [
                [right_line_left, below_points[0][1]],
                [line.coords.right, below_points[0][1]]
            ]
        if min([point[0] for point in above_right_line_points]) > right_line_left:
            # add a left_most point with the same height as the first selected point in the coords
            above_right_line_points = [[right_line_left, above_points[0][1]]] + above_right_line_points
        if min([point[0] for point in below_right_line_points]) > right_line_left:
            # add a left_most point with the same height as the first selected point in the coords
            below_right_line_points += [[right_line_left, below_points[0][1]]]
        return pdm.Coords(above_right_line_points + below_right_line_points)
    elif left_line_right is not None:
        above_left_line_points = [point for point in above_points if point[0] <= left_line_right]
        below_left_line_points = [point for point in below_points if point[0] <= left_line_right]
        if debug > 0:
            print(f"left_line_right: {left_line_right}\tabove_left_line_points: {above_left_line_points}")
            print(f"\tbelow_left_line_points: {below_left_line_points}")
        if len(above_left_line_points) == 0 and len(below_left_line_points) == 0:
            return None
        elif len(above_left_line_points) == 0:
            above_left_line_points = [
                [left_line_right, above_points[0][1]],
                [line.coords.left, above_points[0][1]]
            ]
        elif len(below_left_line_points) == 0:
            below_left_line_points = [
                [left_line_right, below_points[0][1]],
                [line.coords.left, below_points[0][1]]
            ]
        if max([point[0] for point in above_left_line_points]) < left_line_right:
            # add a left_most point with the same height as the first selected point in the coords
            above_left_line_points += [[left_line_right, above_points[0][1]]]
        if max([point[0] for point in below_left_line_points]) < left_line_right:
            # add a left_most point with the same height as the first selected point in the coords
            below_left_line_points = [[left_line_right, below_points[0][1]]] + below_left_line_points
        return pdm.Coords(above_left_line_points + below_left_line_points)
    else:
        raise ValueError("one of 'left' and 'right' must be an integer")


class LineSplitter:

    def __init__(self, min_merged_width: int,
                 default_line_width: int, default_line_num_chars: int,
                 text_left_boundary: int, text_right_boundary: int,
                 column_sep_width: int = 20):
        self.min_merged_width = min_merged_width
        self.default_line_num_chars = default_line_num_chars
        self.default_line_width = default_line_width
        self.text_left_boundary = text_left_boundary
        self.text_right_boundary = text_right_boundary
        self.min_offset = default_line_num_chars - 15
        self.max_offset = default_line_num_chars + 15
        self.column_sep_width = column_sep_width
        if default_line_width is None:
            self.default_line_width = int((text_right_boundary - text_left_boundary - column_sep_width) / 2)
        self.left_col_left = text_left_boundary
        self.left_col_right = text_left_boundary + self.default_line_width
        self.right_col_left = self.left_col_right + column_sep_width
        self.right_col_right = text_right_boundary

    def is_merged_line(self, line: pdm.PageXMLTextLine, min_merged_width: int = None):
        """Check if a text line is a merge of lines from adjacent columns."""
        if line.text is None:
            return None
        if len(line.text) < self.default_line_num_chars:
            return None
        if min_merged_width is None:
            min_merged_width = self.min_merged_width
        return width_in_range(line, min_width=min_merged_width)

    def is_merged_hyphenated_line(self, line: pdm.PageXMLTextLine, min_merged_width: int = None,
                                  debug: int = 0):
        """Check if a text line is a merge of lines from adjacent columns, where
        the first line ends in a hyphenated word break."""
        if line.text is None:
            return None
        if self.is_merged_line(line, min_merged_width=min_merged_width) is False:
            return False
        if debug > 1:
            print(f"min_offset: {self.min_offset}\tmax_offset: {self.max_offset}")
        if match := re.search(r"(\w+)- (\w+)", line.text[self.min_offset-1:]):
            start, end = match.span()
            hyphen_offset = self.min_offset - 1 + start + len(match.group(1))
            if debug > 1:
                print(f"start: {start}\tend: {end}\thyphen_offset: {hyphen_offset}")
            return self.min_offset <= hyphen_offset <= self.max_offset
        else:
            return False

    def get_left_right_ends(self, line: pdm.PageXMLTextLine, line_info: LineInfo,
                            column_sep_width: int = None):
        """Determine the left and right side coordinates of the left and right parts of the
        merged line."""

        left_indent = line.coords.left - line_info.text_left_boundary
        if left_indent < 0:
            left_indent = 0
        if column_sep_width is None:
            column_sep_width = self.column_sep_width
        left_line_left = line.coords.left
        left_line_right = line.coords.left + self.default_line_width - left_indent
        # add average column separation space
        right_line_left = line.coords.left + column_sep_width + self.default_line_width - left_indent
        right_line_right = line.coords.right
        if any([pos is None for pos in [left_line_left, left_line_right, right_line_left, right_line_right]]):
            print("long_line_splitter.get_left_right_ends:")
            print(f"    left_line_left: #{left_line_left}#")
            print(f"    left_line_right: #{left_line_right}#")
            print(f"    right_line_left: #{right_line_left}#")
            print(f"    right_line_right: #{right_line_right}#")
            raise ValueError(f"invalid left/right position value")
        return left_line_left, left_line_right, right_line_left, right_line_right

    def make_split_lines(self, line: pdm.PageXMLTextLine, line_info: LineInfo,
                         left_line_text: str, right_line_text: str, debug: int = 0):
        left_line_left, left_line_right, right_line_left, right_line_right = self.get_left_right_ends(line, line_info)
        return make_split_lines(line, left_line_left, left_line_right, right_line_left, right_line_right,
                                left_line_text, right_line_text, debug=debug)

    def split_merged_hyphenated_line(self, line: pdm.PageXMLTextLine, line_info: LineInfo,
                                     debug: int = 0) -> Tuple[pdm.PageXMLTextLine, Union[pdm.PageXMLTextLine, None]]:
        """Split a merged line where the left part ends in a word-break with a hyphen."""
        match = re.search(r"(\w+)- (\w+)", line.text[self.min_offset-1:self.max_offset+3])
        if match is None:
            return line, None
        left_line_text, right_line_text = extract_left_right_splits_from_regex_match(line, match, self.min_offset)
        left_line, right_line = self.make_split_lines(line, line_info, left_line_text,
                                                      right_line_text, debug=debug)
        return left_line, right_line

    def get_merged_hyphenated_lines(self, doc: Union[pdm.PageXMLTextRegion, List[pdm.PageXMLTextLine]],
                                    min_merged_width: int = None):
        """Return all lines from a text region that are merged hyphenated lines"""
        if min_merged_width is None:
            min_merged_width = self.min_merged_width
        lines = doc if isinstance(doc, list) else doc.get_lines()
        return [line for line in lines if self.is_merged_hyphenated_line(line, min_merged_width=min_merged_width)]

    def get_merged_lines(self, doc: Union[pdm.PageXMLTextRegion, List[pdm.PageXMLTextLine]],
                         min_merged_width: int = None):
        """Return all lines from a text region that are merged hyphenated lines"""
        lines = doc if isinstance(doc, list) else doc.get_lines()
        if min_merged_width is None:
            min_merged_width = self.min_merged_width
        return [line for line in lines if self.is_merged_line(line, min_merged_width=min_merged_width)]

    def has_merged_lines(self, doc: Union[pdm.PageXMLTextRegion, List[pdm.PageXMLTextLine]],
                         min_merged_width: int = None) -> bool:
        """Check if a PageXMLTextRegion document has any lines
        that are the merge of lines from two adjacent columns."""
        lines = doc if isinstance(doc, list) else doc.get_lines()
        if min_merged_width is None:
            min_merged_width = self.min_merged_width
        return any([self.is_merged_line(line, min_merged_width=min_merged_width) for line in lines])

    @staticmethod
    def doc_has_regular_lines(doc: Union[pdm.PageXMLTextRegion, List[pdm.PageXMLTextLine]], max_width: int) -> bool:
        """Check if a PageXMLTextRegion document has any lines
        that are the merge of lines from two adjacent columns."""
        lines = doc if isinstance(doc, list) else doc.get_lines()
        return any([width_in_range(line, max_width=max_width) for line in lines])


def get_split_word_candidates(line_splitter: LineSplitter, line_info: LineInfo, debug: int = 0):
    split_words = {
        'left_first': [],
        'left_last': [],
        'right_first': [],
        'right_last': [],
    }
    text_lines = [line for line in line_info.line_group if line.text is not None]
    if len(text_lines) == 0:
        return split_words
    first_line, last_line = text_lines[0], text_lines[-1]
    left_indent_width = first_line.coords.left - line_info.left_col_left
    right_indent_width = line_info.right_col_right - last_line.coords.right
    left_indent = True if left_indent_width > 250 else False
    right_indent = True if right_indent_width > 100 else False

    if debug > 0:
        print(f"long_line_splitter.get_split_word_candidates:")
        print(f"    first_line.coords.left: {first_line.coords.left}\tleft_col_left: {line_info.left_col_left}")
        print(f"   left_indent: {left_indent}\tright_indent: {right_indent}")
    # if the first line is not left indented, it starts on the left side of the column and
    # its first word probably is the continuation of the sentence of the previous left-column
    # line
    if left_indent is False:
        first_line_words = [word for word in line_info.words if word.line == first_line]
        split_words['left_first'] = [first_line_words[0]]

    # if the last line is not right indented, it ends on the right side of the column and
    # its last word probably is the location of the line break, and the sentence is continued
    # on the next line
    if right_indent is False:
        last_line_words = [word for word in line_info.words if word.line == last_line]
        split_words['right_last'] = [last_line_words[-1]]

    for line in line_info.line_group:
        line_words = [word for word in line_info.words if word.line == line]
        if abs(line.coords.right - line_info.left_col_right) < 100:
            # Line ends close to right side of left column.
            # Its last word is probably at the line break
            split_words['left_last'] = [line_words[-1]]
        elif abs(line.coords.left - line_info.right_col_left) < 100:
            # Line starts close to the left side of right column.
            # Its first word is probably the continuation after the previous line break
            split_words['right_first'] = [line_words[0]]
        if line_splitter.is_merged_line(line):
            # TO DO: check if there are relatively fewer characters for a full width line
            # Consider changing the offsets based on that.
            # If the line is left-indented (typically the start of a paragraph or an
            # unrecognised drop capital), adjust the min offset accordingly
            min_offset = line_splitter.min_offset
            if left_indent_width > 100:
                left_indent_width = line.coords.left - line_info.text_left_boundary
                avg_char_width = line.coords.width / len(line.text)
                offset_shift = int(left_indent_width / avg_char_width)
                min_offset -= offset_shift
                if debug > 0:
                    print(f"adjusting the min offset by {offset_shift} for line {line.id}")
            split_indexes = get_split_indexes(line_words, min_offset=min_offset,
                                              max_offset=line_splitter.max_offset)
            if debug > 0 and left_indent is True:
                print(f"min_offset: {min_offset}")
                print(f"split_indexes: {split_indexes}")
            sws = [line_words[si] for si in split_indexes]
            if debug > 0:
                print(f"merged_line - words: {line_words}")
                print(f"merged_line - split_indexes: {split_indexes}")
                print(f"merged_line - sws: {sws}")
            split_words['left_last'] = sws
            split_words['right_first'] = sws
    return split_words


def make_page_merged_line_contexts(line_splitter: LineSplitter, page: pdm.PageXMLPage,
                                   debug: int = 0):
    content_lines = [line for col in page.columns for line in col.get_lines() if line.text is not None]
    if not all([line.id is None or line.id.startswith('NL-HaNA') for line in content_lines]):
        print(f"long_line_splitter.make_page_merged_line_contexts - some of content_lines have no ID")
        for li, line in enumerate(content_lines):
            print(f"    content_lines[{li}]: #{line.id}#\t{line.text}")
    if debug > 0:
        print("long_line_splitter.make_page_merged_line_contexts:")
        print(f"\t{page.id}, number of content lines: {len(content_lines)}")
    line_groups = horizontal_group_lines(content_lines)
    line_infos = []
    for li, line_group in enumerate(line_groups):
        if not all([line.id is None or line.id.startswith('NL-HaNA') for line in line_group]):
            print(f"long_line_splitter.make_page_merged_line_contexts - some of line_group have no ID")
            for lgi, line in enumerate(line_group):
                print(f"    line_group[{lgi}]: #{line.id}#\t{line.text}")
        dist_to_prev = None if li == 0 else get_dist_to_other(line_group, line_groups[li-1])
        dist_to_next = None if li == len(line_groups) - 1 else get_dist_to_other(line_group, line_groups[li+1])
        line_info = LineInfo(line_group, line_splitter.column_sep_width,
                             line_splitter.default_line_num_chars,
                             dist_to_prev, dist_to_next)
        add_word_info(line_info)
        line_infos.append(line_info)
    assert len(line_infos) == len(line_groups)
    for li, line_info in enumerate(line_infos):
        context_infos = [line_info]
        if line_info.dist_to_prev is not None:
            max_dist_to_prev = 400
            sum_dist = line_info.dist_to_prev
            for pi in range(0, li):
                prev_info = line_infos[pi]
                if sum_dist > max_dist_to_prev:
                    break
                context_infos.append(prev_info)
                if prev_info.dist_to_prev is not None:
                    sum_dist = sum_dist + prev_info.dist_to_prev
        if line_info.dist_to_next is not None:
            max_dist_to_next = 400
            sum_dist = line_info.dist_to_next
            for ni in range(li+1, len(line_infos)):
                next_info = line_infos[ni]
                if sum_dist > max_dist_to_next:
                    break
                context_infos.append(next_info)
                if next_info.dist_to_next is not None:
                    sum_dist = sum_dist + next_info.dist_to_next
        full_width_context = [ci for ci in context_infos if ci.width > 1700]
        if len(full_width_context) == 0:
            full_width_context = context_infos
        context_lefts = np.array([ci.min_left for ci in full_width_context])
        context_rights = np.array([ci.max_right for ci in full_width_context])
        line_info.update_boundaries(int(context_lefts.mean()), int(context_rights.mean()))
        line_info.split_words = get_split_word_candidates(line_splitter, line_info)
    merged_context_windows = []
    for li, line_info in enumerate(line_infos):
        # print(f"long_line_splitter.make_page_line_context_windows - line_info")
        line_info = line_infos[li]
        # print(line_info)
        if len(line_infos) == 1:
            prev_group = None
            next_group = None
        else:
            prev_group = line_infos[-1] if li == 0 else line_infos[li-1]
            next_group = line_infos[0] if li == len(line_infos) - 1 else line_infos[li+1]
        mlc = MergedLineContext(line_info, prev_group, next_group,
                                column_sep_width=line_splitter.column_sep_width,
                                default_line_num_chars=line_splitter.default_line_num_chars)
        # mlc.prev_info.split_words = get_split_word_candidates(line_splitter, mlc.prev_info)
        # mlc.curr_info.split_words = get_split_word_candidates(line_splitter, mlc.curr_info)
        # mlc.next_info.split_words = get_split_word_candidates(line_splitter, mlc.next_info)
        merged_context_windows.append(mlc)
    return merged_context_windows


def replace_merged_line(merged_line: pdm.PageXMLTextLine, left_line: pdm.PageXMLTextLine,
                        right_line: pdm.PageXMLTextLine):
    """Replace the merged lines in its parent text region with the left and right lines."""
    merged_line_tr = merged_line.parent
    new_lines = []
    for tr_line in merged_line_tr.lines:
        if tr_line == merged_line:
            new_lines.extend([left_line, right_line])
        else:
            new_lines.append(tr_line)
    merged_line_tr.lines = new_lines


def update_merged_line_context(line_splitter: LineSplitter, mlc: MergedLineContext, merged_line: pdm.PageXMLTextLine,
                               left_line: pdm.PageXMLTextLine, right_line: pdm.PageXMLTextLine):
    """Replace the merged line with the left and right split lines in the merged line context
    and update the split words in the current line info."""
    new_line_group = []
    for line in mlc.curr_info.line_group:
        if line == merged_line:
            new_line_group.extend([left_line, right_line])
        else:
            new_line_group.append(line)
    # add the updates lines with split lines as the new line group
    mlc.curr_info.line_group = new_line_group
    # update the word info list
    add_word_info(mlc.curr_info)
    # update the split word candidates
    mlc.curr_info.split_words = get_split_word_candidates(line_splitter, mlc.curr_info)


def page_split_merged_hyphenated_lines(line_splitter: LineSplitter, page: pdm.PageXMLPage):
    new_page = copy_page(page)
    mlcs = make_page_merged_line_contexts(line_splitter, new_page)
    pdm.set_parentage(new_page)
    for mlc in mlcs:
        for line in mlc.curr_info.line_group:
            if line.text is not None and line_splitter.is_merged_hyphenated_line(line):
                left_line, right_line = line_splitter.split_merged_hyphenated_line(line, mlc.curr_info, debug=0)
                if left_line is None or right_line is None:
                    # if one of the split lines is None, it means the original line is not a merged line.
                    # This happens for example when there are two hyphens close to each other, as in
                    # the following line: "Ontfangen een Missive van den Vice- Admi-".
                    # The first hyphen triggers the merged hyphenation splitter, but splitting on the
                    # regular line width sets "Admi-" as the last word and finds nothing after it for
                    # the right line.
                    continue
                replace_merged_line(line, left_line, right_line)
    return new_page


def split_merged_non_hyphenated_lines(line_splitter: LineSplitter, mlc: MergedLineContext,
                                      ngram_scorer: BigramCollocationFinder, debug: int = 0):
    if debug > 0:
        print([line.id for line in mlc.curr_info.line_group])
        print([line.text for line in mlc.prev_info.line_group])
        print([line.text for line in mlc.curr_info.line_group])
        print([line.text for line in mlc.next_info.line_group])
    combinations = make_bigram_combinations(mlc, ngram_scorer, debug=0)
    if len(combinations) == 0:
        print("long_line_splitter.split_merged_non_hyphenated_lines:")
        line_ids = [line.id for line in mlc.curr_info.line_group]
        print(f"\tno combinations for lines {line_ids}!")
        print([line.text for line in mlc.curr_info.line_group])
        return None
    best_comb = select_best_combination(combinations)
    if debug > 0:
        print(f"\nbest_comb:")
        print_comb(best_comb)
        if 'curr_left_before_last' in best_comb:
            print([best_comb['curr_left_before_last'], best_comb['curr_left_last'],
                   best_comb['next_left_first']])
        else:
            print([best_comb['curr_left_last'], best_comb['next_left_first']])
        if 'prev_right_before_last' in best_comb:
            print([best_comb['prev_right_before_last'], best_comb['prev_right_last'],
                   best_comb['curr_right_first']])
        else:
            print([best_comb['prev_right_last'], best_comb['curr_right_first']])
    left_text, right_text = extract_left_right_split_from_combination(mlc.curr_info, best_comb)
    if left_text is None or right_text is None:
        # if one of the split line texts is None, it means there is no good place to split the original.
        return None
    left_last = best_comb['curr_left_last']
    merged_line = [line for line in mlc.curr_info.line_group if line.id == left_last.line.id][0]
    left_line, right_line = line_splitter.make_split_lines(merged_line, mlc.curr_info, left_text, right_text)
    if left_line is None or right_line is None:
        # if one of the split lines is None, it means the original line is not a merged line.
        return None
    replace_merged_line(merged_line, left_line, right_line)
    try:
        update_merged_line_context(line_splitter, mlc, merged_line, left_line, right_line)
    except IndexError:
        print("long_line_splitter.split_merged_non_hyphenated_lines - error updating merged line context:")
        print(f"  merged_line: {merged_line.text}")
        print(f"  left_line: {left_line.text}")
        print(f"  right_line: {right_line.text}")
        raise
    if debug > 0:
        print('\n------------------\n')


def get_page_content_lines(page: pdm.PageXMLPage) -> List[pdm.PageXMLTextLine]:
    return [line for col in page.columns for tr in col.text_regions for line in tr.lines]


def is_merged_line_distractor(mlc: MergedLineContext):
    if 'left_last' not in mlc.curr_info.split_words:
        return False
    if len(mlc.curr_info.split_words['left_last']) > 1:
        # There are multiple words
        return False
    # elif line_splitter.is_merged_line(line_info.line_group[0]):
    #     return False
    else:
        return True


def page_split_merged_non_hyphenated_lines(line_splitter: LineSplitter, page: pdm.PageXMLPage,
                                           ngram_scorer: BigramCollocationFinder,
                                           debug: int = 0):
    new_page = copy_page(page)

    if debug > 0:
        print(f"long_line_splitter.page_split_merged_non_hyphenated_lines - iterating over mlcs")
    mlcs = make_page_merged_line_contexts(line_splitter, new_page)
    for mi, mlc in enumerate(mlcs):
        if mlc == mlcs[0] and len(mlcs) > 1:
            # There is no line above, so prev is bottom of the column.
            # Use left_last as right_last
            prev_split_words = copy.deepcopy(mlc.prev_info.split_words)
            mlc.prev_info = LineInfo(mlc.prev_info.line_group, line_splitter.column_sep_width,
                                     line_splitter.default_line_num_chars, mlc.prev_info.dist_to_prev,
                                     mlc.prev_info.dist_to_next, line_splitter.default_line_width,
                                     mlc.prev_info.text_left_boundary, mlc.prev_info.text_right_boundary,
                                     mlc.prev_info.words, split_indexes=mlc.prev_info.split_indexes)
            mlc.prev_info.split_words = prev_split_words
            mlc.prev_info.split_words['right_last'] = mlc.prev_info.split_words['left_last']
            mlc.prev_info.split_words['left_last'] = []
        if mlc == mlcs[-1] and len(mlcs) > 1:
            # There is no line below, so next is top of the column.
            # Use right_first as left_first
            mlc.prev_info.split_words['left_first'] = mlc.prev_info.split_words['right_first']
            mlc.prev_info.split_words['right_first'] = []
        if line_splitter.has_merged_lines(mlc.curr_info.line_group):
            if is_merged_line_distractor(mlc) is False:
                if mlcs[mlcs.index(mlc)] == mlcs[-1]:
                    next_mlc = mlcs[0]
                else:
                    next_mlc = mlcs[mlcs.index(mlc) + 1]
                if debug > 0:
                    print(f"prev lines in next mlc before: {[line.text for line in next_mlc.prev_info.line_group]}")
                split_merged_non_hyphenated_lines(line_splitter, mlc, ngram_scorer, debug=debug)
                if debug > 0:
                    print(f"curr lines: {[line.text for line in mlc.curr_info.line_group]}")
                    print(f"prev lines in next mlc after: {[line.text for line in next_mlc.prev_info.line_group]}")
                if mlc == mlcs[-1]:
                    continue
                # if this merged line is split in this MergedLineContext, it
                # must be updated in the next MergedLineContext as well.
                # next_mlc = mlcs[mi+1]
                # next_mlc.prev_info
    return new_page


def evaluate_combination(combination):
    """Score a candidate line split position."""
    # 		curr_left_before_last	'de'
    # 		curr_left_last	'Provincie'
    # 		curr_right_first	'van'
    # 		curr_right_after_first	'den'
    # 		curr_left_last_curr_right_first	3.8382985408021213
    # 		prev_right_before_last	'geaddresseert'
    # 		prev_right_last	'aen'
    # 		prev_right_last_curr_right_first	-7.021463352203963
    # 		next_right_after_first	'op'
    # 		next_left_first	'Zeelandt.'
    # 		curr_left_last_next_left_first	-6.998636944631681
    scores = []
    for field in ['prev_right_last_curr_right_first', 'curr_left_last_next_left_first']:
        if field in combination:
            scores.append(combination[field])
    neg_scores = [score for score in scores if score < 0.0]
    pos_scores = [score for score in scores if score > 0.0]
    return {
        'scores': scores,
        'continue': combination['curr_left_last_curr_right_first'],
        'num_pos': len(pos_scores),
        'num_neg': len(neg_scores),
        'min_neg': min(neg_scores) if len(neg_scores) > 0 else 0.0,
        'sum_scores': sum(scores)
    }


def select_best_combination(combinations):
    """Select the best line split position."""
    best_comb = None
    best_scores = None
    for combination in combinations:
        scores = evaluate_combination(combination)
        if best_scores is None:
            best_scores = scores
            best_comb = combination
        elif scores['num_neg'] < best_scores['num_neg']:
            best_scores = scores
            best_comb = combination
        elif scores['continue'] < 0.0 and scores['continue'] < best_scores['continue']:
            best_scores = scores
            best_comb = combination
        elif scores['sum_scores'] > best_scores['sum_scores']:
            best_scores = scores
            best_comb = combination
    return best_comb


def print_comb(comb, prefix=None):
    if prefix is None:
        prefix = ''
    print()
    for field in comb:
        if isinstance(comb[field], SplitWord):
            print(f"\t{prefix}{field}\t{comb[field].word}")
        else:
            print(f"\t{prefix}{field}\t{comb[field]}")
    print()


def make_bigram_combinations(mlc, ngram_scorer, debug: int = 0):
    curr_sws = mlc.curr_info.split_words
    prev_sws = mlc.prev_info.split_words
    next_sws = mlc.next_info.split_words
    if debug > 0:
        print("prev_sws:", prev_sws)
        print("curr_sws:", curr_sws)
        print("next_sws:", next_sws)

    if len(curr_sws['left_last']) == 0:
        raise ValueError(f"curr left_last is empty, line is not merged?")
    if len(curr_sws['left_last']) == 1:
        print(f"long_line_splitter.make_bigram_combinations - curr_line group:")
        print([line.text for line in mlc.curr_info.line_group])
        print(f"curr_info.split_words: {curr_sws}")
        raise ValueError(f"curr left_last is single split word, line is not merged?")
    combs = []
    prev_combs = []
    next_combs = []

    for idx in range(len(curr_sws['left_last']) - 1):
        curr_words = mlc.curr_info.words
        # print(f"idx: {idx}\tcurr left_last: {curr_sws['left_last']}\t right_first{curr_sws['right_first']}")
        curr_left_last = curr_sws['left_last'][idx]
        curr_right_first = curr_sws['left_last'][idx + 1]
        if debug > 0:
            print("curr_left_last:", curr_left_last, curr_left_last.index, curr_left_last.lg_index, curr_left_last.word)
        lg_index = curr_left_last.lg_index
        comb = {
            'curr_left_before_last': curr_words[lg_index - 1],
            'curr_left_last': curr_left_last,
            'curr_right_first': curr_words[lg_index + 1],
            'curr_right_after_first': curr_words[lg_index + 2] if len(curr_words) > lg_index + 2 else None,
            'curr_left_last_curr_right_first': ngram_scorer(curr_left_last.word, curr_right_first.word),
        }

        if debug > 1:
            print_comb(comb)
        combs.append(comb)
    if debug > 0:
        print(f"CURR: number of combinations: {len(combs)}")
        print('prev words:', mlc.prev_info.words)

    for comb in combs:
        if len(prev_sws['right_last']) == 0:
            prev_combs = [comb for comb in combs]
        for prev_right_last in prev_sws['right_last']:
            prev_right_before_last = mlc.prev_info.words[prev_right_last.lg_index - 1]
            curr_right_first = comb['curr_right_first']
            if debug > 0:
                print(prev_right_before_last, prev_right_last.word, curr_right_first.word)
            # prev_comb = copy.deepcopy(comb)
            prev_comb = {field: comb[field] for field in comb}
            prev_comb['prev_right_before_last'] = prev_right_before_last
            prev_comb['prev_right_last'] = prev_right_last
            prev_comb['prev_right_last_curr_right_first'] = ngram_scorer(prev_right_last.word, curr_right_first.word)

            prev_combs.append(prev_comb)
            if debug > 1:
                print_comb(prev_comb, '\t')

    if debug > 0:
        print(f"PREV: number of combinations: {len(prev_combs)}")
        print('next words:', mlc.next_info.words)

    for prev_comb in prev_combs:
        if len(next_sws['left_first']) == 0:
            next_combs = [comb for comb in prev_combs]
        next_words = mlc.next_info.words
        for next_left_first in next_sws['left_first']:
            lg_index = next_left_first.lg_index
            next_right_after_first = next_words[lg_index + 1] if len(next_words) > lg_index + 1 else None
            curr_left_last = prev_comb['curr_left_last']
            if debug > 0:
                print(curr_left_last, next_left_first, next_right_after_first)
            next_comb = {field: prev_comb[field] for field in prev_comb}
            next_comb['next_right_after_first'] = next_right_after_first
            next_comb['next_left_first'] = next_left_first
            next_comb['curr_left_last_next_left_first'] = ngram_scorer(curr_left_last.word, next_left_first.word)

            next_combs.append(next_comb)
            if debug > 1:
                print_comb(next_comb, '\t')
    if debug > 0:
        print(f"NEXT: number of combinations: {len(next_combs)}")
    return next_combs


def make_column_text_region(col_lines, page, first_tr):
    coords = pdm.parse_derived_coords(col_lines)
    tr = pdm.PageXMLTextRegion(metadata=copy.deepcopy(first_tr.metadata), coords=coords,
                               lines=col_lines)
    tr.set_derived_id(page.metadata['scan_id'])
    tr.set_as_parent(tr.lines)
    return tr


def determine_line_column_side(line, left_col_right, right_col_left):
    if line.coords.right < right_col_left:
        return 'left'
    if line.coords.left > left_col_right:
        return 'right'
    left_side_width = left_col_right - line.coords.left
    right_side_width = line.coords.right - right_col_left
    if left_side_width > right_side_width:
        return 'left'
    elif right_side_width > left_side_width:
        return 'right'
    else:
        print(f"line.text: {line.text}")
        print(f"line.coords.box: {line.coords.box}")
        print(f"left_col_right: {left_col_right}\tright_col_left: {right_col_left}")
        return 'left'


def make_column(col_lines, page, first_col, first_tr):
    coords = pdm.parse_derived_coords(col_lines)
    tr = make_column_text_region(col_lines, page, first_tr)
    col = pdm.PageXMLColumn(metadata=copy.deepcopy(first_col.metadata), coords=coords,
                            text_regions=[tr])
    col.set_derived_id(page.metadata['scan_id'])
    col.set_as_parent(col.text_regions)
    tr.metadata['column_id'] = col.id
    for line in tr.lines:
        line.metadata['text_region_id'] = tr.id
        line.metadata['column_id'] = col.id
    return col


def page_split_columns(line_splitter: LineSplitter, page: pdm.PageXMLPage, debug: int = 0):
    """Split the lines of a page into two columns after the merged lines have been split."""
    page = copy_page(page)
    if page.stats['lines'] == 0:
        return page
    trs = [tr for tr in page.get_all_text_regions()]
    first_tr = trs[0]
    first_col = page.columns[0]
    if debug > 0:
        print("PRE:", page.id, page.stats)
    if page.coords.width > 1500:
        col_default_width = int((page.coords.width - line_splitter.column_sep_width) / 2)
    else:
        col_default_width = 900
    left_col_right = page.coords.left + col_default_width
    right_col_left = left_col_right + line_splitter.column_sep_width
    left_col_lines = []
    right_col_lines = []
    extra_lines = []
    mlcs = make_page_merged_line_contexts(line_splitter, page)
    for mlc in mlcs:
        ci = mlc.curr_info
        curr_line_width = ci.text_right_boundary - ci.text_left_boundary
        if curr_line_width > 1500:
            left_col_right, right_col_left = ci.left_col_right, ci.right_col_left
        for line in ci.line_group:
            col_side = determine_line_column_side(line, left_col_right, right_col_left)
            if col_side == 'left':
                left_col_lines.append(line)
            elif col_side == 'right':
                right_col_lines.append(line)
            else:
                extra_lines.append(line)

    columns = []
    if len(left_col_lines) > 0:
        left_col = make_column(left_col_lines, page, first_col, first_tr)
        columns.append(left_col)
    if len(right_col_lines) > 0:
        right_col = make_column(right_col_lines, page, first_col, first_tr)
        columns.append(right_col)
    if len(columns) > 0:
        page.columns = columns
    if len(extra_lines) > 0:
        extra_tr = make_column_text_region(extra_lines, page, first_tr)
        page.extra.append(extra_tr)
    if debug > 0:
        print("POST:", page.id, page.stats)

    return page
