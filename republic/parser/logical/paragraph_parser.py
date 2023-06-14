from __future__ import annotations
import copy
import time
from collections import defaultdict
from typing import Dict, Generator, List, Tuple, Union

import numpy as np
import pagexml.model.physical_document_model as pdm
import pagexml.helper.pagexml_helper as pagexml_helper
import pagexml.analysis.layout_stats as layout_helper
from pagexml.analysis.text_stats import WordBreakDetector

import republic.helper.paragraph_helper as para_helper
import republic.model.republic_document_model as rdm


def running_id_generator(base_id: str, suffix: str, count: int = 0):
    """Returns an ID generator based on running numbers."""

    def generate_id():
        nonlocal count
        count += 1
        return f'{base_id}{suffix}{count}'

    return generate_id


def is_paragraph_boundary(prev_line: Union[None, pdm.PageXMLTextLine],
                          curr_line: pdm.PageXMLTextLine,
                          next_line: Union[None, pdm.PageXMLTextLine]) -> bool:
    if prev_line and pdm.in_same_column(curr_line, prev_line):
        if curr_line.is_next_to(prev_line):
            # print("SAME HEIGHT", prev_line['text'], '\t', line['text'])
            return False
        elif curr_line.coords.left > prev_line.coords.left + 20:
            # this line is left indented w.r.t. the previous line
            # so is the start of a new paragraph
            return True
        elif curr_line.coords.left - prev_line.coords.left < 20:
            if curr_line.coords.right > prev_line.coords.right + 40:
                # this line starts at the same horizontal level as the previous line
                # but the previous line ends early, so is the end of a paragraph.
                return True
            else:
                return False
    elif next_line and pdm.in_same_column(curr_line, next_line):
        if curr_line.coords.left > next_line.coords.left + 20:
            return True
    return False


class ParagraphLines:

    def __init__(self, lines: Union[pdm.PageXMLTextLine, List[pdm.PageXMLTextLine]] = None):
        self.lines = []
        self.lefts: np.array = np.array([])
        self.rights: np.array = np.array([])
        self.widths: np.array = np.array([])
        self.heights: np.array = np.array([])
        self.start_type = None
        self.end_type = None
        self.top = None
        self.bottom = None
        self.avg_distances = np.empty(0)
        self.num_chars = 0
        self.avg_char_width = 0
        self.insertion_lines = set()
        self.noise_lines = set()
        self.empty_lines = set()
        if lines is not None:
            self.add_lines(lines)

    def __iter__(self):
        for line in self.lines:
            yield line

    def __len__(self):
        return len(self.lines)

    def num_lines(self, count_all: bool = False):
        if count_all:
            return len(self.lines) + len(self.empty_lines) + len(self.noise_lines)
        else:
            return len(self.lines)

    def __add__(self, other: ParagraphLines):
        merge_lines = self.lines + other.lines
        merge_para = ParagraphLines(merge_lines)
        merge_para.start_type = self.start_type
        merge_para.end_type = other.end_type
        merge_para.insertion_lines = self.insertion_lines.union(other.insertion_lines)
        merge_para.noise_lines = self.noise_lines.union(other.noise_lines)
        return merge_para

    @property
    def json(self):
        return {
            'lefts': self.lefts,
            'rights': self.rights,
            'widths': self.widths,
            'heights': self.heights,
            'top': self.top,
            'bottom': self.bottom,
            'avg_distances': self.avg_distances,
            'num_chars': self.num_chars,
            'avg_char_width': self.avg_char_width,
            'lines': [line.text for line in self.lines],
        }

    @property
    def first(self):
        if len(self.lines) > 0:
            for line in self.lines:
                if line in self.insertion_lines:
                    continue
                return line
        else:
            return None

    @property
    def last(self):
        if len(self.lines) > 0:
            for line in self.lines[::-1]:
                if line in self.insertion_lines:
                    continue
                return line
        else:
            return None

    def _set_left_right(self):
        coords_list = [line.baseline if line.baseline else line.coords for line in self.lines
                       if line not in self.insertion_lines]
        self.lefts = np.array([coords.left for coords in coords_list])
        self.rights = np.array([coords.right for coords in coords_list])
        self.widths = np.array([coords.width for coords in coords_list])
        self.heights = np.array([coords.height for coords in coords_list])

    def _set_top_bottom(self):
        coords_list = [line.baseline if line.baseline else line.coords for line in self.lines
                       if line not in self.insertion_lines]
        self.top = min([coords.top for coords in coords_list])
        self.bottom = max([coords.bottom for coords in coords_list])

    def add_insertion_line(self, line: pdm.PageXMLTextLine):
        self.insertion_lines.add(line)
        self.lines.append(line)

    def add_lines(self, lines: Union[pdm.PageXMLTextLine, List[pdm.PageXMLTextLine]]):
        # print('\tADDING LINES', lines)
        if isinstance(lines, pdm.PageXMLTextLine):
            lines = [lines]
        if len(self.lines) == 0:
            new_interval_lines = lines
        else:
            new_interval_lines = [self.lines[-1]] + lines
        content_lines = []
        for line in lines:
            if line.text is None:
                self.empty_lines.add(line)
                continue
            content_lines.append(line)
            self.num_chars += len(line.text)
        self.lines.extend(content_lines)
        self._set_top_bottom()
        self._set_left_right()
        # print(f'\tWIDTHS: {self.widths}\t\tSUM OF WIDTHS: {self.widths.sum()}\n')
        self.avg_char_width = self.widths.sum() / self.num_chars
        if len(new_interval_lines) >= 2:
            new_distances = layout_helper.get_line_distances(new_interval_lines)
            avg_distances = [point_distances.mean() for point_distances in new_distances]
            if len(self.avg_distances) > 0:
                avg_distances = [dist for dist in self.avg_distances] + avg_distances
            # print(avg_distances)
            self.avg_distances = np.array(avg_distances)

    def get_horizontal_overlap(self, element: pdm.PageXMLDoc):
        min_left, max_left = sorted([self.lefts.mean(), element.coords.left])
        min_right, max_right = sorted([self.rights.mean(), element.coords.right])
        return min_right - max_left, (min_right - max_left) / (max_right - min_left)


