from collections import Counter, defaultdict
from typing import Dict, Generator, List, Set, Tuple, Union
import datetime
import copy
import re
import json

from fuzzy_search.fuzzy_match import PhraseMatch, Phrase
from fuzzy_search.fuzzy_phrase_searcher import FuzzyPhraseSearcher, PhraseModel
from republic.model.physical_document_model import StructureDoc
from republic.model.physical_document_model import same_height, same_column, order_lines
from republic.model.physical_document_model import parse_derived_coords, line_ends_with_word_break
from republic.model.republic_date import RepublicDate
from republic.helper.metadata_helper import make_scan_urls, make_iiif_region_url
import republic.model.resolution_phrase_model as rpm


class ResolutionDoc(StructureDoc):

    def __init__(self, metadata: Union[None, Dict] = None,
                 coords: Union[None, Dict] = None,
                 lines: Union[None, List[Dict[str, Union[str, int, Dict[str, int]]]]] = None,
                 columns: Union[None, List[Dict[str, Union[dict, list]]]] = None):
        super().__init__(metadata=metadata, coords=coords, lines=lines, columns=columns)
        self.type = "resolution_doc"
        self.check_bleed_through: bool = False

    def stream_ordered_lines(self, word_freq_counter: Counter = None,
                             check_bleed_through: bool = None) -> Generator[Dict[str, any], None, None]:
        if check_bleed_through is None:
            check_bleed_through = self.check_bleed_through
        if check_bleed_through:
            for column in self.columns:
                check_special_column_for_bleed_through(column, word_freq_counter)
        columns = sort_resolution_columns(self.columns)
        for column_index, column in columns:
            sorted_text_regions = sort_resolution_text_regions(column['textregions'])
            for ti, text_region in enumerate(sorted_text_regions):
                if 'metadata' not in  text_region:
                    text_region['metadata'] = {}
                if 'id' not in text_region['metadata']:
                    text_region['metadata']['id'] = column['metadata']['id'] + f'-tr-{ti}'
                for li, line in enumerate(order_lines(text_region["lines"])):
                    line["metadata"]["inventory_num"] = self.metadata["inventory_num"]
                    line["metadata"]["doc_id"] = self.metadata["id"]
                    line["metadata"]["column_index"] = column_index
                    line["metadata"]["column_id"] = column['metadata']['id']
                    line["metadata"]["textregion_index"] = ti
                    if 'id' not in line['metadata']:
                        line["metadata"]["id"] = text_region['metadata']['id'] + f'-line-{li}'
                    if 'is_bleed_through' not in line['metadata']:
                        line['metadata']['is_bleed_through'] = False
                    if 'page_column_id' in column['metadata']:
                        line['metadata']['page_column_id'] = column['metadata']['page_column_id']
                    yield line


class ResolutionPageDoc(ResolutionDoc):

    def __init__(self, metadata: Dict[str, any] = None, coords: Dict = None, scan_version: dict = None,
                 lines: List[Dict[str, Union[str, int, Dict[str, int]]]] = None,
                 columns: List[Dict[str, Union[dict, list]]] = None,
                 header: Dict[str, any] = None):
        super().__init__(metadata=metadata, coords=coords, lines=lines, columns=columns)
        self.check_bleed_through: bool = True
        self.type = ["page", "resolution_page"]
        self.scan_version = scan_version
        self.header = header

    def json(self, include_header: bool = True) -> Dict[str, any]:
        """Return a JSON/dictionary representation."""
        page_json = {
            'metadata': self.metadata,
            'coords': self.coords,
            'columns': self.columns,
            'version': self.scan_version
        }
        if include_header:
            page_json['header'] = self.header
        return page_json

    def stream_ordered_lines(self, word_freq_counter: Counter = None,
                             check_bleed_through: bool = None,
                             include_header: bool = False) -> Generator[Dict[str, any], None, None]:
        if include_header:
            for ti, tr in enumerate(self.header['textregions']):
                if 'metadata' not in tr:
                    tr['metadata'] = {}
                if 'id' not in tr['metadata']:
                    tr['metadata']['id'] = self.metadata['id'] + f'-header-tr-{ti}'
                for line in tr['lines']:
                    if 'metadata' not in line:
                        line['metadata'] = {}
                    if 'id' not in line['metadata']:
                        line['metadata']['id'] = tr['metadata']['id'] + f'-line-{ti}'
                    line['metadata']['column_id'] = self.metadata['id'] + f'-header'
                    line['metadata']['doc_id'] = self.metadata['id']
                    line['metadata']['scan_id'] = self.metadata['scan_id']
                    yield line
        for line in super().stream_ordered_lines(word_freq_counter=word_freq_counter,
                                                 check_bleed_through=check_bleed_through):
            yield line


