from typing import Dict, List, Union
from collections import defaultdict
import copy
import datetime

from republic.fuzzy.fuzzy_phrase_model import PhraseModel
from republic.fuzzy.fuzzy_event_searcher import EventSearcher
from republic.model.inventory_mapping import get_inventory_by_num
from republic.model.republic_date import RepublicDate, get_next_date_strings, get_coming_holidays_phrases
from republic.model.republic_date import get_next_day, get_date_exception_shift, is_meeting_date_exception
from republic.model.republic_date import get_next_workday, derive_date_from_string, get_shifted_date
from republic.model.republic_pagexml_model import parse_derived_coords
from republic.helper.metadata_helper import make_scan_urls, make_iiif_region_url


meetingdate_config = {
    'char_match_threshold': 0.6,
    'ngram_threshold': 0.5,
    'levenshtein_threshold': 0.6,
    'max_length_variance': 3,
    'use_word_boundaries': False,
    'perform_strip_suffix': False,
    'ignorecase': False,
    'ngram_size': 2,
    'skip_size': 2
}
attendance_config = {
    "char_match_threshold": 0.6,
    "ngram_threshold": 0.5,
    "levenshtein_threshold": 0.6,
    "max_length_variance": 3,
    "use_word_boundaries": False,
    "perform_strip_suffix": False,
    "ignorecase": False,
    "ngram_size": 2,
    "skip_size": 2,
}


class LogicalStructureDoc:

    def __init__(self):
        """This is a generic class for gathering lines that belong to the same logical structural element,
        even though they appear across different columns and pages."""
        self.lines: List[Dict[str, Union[str, int, Dict[str, int]]]] = []
        self.columns = defaultdict(list)

    def add_lines(self, lines: List[Dict[str, Union[str, int, Dict[str, int]]]]):
        """Add lines to the document, keeping track which column each line belongs to."""
        for line in lines:
            self.lines.append(line)
            self.columns[line['column_id']].append(line)

    def get_columns(self) -> List[dict]:
        """Return all the columns and lines belonging to this document.
        The coordinates of the columns are derived from the coordinates of the lines they contain."""
        columns = []
        for column_id in self.columns:
            line = self.columns[column_id][0]
            textregion_lines = defaultdict(list)
            for line in self.columns[column_id]:
                textregion_lines[line['textregion_id']] += [line]
            column = {
                'metadata': {
                    'column_id': column_id,
                    'inventory_num': line['inventory_num'],
                    'scan_id': line['scan_id'],
                    'scan_num': line['scan_num'],
                    'page_id': line['page_id'],
                    'page_num': line['page_num'],
                    'column_index': line['column_index'],
                },
                'coords': parse_derived_coords(self.columns[column_id]),
                'textregions': []
            }
            inv_metadata = get_inventory_by_num(line['inventory_num'])
            urls = make_scan_urls(inv_metadata, scan_num=line['scan_num'])
            column['metadata']['iiif_url'] = make_iiif_region_url(urls['jpg_url'], column['coords'], add_margin=100)
            for textregion_id in textregion_lines:
                textregion = {
                    'metadata': {'textregion_id': textregion_id},
                    'coords': parse_derived_coords(textregion_lines[textregion_id]),
                    'lines': textregion_lines[textregion_id]
                }
                column['textregions'] += [textregion]
            columns += [column]
        return columns


class Resolution(LogicalStructureDoc):

    def __init__(self):
        """A resolution has textual content of the resolution, as well as an opening formula, decision information,
        and type information on the source document that instigated the discussion and resolution. Source documents
        can be missives, requests, reports, ..."""
        super(self.__class__, self).__init__()
        self.opening = None
        self.decision = None
        # source type is one of missive, requeste, rapport, ...
        self.source_type = None