def get_relative_position(curr_line: pdm.PageXMLTextLine, para_lines: ParagraphLines):
    if len(para_lines.lines) == 0:
        raise ValueError(f'cannot get position relative to empty {para_lines.__class__.__name__}')
    if curr_line.metadata['scan_id'] != para_lines.lines[-1].metadata['scan_id']:
        left_indent, right_indent, vertical_distance, overlap_abs, overlap_ratio = -1, -1, -1, -1, -1
    else:
        line_coords = curr_line.baseline if curr_line.baseline else curr_line.coords
        line_bottom = line_coords.bottom
        overlap_abs, overlap_ratio = para_lines.get_horizontal_overlap(curr_line)
        left_indent = line_coords.left - para_lines.lefts.mean()
        right_indent = para_lines.rights.mean() - line_coords.right
        vertical_distance = line_bottom - para_lines.bottom
        # print('get_relative_position - line_bottom:', line_bottom)
        # print('get_relative_position - para_lines.bottom:', para_lines.bottom)
        # print('get_relative_position - vertical_distance:', vertical_distance)
    relative_position = {
        'left_indent': left_indent,
        'right_indent': right_indent,
        'vertical_distance': vertical_distance,
        'overlap_abs': overlap_abs,
        'overlap_ratio': overlap_ratio
    }
    return relative_position


