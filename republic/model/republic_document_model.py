from collections import Counter
from typing import Dict, Generator, List, Set, Union
import copy
import re
import json

from fuzzy_search.fuzzy_match import PhraseMatch, Phrase
from fuzzy_search.fuzzy_phrase_searcher import FuzzyPhraseSearcher, PhraseModel
import republic.model.physical_document_model as pdm
from republic.model.physical_document_model import LogicalStructureDoc, PageXMLTextLine, PageXMLWord
from republic.model.physical_document_model import PageXMLTextRegion
from republic.model.physical_document_model import same_column, json_to_pagexml_text_region
from republic.model.physical_document_model import json_to_pagexml_line
from republic.model.physical_document_model import line_ends_with_word_break
from republic.model.republic_date import RepublicDate
from republic.helper.metadata_helper import make_scan_urls, make_iiif_region_url
import republic.model.resolution_phrase_model as rpm


class RepublicDoc(LogicalStructureDoc):

    def __init__(self, doc_id: str = None, doc_type: str = None, metadata: Union[None, Dict] = None,
                 lines: List[PageXMLTextLine] = None,
                 text_regions: List[PageXMLTextRegion] = None):
        super().__init__(doc_id=doc_id, doc_type='republic_doc', metadata=metadata,
                         lines=lines, text_regions=text_regions)
        self.main_type = "republic_doc"
        if doc_type:
            self.add_type(doc_type)
        self.add_text_region_iiif_url()

    def add_text_region_iiif_url(self):
        """Add text_region iiif url based on the scan it is part of."""
        for text_region in self.text_regions:
            scan_id = text_region.metadata['scan_id']
            # Example scan_id: NL-HaNA_1.01.02_3783_0051
            inventory_num = int(scan_id.replace('NL-HaNA_1.01.02_', '').split('_')[0])
            urls = make_scan_urls(inventory_num=inventory_num, scan_id=scan_id)
            text_region.metadata['iiif_url'] = make_iiif_region_url(urls['jpg_url'], text_region.coords.box,
                                                                    add_margin=100)

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


class RepublicParagraph(RepublicDoc):

    def __init__(self, doc_id: str = None, doc_type: str = None,
                 lines: List[PageXMLTextLine] = None, text_regions: List[PageXMLTextRegion] = None,
                 metadata: dict = None,
                 scan_versions: List[Dict[str, any]] = None, text: str = None, text_region_ids: List[str] = None,
                 line_ranges: List[Dict[str, any]] = None, word_freq_counter: Counter = None):
        super().__init__(doc_id=doc_id, doc_type='resolution_paragraph', lines=lines,
                         text_regions=text_regions, metadata=metadata)
        if not self.id and 'id' in self.metadata:
            self.id = self.metadata['id']
        self.line_ranges = line_ranges if line_ranges else []
        self.text = text if text else ""
        self.text_region_ids: Set[str] = set()
        if doc_type:
            self.add_type(doc_type)
        if text_region_ids:
            self.text_region_ids = set(text_region_ids)
        else:
            self.text_region_ids = {text_region.metadata['id'] for text_region in self.text_regions}
        if not text:
            self.set_text(word_freq_counter)
        self.metadata["type"] = "republic_paragraph"
        self.scan_versions = scan_versions
        self.evidence: List[PhraseMatch] = []

    def __repr__(self):
        return f"{self.__class__.__name__}(lines={[line.metadata['id'] for line in self.lines]}, text={self.text})"

    @property
    def json(self, include_text_regions: bool = True):
        json_data = {
            "id": self.id,
            "type": self.type,
            "metadata": self.metadata,
            "text_region_ids": list(self.text_region_ids),
            "text": self.text,
            "line_ranges": self.line_ranges,
            "scan_versions": self.scan_versions
        }
        if include_text_regions:
            json_data["text_regions"] = self.text_regions
        return json_data

    def set_text(self, word_freq_counter: Counter = None):
        self.line_ranges = []
        for li, line in enumerate(self.lines):
            if line.text is None:
                continue
            elif "is_bleed_through" in line.metadata and line.metadata["is_bleed_through"]:
                continue
            elif len(line.text) == 1:
                continue
            next_line = self.lines[li + 1] if len(self.lines) > li + 1 else None
            if len(line.text) > 2 and line.text[-2] == "-" and not line.text[-1].isalpha():
                line_text = line.text[:-2]
            elif line.text[-1] == "-":
                line_text = line.text[:-1]
            elif line_ends_with_word_break(line, next_line, word_freq_counter):
                line_text = re.split(r"\W+$", line.text)[0]
            elif (li + 1) == len(self.lines):
                line_text = line.text
            else:
                line_text = line.text + " "
            line_range = {
                "start": len(self.text), "end": len(self.text + line_text),
                "line_id": line.id
            }
            self.text += line_text
            self.line_ranges.append(line_range)

    def get_match_lines(self, match: PhraseMatch) -> List[PageXMLTextLine]:
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


