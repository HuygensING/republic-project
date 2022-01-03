import string
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple, Union, Generator
import re

import numpy as np

import republic.model.physical_document_model as pdm
import republic.parser.pagexml.republic_pagexml_parser as page_parser
import republic.helper.pagexml_helper as page_helper
from republic.helper.annotation_helper import make_hash_id
from republic.helper.metadata_helper import coords_to_iiif_url


def categorise_line_dist(lines: List[dict]):
    dist_freq = Counter()
    for curr_index in range(len(lines)):
        start = curr_index - 5 if curr_index >= 5 else 0
        curr_line = lines[curr_index]
        for prev_index in range(start, curr_index):
            prev_line = lines[prev_index]
            line_dist = abs(curr_line["line"].baseline.x - prev_line["line"].baseline.x)
            norm_dist = int(line_dist / 5) * 5
            dist_freq.update([norm_dist])
            # print(line_dist, norm_dist)
    print('num dists:', sum(dist_freq.values()))
    for dist, freq in sorted(dist_freq.items()):
        print(dist, freq)


def is_page_ref_line(line: dict) -> False:
    if line[0].isdigit():
        return True
    if len(line) >= 3 and line[0].isalpha() and line[1].isalpha() and line[2].isalpha():
        return False
    letters = sum(c.isalpha() for c in line)
    if letters > 5:
        return False
    numbers = sum(c.isdigit() for c in line)
    if numbers == 0:
        return False
    if numbers / len(line) > 0.75:
        return True
    elif letters / numbers > 0.5:
        return False
    elif numbers > 5:
        return True
    else:
        return True
        # print('not sure if line is page_ref:', line)