def split_paragraphs(lines: List[pdm.PageXMLTextLine], debug: int = 0):
    start = time.time()
    if len(lines) == 0:
        return []
    column_lines = defaultdict(list)
    for line in lines:
        column_lines[line.metadata['column_id']].append(line)
    grouped_lines = []
    for column_id in column_lines:
        column_grouped_lines = pagexml_helper.horizontal_group_lines(column_lines[column_id])
        grouped_lines.extend(column_grouped_lines)
    if lines[0].baseline:
        lefts = [line.baseline.left for line in lines]
    else:
        lefts = [line.coords.left for line in lines]
    if len(lines) <= 1:
        return lines
    paras = []
    para_lines = None
    prev_page_id = None
    num_lines = len([line for line in lines if line.text is not None])
    num_grouped_lines = sum([len(line_group) for line_group in grouped_lines])
    if num_grouped_lines != num_lines:
        raise ValueError(f'horizontal grouping of lines has changed the number of lines '
                         f'from {num_lines} to {num_grouped_lines}')
    for gi, curr_group in enumerate(grouped_lines):
        if debug > 1:
            print(f'split_paragraphs - LINE GROUP {gi}')
        for ci, curr_line in enumerate(curr_group):
            if debug > 0:
                print('split_paragraphs - curr_line:', curr_line.id)
            if prev_page_id is None or prev_page_id != curr_line.metadata['page_id']:
                if debug > 1:
                    print(f'-----------------------------------\n'
                          f'{curr_line.metadata["page_id"]}\n'
                          f'-----------------------------------')
                pass
            prev_page_id = curr_line.metadata['page_id']
            if curr_line.text is None:
                if para_lines is None:
                    para_lines = ParagraphLines()
                para_lines.empty_lines.add(curr_line)
                if debug > 0:
                    print('\tnoise line:', curr_line.id)
                continue
            if debug > 0:
                print('----------------------------------------------------------------------------')
                print('split_paragraphs - iterating lines - curr_line:', curr_line.id, curr_line.text)
            if debug > 2:
                coords = curr_line.coords
                baseline = curr_line.baseline
                print(f'\t{coords.left: >4}-{coords.right: <4}\t{coords.top: >4}-{coords.bottom}')
                print(f'\t{baseline.left: >4}-{baseline.right: <4}\t{baseline.top: >4}-{baseline.bottom}')
            if debug > 3:
                print(curr_line.metadata)
                # if para_lines:
                #     print(f'\t{para_lines.rights.mean()}')
                #     print(f'start of iteration, para_lines has {len(para_lines.lines)} lines')
            if para_lines is None or para_lines.last is None:
                if debug > 0:
                    print('\tSTART: empty para_lines')
                para_lines = ParagraphLines([curr_line])
                para_lines.start_type = 'para_start' if curr_line.text[0].isupper() else 'para_mid'
                continue
            elif pdm.in_same_column(curr_line, para_lines.last) is False:
                if debug > 0:
                    print('\tSPLIT: different column, appending para_lines')
                para_lines.end_type = 'para_mid'
                paras.append(para_lines)
                step = time.time()
                prev_step = step
                yield para_lines
                para_lines = ParagraphLines([curr_line])
                para_lines.start_type = 'para_mid'
                continue
            else:
                rel_pos = get_relative_position(curr_line, para_lines)
                if debug > 0:
                    print('\n\tRELATIVE POSITION', rel_pos)
                    print('\tpara_lines.avg_char_width:', para_lines.avg_char_width)
                    # print('\tpara_lines - lines:', para_lines.lines)
                if rel_pos['vertical_distance'] > curr_line.coords.height * 2:
                    # vertical distance to prev line is twice the height of current line
                    # so this is probably the start of a new para
                    if debug > 0:
                        print('\tSPLIT: vertical distance more than twice line height')
                    para_lines.end_type = 'para_end'
                    paras.append(para_lines)
                    yield para_lines
                    para_lines = ParagraphLines([curr_line])
                    para_lines.start_type = 'para_start'
                    continue
                if len(para_lines.lines) >= 2:
                    if len(para_lines.avg_distances) > 0 and \
                            rel_pos['vertical_distance'] > para_lines.avg_distances.mean() * 1.5:
                        if debug > 0:
                            print('\tSPLIT: vertical distance more than 1.5 avg vertical distance')
                        para_lines.end_type = 'para_end'
                        paras.append(para_lines)
                        yield para_lines
                        para_lines = ParagraphLines([curr_line])
                        para_lines.start_type = 'para_start'
                        continue
                if rel_pos['overlap_ratio'] > 0.85:
                    # curr_line and para are left- and right-aligned
                    if debug > 0:
                        print('\tAPPEND: line and para are left- and right-aligned')
                    para_lines.add_lines(curr_line)
                    continue
                elif abs(rel_pos['left_indent']) < para_lines.avg_char_width * 3:
                    # print('left_indent:', rel_pos['left_indent'], abs(rel_pos['left_indent']), para_lines.avg_char_width)
                    # print(para_lines.json)
                    if rel_pos['right_indent'] > para_lines.avg_char_width * 3:
                        # line and para are left-aligned but line is right-indented
                        if debug > 0:
                            print('\tAPPEND AND SPLIT: line and para are left-aligned but line is right-indented')
                        para_lines.end_type = 'para_end'
                        para_lines.add_lines(curr_line)
                        paras.append(para_lines)
                        yield para_lines
                        para_lines = None
                    else:
                        # line is left-aligned with para but longer
                        if debug > 0:
                            print('\tAPPEND: line is left-aligned with para but longer')
                        para_lines.add_lines(curr_line)
                elif abs(rel_pos['right_indent']) < para_lines.avg_char_width * 2:
                    # line and para are right-aligned
                    if len(curr_group) > 1 and curr_line == curr_group[-1]:
                        para_lines.noise_lines.add(curr_line)
                        if debug > 0:
                            print('\tSKIP: curr line is right-aligned with para, and is noise')
                    elif rel_pos['left_indent'] > 0:
                        # curr line is right-aligned with para, but is left-indented
                        if debug > 0:
                            print('\tAPPEND: curr line is right-aligned with para, but is left-indented')
                        para_lines.add_lines(curr_line)
                    else:
                        # curr line is negatively left-indented, new para
                        if debug > 0:
                            print('\tSPLIT: curr line is negatively left-indented, new para')
                        para_lines.end_type = 'para_end'
                        paras.append(para_lines)
                        yield para_lines
                        para_lines = ParagraphLines([curr_line])
                        para_lines.start_type = 'para_start'
                else:
                    # print('PARA_LINES WIDTHS:', para_lines.widths)
                    # print('AVG PARA_LINES WIDTH:', para_lines.widths.mean())
                    # print('\t', rel_pos['left_indent'] > para_lines.widths.mean())
                    if rel_pos['left_indent'] / para_lines.widths.mean() > 0.8 and len(curr_group) > 1 and curr_line == curr_group[-1]:
                        para_lines.noise_lines.add(curr_line)
                        if debug > 0:
                            print('\tSKIP: curr line is right-aligned with para, and is noise')
                    # line and para are not aligned
                    elif is_missing_text_insertion(curr_line, gi, grouped_lines, para_lines, debug=debug):
                        if debug > 0:
                            print('\tAPPEND: line is insertion of missing text')
                        para_lines.add_insertion_line(curr_line)
                    else:
                        if debug > 0:
                            print('\tSPLIT: line and para are not aligned')
                        para_lines.end_type = 'para_end'
                        paras.append(para_lines)
                        yield para_lines
                        para_lines = ParagraphLines([curr_line])
                        para_lines.start_type = 'para_start'
    if para_lines and len(para_lines.lines) > 0:
        para_lines.end_type = 'para_end'
        paras.append(para_lines)
        yield para_lines
    return None
    # return paras