class ResolutionElementDoc(RepublicDoc):

    def __init__(self,
                 doc_id: str = None, doc_type: str = None,
                 metadata: dict = None, scan_versions: dict = None,
                 lines: Union[None, List[Dict[str, Union[str, int, Dict[str, int]]]]] = None,
                 text_regions: Union[None, List[Dict[str, Union[dict, list]]]] = None,
                 paragraphs: List[RepublicParagraph] = None,
                 evidence: List[PhraseMatch] = None):
        """An attendance list has textual content."""
        if not metadata:
            metadata = {}
        super().__init__(doc_id=doc_id, doc_type='resolution_element', metadata=metadata,
                         lines=lines, text_regions=text_regions)
        if doc_type:
            self.add_type(doc_type)
        self.scan_versions = scan_versions if scan_versions else []
        self.session_date: Union[RepublicDate, None] = None
        self.paragraphs: List[RepublicParagraph] = paragraphs if paragraphs else []
        self.text_region_ids: Set[str] = set()
        self.evidence: List[PhraseMatch] = []
        if evidence:
            for match in evidence:
                if not isinstance(match, PhraseMatch):
                    print(match)
                    raise TypeError('Evidence must be a list of PhraseMatch objects')
            self.evidence = evidence

    def __repr__(self):
        return f"ResolutionElementDoc({json.dumps(self.json, indent=4)}"

    def get_text_regions_from_paragraphs(self):
        return [text_region for paragraph in self.paragraphs for text_region in paragraph.text_regions]

    def add_paragraph(self, paragraph: RepublicParagraph, matches: List[PhraseMatch] = None):
        paragraph.metadata['paragraph_index'] = len(self.paragraphs)
        self.paragraphs.append(paragraph)
        self.text_region_ids = self.text_region_ids.union([text_region.metadata['id']
                                                           for text_region in paragraph.text_regions])
        self.evidence += matches

    @property
    def stats(self) -> Dict[str, int]:
        stats = super().stats
        if self.paragraphs:
            for paragraph in self.paragraphs:
                para_stats = paragraph.stats
                for field in para_stats:
                    stats[field] += para_stats[field]
            stats['paragraphs'] = len(self.paragraphs)
        return stats

    @property
    def json(self):
        json_doc = {
            'id': self.id,
            'type': self.type,
            'metadata': self.metadata,
            'evidence': [match.json() for match in self.evidence],
            'stats': self.stats
        }
        if self.paragraphs:
            json_doc['paragraphs'] = [paragraph.json for paragraph in self.paragraphs]
        if self.text_regions:
            json_doc['text_regions'] = [text_region.json for text_region in self.text_regions]
        if self.lines:
            json_doc['lines'] = [line.json for line in self.lines]
        if self.scan_versions:
            json_doc["scan_versions"] = self.scan_versions
        return json_doc