def categorise_line_type(curr_line: dict,
                         next_line: dict) -> Tuple[Union[str, None], Union[str, None]]:
    """Identify index line types (lemma, repeat_lemma, continuation, anomaly)
    for the current and next line.

    :param curr_line: the current line for which to identify type
    :type curr_line: dict
    :param next_line: the next line for the which to identify type
    :type next_line: dict
    :return: estimated types of current and next line
    :rtype: Tuple[Union[str, None], Union[str, None]]
    """
    if curr_line["type"] and next_line["type"]:
        return curr_line["type"], next_line["type"]
    next_line["x_dist"] = next_line["line"].baseline.x - curr_line["line"].baseline.x
    next_line["y_dist"] = next_line["line"].baseline.y - curr_line["line"].baseline.y
    # print("next line dist:", next_line["x_dist"])
    if curr_line["type"] is None and is_page_ref_line(curr_line["line"].text):
        curr_line["type"] = 'continuation'
    if next_line["type"] is None and is_page_ref_line(next_line["line"].text):
        next_line["type"] = 'continuation'
    if next_line["x_dist"] < -200:
        if curr_line["type"] and curr_line["type"] != "anomaly":
            # the current line is a normal line, so next must be anomaly
            return curr_line["type"], "anomaly"
        elif next_line["type"] != "anomaly":
            # the next line is a normal line, so current must be anomaly
            return "anomaly", next_line["type"]
        else:
            # one of the lines is an anomaly but we don't know which one
            return None, None
    elif -200 <= next_line["x_dist"] < -140:
        return "repeat_lemma", "lemma"
    elif -140 <= next_line["x_dist"] < -110:
        if curr_line["type"] == "continuation":
            return "continuation", "repeat_lemma"
        elif next_line["type"] == "continuation":
            return "repeat_lemma", "continuation"
        else:
            return curr_line["type"], next_line["type"]
            # return "continuation", "lemma"
    elif -110 <= next_line["x_dist"] < -70:
        if curr_line["anomaly_left_side"]:
            return "repeat_lemma", "lemma"
        elif curr_line["type"] == "repeat_lemma":
            return "repeat_lemma", "continuation"
        elif curr_line["type"] == "continuation":
            return "continuation", "lemma"
        elif next_line["type"] == "lemma":
            return "continuation", "lemma"
        elif next_line["type"] == "continuation":
            return "repeat_lemma", "continuation"
        else:
            return curr_line["type"], next_line["type"]
    elif -70 <= next_line["x_dist"] < -25:
        if curr_line["type"] == "repeat_lemma":
            return "repeat_lemma", "continuation"
        elif curr_line["type"] == "continuation":
            return "continuation", "lemma"
        else:
            return curr_line['type'], next_line['type']
    elif -25 <= next_line["x_dist"] < 25:
        if abs(next_line['x_dist']) < 20:
            if curr_line['line'].coords.w > 800 and next_line['line'].coords.w < 700:
                if curr_line['type'] is None:
                    return "continuation", "continuation"
                else:
                    return curr_line['type'], "continuation"
        same_type = curr_line["type"] if curr_line["type"] else next_line["type"]
        return same_type, same_type
    elif 25 <= next_line["x_dist"] < 70:
        if curr_line["type"] == "continuation":
            next_line["anomaly_left_side"] = True
            return "continuation", "repeat_lemma"
        else:
            return "lemma", "continuation"
    elif 70 <= next_line["x_dist"] < 110:
        if curr_line["type"] == "continuation":
            return "continuation", "repeat_lemma"
        elif curr_line["type"] == "lemma":
            return "lemma", "continuation"
        elif next_line["type"] == "continuation":
            return "lemma", "continuation"
        elif next_line["type"] == "repeat_lemma":
            return "continuation", "repeat_lemma"
        else:
            return curr_line['type'], next_line['type']
            # return "continuation", "repeat_lemma"
    elif 110 <= next_line["x_dist"] < 140:
        if curr_line["type"] == "continuation":
            return "continuation", "repeat_lemma"
        elif curr_line["type"] == "repeat_lemma":
            return "repeat_lemma", "non_index_line"
        elif next_line["type"] == "continuation":
            return "lemma", "continuation"
        elif next_line["type"] == "lemma":
            return "non_index_line", "lemma"
        else:
            return curr_line['type'], next_line['type']
            # return "continuation", "repeat_lemma"
    elif 140 <= next_line["x_dist"] <= 200:
        if curr_line["type"] == "continuation":
            return "continuation", "repeat_lemma"
        elif curr_line["type"] == "repeat_lemma":
            return "repeat_lemma", "non_index_line"
        elif next_line["type"] == "continuation":
            return "lemma", "continuation"
        elif next_line["type"] == "lemma":
            return "non_index_line", "lemma"
        return "lemma", "repeat_lemma"
    elif next_line["x_dist"] > 200:
        if curr_line["type"] and curr_line["type"] != "anomaly":
            # the current line is a normal line, so next must be anomaly
            return curr_line["type"], "anomaly"
        elif next_line["type"] != "anomaly":
            # the next line is a normal line, so current must be anomaly
            return "anomaly", next_line["type"]
        else:
            # one of the lines is an anomaly but we don't know which one
            return None, None
    else:
        raise ValueError('Unexpected distance value:', next_line["x_dist"])


def get_indent(line_type: str) -> str:
    """Determine amount of whitespace indentation for a line given its type."""
    if line_type == "lemma":
        return ""
    elif line_type == "continuation":
        return "    "
    else:
        return "        "


def get_neighbour_votes(curr_index: int, lines: List[dict]) -> Counter:
    start = curr_index - 5 if curr_index >= 5 else 0
    end = curr_index + 5 if curr_index + 5 < len(lines) else len(lines)
    curr_line = lines[curr_index]
    type_votes = Counter()
    for prev_index in range(start, curr_index):
        prev_line = lines[prev_index]
        prev_type, curr_type = categorise_line_type(prev_line, curr_line)
        type_votes.update([curr_type])
    for next_index in range(curr_index, end):
        next_line = lines[next_index]
        curr_type, next_type = categorise_line_type(curr_line, next_line)
        type_votes.update([curr_type])
    return type_votes


