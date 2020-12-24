from collections import Counter
from typing import List, Union
import copy
import re
import json

from republic.fuzzy.fuzzy_match import Match
from republic.model.generic_document_model import PhysicalStructureDoc, Paragraph
from republic.model.generic_document_model import same_height, same_column, order_lines
from republic.model.generic_document_model import parse_derived_coords, line_ends_with_word_break


class ResolutionPageDoc(PhysicalStructureDoc):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.type = ["page", "resolution_page"]
        # make sure page has scan id in metadata
        if "scan_id" not in self.metadata:
            self.metadata["scan_id"] = self.metadata["id"].split("-page")[0]
        # make sure each column has a scan_id
        for column in self.columns:
            if "scan_id" not in column["metadata"]:
                column["metadata"]["scan_id"] = self.metadata["scan_id"]

    def stream_ordered_lines(self, word_freq_counter: Counter = None):
        # if len(columns) > 2:
        #     print("\n\nWEIRD NUMBER OF COLUMNS:", len(columns), 'in doc', self.metadata['id'])
        for column in self.columns:
            check_special_column_for_bleed_through(column, word_freq_counter)
        columns = sort_resolution_columns(self.columns)
        for column_index, column in columns:
            # print('\ncolumn:', column_index)
            sorted_text_regions = sort_resolution_text_regions(column['textregions'])
            for ti, text_region in enumerate(sorted_text_regions):
                # print(text_region['coords'])
                for line in order_lines(text_region["lines"]):
                    line["metadata"]["inventory_num"] = self.metadata["inventory_num"]
                    line["metadata"]["doc_id"] = self.metadata["id"]
                    line["metadata"]["column_index"] = column_index
                    line["metadata"]["textregion_index"] = ti
                    if 'is_bleed_through' not in line['metadata']:
                        line['metadata']['is_bleed_through'] = False
                    yield line


class ResolutionParagraph:

    def __init__(self, para_lines: list, word_freq_counter: Counter = None):
        self.lines = copy.deepcopy(para_lines)
        self.metadata = {
            "inventory_num": para_lines[0]["metadata"]["inventory_num"]
        }
        self.text = ""
        self.line_ranges = []
        self.set_text(word_freq_counter)

    def __repr__(self):
        return f"ResolutionParagraph(lines={[line['metadata']['id'] for line in self.lines]}, text={self.text})"

    def json(self):
        return {
            "metadata": self.metadata,
            "lines": [line['metadata']['id'] for line in self.lines],
            "text": self.text,
            "line_ranges": self.line_ranges
        }

    def set_text(self, word_freq_counter: Counter = None):
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
            elif line_ends_with_word_break(line, next_line, word_freq_counter):
                line_text = re.split(r'\W+$', line["text"])[0]
            elif (li + 1) == len(self.lines):
                line_text = line["text"]
            else:
                line_text = line["text"] + " "
            line_range = {"start": len(self.text), "end": len(self.text + line_text), "line_index": li}
            self.text += line_text
            self.line_ranges.append(line_range)

    def get_match_lines(self, match: Match) -> List[dict]:
        # part_of_match = False
        match_lines = []
        for line_range in self.line_ranges:
            if line_range["start"] <= match.offset < line_range["end"]:
                match_lines.append(self.lines[line_range["line_index"]])
        return match_lines


def check_special_column_for_bleed_through(column: dict, word_freq_counter: Counter) -> None:
    if column['metadata']['median_normal_length'] >= 15:
        return None
    # print(json.dumps(column['metadata'], indent=4))
    for tr in column['textregions']:
        for line in tr['lines']:
            if not word_freq_counter:
                continue
            if not line['text']:
                line['metadata']['is_bleed_through'] = True
                # print('BLOOD THROUGH?', line['metadata']['is_bleed_through'], line['text'])
                continue
            words = re.split(r'\W+', line['text'])
            word_counts = [word_freq_counter[word] for word in words if word != '']
            if len(word_counts) == 0:
                line['metadata']['is_bleed_through'] = True
                # print('BLOOD THROUGH?', line['metadata']['is_bleed_through'], line['text'])
                continue
            max_count_index = word_counts.index(max(word_counts))
            max_count_word = words[max_count_index]
            # print(max_count_word, len(max_count_word), word_freq_counter[max_count_word])
            if len(max_count_word) > 5 and max(word_counts) > 2:
                line['metadata']['is_bleed_through'] = False
            elif len(word_counts) == 0 or max(word_counts) < 10:
                line['metadata']['is_bleed_through'] = True
            else:
                line['metadata']['is_bleed_through'] = False
            # print('BLOOD THROUGH?', line['metadata']['is_bleed_through'], line['text'])