def page_json_to_resolution_page(page_json: Dict[str, any]) -> ResolutionPageDoc:
    return ResolutionPageDoc(metadata=page_json['metadata'], coords=page_json['coords'],
                             columns=page_json['columns'], header=page_json['header'],
                             scan_version=page_json['version'])


class ResolutionParagraph(ResolutionDoc):

    def __init__(self, lines: List[dict] = None, columns: List[dict] = None, metadata: dict = None,
                 scan_versions: List[Dict[str, any]] = None, text: str = None, column_ids: List[str] = None,
                 line_ranges: List[Dict[str, any]] = None, word_freq_counter: Counter = None):
        super().__init__(lines=lines, columns=columns, metadata=metadata)
        self.id = self.metadata['id']
        self.line_ranges = line_ranges if line_ranges else []
        self.text = text if text else ""
        self.column_ids: Set[str] = set()
        if column_ids:
            self.column_ids = set(column_ids)
        else:
            self.column_ids = {column['metadata']['id'] for column in self.columns}
        if not text:
            self.set_text(word_freq_counter)
        self.metadata['num_columns'] = len(self.columns)
        self.metadata['num_lines'] = len(self.lines)
        self.metadata["type"] = "resolution_paragraph"
        self.metadata["num_words"] = len([word for word in re.split(r'\W+', self.text) if word != ''])
        self.scan_versions = scan_versions
        self.evidence: List[PhraseMatch] = []

    def __repr__(self):
        return f"ResolutionParagraph(lines={[line['metadata']['id'] for line in self.lines]}, text={self.text})"

    def json(self, include_columns: bool = True):
        json_data = {
            "metadata": self.metadata,
            "column_ids": list(self.column_ids),
            "text": self.text,
            "line_ranges": self.line_ranges,
            "scan_versions": self.scan_versions
        }
        if include_columns:
            json_data["columns"] = self.columns
        return json_data

    def set_text(self, word_freq_counter: Counter = None):
        self.line_ranges = []
        for li, line in enumerate(self.lines):
            if line["text"] is None:
                continue
            elif 'is_bleed_through' in line['metadata'] and line['metadata']['is_bleed_through']:
                continue
            elif len(line['text']) == 1:
                continue
            next_line = self.lines[li + 1] if len(self.lines) > li + 1 else {'text': None}
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
            line_range = {
                "start": len(self.text), "end": len(self.text + line_text),
                'line_id': line['metadata']['id']
            }
            self.text += line_text
            self.line_ranges.append(line_range)

    def get_match_lines(self, match: PhraseMatch) -> List[dict]:
        # part_of_match = False
        match_lines = []
        for line_range in self.line_ranges:
            if line_range["start"] <= match.offset < line_range["end"]:
                match_lines.append(self.lines[line_range["line_index"]])
        return match_lines


def lines_to_paragraph_text(lines: List[dict], line_break_chars: str = '-',
                            term_freq: Counter = None):
    if term_freq:
        raise ValueError('term frequency handling is not yet implemented!')
    paragraph_text = ''
    line_ranges = []
    for line in lines:
        if line['text'][-1] in line_break_chars:
            line_text = line['text'][:-1]
        else:
            line_text = line['text'] + ' '
        line_range = {
            "start": len(paragraph_text), "end": len(paragraph_text + line_text),
            'line_id': line['metadata']['id']
        }
        line_ranges.append(line_range)
        paragraph_text += line_text
    return {'paragraph_text': paragraph_text, 'line_ranges': line_ranges}