class Session(ResolutionElementDoc):

    def __init__(self, doc_id: str = None, doc_type: str = None, metadata: Dict = None,
                 paragraphs: List[RepublicParagraph] = None, text_regions: List[PageXMLTextRegion] = None,
                 lines: List[PageXMLTextLine] = None,
                 scan_versions: List[dict] = None, evidence: List[PhraseMatch] = None, **kwargs):
        """A meeting session occurs on a specific day, with a president and attendants,
        and has textual content in the form of
         lines or possibly as Resolution objects."""
        super().__init__(doc_id=doc_id, doc_type='session', metadata=metadata, paragraphs=paragraphs,
                         text_regions=text_regions, lines=lines, evidence=evidence, **kwargs)
        self.session_date = RepublicDate(date_string=metadata['session_date'])
        self.main_type = "session"
        if doc_type:
            self.add_type(doc_type)
        self.date = self.session_date
        if not doc_id:
            self.id = f"session-{self.session_date.as_date_string()}-num-1"
            self.metadata['id'] = self.id
        self.president: Union[str, None] = None
        self.attendance: List[str] = []
        self.scan_versions: Union[None, List[dict]] = scan_versions
        self.resolutions = []

    def __repr__(self):
        return f"Session({json.dumps(self.json, indent=4)}"

    def add_page_text_region_metadata(self, page_text_region_metadata: Dict[str, dict]) -> None:
        for ci, text_region in enumerate(self.text_regions):
            page_col_metadata = page_text_region_metadata[text_region.metadata['page_text_region_id']]
            for key in page_col_metadata:
                if key == 'id':
                    text_region.metadata['page_text_region_id'] = page_col_metadata[key]
                elif key in ['num_words', 'num_lines', 'iiif_url']:
                    continue
                else:
                    text_region.metadata[key] = page_col_metadata[key]

    def get_metadata(self) -> Dict[str, Union[str, List[str]]]:
        """Return the metadata of the session, including date, president and attendants."""
        return self.metadata

    @property
    def json(self) -> dict:
        """Return a JSON presentation of the session."""
        json_doc = super().json
        if self.resolutions:
            json_doc['resolutions'] = [resolution.json for resolution in self.resolutions]
        return json_doc

    @property
    def stats(self) -> Dict[str, int]:
        stats = super().stats
        if self.resolutions:
            for resolution in self.resolutions:
                resolution_stats = resolution.stats
                for field in resolution_stats:
                    stats[field] += resolution_stats[field]
            stats['resolutions'] = len(self.resolutions)
        return stats

    def get_paragraphs(self, use_indent=False,
                       use_vertical_space=True) -> Generator[RepublicParagraph, None, None]:
        if self.paragraphs:
            for paragraph in self.paragraphs:
                yield paragraph
        else:
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
    if 'metadata' in match:
        match_phrase.metadata = match['metadata']
    match_variant = Phrase(match['variant'])
    if 'text_id' not in match:
        match['text_id'] = None
    if 'match_scores' not in match:
        match['match_scores'] = None
    try:
        match_object = PhraseMatch(match_phrase, match_variant, match['string'],
                                   match_offset=match['offset'], text_id=match['text_id'],
                                   match_scores=match['match_scores'], match_label=match['label'])
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


class AttendanceList(ResolutionElementDoc):

    def __init__(self,
                 doc_id: str = None, doc_type: str = None,
                 metadata: dict = None, scan_versions: dict = None,
                 lines: List[PageXMLTextLine] = None,
                 text_regions: List[PageXMLTextRegion] = None,
                 paragraphs: List[RepublicParagraph] = None,
                 evidence: Union[List[dict], List[PhraseMatch]] = None):
        """An attendance list has textual content."""
        if not metadata:
            metadata = {}
        metadata['type'] = 'attendance_list'
        super().__init__(doc_id=doc_id, doc_type='attendance_list', metadata=metadata,
                         paragraphs=paragraphs, lines=lines, text_regions=text_regions,
                         evidence=evidence)
        if doc_type:
            self.add_type(doc_type)
        self.scan_versions = scan_versions if scan_versions else []
        self.session_date: Union[RepublicDate, None] = None
        self.text_region_ids: Set[str] = set()

    def __repr__(self):
        return f"AttendanceList({json.dumps(self.json, indent=4)}"


