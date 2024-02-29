import json
import re
from collections import Counter
from typing import Dict, List, Set, Union

import pagexml.model.physical_document_model as pdm
import republic.helper.pagexml_helper as pagexml
from fuzzy_search.phrase.phrase import Phrase
from fuzzy_search.match.phrase_match import PhraseMatch
from republic.model.republic_date import DateNameMapper
from republic.model.republic_date import RepublicDate
from republic.helper.metadata_helper import make_scan_urls, make_iiif_region_url


class RepublicDoc(pdm.LogicalStructureDoc):

    def __init__(self, doc_id: str = None, doc_type: str = None, metadata: Union[None, Dict] = None,
                 lines: List[pdm.PageXMLTextLine] = None,
                 text_regions: List[pdm.PageXMLTextRegion] = None):
        super().__init__(doc_id=doc_id, doc_type='republic_doc', metadata=metadata,
                         lines=lines, text_regions=text_regions)
        self.main_type = "republic_doc"
        self.linked_text_regions = []
        if lines:
            self.set_as_logical_parent(lines)
        if text_regions:
            self.set_as_logical_parent(text_regions)
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

    def get_lines(self) -> List[pdm.PageXMLTextLine]:
        lines: List[pdm.PageXMLTextLine] = []
        if self.text_regions:
            for text_region in self.text_regions:
                lines += text_region.get_lines()
        if self.lines:
            lines += self.lines
        return lines

    def get_words(self):
        words: List[pdm.PageXMLWord] = []
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
                 lines: List[pdm.PageXMLTextLine] = None, text_regions: List[pdm.PageXMLTextRegion] = None,
                 metadata: dict = None,
                 scan_versions: List[Dict[str, any]] = None, text: str = None, text_region_ids: List[str] = None,
                 line_ranges: List[Dict[str, any]] = None):
        super().__init__(doc_id=doc_id, doc_type='resolution_paragraph', lines=lines,
                         text_regions=text_regions, metadata=metadata)
        if not self.id and 'id' in self.metadata:
            self.id = self.metadata['id']
        self.line_ranges = line_ranges if line_ranges else []
        self.text_page_nums: List[int] = []
        self.page_nums: List[int] = []
        self.text = text if text else ""
        self.text_region_ids: Set[str] = set()
        if doc_type:
            self.add_type(doc_type)
        self.main_type = 'republic_paragraph'
        if text_region_ids:
            self.text_region_ids = set(text_region_ids)
        else:
            self.text_region_ids = {text_region.id for text_region in self.text_regions}
        if len(self.text_page_nums) == 0:
            self.set_text_page_nums()
        self.add_type("republic_paragraph")
        self.scan_versions = scan_versions
        self.evidence: List[PhraseMatch] = []

    def __repr__(self):
        return f"{self.__class__.__name__}(lines={[line.id for line in self.lines]}, text={self.text})"

    @property
    def json(self, include_text_regions: bool = True):
        json_data = {
            "id": self.id,
            "type": self.type,
            "metadata": self.metadata,
            "text_region_ids": list(self.text_region_ids),
            "text": self.text,
            "line_ranges": self.line_ranges,
            "scan_versions": self.scan_versions,
            "stats": self.stats
        }
        if include_text_regions:
            json_data["text_regions"] = [tr.json for tr in self.text_regions]
        if self.linked_text_regions:
            json_data["linked_text_regions"] = [tr.json for tr in self.linked_text_regions]
        return json_data

    def set_text_page_nums(self):
        text_page_nums = set()
        page_nums = set()
        if len(self.lines) > 0:
            for line in self.lines:
                if "text_page_num" in line.metadata and line.metadata["text_page_num"]:
                    text_page_nums.add(line.metadata["text_page_num"])
                if "page_num" in line.metadata and line.metadata["page_num"]:
                    page_nums.add(line.metadata["page_num"])
        if len(self.line_ranges) > 0:
            for line_range in self.line_ranges:
                if "text_page_num" in line_range and line_range["text_page_num"]:
                    text_page_nums.add(line_range["text_page_num"])
                if "page_num" in line_range and line_range["page_num"]:
                    page_nums.add(line_range["page_num"])
        self.metadata["text_page_num"] = sorted(list(text_page_nums))
        self.metadata["page_num"] = sorted(list(page_nums))

    def get_match_lines(self, match: PhraseMatch) -> List[pdm.PageXMLTextLine]:
        # part_of_match = False
        match_lines = []
        for line_range in self.line_ranges:
            if line_range["start"] <= match.offset < line_range["end"]:
                match_lines.append(self.lines[line_range["line_index"]])
        return match_lines

    @property
    def stats(self) -> dict:
        stats_json = {
            "words": len(re.split(r'\W+', self.text.strip())),
            "lines": len(self.line_ranges)
        }
        return stats_json


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
        self.text_region_ids = self.text_region_ids.union([text_region.id
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
            'type': list(self.type),
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
        if self.linked_text_regions:
            json_doc["linked_text_regions"] = [tr.json for tr in self.linked_text_regions]
        return json_doc


class Session(ResolutionElementDoc):

    def __init__(self, doc_id: str = None, doc_type: str = None, metadata: Dict = None,
                 session_data: Dict = None,
                 session_type: str = "ordinaris", date_mapper: DateNameMapper = None,
                 paragraphs: List[RepublicParagraph] = None, text_regions: List[pdm.PageXMLTextRegion] = None,
                 lines: List[pdm.PageXMLTextLine] = None,
                 scan_versions: List[dict] = None, evidence: List[PhraseMatch] = None, **kwargs):
        """A meeting session occurs on a specific day, with a president and attendants,
        and has textual content in the form of
         lines or possibly as Resolution objects."""
        date_string = None
        if session_data and 'metadata' in session_data and metadata is None:
            metadata = session_data['metadata']
            metadata['page_ids'] = [page_id for page_id in session_data['page_ids']]
            metadata['scan_ids'] = [scan_id for scan_id in session_data['scan_ids']]
            metadata['session_date'] = session_data['date']['session_date']
        if session_data and 'date' in session_data:
            date_string = session_data['date']['session_date']
        elif metadata and 'date' in metadata:
            date_string = metadata['date']['session_date']
        elif metadata and 'session_date' in metadata:
            date_string = metadata['session_date']
        if date_string is None:
            print('MISSING DATE:', doc_id)
            print(metadata['date'])
        # if 'metadata' in metadata:
        #     metadata = metadata['metadata']

        super().__init__(doc_id=doc_id, doc_type='session', metadata=metadata, paragraphs=paragraphs,
                         text_regions=text_regions, lines=lines, evidence=evidence, **kwargs)
        self.session_date = RepublicDate(date_string=date_string, date_mapper=date_mapper)
        # if 'page_ids' in metadata and 'page_ids' not in self.metadata:
        #     self.metadata['page_ids'] = [page_id for page_id in metadata['page_ids']]
        self.main_type = "session"
        self.session_type = session_type
        if doc_type:
            self.add_type(doc_type)
        self.date = self.session_date
        if not doc_id:
            self.id = f"session-{self.session_date.as_date_string()}-{self.session_type}-num-1"
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
                 lines: List[pdm.PageXMLTextLine] = None,
                 text_regions: List[pdm.PageXMLTextRegion] = None,
                 paragraphs: List[RepublicParagraph] = None,
                 evidence: Union[List[dict], List[PhraseMatch]] = None,
                 attendance_spans: List[dict] = None):
        """An attendance list has textual content."""
        if not metadata:
            metadata = {}
        metadata['type'] = 'attendance_list'
        super().__init__(doc_id=doc_id, doc_type='attendance_list', metadata=metadata,
                         paragraphs=paragraphs, lines=lines, text_regions=text_regions,
                         evidence=evidence)
        if doc_type:
            self.add_type(doc_type)
        self.main_type = 'attendance_list'
        self.scan_versions = scan_versions if scan_versions else []
        self.session_date: Union[RepublicDate, None] = None
        self.text_region_ids: Set[str] = set()
        self.attendance_spans: List[dict] = attendance_spans if attendance_spans is not None else []

    def __repr__(self):
        return f"AttendanceList({json.dumps(self.json, indent=4)}"

    @property
    def json(self) -> dict:
        json_doc = super().json
        json_doc["attendance_spans"] = self.attendance_spans
        return json_doc


class Resolution(ResolutionElementDoc):

    def __init__(self,
                 doc_id: str = None, doc_type: str = None,
                 metadata: dict = None,
                 scan_versions: dict = None,
                 lines: List[pdm.PageXMLTextLine] = None,
                 text_regions: List[pdm.PageXMLTextRegion] = None,
                 paragraphs: List[RepublicParagraph] = None,
                 evidence: Union[List[dict], List[PhraseMatch]] = None,
                 labels: List[Dict[str, str]] = None):
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
        self.main_type = 'resolution'
        self.metadata['resolution_type'] = 'ordinaris'
        self.labels = labels if labels else []
        self.scan_versions = scan_versions if scan_versions else []
        self.opening = None
        self.decision = None
        # proposition type is one of missive, requeste, rapport, ...
        self.proposition_type: Union[None, str] = None
        self.proposer: Union[None, str, List[str]] = None
        self.session_date: Union[RepublicDate, None] = None
        self.text_region_ids: Set[str] = set()
        self.set_proposition_type()
        if "session_date" in self.metadata and self.metadata["session_date"] is not None:
            self.session_date = RepublicDate(date_string=self.metadata["session_date"])

    def __repr__(self):
        return f"Resolution({json.dumps(self.json, indent=4)}"

    def add_label(self, label_string: str, label_type: str, provenance: dict = None):
        for label in self.labels:
            if label['label_string'] == label_string and label['label_type'] == label_type:
                break
        else:
            label = {
                'label_string': label_string,
                'label_type': label_type
            }
            if provenance:
                for field in provenance:
                    label[field] = provenance[field]
            self.labels.append(label)

    def set_proposition_type(self):
        if self.evidence:
            if self.metadata['proposition_type']:
                self.proposition_type = self.metadata['proposition_type']
            else:
                self.proposition_type = get_proposition_type_from_evidence(self.evidence)
                self.metadata['proposition_type'] = self.proposition_type

    @property
    def json(self):
        json_doc = super().json
        json_doc['labels'] = self.labels
        return json_doc


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
    attendance_spans = attendance_json["attendance_spans"] if "attendance_spans" in attendance_json else None
    return AttendanceList(doc_id=attendance_json['id'], doc_type=attendance_json['type'],
                          metadata=attendance_json['metadata'],
                          paragraphs=paragraphs, text_regions=text_regions,
                          lines=lines, scan_versions=scan_versions,
                          evidence=evidence, attendance_spans=attendance_spans)


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


def json_to_republic_resolution(resolution_json: dict) -> Union[Resolution, AttendanceList]:
    if 'attendance_list' in resolution_json['type'] or 'attendance_list' in resolution_json['metadata']['type']:
        return json_to_republic_attendance_list(resolution_json)
    paragraphs = []
    for paragraph_json in resolution_json['paragraphs']:
        try:
            paragraph = json_to_republic_resolution_paragraph(paragraph_json)
        except KeyError:
            print(resolution_json["metadata"])
            print(paragraph_json["metadata"])
            raise
        paragraphs.append(paragraph)
    text_regions, lines, evidence = json_to_physical_elements(resolution_json)
    resolution = Resolution(doc_id=resolution_json['id'], doc_type=resolution_json['type'],
                            metadata=resolution_json['metadata'], evidence=evidence,
                            paragraphs=paragraphs, text_regions=text_regions, lines=lines)
    if 'linked_text_regions' in resolution_json:
        linked_json = resolution_json['linked_text_regions']
        resolution.linked_text_regions = [pagexml.json_to_pagexml_text_region(tr_json) for tr_json in linked_json]
    if 'labels' in resolution_json:
        resolution.labels = [label for label in resolution_json['labels']]
    return resolution


def json_to_physical_elements(republic_json: dict):
    text_regions = republic_json['text_regions'] if 'text_regions' in republic_json else []
    text_regions = [pagexml.json_to_pagexml_text_region(tr_json) for tr_json in text_regions]
    lines = republic_json['lines'] if 'lines' in republic_json else []
    lines = [pagexml.json_to_pagexml_line(line_json) for line_json in lines]
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
            # print('BLEED THROUGH?', line['metadata']['is_bleed_through'], line['text'])