class Session(ResolutionDoc):

    def __init__(self, metadata: Dict, scan_versions: List[dict] = None,
                 evidence: List[dict] = None, **kwargs):
        """A meeting session occurs on a specific day, with a president and attendants,
        and has textual content in the form of
         lines or possibly as Resolution objects."""
        super().__init__(metadata=metadata, **kwargs)
        self.session_date = RepublicDate(date_string=metadata['session_date'])
        self.type = "session"
        self.date = self.session_date
        self.id = f"session-{self.session_date.as_date_string()}-num-1"
        self.president: Union[str, None] = None
        self.attendance: List[str] = []
        self.scan_versions: Union[None, List[dict]] = scan_versions
        self.resolutions = []
        self.metadata['num_columns'] = len(self.columns)
        self.metadata['num_lines'] = len(self.lines)
        self.metadata['num_words'] = 0
        self.add_column_metadata()
        self.evidence: List[dict] = evidence

    def add_column_metadata(self):
        """Add page column id, iiif urls and stats on number of columns, lines, words."""
        for ci, column in enumerate(self.columns):
            if '-page-' in column['metadata']['id']:
                column['metadata']['page_column_id'] = column['metadata']['id']
                column['metadata']['page_id'] = column['metadata']['doc_id']
            column['metadata']['doc_id'] = self.id
            column['metadata']['id'] = self.id + f'-column-{ci}'
            urls = make_scan_urls(inventory_num=self.metadata['inventory_num'],
                                  scan_id=column['metadata']['scan_id'])
            column['metadata']['iiif_url'] = make_iiif_region_url(urls['jpg_url'],
                                                                  column['coords'],
                                                                  add_margin=100)
            words = []
            column['metadata']['num_lines'] = 0
            for tr in column['textregions']:
                for line in tr['lines']:
                    column['metadata']['num_lines'] += 1
                    if line["text"]:
                        words += [word for word in re.split(r'\W+', line['text']) if word != '']
                # words = [word for line in self.lines for word in re.split(r"\W+", line["text"]) if line["text"]]
            column['metadata']['num_words'] = len(words)
            self.metadata['num_words'] += len(words)

    def add_page_column_metadata(self, page_column_metadata: Dict[str, dict]) -> None:
        for ci, column in enumerate(self.columns):
            page_col_metadata = page_column_metadata[column['metadata']['page_column_id']]
            for key in page_col_metadata:
                if key == 'id':
                    column['metadata']['page_column_id'] = page_col_metadata[key]
                elif key in ['num_words', 'num_lines', 'iiif_url']:
                    continue
                else:
                    column['metadata'][key] = page_col_metadata[key]

    def get_metadata(self) -> Dict[str, Union[str, List[str]]]:
        """Return the metadata of the session, including date, president and attendants."""
        return self.metadata

    def json(self, with_resolutions: bool = False, with_columns: bool = True,
             with_lines: bool = False, with_scan_versions: bool = True) -> dict:
        """Return a JSON presentation of the session."""
        json_doc = {
            'metadata': self.metadata,
            'columns': self.columns,
            'evidence': self.evidence
        }
        self.metadata['type'] = self.type
        if with_resolutions:
            json_doc['resolutions'] = self.resolutions
        if with_columns:
            json_doc['columns'] = self.get_columns()
        if with_lines:
            json_doc['lines'] = self.get_lines()
        if with_scan_versions:
            json_doc["scan_versions"] = self.scan_versions
        return json_doc

    def get_paragraphs(self, use_indent=False,
                       use_vertical_space=True) -> Generator[ResolutionParagraph, None, None]:
        if 1705 <= self.date.date.year < 1711:
            use_indent = True
        for paragraph in get_paragraphs(self, use_indent=use_indent, use_vertical_space=use_vertical_space):
            paragraph.metadata['doc_id'] = self.metadata['id']
            yield paragraph


def get_proposition_type_from_evidence(evidence: List[PhraseMatch]) -> Union[None, str]:
    proposition_type = None
    for phrase_match in evidence:
        if has_proposition_type_label(phrase_match):
            return get_proposition_type_from_label(phrase_match)
    return proposition_type


def get_proposition_type_from_label(phrase_match: PhraseMatch) -> str:
    if not phrase_match.label:
        raise ValueError('phrase_match has no label')
    if isinstance(phrase_match.label, str):
        if not phrase_match.label.startswith('proposition_type:'):
            raise ValueError('phrase_match has no proposition_type label')
        return phrase_match.label.replace('proposition_type:', '')
    else:
        for label in phrase_match.label:
            if label.startswith('proposition_type:'):
                return label.replace('proposition_type:', '')
    raise ValueError('phrase_match has no proposition_type label')


def has_proposition_type_label(phrase_match: PhraseMatch) -> bool:
    if not phrase_match.label:
        return False
    if isinstance(phrase_match.label, str):
        return phrase_match.label.startswith('proposition_type:')
    else:
        for label in phrase_match.label:
            if label.startswith('proposition_type:'):
                return True
    return False


def parse_phrase_match(match: Union[PhraseMatch, dict]) -> PhraseMatch:
    if isinstance(match, PhraseMatch):
        return match
    match_phrase = Phrase(match['phrase'])
    match_variant = Phrase(match['variant'])
    if 'text_id' not in match:
        match['text_id'] = None
    if 'match_scores' not in match:
        match['match_scores'] = None
    try:
        match_object = PhraseMatch(match_phrase, match_variant, match['string'], match_offset=match['offset'],
                                   text_id=match['text_id'], match_scores=match['match_scores'])
    except ValueError:
        print(match)
        raise
    if 'label' in match:
        match_object.label = match['label']
    return match_object