def categorise_index_lines(lines: List[pdm.PageXMLTextLine]) -> List[dict]:
    """Determine the line types of a list of PageXMLTextLines."""
    lines = [{"line": line, "type": None, "x_dist": None,
              "y_dist": None, "anomaly_left_side": False} for line in lines]
    type_votes = defaultdict(Counter)
    for curr_index in range(len(lines)):
        start = curr_index - 5 if curr_index >= 5 else 0
        curr_line = lines[curr_index]
        for prev_index in range(start, curr_index):
            prev_line = lines[prev_index]
            prev_type, curr_type = categorise_line_type(prev_line, curr_line)
            # print('\t', prev_type, prev_line["line"].baseline.x, prev_line["line"].text)
            # print('\t', curr_type, curr_line["line"].baseline.x, curr_line["line"].text)
            # print()
            type_votes[prev_index].update([prev_type])
            type_votes[curr_index].update([curr_type])
    for li, line in enumerate(lines):
        # print(li, line["line"].baseline.x, line["line"].baseline.y, line["line"].text)
        for line_type, votes in type_votes[li].most_common():
            if line_type is None:
                break
            line["type"] = line_type
            # print(f"\t{line_type: <15}\tvotes:{votes: >4}")
            break
    updated = True
    while updated:
        updated = False
        for curr_index in range(len(lines)):
            curr_line = lines[curr_index]
            if curr_line["type"] is not None:
                continue
            type_votes = get_neighbour_votes(curr_index, lines)
            for line_type, votes in type_votes.most_common():
                if line_type is None:
                    continue
                if line_type != curr_line["type"]:
                    updated = True
                curr_line["type"] = line_type
                break
    return lines


def filter_index_line_type(line_types: Set[str]) -> str:
    """Get the index line type for a given line, or unknown_line_type if
    the line has no index line type."""
    index_line_types = {
        'lemma', 'continuation', 'repeat_lemma', 'anomaly',
        'non_index_line', 'empty_line', 'letter_heading'
    }
    for line_type in line_types:
        if line_type in index_line_types:
            return line_type
    return 'unknown_line_type'


def get_index_lines(column: pdm.PageXMLColumn) -> List[pdm.PageXMLTextLine]:
    """Return the lines that are part of the index content for a given column.
    That is, filter out lines that are outliers."""
    index_lines = []
    # very small columns are not proper index columns
    if column.coords.w < 700:
        return index_lines
    # columns with very few lines don't have enough information
    # for proper classification
    if len(column.lines) < 5:
        return index_lines
    column_left = column.coords.x
    median_line_left = np.median([line.coords.x for line in column.lines])
    if column.coords.w > 1000 and median_line_left > column_left + 200:
        column_left = median_line_left
    # print('get_lines:', len(column.get_lines()))
    # for line in sorted(column.get_lines(), key=lambda x: x.baseline.y):
    for line in page_helper.horizontally_merge_lines(column.get_lines()):
        dist = line.baseline.x - column_left
        if line.baseline.bottom < 450 and len(line.text) < 5:
            # This is likely part of the I N D E X header
            continue
        if line.text is None:
            # Skip empty lines
            line.add_type('empty_line')
            continue
        if 300 < dist < 500:
            if re.match(r'[A-Z]\.?$', line.text):
                line.add_type('letter_heading')
        elif dist > 300 or dist < -250:
            line.add_type('non_index_line')
            # print(dist, 'non_index_line:', line.text)
            continue
        index_lines.append(line)
    # print('append:', len(index_lines))
    return index_lines


def parse_inventory_index_page(page: pdm.PageXMLPage) -> Generator[pdm.PageXMLTextLine, None, None]:
    """Return a list of lines with index line types for a given index page."""
    # process the columns from left to right
    full_text_columns = page_parser.get_page_full_text_columns(page)
    for column in sorted(full_text_columns, key=lambda x: x.coords.x):
        index_lines = get_index_lines(column)
        if len(column.get_lines()) - len(index_lines) > 10:
            print('LARGE NUMBER OF NON-INDEX LINES:', column.id)
            print('column bounding box:', column.coords.box)
            print()
        categorised_lines = categorise_index_lines(index_lines)
        for line_info in categorised_lines:
            line = line_info["line"]
            if line_info["type"]:
                line.add_type(line_info["type"])
            else:
                line.add_type("unknown_line_type")
            # print(f'{line_type: <15}', line.coords.x, line.coords.y, indent, line.text)
            yield line


