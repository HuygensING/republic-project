from typing import Dict, Generator, List, Tuple, Union
from collections import Counter
import string
import re

import numpy as np

import republic.model.physical_document_model as pdm


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


def get_baseline_y(line: pdm.PageXMLTextLine) -> List[int]:
    """Return the Y/vertical coordinates of a text line's baseline."""
    if line_starts_with_big_capital(line):
        return [point[1] for point in line.baseline.points if point[1] < line.baseline.bottom - 20]
    else:
        return [point[1] for point in line.baseline.points]


def line_starts_with_big_capital(line: pdm.PageXMLTextLine) -> bool:
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


def find_lowest_point(line: pdm.PageXMLTextLine) -> Tuple[int, int]:
    """Find the first baseline point that corresponds to the lowest vertical point.

    :param line: a pdm.PageXML TextLine object with baseline information
    :type line: pdm.PageXMLTextLine
    :return: the left most point that has the lowest vertical coordinate
    :rtype: Tuple[int, int]
    """
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
    if p2[0] == p1[0]:
        # points 1 and 2 have the same x coordinate
        # so there is nothing to interpolate
        return None
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
        if next_point[0] == curr_point[0]:
            # skip pair when they have the same x coordinate
            continue
        # interpolate points between the current and next points using step as size
        for int_x, int_y in interpolate_points(curr_point, next_point, step=step):
            interpolated_baseline_points[int_x] = int_y
    return interpolated_baseline_points


def compute_baseline_distances(baseline1: pdm.Baseline, baseline2: pdm.Baseline,
                               step: int = 50) -> np.ndarray:
    """Compute the vertical distance between two baselines, based on
    their horizontal overlap, using a fixed step size. Interpolated
    points will be generated at fixed increments of step size for
    both baselines, so they have points with corresponding x
    coordinates to calculate the distance.

    If two lines have no horizontal overlap, it returns a list with
    a single distance between the average heights of the two baselines

    :param baseline1: the first pdm.Baseline object to compare
    :type baseline1: pdm.Baseline
    :param baseline2: the second pdm.Baseline object to compare
    :type baseline2: pdm.Baseline
    :param step: the step size in pixels for interpolation
    :type step: int
    :return: a list of vertical distances based on horizontal overlap
    :rtype: List[int]
    """
    b1_points = interpolate_baseline_points(baseline1.points, step=step)
    b2_points = interpolate_baseline_points(baseline2.points, step=step)
    distances = np.array([abs(b2_points[curr_x] - b1_points[curr_x]) for curr_x in b1_points
                          if curr_x in b2_points])
    if len(distances) == 0:
        avg1 = average_baseline_height(baseline1)
        avg2 = average_baseline_height(baseline2)
        distances = np.array([abs(avg1 - avg2)])
    return distances


def average_baseline_height(baseline: pdm.Baseline) -> int:
    """Compute the average (mean) baseline height for comparing lines that
    are not horizontally aligned.

    :param baseline: the baseline of a TextLine
    :type baseline: pdm.Baseline
    :return: the average (mean) baseline height across all its baseline points
    :rtype: int
    """
    total_avg = 0
    # iterate over each subsequent pair of baseline points
    for ci, curr_point in enumerate(baseline.points[:-1]):
        next_point = baseline.points[ci + 1]
        segment_avg = (curr_point[1] + next_point[1]) / 2
        # segment contributes its average height times its width
        total_avg += segment_avg * (next_point[0] - curr_point[0])
    # average is total of average heights divided by total width
    return int(total_avg / (baseline.points[-1][0] - baseline.points[0][0]))


def get_textregion_line_distances(text_region: pdm.PageXMLTextRegion) -> List[np.ndarray]:
    """Returns a list of line distance numpy arrays. For each line, its distance
    to the next at 50 pixel intervals is computed and stored in an numpy ndarray.

    :param text_region: a TextRegion object that contains TextLines
    :type text_region: pdm.PageXMLTextRegion
    :return: a list of numpy ndarrays of line distances
    :rtype: List[np.ndarray]
    """
    all_distances: List[np.ndarray] = []
    text_regions = text_region.get_inner_text_regions()
    for ti, curr_tr in enumerate(text_regions):
        above_next_tr = False
        next_tr = None
        if ti + 1 < len(text_regions):
            # check if the next textregion is directly below the current one
            next_tr = text_regions[ti + 1]
            above_next_tr = pdm.same_column(curr_tr, next_tr)
        for li, curr_line in enumerate(curr_tr.lines):
            next_line = None
            if li + 1 < len(curr_tr.lines):
                next_line = curr_tr.lines[li + 1]
            elif above_next_tr and next_tr.lines:
                # if the next textregion is directly below this one, include the distance
                # of this textregion's last line and the next textregion's first line
                next_line = next_tr.lines[0]
            if next_line:
                distances = compute_baseline_distances(curr_line.baseline, next_line.baseline)
                all_distances.append(distances)
    return all_distances