def parse_phrase_matches(phrase_matches: Union[List[PhraseMatch], List[dict]]):
    match_objects: List[PhraseMatch] = []
    for match in phrase_matches:
        match_objects.append(parse_phrase_match(match))
    return match_objects


class AttendanceList(ResolutionDoc):

    def __init__(self,
                 metadata: dict = None,
                 coords: Union[None, Dict] = None, scan_versions: dict = None,
                 lines: Union[None, List[Dict[str, Union[str, int, Dict[str, int]]]]] = None,
                 session: Union[None, Session] = None,
                 columns: Union[None, List[Dict[str, Union[dict, list]]]] = None,
                 paragraphs: List[ResolutionParagraph] = None,
                 evidence: Union[List[dict], List[PhraseMatch]] = None):
        """An attendance list has textual content."""
        if not metadata:
            metadata = {}
        metadata['type'] = 'attendance_list'
        if session:
            metadata['session_date'] = session.metadata['session_date']
            metadata['session_id'] = session.metadata['id']
            metadata['session_num'] = session.metadata['session_num']
            metadata['inventory_num'] = session.metadata['inventory_num']
            metadata['president'] = session.metadata['president']
        super().__init__(metadata=metadata, coords=coords, lines=lines, columns=columns)
        self.type = "attendance_list"
        self.scan_versions = scan_versions if scan_versions else []
        self.session_date: Union[RepublicDate, None] = None
        self.paragraphs: List[ResolutionParagraph] = paragraphs if paragraphs else []
        if paragraphs and not columns:
            self.add_columns_from_paragraphs()
        self.column_ids: Set[str] = set()
        if len(self.paragraphs) == 0:
            self.metadata['num_paragraphs'] = 0
            self.metadata['num_columns'] = 0
            self.metadata['num_lines'] = 0
            self.metadata['num_words'] = 0
        # if 'evidence' in self.metadata and self.metadata['evidence']:
        #     self.evidence = parse_phrase_matches(metadata['evidence'])
        #     self.metadata['evidence'] = self.evidence
        self.evidence: List[PhraseMatch] = []
        if evidence:
            self.evidence = parse_phrase_matches(evidence)

    def __repr__(self):
        return f"AttendanceList({json.dumps(self.json(), indent=4)}"

    def add_columns_from_paragraphs(self):
        for paragraph in self.paragraphs:
            for column in paragraph.columns:
                self.columns.append(column)

    def add_paragraph(self, paragraph: ResolutionParagraph, matches: List[PhraseMatch] = None):
        paragraph.metadata['paragraph_index'] = len(self.paragraphs)
        self.paragraphs.append(paragraph)
        self.column_ids = self.column_ids.union([column['metadata']['id'] for column in paragraph.columns])
        self.columns += paragraph.columns
        self.metadata['num_paragraphs'] = len(self.paragraphs)
        self.metadata['num_columns'] = len(self.column_ids)
        self.metadata['num_lines'] += paragraph.metadata['num_lines']
        self.metadata['num_words'] += paragraph.metadata['num_words']
        self.evidence += matches

    def json(self):
        json_data = {
            'metadata': self.metadata,
            'paragraphs': [paragraph.json(include_columns=False) for paragraph in self.paragraphs],
            'evidence': [match.json() for match in self.evidence],
            'columns': self.columns
        }
        return json_data