def initialise_index_entry(lemma: str = None,
                           lines: List[pdm.PageXMLTextLine] = None,
                           main_term: str = None,
                           inventory_num: int = None,
                           year: int = None,
                           scan_id: str = None) -> Dict[str, any]:
    return {
        'lemma': lemma,
        'lines': lines if lines else [],
        'main_term': main_term,
        "inventory_num": inventory_num,
        "year": year,
        "scan_id": scan_id
    }


def parse_inventory_index_pages(pages: List[pdm.PageXMLPage]) -> List[dict]:
    """Parse the index entries from a list of index pages."""
    entries = []
    entry = initialise_index_entry(inventory_num=pages[0].metadata["inventory_num"],
                                   year=pages[0].metadata["inventory_year"],
                                   scan_id=pages[0].metadata["scan_id"])
    for page in pages:
        if page_parser.is_title_page(page):
            print('TITLE PAGE:', page.id)
            page = page_parser.parse_title_page_columns(page)
        for line in parse_inventory_index_page(page):
            if line.has_type('repeat_lemma'):
                if entry['lemma'] is not None:
                    entries.append(entry)
                    # reuse the lemma from the previous entry
                entry = initialise_index_entry(lemma=entry['lemma'],
                                               main_term=entry['main_term'],
                                               inventory_num=page.metadata["inventory_num"],
                                               year=page.metadata["inventory_year"],
                                               scan_id=page.metadata["scan_id"])
            if line.has_type('lemma'):
                if entry['lemma'] is not None:
                    entries.append(entry)
                lemma_info = parse_lemma_line(line)
                if lemma_info['main_term'] in {'.', ':', '-'}:
                    # print([lemma_info['main_term'], lemma_info['full_term'], entry['lemma']])
                    lemma_info['full_term'] = entry['lemma']
                    if "main_term" not in entry:
                        print("entry without main_term on page:", page.id)
                        print(entry)
                    lemma_info['main_term'] = entry['main_term']
                entry = initialise_index_entry(lemma=lemma_info['full_term'],
                                               main_term=lemma_info['main_term'],
                                               inventory_num=page.metadata["inventory_num"],
                                               year=page.metadata["inventory_year"],
                                               scan_id=page.metadata["scan_id"])
            entry['lines'].append(line)
    return entries


def accepted_initial(initial: str, expected_initial) -> bool:
    initial = initial.upper()
    if initial == expected_initial:
        return True
    elif chr(ord(initial) + 1) == expected_initial:
        # previous letter, perhaps page swap?
        return True
    elif chr(ord(initial) - 1) == expected_initial:
        # index has reached next letter in the alphabet
        return True
    else:
        return False


def confused_initial(initial: str, expected_initial: str) -> bool:
    print('CHECKING confusion:', initial, expected_initial)
    confused = {
        'C': {'E', 'G'},
        'E': {'C'},
        'G': {'C'},
        'I': {'J'},
        'J': {'I'},
        'O': {'D'},
        'D': {'O'},
    }
    if expected_initial.upper() not in confused:
        return False
    if initial.upper() in confused[expected_initial.upper()]:
        return True
    else:
        return False


def parse_lemma_prefix(lemma_string: str) -> Tuple[str, str]:
    words = re.split(r' +', lemma_string)
    prefix_stopwords = {
        'van', 'de', 'vanden', 'vander', 'ten'
    }
    lemma_term = ''
    if words[0].lower() in prefix_stopwords:
        words[0] = words[0].lower()
        lemma_term = words[0].lower()
        lemma_string = re.sub(r'^' + lemma_term, '', lemma_string).strip()
    return lemma_term, lemma_string


