import re
from typing import List

import pagexml.model.physical_document_model as pdm


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


def is_merged_line(line: pdm.PageXMLTextLine, min_width: int):
    """Check if a text line is a merge of lines from adjacent columns."""
    return width_in_range(line, min_width=min_width)


def is_merged_hyphenated_line(line: pdm.PageXMLTextLine, min_width: int):
    """Check if a text line is a merge of lines from adjacent columns, where
    the first line ends in a hyphenated word break."""
    return is_merged_line(line, min_width=min_width) and re.search(r"(\w+-) (\w+)", line.text)


def get_merged_hyphenated_lines(doc: pdm.PageXMLTextRegion, min_width: int):
    """Return all lines from a text region that are merged hyphenated lines"""
    return [line for line in doc.get_lines() if is_merged_hyphenated_line(line, min_width=min_width)]


def get_merged_lines(doc: pdm.PageXMLTextRegion, min_width: int):
    """Return all lines from a text region that are merged hyphenated lines"""
    return [line for line in doc.get_lines() if is_merged_line(line, min_width=min_width)]


def doc_has_merged_lines(doc: pdm.PageXMLTextRegion, min_width: int) -> bool:
    """Check if a PageXMLTextRegion document has any lines
    that are the merge of lines from two adjacent columns."""
    return any([is_merged_line(line, min_width=min_width) for line in doc.get_lines()])


def doc_has_regular_lines(doc: pdm.PageXMLTextRegion, max_width: int) -> bool:
    """Check if a PageXMLTextRegion document has any lines
    that are the merge of lines from two adjacent columns."""
    return any([width_in_range(line, max_width=max_width) for line in doc.get_lines()])


def get_regular_line_sequences(text_region: pdm.PageXMLTextRegion, max_width: int):
    """Return a list of lists of consecutive lines in a text region that have a
    width below a given max width"""
    sequences = []
    sequence = []
    if len(text_region.lines) < 2:
        return sequences
    for line in text_region.lines:
        if line.coords.w > max_width:
            if len(sequence) > 0:
                sequences.append(sequence)
                sequence = []
            continue
        sequence.append(line)
    return sequences

