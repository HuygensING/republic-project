from typing import Dict, List, Union
from collections import defaultdict
import copy
import datetime

from fuzzy_search.fuzzy_phrase_searcher import PhraseModel
from fuzzy_search.fuzzy_match import PhraseMatch

from republic.fuzzy.fuzzy_event_searcher import EventSearcher
from republic.model.republic_date import RepublicDate, get_next_date_strings, get_coming_holidays_phrases
from republic.model.republic_date import get_date_exception_shift, is_session_date_exception, exception_dates
from republic.model.republic_date import get_next_workday, derive_date_from_string, get_shifted_date
from republic.model.republic_document_model import Session


sessiondate_config = {
    'char_match_threshold': 0.7,
    'ngram_threshold': 0.6,
    'levenshtein_threshold': 0.7,
    'max_length_variance': 3,
    'use_word_boundaries': False,
    'perform_strip_suffix': False,
    'ignorecase': False,
    'ngram_size': 3,
    'skip_size': 1
}
attendance_config = {
    "char_match_threshold": 0.7,
    "ngram_threshold": 0.6,
    "levenshtein_threshold": 0.7,
    "max_length_variance": 3,
    "use_word_boundaries": False,
    "perform_strip_suffix": False,
    "ignorecase": False,
    "ngram_size": 3,
    "skip_size": 1
}

session_opening_element_order = [
    'session_date', 'session_year',
    # This is mainly for the period of the Bataafsche Repbulic (1795-1796)
    'tagline',
    # holidays like new years day, Easter, Christmas, ... are mentioned if they are on normal work days
    'holiday',
    # rest days are Sundays and holidays (and Saturdays after 1753)
    'rest_day',
    # Special attendance by the prince is rare
    'special_attendance', 'prince_attending',
    'presiding', 'president',
    'attending', 'attendants',
    'reviewed',
]


def session_from_json(json_doc: dict) -> Session:
    """Turn a session JSON representation into a Session object."""
    return Session(metadata=json_doc['metadata'], columns=json_doc['columns'], evidence=json_doc['evidence'])


def calculate_work_day_shift(current_date: RepublicDate, prev_date: RepublicDate) -> int:
    """Calculate the number of work days different between current session date and previous session date."""
    if current_date.date < prev_date.date:
        return 0
    #     raise ValueError("current session dates should be later than previous session date.")
    next_date = get_next_workday(prev_date)
    workday_shift = 1
    # if not next_date:
    #     print('NO NEXT DATE FOR PREV DATE:', prev_date.isoformat())
    # if not current_date:
    #     print('NO CURRENT DATE FOR PREV DATE:', prev_date.isoformat())
    while next_date and next_date.isoformat() < current_date.isoformat():
        # print('getting next workday')
        next_date = get_next_workday(next_date)
        # print('next_date:', next_date.isoformat())
        workday_shift += 1
    return workday_shift


def has_attendance_match(line: Dict[str, Union[str, int, dict]]) -> bool:
    """Return boolean checking if one of the matches is an attendance match."""
    attendance_labels = [
        'special_attendance', 'prince_attending', 'presiding', 'president', 'attending', 'attendants'
    ]
    for match in line['matches']:
        for label in match.label_list:
            if label in attendance_labels:
                return True
    return False


