import copy
import re
from typing import List, Tuple, Union

import pagexml.model.physical_document_model as pdm
from pagexml.analysis.layout_stats import sort_coords_above_below_baseline


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


def get_words(line: pdm.PageXMLTextLine):
    """Return the word tokens of a line."""
    if len(line.words) > 0:
        return [word.text for word in line.words]
    elif line.text is not None:
        return line.text.split(' ')
    else:
        return None


def get_split_indexes(words: List[str], min_offset: int, max_offset: int):
    offset = 0
    split_indexes = []
    for wi, word in enumerate(words):
        word_start, word_end = offset, offset + len(word)
        if min_offset <= word_start <= max_offset:
            split_indexes.append(wi)
        offset = word_end + 1
    return split_indexes


class SplitWord:

    def __init__(self, word: str, index: int, line_id: str, line_pos: str, word_pos: str):
        self.word = word
        self.index = index
        self.line_id = line_id
        self.line_pos = line_pos
        self.word_pos = word_pos

    def __repr__(self):
        attr_string = (f"word='{self.word}', index={self.index}, line_id='{self.line_id}', \n"
                       f"\tline_pos='{self.line_pos}', word_pos='{self.word_pos}'")
        return f"{self.__class__.__name__}({attr_string})"


class ColumnLines:

    def __init__(self, lines: pdm.PageXMLTextLine, line_pos: str,
                 left_first: SplitWord = None, left_last: Union[SplitWord, List[SplitWord]] = None,
                 right_first: Union[SplitWord, List[SplitWord]] = None, right_last: SplitWord = None
                 ):
        self.lines = lines
        self.line_pos = line_pos
        self.num_columns = 2
        self.left_first = left_first
        self.left_last = [left_last] if isinstance(left_last, SplitWord) else left_last
        self.right_first = right_first
        self.right_last = right_last