def sort_resolution_text_regions(text_regions) -> List[dict]:
    sorted_text_regions = sorted(text_regions, key=lambda tr: tr['coords']['top'])
    merge_tr = {}
    for ti1, curr_tr in enumerate(sorted_text_regions):
        # print("ti1:", ti1, curr_tr['coords'])
        if ti1 in merge_tr:
            continue
        for ti2, next_tr in enumerate(sorted_text_regions):
            if ti2 <= ti1:
                continue
            if next_tr['coords']['left'] > curr_tr['coords']['right'] or \
                    curr_tr['coords']['left'] > next_tr['coords']['right']:
                # the text regions are next to each other, don't merge
                continue
            if next_tr['coords']['top'] > curr_tr['coords']['bottom'] - 30:
                # the next text region is below the current one, don't merge
                continue
            # print("OVERLAPPING TEXT REGIONS")
            # print('\t', curr_tr['coords'])
            # print('\t', next_tr['coords'])
            merge_tr[ti2] = curr_tr
    for inner_ti in merge_tr:
        inner_tr = sorted_text_regions[inner_ti]
        outer_tr = merge_tr[inner_ti]
        outer_tr['lines'] = sorted(outer_tr['lines'] + inner_tr['lines'], key=lambda l: l['coords']['top'])
        outer_tr['coords'] = parse_derived_coords(outer_tr['lines'])
    return [tr for ti, tr in enumerate(sorted_text_regions) if ti not in merge_tr]


def sort_resolution_columns(columns):
    merge = {}
    columns = copy.deepcopy(columns)
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


def get_paragraphs_with_indent(doc: ResolutionPageDoc, prev_line: Union[None, dict] = None,
                               word_freq_counter: Counter = None) -> List[ResolutionParagraph]:
    paragraphs: List[ResolutionParagraph] = []
    para_lines = []
    lines = [line for line in doc.stream_ordered_lines(word_freq_counter=word_freq_counter)]
    for li, line in enumerate(lines):
        next_line = lines[li+1] if len(lines) > (li+1) else None
        if prev_line and same_column(line, prev_line):
            if same_height(line, prev_line):
                # print("SAME HEIGHT", prev_line['text'], '\t', line['text'])
                pass
            elif line["coords"]["left"] > prev_line["coords"]["left"] + 20:
                # this line is left indented w.r.t. the previous line
                # so is the start of a new paragraph
                if len(para_lines) > 0:
                    paragraph = ResolutionParagraph(para_lines, word_freq_counter=word_freq_counter)
                    paragraphs.append(paragraph)
                para_lines = []
            elif line['coords']['left'] - prev_line['coords']['left'] < 20:
                if line['coords']['right'] > prev_line['coords']['right'] + 40:
                    # this line starts at the same horizontal level as the previous line
                    # but the previous line ends early, so is the end of a paragraph.
                    if len(para_lines) > 0:
                        paragraph = ResolutionParagraph(para_lines, word_freq_counter=word_freq_counter)
                        paragraphs.append(paragraph)
                    para_lines = []
        elif next_line and same_column(line, next_line):
            if line["coords"]["left"] > next_line["coords"]["left"] + 20:
                if len(para_lines) > 0:
                    paragraph = ResolutionParagraph(para_lines, word_freq_counter=word_freq_counter)
                    paragraphs.append(paragraph)
                para_lines = []
        para_lines.append(line)
        if not line['text'] or len(line['text']) == 1:
            continue
        if prev_line and same_height(prev_line, line):
            continue
        if prev_line and line['text'] and same_height(line, prev_line):
            words = re.split(r'\W+', line['text'])
            word_counts = [word_freq_counter[word] for word in words if word != '']
            if len(word_counts) == 0 or max(word_counts) < 10:
                line['metadata']['is_blood_through'] = True
        prev_line = line
    if len(para_lines) > 0:
        paragraph = ResolutionParagraph(para_lines, word_freq_counter=word_freq_counter)
        paragraphs.append(paragraph)
    return paragraphs


def get_paragraphs(doc: ResolutionPageDoc, prev_line: Union[None, dict] = None,
                   use_indent: bool = False, use_vertical_space: bool = True,
                   word_freq_counter: Counter = None) -> List[ResolutionParagraph]:
    if use_indent:
        return get_paragraphs_with_indent(doc, prev_line=prev_line, word_freq_counter=word_freq_counter)
    elif use_vertical_space:
        return get_paragraphs_with_vertical_space(doc, prev_line=prev_line, word_freq_counter=word_freq_counter)


def get_paragraphs_with_vertical_space(doc: ResolutionPageDoc, prev_line: Union[None, dict] = None,
                                       word_freq_counter: Counter = None) -> List[ResolutionParagraph]:
    para_lines = []
    paragraphs = []
    lines = [line for line in doc.stream_ordered_lines()]
    for li, line in enumerate(lines):
        if prev_line and line["coords"]["top"] - prev_line["coords"]["top"] > 65:
            if len(para_lines) > 0:
                paragraph = ResolutionParagraph(para_lines, word_freq_counter=word_freq_counter)
                paragraphs.append(paragraph)
            para_lines = []
        para_lines.append(line)
        if not line['text'] or len(line['text']) == 1:
            continue
        if prev_line and same_height(prev_line, line):
            continue
        prev_line = line
    if len(para_lines) > 0:
        paragraph = ResolutionParagraph(para_lines, word_freq_counter=word_freq_counter)
        paragraphs.append(paragraph)
    return paragraphs