def is_missing_text_insertion(curr_line, group_index, grouped_lines, para_lines,
                              debug: int = 0):
    if len(grouped_lines) <= group_index+1:
        return False
    next_line = grouped_lines[group_index+1][0]
    prev_line = para_lines.last
    if prev_line.metadata['column_id'] == curr_line.metadata['column_id']:
        vertical_overlap_prev = pdm.get_vertical_overlap(curr_line, para_lines.lines[-1])
    else:
        vertical_overlap_prev = 0
    vertical_overlap_next = pdm.get_vertical_overlap(curr_line, next_line)
    if debug > 2:
        print('\t\tvertical_overlap_prev:', vertical_overlap_prev)
        print('\t\tvertical_overlap_next:', vertical_overlap_next)
    rel_pos = get_relative_position(next_line, para_lines)
    if debug > 2:
        print('\t\tRELATIVE POSITION OF NEXT LINE:', rel_pos)
        print('\t\tDISTANCES:', para_lines.avg_distances)
    if vertical_overlap_prev + vertical_overlap_next > 0.75 * curr_line.coords.height:
        return True
    elif len(para_lines.avg_distances) == 0:
        return False
    elif abs(rel_pos['vertical_distance'] - para_lines.avg_distances.mean()) / para_lines.avg_distances.mean() > 0.9:
        return True
    else:
        return False