class Resolution(ResolutionDoc):

    def __init__(self,
                 metadata: dict = None,
                 coords: Union[None, Dict] = None, scan_versions: dict = None,
                 lines: Union[None, List[Dict[str, Union[str, int, Dict[str, int]]]]] = None,
                 session: Union[None, Session] = None,
                 columns: Union[None, List[Dict[str, Union[dict, list]]]] = None,
                 paragraphs: List[ResolutionParagraph] = None,
                 evidence: Union[List[dict], List[PhraseMatch]] = None):
        """A resolution has textual content of the resolution, as well as an
        opening formula, decision information, and type information on the
        source document that instigated the discussion and resolution. Source
        documents can be missives, requests, reports, ..."""
        if not metadata:
            metadata = {}
        if 'proposition_type' not in metadata:
            metadata['proposition_type'] = None
        if 'proposer' not in metadata:
            metadata['proposer'] = None
        if 'decision' not in metadata:
            metadata['decision'] = None
        metadata['type'] = 'resolution'
        if session:
            metadata['session_date'] = session.metadata['session_date']
            metadata['session_id'] = session.metadata['id']
            metadata['session_num'] = session.metadata['session_num']
            metadata['inventory_num'] = session.metadata['inventory_num']
            metadata['president'] = session.metadata['president']
        super().__init__(metadata=metadata, coords=coords, lines=lines, columns=columns)
        self.type = "resolution"
        self.metadata['resolution_type'] = 'ordinaris'
        self.scan_versions = scan_versions if scan_versions else []
        self.opening = None
        self.decision = None
        # proposition type is one of missive, requeste, rapport, ...
        self.proposition_type: Union[None, str] = None
        self.proposer: Union[None, str, List[str]] = None
        self.session_date: Union[RepublicDate, None] = None
        self.paragraphs: List[ResolutionParagraph] = paragraphs if paragraphs else []
        if paragraphs and not columns:
            self.add_columns_from_paragraphs()
        self.column_ids: Set[str] = set()
        if len(self.paragraphs) == 0:
            self.metadata['num_paragraphs'] = 0
            self.metadata['num_columns'] = 0
            self.metadata['num_lines'] = 0
            self.metadata['num_words'] = 0
        # if 'evidence' in self.metadata and self.metadata['evidence']:
        #     self.evidence = parse_phrase_matches(metadata['evidence'])
        #     self.metadata['evidence'] = self.evidence
        self.evidence: List[PhraseMatch] = []
        if evidence:
            self.evidence = parse_phrase_matches(evidence)
            if self.metadata['proposition_type']:
                self.proposition_type = self.metadata['proposition_type']
            else:
                self.proposition_type = get_proposition_type_from_evidence(self.evidence)
                self.metadata['proposition_type'] = self.proposition_type

    def __repr__(self):
        return f"Resolution({json.dumps(self.json(), indent=4)}"

    def add_columns_from_paragraphs(self):
        for paragraph in self.paragraphs:
            for column in paragraph.columns:
                self.columns.append(column)

    def add_paragraph(self, paragraph: ResolutionParagraph, matches: List[PhraseMatch] = None):
        paragraph.metadata['paragraph_index'] = len(self.paragraphs)
        self.paragraphs.append(paragraph)
        self.column_ids = self.column_ids.union([column['metadata']['id'] for column in paragraph.columns])
        self.columns += paragraph.columns
        self.metadata['num_paragraphs'] = len(self.paragraphs)
        self.metadata['num_columns'] = len(self.column_ids)
        self.metadata['num_lines'] += paragraph.metadata['num_lines']
        self.metadata['num_words'] += paragraph.metadata['num_words']
        self.evidence += matches

    def json(self):
        json_data = {
            'metadata': self.metadata,
            'paragraphs': [paragraph.json(include_columns=False) for paragraph in self.paragraphs],
            'evidence': [match.json() for match in self.evidence],
            'columns': self.columns
        }
        return json_data


def resolution_from_json(resolution_json: dict) -> Resolution:
    paragraphs = []
    for paragraph_json in resolution_json['paragraphs']:
        if 'columns' not in paragraph_json:
            paragraph_json['columns'] = []
        if 'column_ids' not in paragraph_json:
            paragraph_json['column_ids'] = []
        paragraph = ResolutionParagraph(metadata=paragraph_json['metadata'], columns=paragraph_json['columns'],
                                        column_ids=paragraph_json['column_ids'],
                                        scan_versions=paragraph_json['scan_versions'],
                                        text=paragraph_json['text'],
                                        line_ranges=paragraph_json['line_ranges'])
        paragraphs.append(paragraph)
    if 'columns' not in resolution_json:
        resolution_json['columns'] = []
    column_map = defaultdict(list)
    for column in resolution_json['columns']:
        column_map[column['metadata']['id']].append(column)
    return Resolution(metadata=resolution_json['metadata'], paragraphs=paragraphs,
                      evidence=resolution_json['evidence'], columns=resolution_json['columns'])


def stream_ordered_lines(resolution_doc: ResolutionDoc, word_freq_counter: Counter = None):
    # if len(columns) > 2:
    #     print("\n\nWEIRD NUMBER OF COLUMNS:", len(columns), 'in doc', self.metadata['id'])
    for column in resolution_doc.columns:
        check_special_column_for_bleed_through(column, word_freq_counter)
    columns = sort_resolution_columns(resolution_doc.columns)
    for column_index, column in columns:
        # print('\ncolumn:', column_index)
        sorted_text_regions = sort_resolution_text_regions(column['textregions'])
        for ti, text_region in enumerate(sorted_text_regions):
            # print(text_region['coords'])
            for line in order_lines(text_region["lines"]):
                line["metadata"]["inventory_num"] = resolution_doc.metadata["inventory_num"]
                line["metadata"]["doc_id"] = resolution_doc.metadata["id"]
                line["metadata"]["column_index"] = column_index
                line["metadata"]["column_id"] = column['metadata']['id']
                line["metadata"]["textregion_index"] = ti
                if 'is_bleed_through' not in line['metadata']:
                    line['metadata']['is_bleed_through'] = False
                if 'page_column_id' in column['metadata']:
                    line['metadata']['page_column_id'] = column['metadata']['page_column_id']
                yield line


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