def get_textregion_avg_line_distance(text_region: pdm.PageXMLTextRegion,
                                     avg_type: str = "macro") -> np.float:
    """Returns the median distance between subsequent lines in a
    textregion object. If the textregion contains smaller textregions, it only
    considers line distances between lines within the same column (i.e. only
    lines from textregions that are horizontally aligned.

    By default the macro-average is returned.

    :param text_region: a TextRegion object that contains TextLines
    :type text_region: pdm.PageXMLTextRegion
    :param avg_type: the type of averging to apply (macro or micro)
    :type avg_type: str
    :return: the median distance between horizontally aligned lines
    :rtype: np.float
    """
    if avg_type not in ["micro", "macro"]:
        raise ValueError(f'Invalid avg_type "{avg_type}", must be "macro" or "micro"')
    all_distances = get_textregion_line_distances(text_region)
    if len(all_distances) == 0:
        return 0
    if avg_type == "micro":
        return float(np.median(np.concatenate(all_distances)))
    else:
        return float(np.median(np.array([distances.mean() for distances in all_distances])))


def get_textregion_avg_char_width(text_region: pdm.PageXMLTextRegion) -> float:
    """Return the estimated average (mean) character width, determined as the sum
    of the width of text lines divided by the sum of the number of characters
    of all text lines.

    :param text_region: a TextRegion object that contains TextLines
    :type text_region: pdm.PageXMLTextRegion
    :return: the average (mean) character width
    :rtype: float
    """
    total_chars = 0
    total_text_width = 0
    for tr in text_region.get_inner_text_regions():
        for line in tr.lines:
            if line.text is None:
                continue
            total_chars += len(line.text)
            total_text_width += line.coords.width
    return total_text_width / total_chars if total_chars else 0.0


def get_textregion_avg_line_width(text_region: pdm.PageXMLTextRegion, unit: str = "char") -> float:
    """Return the estimated average (mean) character width, determined as the sum
    of the width of text lines divided by the sum of the number of characters
    of all text lines.

    :param text_region: a TextRegion object that contains TextLines
    :type text_region: pdm.PageXMLTextRegion
    :param unit: the unit to measure line width, either char or pixel
    :type unit: str
    :return: the average (mean) character width
    :rtype: float
    """
    if unit not in {'char', 'pixel'}:
        raise ValueError(f'Invalid unit "{unit}", must be "char" (default) or "pixel"')
    total_lines = 0
    total_line_width = 0
    for tr in text_region.get_inner_text_regions():
        for line in tr.lines:
            if line.text is None:
                # skip non-text lines
                continue
            total_lines += 1
            total_line_width += len(line.text) if unit == 'char' else line.coords.width
    return total_line_width / total_lines if total_lines > 0 else 0.0


def print_textregion_stats(text_region: pdm.PageXMLTextRegion) -> None:
    """Print statistics on the textual content of a text region.

    :param text_region: a TextRegion object that contains TextLines
    :type text_region: pdm.PageXMLTextRegion
    """
    avg_line_distance = get_textregion_avg_line_distance(text_region)
    avg_char_width = get_textregion_avg_char_width(text_region)
    avg_line_width_chars = get_textregion_avg_line_width(text_region, unit="char")
    avg_line_width_pixels = get_textregion_avg_line_width(text_region, unit="pixel")
    print("\n--------------------------------------")
    print("Document info")
    print(f"  {'id:': <30}{text_region.id}")
    print(f"  {'type:': <30}{text_region.type}")
    stats = text_region.stats
    for element_type in stats:
        element_string = f'number of {element_type}:'
        print(f'  {element_string: <30}{stats[element_type]:>6.0f}')
    print(f"  {'avg. distance between lines:': <30}{avg_line_distance: >6.0f}")
    print(f"  {'avg. char width:': <30}{avg_char_width: >6.0f}")
    print(f"  {'avg. chars per line:': <30}{avg_line_width_chars: >6.0f}")
    print(f"  {'avg. pixels per line:': <30}{avg_line_width_pixels: >6.0f}")
    print("--------------------------------------\n")