def is_resolution_gap(prev_line: pdm.PageXMLTextLine, line: pdm.PageXMLTextLine, resolution_gap: int) -> bool:
    # print('resolution_gap:', resolution_gap)
    # print('prev_line.coords.bottom:', prev_line.coords.bottom if prev_line else None)
    # print('line.coords.bottom:', line.coords.bottom)
    if not prev_line:
        return False
    # Resolution start line has big capital with low bottom.
    # If gap between box bottoms is small, this is no resolution gap.
    if -20 < line.coords.bottom - prev_line.coords.bottom < resolution_gap:
        # print('is_resolution_gap: False', line.coords.bottom - prev_line.coords.bottom)
        return False
    # If this line starts with a big capital, this is a resolution gap.
    if layout_helper.line_starts_with_big_capital(line):
        # print('is_resolution_gap: True, line starts with capital')
        return True
    # If the previous line has no big capital starting a resolution,
    # and it has a large vertical gap with the current line,
    # this is resolution gap.
    if not layout_helper.line_starts_with_big_capital(prev_line) and line.coords.top - prev_line.coords.top > 70:
        # print('is_resolution_gap: True', line.coords.bottom - prev_line.coords.bottom)
        return True
    else:
        # print('is_resolution_gap: False', line.coords.bottom - prev_line.coords.bottom)
        return False