def get_session_resolutions(session: Session, opening_searcher: FuzzyPhraseSearcher,
                            verb_searcher: FuzzyPhraseSearcher) -> Generator[Resolution, None, None]:
    resolution = None
    resolution_number = 0
    attendance_list = None
    generate_id = running_id_generator(session.metadata['id'], '-resolution-')
    session_offset = 0
    for paragraph in session.get_paragraphs():
        # print(paragraph.text, '\n')
        opening_matches = opening_searcher.find_matches({'text': paragraph.text, 'id': paragraph.metadata['id']})
        verb_matches = verb_searcher.find_matches({'text': paragraph.text, 'id': paragraph.metadata['id']})
        for match in opening_matches + verb_matches:
            match.text_id = paragraph.metadata['id']
            # print('\t', match.offset, '\t', match.string)
        if len(opening_matches) > 0:
            if attendance_list:
                yield attendance_list
                attendance_list = None
            resolution_number += 1
            if resolution:
                yield resolution
            metadata = get_base_metadata(session, generate_id(), 'resolution')
            resolution = Resolution(metadata=metadata, session=session)
            # print('\tCreating new resolution with number:', resolution_number, resolution.metadata['id'])
        if resolution:
            resolution.add_paragraph(paragraph, matches=opening_matches + verb_matches)
        elif attendance_list:
            attendance_list.add_paragraph(paragraph, matches=[])
        else:
            metadata = get_base_metadata(session, session.metadata['id'] + '-attendance_list',
                                         'attendance_list')
            attendance_list = AttendanceList(metadata=metadata, session=session)
            # print('\tCreating new attedance list with number:', 1, attendance_list.metadata['id'])
            attendance_list.add_paragraph(paragraph, matches=[])
        # print('start offset:', session_offset, '\tend offset:', session_offset + len(paragraph.text))
        session_offset += len(paragraph.text)
    if resolution:
        yield resolution


def running_id_generator(base_id: str, suffix: str, count: int = 0):
    """Returns an ID generator based on running numbers."""
    def generate_id():
        nonlocal count
        count += 1
        return f'{base_id}{suffix}{count}'

    return generate_id


def get_base_metadata(source_doc: ResolutionDoc, doc_id: str, doc_type: str) -> Dict[str, Union[str, int]]:
    """Return a dictionary with basic metadata for a structure document."""
    return {
        'inventory_num': source_doc.metadata['inventory_num'],
        'source_id': source_doc.metadata['id'],
        'type': doc_type,
        'id': doc_id
    }


def get_paragraphs(doc: ResolutionDoc, prev_line: Union[None, dict] = None,
                   use_indent: bool = False, use_vertical_space: bool = True,
                   word_freq_counter: Counter = None) -> List[ResolutionParagraph]:
    if use_indent:
        return get_paragraphs_with_indent(doc, prev_line=prev_line, word_freq_counter=word_freq_counter)
    elif use_vertical_space:
        return get_paragraphs_with_vertical_space(doc, prev_line=prev_line, word_freq_counter=word_freq_counter)