class Meeting(LogicalStructureDoc):

    def __init__(self, meeting_date: RepublicDate, metadata: Dict,
                 lines: List[Dict[str, Union[str, int, Dict[str, int]]]]):
        """A meeting occurs on a specific day, with a president and attendants, and has textual content in the form of
         lines or possibly as Resolution objects."""
        super(self.__class__, self).__init__()
        self.date = meeting_date
        self.id = f"meeting-{meeting_date.isoformat()}-session-1"
        self.president: Union[str, None] = None
        self.attendance: List[str] = []
        self.resolutions = []
        self.metadata = copy.copy(metadata)
        if len(lines) > 0:
            self.add_lines(lines)
        self.metadata['num_lines'] = len(lines)

    def get_metadata(self) -> Dict[str, Union[str, List[str]]]:
        """Return the metadata of the meeting, including date, president and attendants."""
        return self.metadata

    def to_json(self, with_resolutions: bool = False, with_columns: bool = False, with_lines: bool = False):
        """Return a JSON presentation of the meeting."""
        json_doc = {
            'metadata': self.metadata,
        }
        if with_resolutions:
            json_doc['resolutions'] = self.resolutions
        if with_columns:
            json_doc['columns'] = self.get_columns()
        if with_lines:
            json_doc['lines'] = self.lines
        return json_doc