class SessionSearcher(EventSearcher):

    def __init__(self, inventory_num: int, current_date: RepublicDate,
                 phrase_model_list: List[Dict[str, Union[str, int, List[str]]]],
                 window_size: int = 30):
        """SessionSearcher extends the generic event searcher to specifically search for the lines
        that express the opening of a new session in the resolutions."""
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
        self.add_session_date_searcher()
        self.session_opening_elements: Dict[str, int] = {}
        self.label_order: List[Dict[str, Union[str, int]]] = []
        self.sessions: Dict[str, List[Dict[str, int]]] = defaultdict(list)

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
        self.phrase_models: Dict[str, PhraseModel] = {'attendance_searcher': PhraseModel(model=attendance_phrases,
                                                                                         config=attendance_config)}
        # Add fuzzy searchers for attendance phrases
        self.add_searcher(attendance_config, 'attendance_searcher', self.phrase_models['attendance_searcher'])

    def add_session_date_searcher(self, num_dates: int = 7) -> None:
        """Add a fuzzy searcher configured with a session date phrase model"""
        # generate session date strings for the current day and next six days
        self.date_strings = get_next_date_strings(self.current_date, num_dates=num_dates, include_year=False)
        # generate session date phrases for the first week covered in this inventory
        date_phrases = [{'phrase': date_string, 'label': 'session_date'} for date_string in self.date_strings]
        date_phrases += [{'phrase': str(self.year), 'label': 'session_year'}]
        self.phrase_models['date_searcher'] = PhraseModel(model=date_phrases, config=sessiondate_config)
        self.add_searcher(sessiondate_config, 'date_searcher', self.phrase_models['date_searcher'])
        # when multiple date string match, only use the best matching one.
        self.searchers['date_searcher'].allow_overlapping_matches = False

    def update_session_date_searcher(self,
                                     current_date: Union[None, RepublicDate] = None,
                                     num_dates: int = 7) -> None:
        """Update the session date searcher with a new set of date strings."""
        # update current date
        if current_date:
            self.current_date = current_date
        self.add_session_date_searcher(num_dates=num_dates)

    def extract_date_matches(self) -> None:
        """Extract matches with session date labels and add the corresponding
        line_index to the session elements in the current sliding window."""
        for line_index, line in enumerate(self.sliding_window):
            if not line:
                continue
            if has_attendance_match(line):
                break
            if line_index > 10:
                # date matches should be early in the sliding window
                break
            date_matches = [match for match in line['matches'] if match.metadata['searcher'] == 'date_searcher']
            if len(date_matches) == 0:
                continue
            # the session date should be at the start of the line
            # the session year can be on separate line, so should start at beginning of line, or
            # on same line as rest of date, so at the end of the line.
            match_offset = min([match.offset for match in date_matches])
            # dates should match at or near the start of the line
            if match_offset > 4:
                continue
            for match in date_matches:
                for label in match.label_list:
                    if label in self.session_opening_elements and self.session_opening_elements[label] < line_index:
                        # Always use the first meeting date line, even if it's a rest day.
                        continue
                    # print('adding line with date match label:', label, match)
                    self.session_opening_elements[label] = line_index
                    break

    def extract_attendance_matches(self):
        """Extract matches with meeting attendance labels and add the corresponding
        line_index to the meeting elements in the current sliding window."""
        first_date = None
        if 'meeting_date' in self.session_opening_elements:
            date_match = self.get_session_date_match()
            first_date = derive_date_from_string(date_match.phrase.phrase_string, self.year)
        for line_index, line in enumerate(self.sliding_window):
            if not line or len(line['matches']) == 0:
                continue
            # check if after the first date in line order, any later dates are found that are temporally
            # out of order (i.e. before the first date). If so, we're not in a meeting opening
            date_matches = [match for match in line['matches'] if match.has_label('meeting_date')]
            dates_ordered = True
            for date_match in date_matches:
                date = derive_date_from_string(date_match.phrase.phrase_string, self.year)
                if first_date and date.date < first_date.date:
                    dates_ordered = False
            if not dates_ordered:
                break
            attendance_matches: List[PhraseMatch] = [match for match in line['matches']
                                                     if match.metadata['searcher'] == 'attendance_searcher']
            attendance_labels = [label for match in attendance_matches for label in match.label_list]
            for match in attendance_matches:
                # attendants keywords should match at or near the start of the line
                if match.offset > 4:
                    continue
                # if not self.has_keyword(match['match_keyword']):
                #     continue
                opening_label = None
                for label in match.label_list:
                    if label not in session_opening_element_order and label != 'extract':
                        continue
                    opening_label = label
                # only add the match if there is no earlier match with the same label
                if opening_label in self.session_opening_elements and \
                        self.session_opening_elements[opening_label] < line_index:
                    continue
                # PRAESIDE and PRAESIDING cannot be on the same line, but the shorter one might match the later
                # one. In that case, ignore the shorter match
                if opening_label == 'presiding' and 'attending' in attendance_labels:
                    continue
                if opening_label == 'president':
                    if 'meeting_date' in self.session_opening_elements:
                        # get all meeting date labels that appear before this president label
                        meeting_date_labels = [label_info['index'] for label_info in self.label_order
                                               if label_info['label'] == 'meeting_date'
                                               and label_info['index'] < line_index]
                        if len(meeting_date_labels) == 0:
                            # if a meeting date is found after this president line, skip this line
                            continue
                        distance = line_index - meeting_date_labels[-1]
                        # president should be no more than 5 lines from last meeting date
                        if distance < 0:
                            continue
                        if distance > 5:
                            # there should be other meeting elements in between meeting_date and president
                            president_index = session_opening_element_order.index('president')
                            earlier_element_indexes = []
                            for earlier_element in session_opening_element_order[:president_index]:
                                if earlier_element in self.session_opening_elements \
                                        and self.session_opening_elements[earlier_element] < line_index:
                                    earlier_element_indexes += [self.session_opening_elements[earlier_element]]
                                max_index = max(earlier_element_indexes)
                                if line_index - max_index > 4:
                                    continue
                    if 'attendants' in self.session_opening_elements and \
                            self.session_opening_elements['attendants'] == line_index:
                        # First match of attendants is on same line as president: same string matches both phrases
                        # so remove the attendants phrase
                        del self.session_opening_elements['attendants']
                if opening_label == 'attendants':
                    if 'meeting_date' in self.session_opening_elements:
                        # attendants should be at least 3 lines below the meeting date
                        # but no more than 12
                        distance = line_index - self.session_opening_elements['session_date']
                        if distance < 3 or distance > 12:
                            continue
                    if 'president' in self.session_opening_elements:
                        distance = line_index - self.session_opening_elements['president']
                        if distance < 1 or distance > 4:
                            # if attendants and first occurrence of president found on the same line, skip attendants
                            # if attendants appear much later than president, this is not an opening
                            continue
                        if 'attendants' in self.session_opening_elements and \
                                line_index - self.session_opening_elements['president'] < 2:
                            # president and attendants should be on separate lines
                            # and with at least one line in between them
                            continue
                # opening_label = self.labels[match['match_keyword']]
                # print('adding line with attendants match label:', opening_label, match)
                self.session_opening_elements[opening_label] = line_index

    def get_session_opening_elements(self) -> Dict[str, int]:
        """
        Check which lines in sliding window match session opening elements.
        The elements should match at or near the start of the line.
        """
        self.session_opening_elements: Dict[str, int] = {}
        self.label_order: List[Dict[str, Union[str, int]]] = []
        for line_index, line in enumerate(self.sliding_window):
            if not line:
                continue
            for match in line['matches']:
                opening_label = None
                for label in match.label_list:
                    if label in session_opening_element_order:
                        opening_label = label
                    elif label == 'extract':
                        opening_label = label
                self.label_order += [{'index': line_index, 'label': opening_label}]

        # print('label order:', self.label_order)
        self.extract_date_matches()
        self.extract_attendance_matches()
        # print('session_opening_elements:', self.session_opening_elements)
        return self.session_opening_elements

    def get_last_session_opening_element(self) -> str:
        """Find the last found session element in the encountered order."""
        sorted_elements = sorted(self.session_opening_elements.items(), key=lambda x: x[1])
        return sorted_elements[-1][0]

    def get_last_session_opening_element_line(self) -> Union[None, Dict[str, Union[str, int, Dict[str, int]]]]:
        """Return the last line in the sliding window that has the last session element."""
        last_element = self.get_last_session_opening_element()
        for line in self.sliding_window:
            if not line:
                continue
            for match in line['matches']:
                if match.has_label(last_element):
                    return line
        return None

    def get_session_date_matches(self) -> List[PhraseMatch]:
        """Return a list of all session date matches in the sliding window."""
        date_matches: List[PhraseMatch] = []
        last_session_opening_element_line = self.get_last_session_opening_element_line()
        for line in self.sliding_window:
            if not line:
                continue
            if has_attendance_match(line):
                break
            if line == last_session_opening_element_line:
                break
            date_matches += [match for match in line['matches'] if match.has_label('date_searcher')]
        return date_matches

    def shift_sliding_window(self):
        """Remove all lines up to the line with the last session element."""
        last_element = self.get_last_session_opening_element()
        last_opening_element_line_index = self.session_opening_elements[last_element]
        self.reset_sliding_window(first_lines=last_opening_element_line_index+1)

    def get_attendance_matches(self) -> List[PhraseMatch]:
        """Return a list of all attendance matches in the sliding window."""
        attendance_matches: List[PhraseMatch] = []
        for line in self.sliding_window:
            if not line:
                continue
            attendance_matches += [match for match in line['matches'] if match.has_label('attendance_searcher')]
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

    def check_date_shift_validity(self, prev_session_metadata: Union[None, dict]) -> str:
        status = 'normal'
        if not prev_session_metadata:
            # First session of the year has no previous session, so no date shift
            return status
        if len(self.sessions[prev_session_metadata['session_date']]) == 0:
            print('NO SESSIONS ON PREVIOUS DATE')
            return status
        # prev_session_info = self.sessions[prev_session_metadata['session_date']][-1]
        # prev_session_num_lines = prev_session_info['num_lines']
        # TO DO:
        # use number of work day shift (to avoid quarantining christmas period with many rest days
        # use number of lines:
        # - jump of more than 4 days is likely correct if num lines > 1500 (see e.g. 1722-12-17)
        # - if num lines exceeds 4000, add extra date string and make exception for large shift
        prev_date, prev_prev_date = self.get_prev_dates()
        prev_date_num_lines = 0
        if prev_date.isoformat() in exception_dates:
            # if previous date or the date before that is an exception, don't shift back
            return status
        if prev_prev_date and prev_prev_date.isoformat() in exception_dates:
            return status
        if prev_date:
            prev_date_num_lines = sum([session['num_lines'] for session in self.sessions[prev_date.isoformat()]])
        if prev_prev_date:
            prev_prev_date_num_lines = sum(
                [session['num_lines'] for session in self.sessions[prev_prev_date.isoformat()]])
            two_sessions_num_lines = prev_prev_date_num_lines + prev_date_num_lines
            prev_prev_date_day_shift = self.current_date - prev_prev_date
            workday_shift = calculate_work_day_shift(self.current_date, prev_prev_date)
            if prev_prev_date_day_shift.days > 7 and two_sessions_num_lines < workday_shift * 200:
                # If the date is more than 7 days ahead of the date two sessions ago
                # and the number of lines for the previous two sessions is low,
                # something went wrong and the date should be pushed back by a week.
                status = 'set_back'
                print('DATE IS SET BACK')
                # update the current session date in the searcher
                self.update_session_date(day_shift=-7)
                # update the searcher with new date strings for the next seven days
                self.update_session_date_searcher()
                return status
        if prev_date:
            workday_shift = calculate_work_day_shift(self.current_date, prev_date)
            # print('workday_shift:', workday_shift)
            if workday_shift > 4 and prev_date_num_lines < workday_shift * 200:
                # If the new date is more than 4 work days ahead of the previous date,
                # and the previous session document has few lines
                # it is likely mis-recognized. This date will be quarantined.
                status = 'quarantined'
                print('DATE IS QUARANTINED')
        return status

    def parse_session_metadata(self, prev_session_metadata: Union[None, dict]) -> dict:
        """Turn session elements and sliding window into proper metadata."""
        # make sure local current_date is a copy and not a reference to the original object
        try:
            date_shift_status = self.check_date_shift_validity(prev_session_metadata)
        except ValueError:
            print('has_session_date_match:', self.has_session_date_match())
            if self.has_session_date_match():
                date_match = self.get_session_date_match()
                print('date_match:', date_match)
            raise
        current_date = copy.copy(self.current_date)
        includes_rest_day = False
        prev_date, prev_prev_date = self.get_prev_dates()
        if current_date.is_rest_day() and prev_date and not is_session_date_exception(prev_date):
            print('current date is rest, shifting')
            # If the current date is a rest day, the subsequent session is on the next work day
            includes_rest_day = True
            next_work_day = get_next_workday(self.current_date)
            if next_work_day:
                current_date = next_work_day
            print('shifting to:', current_date.isoformat())
        session_date = current_date.isoformat()
        session_num = len(self.sessions[session_date]) + 1
        self.sessions[session_date].append({'session_num': session_num, 'num_lines': 0})
        session_metadata = {
            'id': f'session-{session_date}-num-{len(self.sessions[session_date])}',
            'type': 'session',
            'inventory_num': self.inventory_num,
            # copy current date instead passing a reference, as current date gets updated
            'session_date': current_date.isoformat(),
            'session_year': current_date.year,
            'session_month': current_date.month,
            'session_day': current_date.day,
            'session_weekday': current_date.day_name,
            'date_shift_status': date_shift_status,
            # in case there are more session sessions on the same day
            'session_num': self.sessions[session_date][-1]['session_num'],
            'president': None,
            'attendants_list_id': None,
            'resolution_ids': [],
            'is_workday': current_date.is_work_day(),
            'has_session_date_element': False,
            'lines_include_rest_day': includes_rest_day,
            'evidence': []
        }
        attendance_matches = self.get_attendance_matches()
        for session_opening_element, line_index in sorted(self.session_opening_elements.items(), key=lambda x: x[1]):
            session_date_line_indexes = []
            for entry in self.label_order:
                if entry['label'] in ['presiding', 'president', 'attending', 'attendants', 'reviewed']:
                    break
                if entry['label'] == 'session_date':
                    session_date_line_indexes += [entry['index']]
                    # line = self.sliding_window[entry['index']]
            evidence = []
            for sliding_index, line in enumerate(self.sliding_window):
                if not line:
                    continue
                if session_opening_element == 'session_date' and sliding_index not in session_date_line_indexes:
                    continue
                matches = [match for match in line['matches'] if match.has_label(session_opening_element)]
                if len(matches) > 0:
                    # evidence += [{'metadata_field': session_opening_element, 'matches': matches}]
                    evidence += matches
            session_metadata['evidence'] += evidence
            if session_opening_element == 'session_date' and self.get_current_date().is_rest_day():
                # If this is a rest day and there are later session_date matches,
                # use the last one for the date evidence.
                if len(session_date_line_indexes) > 1:
                    line_index = session_date_line_indexes[-1]
            line_info = self.sliding_window[line_index]
            if session_opening_element == 'session_date':
                session_metadata['has_session_date_element'] = True
            elif session_opening_element == 'president':
                president_name = None
                for match in attendance_matches:
                    if match.has_label('president'):
                        president_name = line_info['text'][match.end:]
                session_metadata['president'] = president_name
        return session_metadata

    def has_session_date_match(self) -> bool:
        """Check if the sliding window has a session date match."""
        session_opening_elements = self.get_session_opening_elements()
        if 'session_date' not in session_opening_elements:
            return False
        match_line_index = session_opening_elements['session_date']
        match_line = self.sliding_window[match_line_index]
        for match in match_line['matches']:
            if match.has_label('session_date'):
                return True
        return False

    def get_session_date_match(self) -> Union[None, PhraseMatch]:
        """If the sliding window has a session date match, return it."""
        if 'session_date' not in self.session_opening_elements:
            raise KeyError('No session date in sliding window')
        # Use the last session date match in the sliding window, as earlier matches are more likely to be rest days
        first_date_line = self.sliding_window[self.session_opening_elements['session_date']]
        date_match = None
        for match in first_date_line['matches']:
            if match.has_label('session_date'):
                date_match = match
        last_opening_element_line = self.get_last_session_opening_element_line()
        for line in self.sliding_window:
            if not line:
                continue
            if has_attendance_match(line):
                break
            date_matches = [match for match in line['matches'] if match.has_label('session_date')]
            if len(date_matches) > 0:
                date_match = date_matches[0]
            if line == last_opening_element_line:
                break
        return date_match

    def update_session_date(self, day_shift: Union[None, int] = None) -> RepublicDate:
        """Shift current date by day_shift days. If not day_shift is passed as argument,
        determine the number of days to shift current date based on found session date.
        If no day_shift is passed and not session date was found, keep current date."""
        if is_session_date_exception(self.current_date):
            day_shift = get_date_exception_shift(self.current_date)
            new_date = get_shifted_date(self.current_date, day_shift)
        elif day_shift:
            # print('shifting by passing a day shift:', day_shift)
            # if a day_shift is passed, this is an override, probably because of too large
            # date shifts (see parse_session_metadata method above)
            new_date = get_shifted_date(self.current_date, day_shift)
            if new_date.is_rest_day():
                # if the matched date is a rest day, shift the new date forward to the next workday
                new_date = get_next_workday(new_date)
        elif self.has_session_date_match():
            # there is a session date match
            date_match = self.get_session_date_match()
            # print('shifting by date match:', date_match['match_keyword'])
            # determine number of days to shift based on the match in the list of date strings
            new_date = derive_date_from_string(date_match.phrase.phrase_string, self.year)
            if new_date.is_rest_day():
                # if the matched date is a rest day, shift the new date forward to the next workday
                new_date = get_next_workday(new_date)
            # There are some know exceptions where the printed date in the resolutions is incorrect
            # So far as they are known, they are listed in the date exceptions above
            if is_session_date_exception(self.current_date):
                day_shift = get_date_exception_shift(self.current_date)
                new_date = get_shifted_date(self.current_date, day_shift)
        else:
            # No date string was found and none has been passed in the method call,
            # so assume this is the next day
            day_shift = 1
            # print('shifting by default day_shift:', day_shift)
            # however, if the number of lines for the previous session is high,
            # this is a signal that some days have been missed, so shift and extra day
            # prev_session = self.sessions[self.current_date.isoformat()][-1]
            # if prev_session['num_lines'] > 1000:
            #     print("SHIFTING BY TWO DAYS BECAUSE OF HIGH NUMBER OF SESSION LINES")
            #     day_shift = 2
            new_date = get_shifted_date(self.current_date, day_shift)
            if new_date.is_rest_day():
                # if the matched date is a rest day, shift the new date forward to the next workday
                new_date = get_next_workday(new_date)
            # There are some know exceptions where the printed date in the resolutions is incorrect
            # So far as they are known, they are listed in the date exceptions above
            if is_session_date_exception(self.current_date):
                try:
                    day_shift = get_date_exception_shift(self.current_date)
                    new_date = get_shifted_date(self.current_date, day_shift)
                except KeyError:
                    pass
        if not new_date and self.current_date.month == 12 and self.current_date.day > 28:
            # if at the end of the year there is no new date, keep using the current date
            return self.current_date
        # print('old current_date:', self.current_date.isoformat())
        self.current_date = new_date
        # print('new current_date:', self.current_date.isoformat())
        return self.current_date

    def get_current_date(self) -> RepublicDate:
        """Return the current date."""
        return self.current_date