def get_paragraphs_with_indent(doc: ResolutionDoc, prev_line: Union[None, dict] = None,
                               word_freq_counter: Counter = None) -> List[ResolutionParagraph]:
    paragraphs: List[ResolutionParagraph] = []
    generate_paragraph_id = running_id_generator(base_id=doc.metadata['id'], suffix='-para-')
    para_lines = []
    doc_text_offset = 0
    lines = [line for line in doc.stream_ordered_lines(word_freq_counter=word_freq_counter)]
    for li, line in enumerate(lines):
        next_line = lines[li + 1] if len(lines) > (li + 1) else None
        if prev_line and same_column(line, prev_line):
            if same_height(line, prev_line):
                # print("SAME HEIGHT", prev_line['text'], '\t', line['text'])
                pass
            elif line["coords"]["left"] > prev_line["coords"]["left"] + 20:
                # this line is left indented w.r.t. the previous line
                # so is the start of a new paragraph
                if len(para_lines) > 0:
                    metadata = get_base_metadata(doc, generate_paragraph_id(), "resolution_paragraph")
                    paragraph = ResolutionParagraph(lines=para_lines, metadata=metadata,
                                                    word_freq_counter=word_freq_counter)
                    paragraph.metadata['start_offset'] = doc_text_offset
                    doc_text_offset += len(paragraph.text)
                    paragraphs.append(paragraph)
                para_lines = []
            elif line['coords']['left'] - prev_line['coords']['left'] < 20:
                if line['coords']['right'] > prev_line['coords']['right'] + 40:
                    # this line starts at the same horizontal level as the previous line
                    # but the previous line ends early, so is the end of a paragraph.
                    if len(para_lines) > 0:
                        metadata = get_base_metadata(doc, generate_paragraph_id(), "resolution_paragraph")
                        paragraph = ResolutionParagraph(lines=para_lines, metadata=metadata,
                                                        word_freq_counter=word_freq_counter)
                        paragraph.metadata['start_offset'] = doc_text_offset
                        doc_text_offset += len(paragraph.text)
                        paragraphs.append(paragraph)
                    para_lines = []
        elif next_line and same_column(line, next_line):
            if line["coords"]["left"] > next_line["coords"]["left"] + 20:
                if len(para_lines) > 0:
                    metadata = get_base_metadata(doc, generate_paragraph_id(), "resolution_paragraph")
                    paragraph = ResolutionParagraph(lines=para_lines, metadata=metadata,
                                                    word_freq_counter=word_freq_counter)
                    paragraph.metadata['start_offset'] = doc_text_offset
                    doc_text_offset += len(paragraph.text)
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
        metadata = get_base_metadata(doc, generate_paragraph_id(), "resolution_paragraph")
        paragraph = ResolutionParagraph(lines=para_lines, metadata=metadata,
                                        word_freq_counter=word_freq_counter)
        paragraph.metadata['start_offset'] = doc_text_offset
        doc_text_offset += len(paragraph.text)
        paragraphs.append(paragraph)
    return paragraphs


def get_paragraphs_with_vertical_space(doc: ResolutionDoc, prev_line: Union[None, dict] = None,
                                       word_freq_counter: Counter = None) -> List[ResolutionParagraph]:
    para_lines = []
    paragraphs = []
    doc_text_offset = 0
    generate_paragraph_id = running_id_generator(base_id=doc.metadata['id'], suffix='-para-')
    lines = [line for line in doc.stream_ordered_lines(word_freq_counter=word_freq_counter)]
    for li, line in enumerate(lines):
        if prev_line and line["coords"]["top"] - prev_line["coords"]["top"] > 65:
            if len(para_lines) > 0:
                metadata = get_base_metadata(doc, generate_paragraph_id(), "resolution_paragraph")
                paragraph = ResolutionParagraph(lines=para_lines, metadata=metadata,
                                                word_freq_counter=word_freq_counter)
                paragraph.metadata['start_offset'] = doc_text_offset
                doc_text_offset += len(paragraph.text)
                paragraphs.append(paragraph)
            para_lines = []
        para_lines.append(line)
        if not line['text'] or len(line['text']) == 1:
            continue
        if prev_line and same_height(prev_line, line):
            continue
        prev_line = line
    if len(para_lines) > 0:
        metadata = get_base_metadata(doc, generate_paragraph_id(), "resolution_paragraph")
        paragraph = ResolutionParagraph(lines=para_lines, metadata=metadata,
                                        word_freq_counter=word_freq_counter)
        paragraph.metadata['start_offset'] = doc_text_offset
        doc_text_offset += len(paragraph.text)
        paragraphs.append(paragraph)
    return paragraphs


def get_session_scans_version(session: Session) -> List:
    scans_version = {}
    for line in session.lines:
        scans_version[line['metadata']['doc_id']] = copy.copy(line['metadata']['scan_version'])
        scans_version[line['metadata']['doc_id']]['doc_id'] = line['metadata']['doc_id']
    # print("session scans versions:", scans_version)
    return list(scans_version.values())


def make_paragraph_line_annotations(paragraph: ResolutionParagraph, doc_text_offset: int,
                                    line_index: Dict[str, dict]) -> List[Dict[str, any]]:
    annotations = []
    for line_range in paragraph.line_ranges:
        para_offset = line_range['start']
        para_end = line_range['end']
        line_anno = line_index[line_range['line_id']]
        line_anno['type'] = 'line'
        line_anno = {
            'id': line_range['line_id'],
            'type': 'line',
            'start_offset': doc_text_offset + para_offset,
            'end_offset': doc_text_offset + para_end,
            "metadata": {
                'parent_id': paragraph.metadata['id'],
                'scan_id': line_index[line_range['line_id']]['metadata']['scan_id']
            },
            "coords": line_index[line_range['line_id']]["coords"]
        }
        annotations.append(line_anno)
    return annotations