class MeetingSearcher(EventSearcher):

    def __init__(self, inventory_num: int, current_date: RepublicDate,
                 phrase_model_list: List[Dict[str, Union[str, int, List[str]]]],
                 window_size: int = 30):
        """MeetingSearcher extends the generic event searcher to specifically search for the lines
        that express the opening of a new meeting date in the resolutions."""
        super(self.__class__, self).__init__(window_size=window_size)
        # store the inventory number to add it to meeting metadata
        self.inventory_num = inventory_num
        # set start date based on period covered by inventory
        self.current_date = current_date
        # set year of inventory
        self.year = current_date.year
        # generate initial meeting date strings
        self.date_strings: Union[None, List[str]] = get_next_date_strings(self.current_date, num_dates=7,
                                                                          include_year=False)
        self.add_attendance_searcher(phrase_model_list)
        self.add_meeting_date_searcher()
        self.meeting_elements: Dict[str, int] = {}
        self.label_order: List[Dict[str, Union[str,int]]] = []
        self.sessions: Dict[str, int] = defaultdict(int)

    def add_attendance_searcher(self, phrase_model_list: List[Dict[str, Union[str, int, List[str]]]]):
        """Add a fuzzy searcher configured with the attendance phrase model"""
        # generate meeting attendance phrases for this year
        attendance_phrases: List[Dict[str, Union[str, int, bool, datetime.date]]] = []
        for entry in phrase_model_list:
            if entry['start_year'] <= self.year <= entry['end_year']:
                attendance_phrases.append(entry)
        for coming_holiday_phrase in get_coming_holidays_phrases(self.current_date):
            attendance_phrases.append(coming_holiday_phrase)
        # add phrases as PhraseModel objects
        self.phrase_models: Dict[str, PhraseModel] = {'attendance_searcher': PhraseModel(model=attendance_phrases)}
        # Add fuzzy searchers for attendance phrases
        self.add_searcher(attendance_config, 'attendance_searcher', self.phrase_models['attendance_searcher'])

    def add_meeting_date_searcher(self) -> None:
        """Add a fuzzy searcher configured with a meeting date phrase model"""
        # generate meeting date strings for the current day and next six days
        self.date_strings = get_next_date_strings(self.current_date, num_dates=7, include_year=False)
        # generate meeting date phrases for the first week covered in this inventory
        date_phrases = [{'keyword': date_string, 'label': 'meeting_date'} for date_string in self.date_strings]
        date_phrases += [{'keyword': str(self.year), 'label': 'meeting_year'}]
        self.phrase_models['date_searcher'] = PhraseModel(model=date_phrases)
        self.add_searcher(meetingdate_config, 'date_searcher', self.phrase_models['date_searcher'])
        # when multiple date string match, only use the best matching one.
        self.searchers['date_searcher'].allow_overlapping_matches = False

    def update_meeting_date_searcher(self,
                                     current_date: Union[None, RepublicDate] = None) -> None:
        """Update the meeting date searcher with a new set of date strings."""
        # update current date
        if current_date:
            self.current_date = current_date
        self.add_meeting_date_searcher()

    def extract_date_matches(self) -> None:
        """Extract matches with meeting date labels and add the corresponding
        line_index to the meeting elements in the current sliding window."""
        for line_index, line in enumerate(self.sliding_window):
            if not line:
                continue
            date_matches = [match for match in line['matches'] if match['searcher'] == 'date_searcher']
            if len(date_matches) == 0:
                continue
            # the meeting date should be at the start of the line
            # the meeting year can be on separate line, so should start at beginning of line, or
            # on same line as rest of date, so at the end of the line.
            match_offset = min([match['match_offset'] for match in date_matches])
            # dates should match at or near the start of the line
            if match_offset > 4:
                continue
            for match in date_matches:
                label = match['match_label']
                if label in self.meeting_elements and self.meeting_elements[label] < line_index:
                    # Always use the first meeting date line, even if it's a rest day.
                    continue
                self.meeting_elements[label] = line_index

    def extract_attendance_matches(self):
        """Extract matches with meeting attendance labels and add the corresponding
        line_index to the meeting elements in the current sliding window."""
        for line_index, line in enumerate(self.sliding_window):
            if not line or len(line['matches']) == 0:
                continue
            attendance_matches = [match for match in line['matches'] if match['searcher'] == 'attendance_searcher']
            for match in attendance_matches:
                # attendants keywords should match at or near the start of the line
                if match['match_offset'] > 4:
                    continue
                # if not self.has_keyword(match['match_keyword']):
                #     continue
                label = match['match_label']
                # only add the match if there is no earlier match with the same label
                if label in self.meeting_elements and self.meeting_elements[label] < line_index:
                    continue
                if label == 'president':
                    if 'meeting_date' in self.meeting_elements:
                        # get all meeting date labels that appear before this president label
                        meeting_date_labels = [label_info['index'] for label_info in self.label_order
                                               if label_info['label'] == 'meeting_date'
                                               and label_info['index'] < line_index]
                        if len(meeting_date_labels) == 0:
                            # if a meeting date is found after this president line, skip this line
                            continue
                        distance = line_index - meeting_date_labels[-1]
                        # president should be no more than 5 lines from last meeting date
                        if distance < 0 or distance > 5:
                            continue
                    if 'attendants' in self.meeting_elements and self.meeting_elements['attendants'] == line_index:
                        # First match of attendants is on same line as president: same string matches both phrases
                        # so remove the attendants phrase
                        del self.meeting_elements['attendants']
                if label == 'attendants':
                    if 'meeting_date' in self.meeting_elements:
                        # attendants should be at least 3 lines below the meeting date
                        # but no more than 12
                        distance = line_index - self.meeting_elements['meeting_date']
                        if distance < 3 or distance > 12:
                            continue
                    if 'president' in self.meeting_elements:
                        distance = line_index - self.meeting_elements['president']
                        if distance < 1 or distance > 4:
                            # if attendants and first occurrence of president found on the same line, skip attendants
                            # if attendants appear much later than president, this is not an opening
                            continue
                        if 'attendants' in self.meeting_elements and line_index - self.meeting_elements['president'] < 2:
                            # president and attendants should be on separate lines
                            # and with at least one line in between them
                            continue
                label = self.labels[match['match_keyword']]
                self.meeting_elements[label] = line_index

    def get_meeting_elements(self) -> Dict[str, int]:
        """
        Check which lines in sliding window match meeting opening elements.
        The elements should match at or near the start of the line.
        """
        self.meeting_elements: Dict[str, int] = {}
        self.label_order: List[Dict[str, Union[str, int]]] = []
        for line_index, line in enumerate(self.sliding_window):
            if not line:
                continue
            if len(line['matches']) > 0:
                self.label_order += [{'index': line_index, 'label': match['match_label']} for match in line['matches']]
        self.extract_date_matches()
        self.extract_attendance_matches()
        return self.meeting_elements

    def get_meeting_date_matches(self) -> List[Dict[str, Union[str, int, float]]]:
        """Return a list of all meeting date matches in the sliding window."""
        date_matches: List[Dict[str, Union[str, int, float]]] = []
        for line in self.sliding_window:
            if not line:
                continue
            date_matches += [match for match in line['matches'] if match['searcher'] == 'date_searcher']
        return date_matches

    def get_attendance_matches(self) -> List[Dict[str, Union[str, int, float]]]:
        """Return a list of all attendance matches in the sliding window."""
        attendance_matches: List[Dict[str, Union[str, int, float]]] = []
        for line in self.sliding_window:
            if not line:
                continue
            attendance_matches += [match for match in line['matches'] if match['searcher'] == 'attendance_searcher']
        return attendance_matches

    def get_prev_dates(self):
        found_dates = sorted(self.sessions.keys())
        prev_date, prev_prev_date = None, None
        if len(found_dates) > 0:
            year, month, day = [int(part) for part in found_dates[-1].split('-')]
            prev_date = RepublicDate(year, month, day)
        if len(found_dates) > 1:
            year, month, day = [int(part) for part in found_dates[-2].split('-')]
            prev_prev_date = RepublicDate(year, month, day)
        return prev_date, prev_prev_date

    def check_date_shift_validity(self) -> str:
        status = 'normal'
        prev_date, prev_prev_date = self.get_prev_dates()
        if prev_date and self.current_date - prev_date > datetime.timedelta(days=4):
            # If the new date is more than 4 days ahead of the previous date,
            # it is likely mis-recognized. This date will be quarantined.
            status = 'quarantined'
            print('DATE IS QUARANTINED')
        if prev_prev_date and self.current_date - prev_prev_date > datetime.timedelta(days=7):
            # If the date is more than 7 days ahead if the penultimate date,
            # something went wrong and the date should be pushed back by a week.
            status = 'set_back'
            print('DATE IS SET BACK')
            # update the current meeting date in the searcher
            self.update_meeting_date(day_shift=-7)
            # update the searcher with new date strings for the next seven days
            self.update_meeting_date_searcher()
        return status

    def parse_meeting_metadata(self) -> dict:
        """Turn meeting elements and sliding window into proper metadata."""
        # make sure local current_date is a copy and not a reference to the original object
        date_shift_status = self.check_date_shift_validity()
        current_date = copy.copy(self.current_date)
        includes_rest_day = False
        if current_date.is_rest_day():
            # If the current date is a rest day, the subsequent meeting is on the next work day
            includes_rest_day = True
            next_work_day = get_next_workday(self.current_date)
            if next_work_day:
                current_date = next_work_day
        meeting_date = current_date.isoformat()
        self.sessions[meeting_date] += 1
        meeting_metadata = {
            'id': f'meeting-{meeting_date}-session-{self.sessions[meeting_date]}',
            'inventory_num': self.inventory_num,
            # copy current date instead passing a reference, as current date gets updated
            'meeting_date': current_date.isoformat(),
            'meeting_year': current_date.year,
            'meeting_month': current_date.month,
            'meeting_day': current_date.day,
            'meeting_weekday': current_date.day_name,
            'date_shift_status': date_shift_status,
            # in case there are more meeting sessions on the same day
            'session': self.sessions[meeting_date],
            'president': None,
            'attendants_list_id': None,
            'resolution_ids': [],
            'is_workday': current_date.is_work_day(),
            # 'lines': [line['text_id'] for line in self.sliding_window if line and len(line['matches']) > 0],
            'has_meeting_date_element': False,
            'lines_include_rest_day': includes_rest_day,
            'evidence': []
        }
        attendance_matches = self.get_attendance_matches()
        for meeting_element, line_index in sorted(self.meeting_elements.items(), key=lambda x: x[1]):
            meeting_date_line_indexes = [entry['index'] for entry in self.label_order if entry['label'] == 'meeting_date']
            evidence = []
            for line in self.sliding_window:
                if not line:
                    continue
                matches = [match for match in line['matches'] if match['match_label'] == meeting_element]
                if len(matches) > 0:
                    evidence += [{'metadata_field': meeting_element, 'line_id': line['text_id'], 'matches': matches}]
            meeting_metadata['evidence'] += evidence
            if meeting_element == 'meeting_date' and self.get_current_date().is_rest_day():
                # If this is a rest day and there are later meeting_date matches,
                # use the last one for the date evidence.
                if len(meeting_date_line_indexes) > 1:
                    line_index = meeting_date_line_indexes[-1]
            line_info = self.sliding_window[line_index]
            if meeting_element == 'meeting_date':
                meeting_metadata['has_meeting_date_element'] = True
            elif meeting_element == 'president':
                president_name = None
                for match in attendance_matches:
                    if match['match_label'] == 'president':
                        start_offset = match['match_offset']
                        end_offset = start_offset + len(match['match_string'])
                        president_name = line_info['text_string'][end_offset:]
                meeting_metadata['president'] = president_name
        return meeting_metadata

    def has_meeting_date_match(self):
        """Check if the sliding window has a meeting date match."""
        if 'meeting_date' not in self.meeting_elements:
            return False
        match_line_index = self.meeting_elements['meeting_date']
        match_line = self.sliding_window[match_line_index]
        for match in match_line['matches']:
            if match['match_label'] == 'meeting_date':
                return match
        return False

    def get_meeting_date_match(self) -> Dict[str, Union[str, int, float]]:
        """If the sliding window has a meeting date match, return it."""
        if 'meeting_date' not in self.meeting_elements:
            raise KeyError('Not meeting date in sliding window')
        # Use the last meeting date match in the sliding window, as earlier matches are more likely to be rest days
        match = None
        for line in self.sliding_window:
            if not line:
                continue
            date_matches = [match for match in line['matches'] if match['match_label'] == 'meeting_date']
            if len(date_matches) > 0:
                match = date_matches[0]
        return match

    def update_meeting_date(self, day_shift: Union[None, int] = None) -> RepublicDate:
        """Shift current date by day_shift days. If not day_shift is passed as argument,
        determine the number of days to shift current date based on found meeting date.
        If no day_shift is passed and not meeting date was found, keep current date."""
        if day_shift:
            # if a day_shift is passed, this is an override, probably because of too large
            # date shifts (see parse_meeting_metadata method above)
            new_date = get_shifted_date(self.current_date, day_shift)
            self.current_date = new_date
            return self.current_date
        if self.has_meeting_date_match():
            # there is a meeting date match
            date_match = self.get_meeting_date_match()
            # determine number of days to shift based on the match in the list of date strings
            new_date = derive_date_from_string(date_match['match_keyword'], self.year)
            # There are some know exceptions where the printed date in the resolutions is incorrect
            # So far as they are known, they are listed in the date exceptions above
            if is_meeting_date_exception(self.current_date):
                try:
                    day_shift = get_date_exception_shift(self.current_date)
                    new_date = get_shifted_date(self.current_date, day_shift)
                except KeyError:
                    pass
            self.current_date = new_date
            return self.current_date
        else:
            # No date string was found and none has been passed in the method call,
            # so assume this is the next day
            day_shift = 1
            new_date = get_shifted_date(self.current_date, day_shift)
            self.current_date = new_date
            return self.current_date

    def get_current_date(self) -> RepublicDate:
        """Return the current date."""
        return self.current_date