def parse_lemma_line(line: pdm.PageXMLTextLine) -> Dict[str, Union[str, List[str], None]]:
    """Return the lemma term for a given lemma line."""
    prefix_words = {
        'van', 'de', 'del', 'den', 'du', 'de la', 'het', 'la',
        "'s", 'St.', 'te', 'ten',
        'vanden', 'vander', 'vande',
        'wan'
    }
    infix_phrases = {
        'de', 'den', 'der', 'het', 'in', 'op', 'te', 'ten', 'tot',
        'van', 'vande', 'vanden', 'vander'
    }
    lemma_string = line.text.strip()
    words = re.split(r' +', lemma_string)
    lemma = {
        'prefix': None,
        'main_term': None,
        'infix': [],
        'content_terms': [],
        'all_terms': [],
        'full_term': None
    }
    for wi, word in enumerate(words):
        end_lemma = False
        # a comma means the end of the lemma
        clean_word = word
        if word.endswith(','):
            # remove final comma
            clean_word = word[:-1]
            end_lemma = True
        if len(clean_word) == 0:
            break
        if wi == 0 and clean_word.lower() in prefix_words:
            lemma['prefix'] = clean_word
            lemma['all_terms'].append(clean_word)
        elif wi == 0:
            lemma['main_term'] = clean_word
            lemma['content_terms'].append(clean_word)
            lemma['all_terms'].append(clean_word)
        elif wi == 1 and lemma['prefix'] is not None:
            lemma['main_term'] = clean_word
            lemma['all_terms'].append(clean_word)
        elif clean_word in infix_phrases:
            lemma['infix'].append(clean_word)
            lemma['all_terms'].append(clean_word)
        elif clean_word[0].isupper():
            lemma['content_terms'].append(clean_word)
            lemma['all_terms'].append(clean_word)
        elif word.endswith(','):
            lemma['content_terms'].append(clean_word)
            lemma['all_terms'].append(clean_word)
        else:
            end_lemma = True
        if end_lemma:
            break
    lemma['full_term'] = ' '.join(lemma['all_terms'])
    # remove trailing periods and commas
    lemma['full_term'] = lemma['full_term'].strip(string.punctuation)
    return lemma


def get_reference_iiif_urls(entry):
    urls = []
    column_lines = defaultdict(list)
    for line in entry["lines"]:
        column_id = line.id.split('-line-')[0]
        column_lines[column_id].append(line)
    for column_id in column_lines:
        coords = pdm.parse_derived_coords(column_lines[column_id])
        scan_id = column_id.split('-column-')[0]
        # coords = [int(coord) for coord in line_id.split('-')[-4:]]
        url = coords_to_iiif_url(scan_id, coords.box)
        urls.append(url)
    return urls


def parse_reference(entry: Dict[str, any], page_num_map: Dict[int, str]):
    urls = get_reference_iiif_urls(entry)
    page_ids = {line.metadata["page_id"] for line in entry["lines"]}
    scan_ids = {line.metadata["scan_id"] for line in entry["lines"]}
    reference = {
        "id": make_hash_id(','.join([line.id for line in entry["lines"]])),
        "metadata": {
            "inventory_num": entry["inventory_num"],
            "year": entry["year"],
            "page_id": list(page_ids),
            "scan_id": list(scan_ids),
            "iiif_urls": urls,
        },
        "lemma": entry["lemma"],
        "main_term": entry["main_term"],
        "locators": [],
        "sub_lemma": [line.text for line in entry["lines"]],
        "lines": [line.id for line in entry["lines"]],
        "text_page_nums": []
    }
    for line in reference["sub_lemma"]:
        # Add a preceding whitespace for lines that start with a page locator
        line = ' ' + line
        for match in re.finditer(r' (\d+)\.', line):
            text_page_num = int(match.group(1))
            locator = {
                "text_page_num": text_page_num,
                "page_id": page_num_map[text_page_num] if text_page_num in page_num_map else None
            }
            reference["locators"].append(locator)
            reference["text_page_nums"].append(text_page_num)
    return reference