class ParagraphGenerator:

    def __init__(self, line_break_detector: WordBreakDetector = None,
                 word_break_chars: str = None, use_left_indent: bool = False,
                 use_right_indent: bool = False,
                 resolution_gap: int = None):
        self.lbd = line_break_detector
        self.word_break_chars = word_break_chars
        self.use_left_indent = use_left_indent
        self.use_right_indent = use_right_indent
        self.resolution_gap = resolution_gap

    def get_paragraphs(self, doc: Union[pdm.PageXMLTextRegion, rdm.RepublicDoc],
                       prev_line: Union[None, dict] = None) -> Generator[rdm.RepublicParagraph, None, None]:
        if self.use_left_indent:
            paragraphs = self.get_paragraphs_with_left_indent(doc, prev_line=prev_line)
        elif self.use_right_indent:
            paragraphs = self.get_paragraphs_with_right_indent(doc, prev_line=prev_line)
        else:
            paragraphs = self.get_paragraphs_with_vertical_space(doc, prev_line=prev_line)
        for paragraph in paragraphs:
            paragraph.metadata['doc_id'] = doc.id
            yield paragraph

    def make_paragraph(self, doc: Union[pdm.PageXMLTextRegion, rdm.RepublicDoc],
                       doc_text_offset: int, paragraph_id: str,
                       para_lines: List[pdm.PageXMLTextLine]) -> rdm.RepublicParagraph:
        metadata = copy.deepcopy(doc.metadata)
        metadata['id'] = paragraph_id
        metadata['type'] = "paragraph"
        text_region_ids = []
        for line in para_lines:
            if line.metadata["parent_id"] not in text_region_ids:
                text_region_ids.append(line.metadata["parent_id"])
                if line.metadata['page_id'] not in metadata['page_ids']:
                    metadata['page_ids'].append(line.metadata['page_id'])
        text, line_ranges = self.make_paragraph_text(para_lines)
        paragraph = rdm.RepublicParagraph(lines=para_lines, metadata=metadata,
                                          text=text, line_ranges=line_ranges)
        paragraph.metadata["start_offset"] = doc_text_offset
        return paragraph

    def make_paragraph_text(self, lines: List[pdm.PageXMLTextLine]) -> Tuple[str, List[Dict[str, any]]]:
        text, line_ranges = pagexml_helper.make_text_region_text(lines, word_break_chars=self.word_break_chars)
        return text, line_ranges

    def get_paragraphs_with_left_indent(self, doc: Union[pdm.PageXMLTextRegion, rdm.RepublicDoc],
                                        prev_line: Union[None, pdm.PageXMLTextLine] = None,
                                        text_page_num_map: Dict[str, int] = None,
                                        page_num_map: Dict[str, int] = None) -> List[rdm.RepublicParagraph]:
        paragraphs: List[rdm.RepublicParagraph] = []
        generate_paragraph_id = running_id_generator(base_id=doc.id, suffix='-para-')
        para_lines = []
        doc_text_offset = 0
        lines = [line for line in doc.get_lines()]
        for li, line in enumerate(lines):
            if text_page_num_map is not None and line.metadata["parent_id"] in text_page_num_map:
                line.metadata["text_page_num"] = text_page_num_map[line.metadata["parent_id"]]
            line.metadata["page_num"] = page_num_map[line.metadata["parent_id"]]
            next_line = lines[li + 1] if len(lines) > (li + 1) else None
            if is_paragraph_boundary(prev_line, line, next_line):
                if len(para_lines) > 0:
                    paragraph = self.make_paragraph(doc, doc_text_offset, generate_paragraph_id(),
                                                    para_lines)
                    doc_text_offset += len(paragraph.text)
                    paragraphs.append(paragraph)
                para_lines = []
            para_lines.append(line)
            if not line.text or len(line.text) == 1:
                continue
            if prev_line and line.is_next_to(prev_line):
                continue
            prev_line = line
        if len(para_lines) > 0:
            paragraph = self.make_paragraph(doc, doc_text_offset, generate_paragraph_id(),
                                            para_lines)
            doc_text_offset += len(paragraph.text)
            paragraphs.append(paragraph)
        return paragraphs

    def get_paragraphs_with_right_indent(self, doc: Union[pdm.PageXMLTextRegion, rdm.RepublicDoc],
                                         prev_line: Union[None, dict] = None,
                                         text_page_num_map: Dict[str, int] = None,
                                         page_num_map: Dict[str, int] = None):
        lines = [line for line in doc.get_lines()]

    def get_paragraphs_with_vertical_space(self, doc: Union[pdm.PageXMLTextRegion, rdm.RepublicDoc],
                                           prev_line: Union[None, dict] = None,
                                           text_page_num_map: Dict[str, int] = None,
                                           page_num_map: Dict[str, int] = None) -> List[rdm.RepublicParagraph]:
        para_lines = []
        paragraphs = []
        doc_text_offset = 0
        generate_paragraph_id = running_id_generator(base_id=doc.metadata["id"], suffix="-para-")
        if self.resolution_gap is not None:
            resolution_gap = self.resolution_gap
            lines = [line for line in doc.get_lines()]
        elif isinstance(doc, rdm.Session) and doc.date.date.year < 1705:
            resolution_gap = 120
            margin_trs = []
            body_trs = []
            for tr in doc.text_regions:
                left_margin = 800 if tr.metadata['page_num'] % 2 == 0 else 3100
                if tr.coords.x < left_margin and tr.coords.width < 1000:
                    margin_trs.append(tr)
                else:
                    body_trs.append(tr)
            lines = [line for tr in body_trs for line in tr.lines]
        else:
            resolution_gap = 80
            lines = [line for line in doc.get_lines()]
        print('getting paragraphs with vertical space')
        print('number of lines:', len(lines))
        for li, line in enumerate(lines):
            if text_page_num_map is not None and line.metadata["parent_id"] in text_page_num_map:
                line.metadata["text_page_num"] = text_page_num_map[line.metadata["parent_id"]]
            if page_num_map is not None:
                line.metadata["page_num"] = page_num_map[line.metadata["parent_id"]]
            if prev_line:
                print(prev_line.coords.top, prev_line.coords.bottom, line.coords.top, line.coords.bottom, line.text)
            if is_resolution_gap(prev_line, line, resolution_gap):
                if len(para_lines) > 0:
                    paragraph = self.make_paragraph(doc, doc_text_offset,
                                                    generate_paragraph_id(), para_lines)
                    doc_text_offset += len(paragraph.text)
                    print('\tappending paragraph:', paragraph.id)
                    print('\t', paragraph.text)
                    print()
                    paragraphs.append(paragraph)
                para_lines = []
            para_lines.append(line)
            if not line.text or len(line.text) == 1:
                continue
            if prev_line and line.is_next_to(prev_line):
                continue
            prev_line = line
        if len(para_lines) > 0:
            paragraph = self.make_paragraph(doc, doc_text_offset, generate_paragraph_id(),
                                            para_lines)
            doc_text_offset += len(paragraph.text)
            paragraphs.append(paragraph)
        return paragraphs