class MergedLineContext:

    def __init__(self,
                 curr_line: pdm.PageXMLTextLine,
                 prev_left_line: pdm.PageXMLTextLine,
                 prev_right_line: pdm.PageXMLTextLine,
                 next_left_line: pdm.PageXMLTextLine,
                 next_right_line: pdm.PageXMLTextLine,
                 text_left_boundary: int, text_right_boundary: int,
                 column_sep_width: int,
                 default_line_num_chars: int,
                 default_line_width: int = None,
                 ):
        """A merged line with its surrounding lines (assuming a 2-column layout)
        and the left and right boundaries of the main text on the page. The left
        boundary is the left side of the left-most column, the right boundary is
        the right side of the right-most column.

        :param curr_line: the current merged line that is the focus for splitting
        :type: PageXMLTextLine
        :param prev_left_line: the previous line in the left-side column
        :type: PageXMLTextLine
        :param prev_right_line: the previous line in the right-side column
        :type: PageXMLTextLine
        :param next_left_line: the next line in the left-side column
        :type: PageXMLTextLine
        :param next_right_line: the next line in the right-side column
        :type: PageXMLTextLine
        :param text_left_boundary: the x-coordinate of the left-most side of the
        two text columns
        :type text_left_boundary: int
        :param text_right_boundary: the x-coordinate of the right-most side of the
        two text columns
        :type text_right_boundary: int
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
        self.curr = {'line': curr_line}
        self.prev_left = {'line': prev_left_line}
        self.prev_right = {'line': prev_right_line}
        self.next_left = {'line': next_left_line}
        self.next_right = {'line': next_right_line}
        self.text_left_boundary = text_left_boundary
        self.text_right_boundary = text_right_boundary
        self.column_sep_width = column_sep_width
        self.default_line_num_chars = default_line_num_chars
        self.min_offset = default_line_num_chars - 15
        self.max_offset = default_line_num_chars + 15
        if default_line_width is None:
            self.default_line_width = (text_right_boundary - text_left_boundary - column_sep_width) / 2
        else:
            self.default_line_width = default_line_width
        self.curr['words'] = get_words(self.curr['line'])
        self.curr['split_indexes'] = get_split_indexes(self.curr['words'], self.min_offset, self.max_offset)
        if prev_left_line is None:
            self.prev_left['split_indexes'] = []
        else:
            self.prev_left['split_indexes'] = [self.prev_left['words'][-1]]


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
            self.default_line_width = (text_right_boundary - text_left_boundary - column_sep_width) / 2
        self.left_col_left = text_left_boundary
        self.left_col_right = text_left_boundary + self.default_line_width
        self.right_col_left = self.left_col_right + column_sep_width
        self.right_col_right = text_right_boundary

    def is_merged_line(self, line: pdm.PageXMLTextLine, min_merged_width: int = None):
        """Check if a text line is a merge of lines from adjacent columns."""
        if min_merged_width is None:
            min_merged_width = self.min_merged_width
        return width_in_range(line, min_width=min_merged_width)

    def is_merged_hyphenated_line(self, line: pdm.PageXMLTextLine, min_merged_width: int = None,
                                  debug: int = 0):
        """Check if a text line is a merge of lines from adjacent columns, where
        the first line ends in a hyphenated word break."""
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

    def _extract_left_right_splits(self, line: pdm.PageXMLTextLine, match: re.Match):
        """Determine the x coordinate at which to split a line given a hyphen/word-break
        match. """
        start, end = match.span()
        hyphen_offset = self.min_offset - 1 + start + len(match.group(1))
        left_text = line.text[:hyphen_offset + 1]
        right_text = line.text[hyphen_offset + 2:]
        if left_text + " " + right_text != line.text:
            print(f"long_line_splitter.split_merged_hyphenated_line - splitting error:")
            print(f"line.text: {line.text}")
            print(f"\tleft_text: #{left_text}#")
            print(f"\tright_text: #{right_text}#")
            print(f"\tcombined_text: #{left_text + ' ' + right_text}#")
            raise ValueError(f"splits of merged_hyphenated_line do not combine to the original line")
        return left_text, right_text

    def get_left_right_ends(self, line: pdm.PageXMLTextLine, column_sep_width: int = None):
        """Determine the left and right side coordinates of the left and right parts of the
        merged line."""
        if column_sep_width is None:
            column_sep_width = self.column_sep_width
        left_line_left = line.coords.left
        left_line_right = line.coords.left + self.default_line_width
        # add average column separation space
        right_line_left = line.coords.left + column_sep_width + self.default_line_width
        right_line_right = line.coords.right
        return left_line_left, left_line_right, right_line_left, right_line_right

    @staticmethod
    def make_split_baseline(line: pdm.PageXMLTextLine, left_line_right: int = None,
                            right_line_left: int = None) -> pdm.Baseline:
        """Make baselines for the left and right parts of the merged line."""
        if right_line_left is not None:
            points = [point for point in line.baseline.points if point[0] >= right_line_left]
            if min([point[0] for point in points]) > right_line_left:
                # add a left_most point with the same height as the first selected point in the baseline
                right_line_left_point = (right_line_left, points[0][1])
                return pdm.Baseline([right_line_left_point] + points)
        elif left_line_right is not None:
            points = [point for point in line.baseline.points if point[0] <= left_line_right]
            if max([point[0] for point in points]) < left_line_right:
                # add a right_most point with the same height as the last selected point in the baseline
                left_line_right_point = (left_line_right, points[0][1])
                return pdm.Baseline(points + [left_line_right_point])
        else:
            raise ValueError("one of 'left' and 'right' must be an integer")

    @staticmethod
    def make_split_coords(line: pdm.PageXMLTextLine, left_line_right: int = None,
                          right_line_left: int = None) -> pdm.Coords:
        """Make bounding box coordinates for the left and right parts of the merged line."""
        sort_coords_above_below_baseline(line)
        above_points, below_points = sort_coords_above_below_baseline(line)
        if right_line_left is not None:
            above_right_line_points = [point for point in above_points if point[0] >= right_line_left]
            below_right_line_points = [point for point in below_points if point[0] >= right_line_left]
            if min([point[0] for point in above_right_line_points]) > right_line_left:
                # add a left_most point with the same height as the first selected point in the coords
                above_right_line_points = [(right_line_left, above_points[0][1])] + above_right_line_points
            if min([point[0] for point in below_right_line_points]) > right_line_left:
                # add a left_most point with the same height as the first selected point in the coords
                below_right_line_points = below_right_line_points + [(right_line_left, below_points[0][1])]
            return pdm.Coords(above_right_line_points + below_right_line_points)
        elif left_line_right is not None:
            above_left_line_points = [point for point in above_points if point[0] <= left_line_right]
            below_left_line_points = [point for point in below_points if point[0] <= left_line_right]
            if max([point[0] for point in above_left_line_points]) < left_line_right:
                # add a left_most point with the same height as the first selected point in the coords
                above_left_line_points = above_left_line_points + [(left_line_right, above_points[0][1])]
            if max([point[0] for point in below_left_line_points]) < left_line_right:
                # add a left_most point with the same height as the first selected point in the coords
                below_left_line_points = [(left_line_right, below_points[0][1])] + below_left_line_points
            return pdm.Coords(above_left_line_points + below_left_line_points)
        else:
            raise ValueError("one of 'left' and 'right' must be an integer")

    def split_merged_hyphenated_line(self, line: pdm.PageXMLTextLine,
                                     debug: int = 0) -> Tuple[pdm.PageXMLTextLine, Union[pdm.PageXMLTextLine, None]]:
        """Split a merged line where the left part ends in a word-break with a hyphen."""
        match = re.search(r"(\w+)- (\w+)", line.text[self.min_offset-1:self.max_offset+3])
        if match is None:
            return line, None
        left_line_left, left_line_right, right_line_left, right_line_right = self.get_left_right_ends(line)
        left_line_text, right_line_text = self._extract_left_right_splits(line, match)
        left_baseline = self.make_split_baseline(line, left_line_right=left_line_right)
        right_baseline = self.make_split_baseline(line, right_line_left=right_line_left)
        left_coords = self.make_split_coords(line, left_line_right=left_line_right)
        right_coords = self.make_split_coords(line, right_line_left=right_line_left)
        if debug > 0:
            print("long_line_splitter.split_merged_hyphenated_line - ")
            print(f"    line.left: {line.coords.left}\tline.right: {line.coords.right}")
            print(f"    line.baseline: {line.baseline.points}")
            print(f"    line.coords: {line.coords.points}")
            print(f"    left_line_left: {left_line_left}\tleft_line_right: {left_line_right}")
            print(f"    right_line_left: {right_line_left}\tright_line_right: {right_line_right}")
            print(f"    left_baseline: {left_baseline.points}")
            print(f"    right_baseline: {right_baseline.points}")
            print(f"    left_coords: {left_coords.points}")
            print(f"    right_coords: {right_coords.points}")
        left_line = pdm.PageXMLTextLine(metadata=copy.deepcopy(line.metadata), coords=left_coords,
                                        baseline=left_baseline, text=left_line_text)
        right_line = pdm.PageXMLTextLine(metadata=copy.deepcopy(line.metadata), coords=right_coords,
                                         baseline=right_baseline, text=right_line_text)
        return left_line, right_line

    def get_merged_hyphenated_lines(self, doc: Union[pdm.PageXMLTextRegion, List[pdm.PageXMLTextLine]],
                                    min_merged_width: int = None):
        """Return all lines from a text region that are merged hyphenated lines"""
        lines = doc if isinstance(doc, list) else doc.get_lines()
        return [line for line in lines if self.is_merged_hyphenated_line(line, min_merged_width=min_merged_width)]

    def get_merged_lines(self, doc: Union[pdm.PageXMLTextRegion, List[pdm.PageXMLTextLine]], min_merged_width: int = None):
        """Return all lines from a text region that are merged hyphenated lines"""
        lines = doc if isinstance(doc, list) else doc.get_lines()
        return [line for line in lines if self.is_merged_line(line, min_merged_width=min_merged_width)]

    def doc_has_merged_lines(self, doc: Union[pdm.PageXMLTextRegion, List[pdm.PageXMLTextLine]],
                             min_merged_width: int) -> bool:
        """Check if a PageXMLTextRegion document has any lines
        that are the merge of lines from two adjacent columns."""
        lines = doc if isinstance(doc, list) else doc.get_lines()
        return any([self.is_merged_line(line, min_merged_width=min_merged_width) for line in lines])

    @staticmethod
    def doc_has_regular_lines(doc: Union[pdm.PageXMLTextRegion, List[pdm.PageXMLTextLine]], max_width: int) -> bool:
        """Check if a PageXMLTextRegion document has any lines
        that are the merge of lines from two adjacent columns."""
        lines = doc if isinstance(doc, list) else doc.get_lines()
        return any([width_in_range(line, max_width=max_width) for line in lines])

    def get_split_word_candidates(self, lines: List[pdm.PageXMLTextLine], line_pos: str):
        left_first, left_last, right_first, right_last = None, None, None, None
        split_words = {
            'left_first': None,
            'left_last': None,
            'right_first': None,
            'right_last': None,
        }
        text_lines = [line for line in lines if line.text is not None]
        if len(text_lines) == 0:
            return split_words
        first_line, last_line = text_lines[0], text_lines[-1]
        left_indent = True if first_line.coords.left > self.left_col_left + 100 else False
        right_indent = True if last_line.coords.right + 100 < self.right_col_right else False

        # if the first line is not left indented, it starts on the left side of the column and
        # its first word probably is the continuation of the sentence of the previous left-column
        # line
        if left_indent is False:
            first_words = get_words(first_line)
            first_word, first_idx = first_words[0], 0
            split_words['left_first'] = SplitWord(first_word, first_idx, first_line.id, line_pos, 'left_first')

        # if the last line is not right indented, it ends on the right side of the column and
        # its last word probably is the location of the line break, and the sentence is continued
        # on the next line
        if right_indent is False:
            last_line_words = get_words(last_line)
            last_word, last_idx = last_line_words[0], len(last_line_words) - 1
            split_words['right_last'] = SplitWord(last_word, last_idx, last_line.id, line_pos, 'right_last')

        for line in lines:
            line_words = get_words(line)
            if abs(line.coords.right - self.left_col_right) < 100:
                # Line ends close to right side of left column.
                # Its last word is probably at the line break
                last_word, last_idx = line_words[-1], len(line_words) - 1
                split_words['left_last'] = [SplitWord(last_word, last_idx, line.id, line_pos, 'left_last')]
            elif abs(line.coords.left - self.right_col_left) < 100:
                # Line starts close to the left side of right column.
                # Its first word is probably the continuation after the previous line break
                first_word = line.text.split(' ')[0]
                split_words['right_first'] = [SplitWord(first_word, 0, line.id, line_pos, 'right_first')]
            if self.is_merged_line(line):
                words = get_words(line)
                print(f"merged_line - words: {words}")
                split_indexes = get_split_indexes(words, min_offset=self.min_offset, max_offset=self.max_offset)
                print(f"merged_line - split_indexes: {split_indexes}")
                sws = [SplitWord(words[si], si, line.id, line_pos, 'merge') for si in split_indexes]
                print(f"merged_line - sws: {sws}")
                split_words['left_last'] = sws
                split_words['right_first'] = sws
        return split_words