def pretty_print_textregion(text_region: pdm.PageXMLTextRegion, print_stats: bool = False) -> None:
    """Pretty print the text of a text region, using indentation and
    vertical space based on the average character width and average
    distance between lines. If no corresponding images of the pdm.PageXML
    are available, this can serve as a visual approximation to reveal
    the page layout.

    :param text_region: a TextRegion object that contains TextLines
    :type text_region: pdm.PageXMLTextRegion
    :param print_stats: flag to print text_region statistics if set to True
    :type print_stats: bool
    """
    if print_stats:
        print_textregion_stats(text_region)
    avg_line_distance = get_textregion_avg_line_distance(text_region)
    avg_char_width = get_textregion_avg_char_width(text_region)
    for ti, tr in enumerate(text_region.get_inner_text_regions()):
        if len(tr.lines) < 2:
            continue
        for li, curr_line in enumerate(tr.lines[:-1]):
            next_line = tr.lines[li + 1]
            left_indent = (curr_line.coords.left - tr.coords.left)
            if left_indent > 0 and avg_char_width > 0:
                preceding_whitespace = " " * int(float(left_indent) / avg_char_width)
            else:
                preceding_whitespace = ""
            distances = compute_baseline_distances(curr_line.baseline, next_line.baseline)
            if curr_line.text is None:
                print()
            else:
                print(preceding_whitespace, curr_line.text)
            if np.median(distances) > avg_line_distance * 1.2:
                print()
    print()


def sort_regions_in_reading_order(doc: pdm.PageXMLDoc) -> List[pdm.PageXMLTextRegion]:
    doc_text_regions: List[pdm.PageXMLTextRegion] = []
    if doc.reading_order and hasattr(doc, 'text_regions'):
        text_region_ids = [region for _index, region in sorted(doc.reading_order.items(), key=lambda x: x[0])]
        return [tr for tr in sorted(doc.text_regions, key=lambda x: text_region_ids.index(x))]
    if hasattr(doc, 'columns') and doc.columns:
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
    vertically_sorted = [line for line in sorted(lines, key=lambda line: line.coords.top) if line.text is not None]
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
        if text_region.main_type == 'column':
            text_region.metadata['column_id'] = text_region.id
        #if 'column_id' not in text_region.metadata:
        #    raise KeyError(f'missing column id: {text_region.metadata}')
        for line in text_region.lines:
            if line.metadata is None:
                line.metadata = {'id': line.id, 'type': ['pagexml', 'line'], 'parent_id': text_region.id}
            if 'column_id' in text_region.metadata and 'column_id' not in line.metadata:
                line.metadata['column_id'] = text_region.metadata['column_id']
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
    lines = [json_to_pagexml_line(line) for line in json_doc['lines']] if 'lines' in json_doc else []
    reading_order = json_doc['reading_order'] if 'reading_order' in json_doc else {}

    column = pdm.PageXMLColumn(doc_id=json_doc['id'], doc_type=json_doc['type'], metadata=json_doc['metadata'],
                               coords=pdm.Coords(json_doc['coords']), text_regions=text_regions, lines=lines,
                               reading_order=reading_order)
    pdm.set_parentage(column)
    return column


def json_to_pagexml_page(json_doc: dict) -> pdm.PageXMLPage:
    extra = [json_to_pagexml_text_region(text_region) for text_region in json_doc['extra']] \
        if 'extra' in json_doc else []
    columns = [json_to_pagexml_column(column) for column in json_doc['columns']] if 'columns' in json_doc else []
    text_regions = [json_to_pagexml_text_region(text_region) for text_region in json_doc['text_regions']] \
        if 'text_regions' in json_doc else []
    lines = [json_to_pagexml_line(line) for line in json_doc['lines']] if 'lines' in json_doc else []
    reading_order = json_doc['reading_order'] if 'reading_order' in json_doc else {}

    coords = pdm.Coords(json_doc['coords']) if 'coords' in json_doc else None
    page = pdm.PageXMLPage(doc_id=json_doc['id'], doc_type=json_doc['type'], metadata=json_doc['metadata'],
                           coords=coords, extra=extra, columns=columns,
                           text_regions=text_regions, lines=lines,
                           reading_order=reading_order)
    pdm.set_parentage(page)
    return page


def json_to_pagexml_scan(json_doc: dict) -> pdm.PageXMLScan:
    pages = [json_to_pagexml_page(page) for page in json_doc['pages']] if 'pages' in json_doc else []
    columns = [json_to_pagexml_column(column) for column in json_doc['columns']] if 'columns' in json_doc else []
    text_regions = [json_to_pagexml_text_region(text_region) for text_region in json_doc['text_regions']] \
        if 'text_regions' in json_doc else []
    lines = [json_to_pagexml_line(line) for line in json_doc['lines']] if 'lines' in json_doc else []
    reading_order = json_doc['reading_order'] if 'reading_order' in json_doc else {}

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