def make_paragraph_annotation(paragraph: ResolutionParagraph, doc_text_offset: int,
                              parent_id: str) -> Dict[str, any]:
    return {
        'id': paragraph.id,
        'type': 'paragraph',
        'metadata': {
            'parent_id': parent_id,
            'num_lines': len(paragraph.line_ranges),
            'num_words': len(re.split(r'\W+', paragraph.text))
        },
        'start_offset': doc_text_offset,
        'end_offset': doc_text_offset + len(paragraph.text),
    }


def make_resolution_annotation(resolution: Resolution, doc_text_offset: int, parent_id: str):
    resolution_anno = {
        'id': resolution.metadata['id'],
        'type': resolution.type,
        'metadata': resolution.metadata,
        'paragraphs': [],
        'start_offset': doc_text_offset
    }
    resolution_anno['metadata']['parent_id'] = parent_id
    return resolution_anno


def make_session_text_version(session: Session):
    session.scan_versions = get_session_scans_version(session)
    annotations = []
    line_index = {
        line['metadata']['id']: line for line in session.stream_ordered_lines()
    }
    session_text_offset = 0
    session_text = ''
    opening_searcher, verb_searcher = configure_resolution_searchers()
    resolutions = get_session_resolutions(session, opening_searcher, verb_searcher)
    for resolution in resolutions:
        resolution_anno = make_resolution_annotation(resolution, session_text_offset,
                                                     session.metadata['id'])
        annotations.append(resolution_anno)
        for paragraph in resolution.paragraphs:
            para_annotation = make_paragraph_annotation(paragraph, session_text_offset, resolution.metadata['id'])
            annotations.append(para_annotation)
            annotations += make_paragraph_line_annotations(paragraph, session_text_offset, line_index)
            session_text_offset += len(paragraph.text)
            session_text += paragraph.text
            resolution_anno['paragraphs'].append(paragraph.metadata['id'])
        resolution_anno['end_offset'] = session_text_offset
    annotations += get_scan_annotations(annotations, session)
    session_text_doc = {
        'metadata': session.metadata,
        'text': session_text,
        "annotations": sort_annotations(annotations)
    }
    session_text_doc['metadata']['scan_versions'] = session.scan_versions
    return session_text_doc


def get_scan_annotations(annotations: List[Dict[str, any]],
                         session: Session) -> List[Dict[str, any]]:
    scan_annotations = []
    line_annotations = [anno for anno in annotations if anno['type'] == 'line']
    scan_lines = defaultdict(list)
    for line_anno in line_annotations:
        scan_lines[line_anno['metadata']['scan_id']].append(line_anno)
    for scan_id in scan_lines:
        urls = make_scan_urls(inventory_num=session.metadata['inventory_num'], scan_id=scan_id)
        scan_anno = {
            'id': scan_id,
            'type': 'scan',
            'start_offset': scan_lines[scan_id][0]['start_offset'],
            'end_offset': scan_lines[scan_id][-1]['end_offset'],
            'metadata': {
                'iiif_url': urls['iiif_url']
            }
        }
        scan_annotations.append(scan_anno)
    return scan_annotations


def sort_annotations(annotations: List[Dict[str, any]]) -> List[Dict[str, any]]:
    order = {
        'scan': 0,
        'attendance_list': 1,
        'resolution': 1,
        'paragraph': 2,
        'line': 3,
        'attendant': 4
    }
    return sorted(annotations, key = lambda x: (x['start_offset'], order[x['type']]))


def configure_resolution_searchers():
    opening_searcher_config = {
        'filter_distractors': True,
        'include_variants': True,
        'max_length_variance': 3
    }
    opening_searcher = FuzzyPhraseSearcher(opening_searcher_config)
    opening_phrase_model = PhraseModel(model=rpm.proposition_opening_phrases)
    opening_searcher.index_phrase_model(opening_phrase_model)
    verb_searcher_config = {
        'max_length_variance': 1
    }
    verb_searcher = FuzzyPhraseSearcher(verb_searcher_config)
    verb_phrase_model = PhraseModel(model=rpm.proposition_verbs)
    verb_searcher.index_phrase_model(verb_phrase_model)
    return opening_searcher, verb_searcher