class Resolution(ResolutionElementDoc):

    def __init__(self,
                 doc_id: str = None, doc_type: str = None,
                 metadata: dict = None,
                 scan_versions: dict = None,
                 lines: List[PageXMLTextLine] = None,
                 text_regions: List[PageXMLTextRegion] = None,
                 paragraphs: List[RepublicParagraph] = None,
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
        super().__init__(doc_id=doc_id, doc_type='resolution', metadata=metadata,
                         paragraphs=paragraphs, lines=lines, text_regions=text_regions,
                         evidence=evidence)
        if doc_type:
            self.add_type(doc_type)
        self.metadata['resolution_type'] = 'ordinaris'
        self.scan_versions = scan_versions if scan_versions else []
        self.opening = None
        self.decision = None
        # proposition type is one of missive, requeste, rapport, ...
        self.proposition_type: Union[None, str] = None
        self.proposer: Union[None, str, List[str]] = None
        self.session_date: Union[RepublicDate, None] = None
        self.text_region_ids: Set[str] = set()
        if self.evidence:
            if self.metadata['proposition_type']:
                self.proposition_type = self.metadata['proposition_type']
            else:
                self.proposition_type = get_proposition_type_from_evidence(self.evidence)
                self.metadata['proposition_type'] = self.proposition_type

    def __repr__(self):
        return f"Resolution({json.dumps(self.json, indent=4)}"


def json_to_republic_doc(json_doc: dict) -> RepublicDoc:
    if 'session' in json_doc['type']:
        return json_to_republic_session(json_doc)
    if 'resolution' in json_doc['type']:
        return json_to_republic_resolution(json_doc)
    if 'resolution_paragraph' in json_doc['type']:
        return json_to_republic_resolution_paragraph(json_doc)
    if 'attendance_list' in json_doc['type']:
        return json_to_republic_attendance_list(json_doc)


def json_to_republic_attendance_list(attendance_json: dict) -> AttendanceList:
    paragraphs = []
    for paragraph_json in attendance_json['paragraphs']:
        paragraph = json_to_republic_resolution_paragraph(paragraph_json)
        paragraphs.append(paragraph)
    text_regions, lines, evidence = json_to_physical_elements(attendance_json)
    scan_versions = attendance_json["scan_versions"] if "scan_versions" in attendance_json else None
    return AttendanceList(doc_id=attendance_json['id'], doc_type=attendance_json['type'],
                          metadata=attendance_json['metadata'],
                          paragraphs=paragraphs, text_regions=text_regions,
                          lines=lines,
                          scan_versions=scan_versions)


def json_to_republic_resolution_paragraph(paragraph_json: dict) -> RepublicParagraph:
    if 'text_regions' not in paragraph_json:
        paragraph_json['text_regions'] = []
    if 'text_region_ids' not in paragraph_json:
        paragraph_json['text_region_ids'] = []
    text_regions, lines, evidence = json_to_physical_elements(paragraph_json)
    return RepublicParagraph(doc_id=paragraph_json['id'], doc_type=paragraph_json['type'],
                             metadata=paragraph_json['metadata'],
                             text_regions=text_regions,
                             text_region_ids=paragraph_json['text_region_ids'],
                             scan_versions=paragraph_json['scan_versions'],
                             text=paragraph_json['text'],
                             line_ranges=paragraph_json['line_ranges'])


def json_to_republic_resolution(resolution_json: dict) -> Resolution:
    paragraphs = []
    for paragraph_json in resolution_json['paragraphs']:
        paragraph = json_to_republic_resolution_paragraph(paragraph_json)
        paragraphs.append(paragraph)
    text_regions, lines, evidence = json_to_physical_elements(resolution_json)
    return Resolution(doc_id=resolution_json['id'], doc_type=resolution_json['type'],
                      metadata=resolution_json['metadata'], evidence=evidence,
                      paragraphs=paragraphs, text_regions=text_regions, lines=lines)


def json_to_physical_elements(republic_json: dict):
    text_regions = republic_json['text_regions'] if 'text_regions' in republic_json else []
    text_regions = [json_to_pagexml_text_region(tr_json) for tr_json in text_regions]
    lines = republic_json['lines'] if 'lines' in republic_json else []
    lines = [json_to_pagexml_line(line_json) for line_json in lines]
    evidence = republic_json['evidence'] if 'evidence' in republic_json else []
    try:
        evidence = parse_phrase_matches(evidence)
    except TypeError:
        print(evidence)
        raise
    return text_regions, lines, evidence


def json_to_republic_session(session_json: dict) -> Session:
    paragraphs = []
    if 'paragraph' in session_json:
        for paragraph_json in session_json['paragraphs']:
            paragraph = json_to_republic_resolution_paragraph(paragraph_json)
            paragraphs.append(paragraph)
    text_regions, lines, evidence = json_to_physical_elements(session_json)
    return Session(doc_id=session_json['id'], doc_type=session_json['type'],
                   metadata=session_json['metadata'], evidence=evidence,
                   paragraphs=paragraphs, text_regions=text_regions, lines=lines)


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


def get_session_resolutions(session: Session, opening_searcher: FuzzyPhraseSearcher,
                            verb_searcher: FuzzyPhraseSearcher) -> Generator[Resolution, None, None]:
    resolution = None
    resolution_number = 0
    attendance_list = None
    generate_id = running_id_generator(session.metadata['id'], '-resolution-')
    session_offset = 0
    print('fuzzy searcher version:', opening_searcher.__version__)
    for paragraph in session.get_paragraphs():
        # print('get_session_resolutions - paragraph:\n', paragraph.text, '\n')
        opening_matches = opening_searcher.find_matches({'text': paragraph.text, 'id': paragraph.metadata['id']})
        verb_matches = verb_searcher.find_matches({'text': paragraph.text, 'id': paragraph.metadata['id']})
        for match in opening_matches + verb_matches:
            match.text_id = paragraph.metadata['id']
            # print('\t', match.offset, '\t', match.string, '\t', match.variant.phrase_string)
        if len(opening_matches) > 0:
            if attendance_list:
                yield attendance_list
                attendance_list = None
            resolution_number += 1
            if resolution:
                yield resolution
            metadata = get_base_metadata(session, generate_id(), 'resolution')
            metadata['session_date'] = session.metadata['session_date']
            metadata['session_id'] = session.metadata['id']
            metadata['session_num'] = session.metadata['session_num']
            metadata['inventory_num'] = session.metadata['inventory_num']
            metadata['president'] = session.metadata['president']
            metadata['session_year'] = session.metadata['session_year']
            metadata['session_month'] = session.metadata['session_month']
            metadata['session_day'] = session.metadata['session_day']
            metadata['session_weekday'] = session.metadata['session_weekday']
            resolution = Resolution(doc_id=metadata['id'], metadata=metadata)
            # print('\tCreating new resolution with number:', resolution_number, resolution.metadata['id'])
        if resolution:
            resolution.add_paragraph(paragraph, matches=opening_matches + verb_matches)
        elif attendance_list:
            attendance_list.add_paragraph(paragraph, matches=[])
        else:
            metadata = get_base_metadata(session, session.metadata['id'] + '-attendance_list',
                                         'attendance_list')
            metadata['session_date'] = session.metadata['session_date']
            metadata['session_id'] = session.metadata['id']
            metadata['session_num'] = session.metadata['session_num']
            metadata['inventory_num'] = session.metadata['inventory_num']
            metadata['president'] = session.metadata['president']
            attendance_list = AttendanceList(doc_id=metadata['id'], metadata=metadata)
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


def get_base_metadata(source_doc: RepublicDoc, doc_id: str, doc_type: str) -> Dict[str, Union[str, int]]:
    """Return a dictionary with basic metadata for a structure document."""
    return {
        'inventory_num': source_doc.metadata['inventory_num'],
        'source_id': source_doc.metadata['id'],
        'type': doc_type,
        'id': doc_id
    }


def get_paragraphs(doc: RepublicDoc, prev_line: Union[None, dict] = None,
                   use_indent: bool = False, use_vertical_space: bool = True,
                   word_freq_counter: Counter = None) -> List[RepublicParagraph]:
    if use_indent:
        return get_paragraphs_with_indent(doc, prev_line=prev_line, word_freq_counter=word_freq_counter)
    elif use_vertical_space:
        return get_paragraphs_with_vertical_space(doc, prev_line=prev_line, word_freq_counter=word_freq_counter)


def get_paragraphs_with_indent(doc: RepublicDoc, prev_line: Union[None, PageXMLTextLine] = None,
                               word_freq_counter: Counter = None) -> List[RepublicParagraph]:
    paragraphs: List[RepublicParagraph] = []
    generate_paragraph_id = running_id_generator(base_id=doc.metadata['id'], suffix='-para-')
    para_lines = []
    doc_text_offset = 0
    lines = [line for line in doc.get_lines()]
    for li, line in enumerate(lines):
        next_line = lines[li + 1] if len(lines) > (li + 1) else None
        if prev_line and same_column(line, prev_line):
            if line.is_next_to(prev_line):
                # print("SAME HEIGHT", prev_line['text'], '\t', line['text'])
                pass
            elif line.coords.left > prev_line.coords.left + 20:
                # this line is left indented w.r.t. the previous line
                # so is the start of a new paragraph
                if len(para_lines) > 0:
                    metadata = get_base_metadata(doc, generate_paragraph_id(), "resolution_paragraph")
                    paragraph = RepublicParagraph(lines=para_lines, metadata=metadata,
                                                  word_freq_counter=word_freq_counter)
                    paragraph.metadata["start_offset"] = doc_text_offset
                    doc_text_offset += len(paragraph.text)
                    paragraphs.append(paragraph)
                para_lines = []
            elif line.coords.left - prev_line.coords.left < 20:
                if line.coords.right > prev_line.coords.right + 40:
                    # this line starts at the same horizontal level as the previous line
                    # but the previous line ends early, so is the end of a paragraph.
                    if len(para_lines) > 0:
                        metadata = get_base_metadata(doc, generate_paragraph_id(), "resolution_paragraph")
                        paragraph = RepublicParagraph(lines=para_lines, metadata=metadata,
                                                      word_freq_counter=word_freq_counter)
                        paragraph.metadata["start_offset"] = doc_text_offset
                        doc_text_offset += len(paragraph.text)
                        paragraphs.append(paragraph)
                    para_lines = []
        elif next_line and same_column(line, next_line):
            if line.coords.left > next_line.coords.left + 20:
                if len(para_lines) > 0:
                    metadata = get_base_metadata(doc, generate_paragraph_id(), "resolution_paragraph")
                    paragraph = RepublicParagraph(lines=para_lines, metadata=metadata,
                                                  word_freq_counter=word_freq_counter)
                    paragraph.metadata["start_offset"] = doc_text_offset
                    doc_text_offset += len(paragraph.text)
                    paragraphs.append(paragraph)
                para_lines = []
        para_lines.append(line)
        if not line.text or len(line.text) == 1:
            continue
        if prev_line and line.is_next_to(prev_line):
            continue
        # if prev_line and line.text and line.is_next_to(prev_line):
            # words = re.split(r"\W+", line.text)
            # word_counts = [word_freq_counter[word] for word in words if word != ""]
        prev_line = line
    if len(para_lines) > 0:
        metadata = get_base_metadata(doc, generate_paragraph_id(), "resolution_paragraph")
        paragraph = RepublicParagraph(lines=para_lines, metadata=metadata,
                                      word_freq_counter=word_freq_counter)
        paragraph.metadata["start_offset"] = doc_text_offset
        doc_text_offset += len(paragraph.text)
        paragraphs.append(paragraph)
    return paragraphs


def get_paragraphs_with_vertical_space(doc: RepublicDoc, prev_line: Union[None, dict] = None,
                                       word_freq_counter: Counter = None) -> List[RepublicParagraph]:
    para_lines = []
    paragraphs = []
    doc_text_offset = 0
    generate_paragraph_id = running_id_generator(base_id=doc.metadata["id"], suffix="-para-")
    lines = [line for line in doc.get_lines()]
    # print('getting paragraphs with vertical space')
    for li, line in enumerate(lines):
        # if prev_line:
        #     print(prev_line.coords.top, prev_line.coords.bottom, line.coords.top, line.coords.bottom, line.text)
        if is_resolution_gap(prev_line, line):
            if len(para_lines) > 0:
                metadata = get_base_metadata(doc, generate_paragraph_id(), "resolution_paragraph")
                paragraph = RepublicParagraph(lines=para_lines, metadata=metadata,
                                              word_freq_counter=word_freq_counter)
                paragraph.metadata['start_offset'] = doc_text_offset
                doc_text_offset += len(paragraph.text)
                # print('appending paragraph:', paragraph.id)
                # print(paragraph.text)
                # print()
                paragraphs.append(paragraph)
            para_lines = []
        para_lines.append(line)
        if not line.text or len(line.text) == 1:
            continue
        if prev_line and line.is_next_to(prev_line):
            continue
        prev_line = line
    if len(para_lines) > 0:
        metadata = get_base_metadata(doc, generate_paragraph_id(), "resolution_paragraph")
        paragraph = RepublicParagraph(lines=para_lines, metadata=metadata,
                                      word_freq_counter=word_freq_counter)
        paragraph.metadata['start_offset'] = doc_text_offset
        doc_text_offset += len(paragraph.text)
        paragraphs.append(paragraph)
    return paragraphs


def is_resolution_gap(prev_line: pdm.PageXMLTextLine, line: pdm.PageXMLTextLine) -> bool:
    if not prev_line:
        return False
    # Resolution start line has big capital with low bottom.
    # If gap between box bottoms is small, this is no resolution gap.
    if -20 < line.coords.bottom - prev_line.coords.bottom < 80:
        # print('is_resolution_gap: False', line.coords.bottom - prev_line.coords.bottom)
        return False
    # If this line starts with a big capital, this is a resolution gap.
    if pdm.line_starts_with_big_capital(line):
        # print('is_resolution_gap: True, line starts with capital')
        return True
    # If the previous line has no big capital starting a resolution,
    # and it has a large vertical gap with the current line,
    # this is resolution gap.
    if not pdm.line_starts_with_big_capital(prev_line) and line.coords.top - prev_line.coords.top > 70:
        # print('is_resolution_gap: True', line.coords.bottom - prev_line.coords.bottom)
        return True
    else:
        # print('is_resolution_gap: False', line.coords.bottom - prev_line.coords.bottom)
        return False


def get_session_scans_version(session: Session) -> List:
    scans_version = {}
    for line in session.lines:
        scans_version[line.metadata['doc_id']] = copy.copy(line.metadata['scan_version'])
        scans_version[line.metadata['doc_id']]['doc_id'] = line.metadata['doc_id']
    # print("session scans versions:", scans_version)
    return list(scans_version.values())


def configure_resolution_searchers():
    opening_searcher_config = {
        "char_match_threshold": 0.7,
        "ngram_threshold": 0.6,
        "levenshtein_threshold": 0.7,
        'filter_distractors': True,
        'include_variants': True,
        'ngram_size': 3,
        'skip_size': 1,
        'max_length_variance': 3
    }
    opening_searcher = FuzzyPhraseSearcher(opening_searcher_config)
    opening_phrase_model = PhraseModel(model=rpm.proposition_opening_phrases, config=opening_searcher_config)
    opening_searcher.index_phrase_model(opening_phrase_model)
    verb_searcher_config = {
        "char_match_threshold": 0.7,
        "ngram_threshold": 0.6,
        "levenshtein_threshold": 0.7,
        'ngram_size': 3,
        'skip_size': 1,
        'max_length_variance': 1
    }
    verb_searcher = FuzzyPhraseSearcher(verb_searcher_config)
    verb_phrase_model = PhraseModel(model=rpm.proposition_verbs, config=verb_searcher_config)
    verb_searcher.index_phrase_model(verb_phrase_model)
    return opening_searcher, verb_searcher
