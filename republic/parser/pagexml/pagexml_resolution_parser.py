from typing import List

from republic.fuzzy.fuzzy_keyword_searcher import FuzzyKeywordSearcher


def same_column(line1: dict, line2: dict) -> bool:
    return line1['page_num'] == line2['page_num'] and line1['column_index'] == line2['column_index']


def get_neighbour_lines(curr_line: dict, meeting_lines: List[dict], neighbour_size: int = 4) -> List[dict]:
    line_index = meeting_lines.index(curr_line)
    start_index = line_index - neighbour_size
    end_index = line_index + neighbour_size + 1
    neighbour_lines = []
    if start_index < 0:
        start_index = 0
    if end_index > len(meeting_lines):
        end_index = len(meeting_lines)
    for line in meeting_lines[start_index:end_index]:
        if line == curr_line:
            continue
        if line['coords']['left'] > curr_line['coords']['left'] + 100:
            continue
        if line['text'] and same_column(curr_line, line):
            neighbour_lines += [line]
    return neighbour_lines


def is_paragraph_start(line: dict, meeting_lines: List[dict], neighbour_size: int = 3) -> bool:
    line_index = meeting_lines.index(line)
    if not line['text'] or len(line['text']) == 0:
        # start of paragraph always has text
        return False
    if line_index > 0:
        prev_line = meeting_lines[line_index - 1]
        if line['coords']['bottom'] > prev_line['coords']['bottom'] + 60:
            # for print editions after 1705, new paragraphs
            # start with some vertical whitespace
            return True
    neighbour_lines = get_neighbour_lines(line, meeting_lines, neighbour_size=neighbour_size)
    lefts = [line['coords']['left'] for line in neighbour_lines]
    if len(lefts) == 0:
        # no surrounding text lines so this is no paragraph start
        return False
    else:
        min_left = min(lefts)
        max_left = max(lefts)
        avg_left = sum(lefts) / len(lefts)
    if line['coords']['left'] > avg_left + 100:
        # large indentation signals it's probably an incorrect line
        # from bleed through of opposite side of the page
        return False
    if max_left - min_left > 20:
        # if the surrounding lines include indentation, something else
        # is going on.
        is_start = False
    elif line['coords']['left'] > avg_left + 20:
        # this line is normally indented compared its surrounding lines
        # so probably the start of a new paragraph
        is_start = True
    else:
        # no indentation, so line is part of current paragraph
        is_start = False
    return is_start


def find_paragraph_starts(meeting: dict) -> iter:
    for line in meeting['meeting_lines']:
        if is_paragraph_start(line, meeting['meeting_lines'], neighbour_size=3):
            yield line


def find_resolution_starts(meeting: dict, resolution_searcher: FuzzyKeywordSearcher) -> iter:
    meeting_lines = meeting['meeting_lines']
    for li, line in enumerate(meeting['meeting_lines']):
        if is_paragraph_start(line, meeting_lines):
            opening_matches = resolution_searcher.find_candidates(line['text'])
            if len(opening_matches) > 0:
                yield line


def make_resolution_text(meeting: dict, resolution_searcher: FuzzyKeywordSearcher) -> iter:
    text = ''
    for line in meeting['meeting_lines']:
        if not line['text']:
            continue
        if is_paragraph_start(line, meeting['meeting_lines']):
            opening_matches = resolution_searcher.find_candidates(line['text'])
            if len(opening_matches) > 0:
                yield text
                text = ''
        if line['text'][-1] == '-':
            text += line['text'][:-1]
        else:
            text += line['text'] + ' '
    if len(text) > 0:
        yield text
