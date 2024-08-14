from __future__ import annotations
import copy
import datetime
import re
from calendar import monthrange
from collections import defaultdict
from dateutil.easter import easter
from dateutil.parser import parse
from typing import Dict, List, Tuple, Union

from republic.model.republic_date_phrase_model import week_day_names, month_names
from republic.model.republic_date_phrase_model import holiday_phrases
from republic.model.republic_date_phrase_model import date_name_map as default_date_name_map
from republic.model.republic_date_phrase_model import date_structure_map


exception_dates = {
    # the exception date is the day before the date with the mistake, because in updating to the next date
    # it needs to override the computed day shift
    # "1705-03-31": {"mistake": "next day has wrong month name", "shift_days": 1, "month name": "Maert"},
    "1705-09-11": {"mistake": "next day has wrong week day name", "shift_days": 1},
    "1706-02-01": {"mistake": "next day has wrong week day name", "shift_days": 1},
    "1706-05-21": {"mistake": "next day has wrong week day name", "shift_days": 1},
    "1706-06-01": {"repetition": "next session is on the same day", "shift_days": 0},
    "1706-08-12": {"mistake": "next day has wrong week day name", "shift_days": 1},
    "1708-07-13": {"repetition": "next session is on the same day", "shift_days": 0},
    "1708-11-29": {"repetition": "next session is on the same day", "shift_days": 0},
    "1710-06-07": {"mistake": "next work day is a Sunday", "shift_days": 1},
    "1710-07-23": {"repetition": "next session is on the same day", "shift_days": 0},
    "1713-03-13": {"mistake": "next day has wrong week day name", "shift_days": 1},
    "1713-03-22": {"mistake": "next day has wrong week day name", "shift_days": 1},
    "1713-06-26": {"mistake": "next day has wrong week day name", "shift_days": 1},
    "1714-05-03": {"mistake": "next day matches with Martis instead of Veneris", "shift_days": 1},
    "1714-06-07": {"mistake": "next day matches with Martis instead of Veneris", "shift_days": 1},
    "1714-08-14": {"repetition": "next session is on the same day", "shift_days": 0},
    "1714-09-26": {"repetition": "next session is on the same day", "shift_days": 0},
    "1714-12-18": {"mistake": "next day has wrong week day name", "shift_days": 1},
    "1716-02-27": {"mistake": "next day has wrong week day name", "shift_days": 1},
    "1716-12-07": {"mistake": "next day has wrong week day name", "shift_days": 1},
    "1718-05-23": {"mistake": "next day has wrong week day name", "shift_days": 1},
    "1719-01-26": {"mistake": "next day has wrong week day name", "shift_days": 1},
    "1721-11-03": {"mistake": "next day has wrong week day name", "shift_days": 1},
    "1722-12-28": {"mistake": "avoid jump back", "shift_days": 2},
    "1723-10-01": {"mistake": "next day matches Martis instead of Sabbathi", "shift_days": 1},
    "1730-05-15": {"mistake": "next day has wrong week day name", "shift_days": 1},
    "1732-03-11": {"mistake": "next day has wrong week day name", "shift_days": 1},
    "1732-12-22": {"mistake": "next day is misrecognized", "shift_days": 1},
    "1734-04-15": {"mistake": "next day is misrecognized", "shift_days": 1},
    "1735-10-11": {"mistake": "next day has wrong week day name", "shift_days": 1},
    "1743-07-06": {"repetition": "next session is on the same day", "shift_days": 0},
    "1744-02-29": {"repetition": "next session is on the same day", "shift_days": 0},
    "1744-03-27": {"mistake": "next day is misrecognized", "shift_days": 1},
    "1747-11-13": {"mistake": "next day is misrecognized (Jovis instead of Martis)", "shift_days": 1},
    "1750-02-07": {"mistake": "next day is misrecognized", "shift_days": 3},
    "1761-08-10": {"mistake": "next day has wrong week day name", "shift_days": 1},
    # OCR problems solved with March 2021 batch
    # "1762-11-11": {"mistake": "heavy bleed through on many pages", "shift_days": 11},
    # "1765-05-29": {"mistake": "heavy bleed through on many pages", "shift_days": 6},
    # "1767-11-04": {"mistake": "bad OCR causes week of sessions missed", "shift_days": 7},
    "1771-07-02": {"mistake": "next day is misrecognized", "shift_days": 2},
    # OCR problems solved with March 2021 batch
    # "1777-05-07": {"mistake": "OCR output is missing columns", "shift_days": 16},
    # "1777-05-26": {"mistake": "OCR output is missing columns", "shift_days": 7},
    # "1777-10-02": {"mistake": "OCR output is missing columns", "shift_days": 7},
    # "1777-10-09": {"mistake": "OCR output is missing columns", "shift_days": 5},
    # "1778-04-21": {"mistake": "OCR output is missing columns", "shift_days": 9},
    "1778-10-26": {"mistake": "next day has wrong week day name", "shift_days": 1},
    "1780-01-18": {"mistake": "next day has wrong week day name", "shift_days": 1},
    "1780-12-23": {"mistake": "christmas day has session", "shift_days": 2},
    "1780-12-25": {"mistake": "christmas day has session", "shift_days": 1},
    "1783-08-28": {"repetition": "next session is on the same day", "shift_days": 0},
    "1784-08-25": {"repetition": "next session is on the same day", "shift_days": 0},
    "1784-10-15": {"repetition": "next session is on the same day", "shift_days": 0},
    "1786-09-12": {"repetition": "next session is on the same day", "shift_days": 0},
    "1786-09-25": {"mistake": "next day has wrong week day name", "shift_days": 1},
    "1787-05-11": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1787-05-12": {"mistake": "next Sunday is a work day", "shift_days": 1},
    "1787-05-13": {"repetition": "next session is on the same day", "shift_days": 0},
    "1787-06-04": {"repetition": "next session is on the same day", "shift_days": 0},
    "1787-06-15": {"repetition": "next session is on the same day", "shift_days": 0},
    # OCR problems solved with March 2021 batch
    # "1788-12-24": {"mistake": "OCR problems, skip whole week", "shift_days": 7},
    "1791-02-15": {"mistake": "next day has wrong week day name", "shift_days": 1},
    "1791-11-30": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1791-12-01": {"mistake": "next Sunday is a work day", "shift_days": 1},
    "1792-03-15": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1792-03-16": {"mistake": "next Sunday is a work day", "shift_days": 1},
    "1793-03-04": {"mistake": "next day has wrong week day name", "shift_days": 1},
    # OCR problems solved with March 2021 batch
    # "1794-03-24": {"mistake": "OCR problems, skip whole week", "shift_days": 7},
    "1794-06-27": {"mistake": "next Sunday is a work day", "shift_days": 2},
    "1794-09-27": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1794-10-31": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1794-11-01": {"mistake": "next Sunday is a work day", "shift_days": 1},
    "1794-11-07": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1794-11-21": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1794-11-28": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1794-12-05": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1794-12-12": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1794-12-19": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1795-01-03": {"mistake": "this day is a work day", "shift_days": 2},
    "1795-01-09": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1795-01-10": {"mistake": "next Sunday is a work day", "shift_days": 1},
    "1795-01-16": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1795-01-17": {"mistake": "next Sunday is a work day", "shift_days": 1},
    "1795-01-22": {"repetition": "next session is on the same day", "shift_days": 0},
    "1795-01-23": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1795-01-24": {"mistake": "next Sunday is a work day", "shift_days": 1},
    "1795-01-27": {"repetition": "next session is on the same day", "shift_days": 0},
    "1795-01-30": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1795-01-31": {"mistake": "next Sunday is a work day", "shift_days": 1},
    "1795-02-09": {"mistake": "this day is a work day", "shift_days": 1},
    "1795-03-04": {"repetition": "next session is on the same day", "shift_days": 0},
    "1795-03-06": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1795-03-07": {"mistake": "next Sunday is a work day", "shift_days": 1},
    "1795-03-20": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1795-03-21": {"mistake": "next Sunday is a work day", "shift_days": 1},
    "1795-04-03": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1795-04-02": {"repetition": "next session is on the same day", "shift_days": 0},
    "1795-04-04": {"mistake": "next Sunday is a work day", "shift_days": 1},
    "1795-04-10": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1795-04-11": {"mistake": "next Sunday is a work day", "shift_days": 1},
    "1795-04-17": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1795-04-18": {"mistake": "next Sunday is a work day", "shift_days": 1},
    "1795-05-15": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1795-05-16": {"mistake": "next Sunday is a work day", "shift_days": 1},
    "1795-05-27": {"repetition": "next session is on the same day", "shift_days": 0},
    "1795-05-29": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1795-05-30": {"mistake": "next Sunday is a work day", "shift_days": 1},
    "1795-06-26": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1795-06-27": {"mistake": "next Sunday is a work day", "shift_days": 1},
    "1795-07-03": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1795-07-10": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1795-07-17": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1795-07-18": {"mistake": "next Sunday is a work day", "shift_days": 1},
    "1795-07-31": {"mistake": "next Sunday is a work day", "shift_days": 2},
    "1795-08-07": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1795-08-28": {"repetition": "next session is on the same day", "shift_days": 0},
    "1795-09-04": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1795-10-30": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1795-11-06": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1795-12-04": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1795-12-11": {"mistake": "next Sunday is a work day", "shift_days": 2},
    "1796-01-22": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1796-01-23": {"mistake": "next Sunday is a work day", "shift_days": 1},
    "1796-02-19": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1796-02-20": {"mistake": "next Sunday is a work day", "shift_days": 1},
    "1796-02-26": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1796-02-27": {"mistake": "next Sunday is a work day", "shift_days": 1},
    "1796-02-29": {"repetition": "next session is on the same day", "shift_days": 0},
}


def make_date_name_map(date_elements: List[Tuple[str, str]], debug: int = 0):
    if debug > 1:
        print(f'republic_date.make_date_name_map - received date_elements: {date_elements}')
    date_structure = {
        'week_day_name': None,
        'month_day_name': None,
        'month_name': None,
        'include_year': False,
        'include_den': False
    }
    for date_element in date_elements:
        name_set, set_version = date_element
        if date_structure_map[name_set] and set_version in date_structure_map[name_set]:
            date_structure[name_set] = date_structure_map[name_set][set_version]
        elif name_set == 'den':
            date_structure['include_den'] = True
        elif name_set == 'year':
            date_structure['include_year'] = True
    return date_structure


class DateNameMapper:

    def __init__(self, inv_metadata: Dict[str, any], date_elements: List[Tuple[str, str]], debug: int = 0):
        """
        Creates an object that can map date objects and date strings to dates used to announce
        a new session in the resolutions. Dates are announced as <week_day> <month_day> <month_name>
        or a variation of that, with each element constrained to a list of accepted values.

        The values are specific in republic.model.republic_date_phrase_model.

        Example:
        [
            ('week_day_name', 'roman_early'),
            ('den', 'all'),
            ('month_day_name', 'decimal_en'),
            ('month_name', 'handwritten'),
        ]

        :param inv_metadata:
        :param date_elements:
        """
        self.inv_metadata = inv_metadata
        self.date_element_order = date_elements
        if debug > 3:
            print('DateNameMapper - date_elements:', date_elements)
        self.date_name_map = make_date_name_map(date_elements)
        if self.date_name_map is None:
            print(f"republic_date.DateNameMapper")
        if debug > 3:
            print('DateNameMapper - self.date_name_map:', self.date_name_map)
        self.include_year = self.date_name_map['include_year']
        self.include_den = self.date_name_map['include_den']
        if self.include_year:
            self.date_element_order
        self.index_week_day = {}
        self.index_month = {}
        self.index_month_day = {}
        if 'week_day_name' in self.date_name_map and self.date_name_map['week_day_name'] is not None:
            # print(f'republic_date.DateNameMapper.__init__ - self.date_name_map: {self.date_name_map}')
            self._set_week_day_name_map()
        if 'month_name' in self.date_name_map and self.date_name_map['month_name'] is not None:
            self._set_month_name_map()
        if 'month_day_name' in self.date_name_map and self.date_name_map['month_day_name'] is not None:
            self._set_month_day_name_map()

    def _set_week_day_name_map(self):
        self.index_week_day = defaultdict(set)
        for week_day_name in self.date_name_map['week_day_name']:
            week_day_index = self.date_name_map['week_day_name'][week_day_name]
            self.index_week_day[week_day_index].add(week_day_name)
        return None

    def _set_month_name_map(self):
        self.index_month = defaultdict(set)
        for month_name in self.date_name_map['month_name']:
            month_index = self.date_name_map['month_name'][month_name]
            self.index_month[month_index].add(month_name)
        return None

    def _set_month_day_name_map(self):
        self.index_month_day = defaultdict(set)
        for month_day_name in self.date_name_map['month_day_name']:
            month_day_index = self.date_name_map['month_day_name'][month_day_name]
            self.index_month_day[month_day_index].add(month_day_name)
        return None

    def generate_day_string(self, year: int, month: int, day: int,
                            include_year: bool = None, include_den: bool = None,
                            debug: int = 0) -> Union[str, List[str], None]:
        debug_prefix = 'DateNameMapper.generate_day_string'
        if include_year is None:
            include_year = self.include_year
        if include_den is None:
            include_den = self.include_den
        if debug > 0:
            print(f'{debug_prefix} - 1. generate for {year} {month} {day}')
        day_strings = []
        try:
            date = datetime.date(year, month, day)
        except TypeError:
            print(f'Error generating date object for year: {year}\tmonth: {month}\tday: {day}')
            raise
        week_day = date.weekday()
        names = {
            'month_name': self.index_month[month],
            'month_day_name': [],
            'week_day_name': self.index_week_day[week_day],
            'den': ['den'],
            'year': [year for year in range(self.inv_metadata['year_start'], self.inv_metadata['year_end']+1)]
        }

        if debug > 1:
            print(f'\n{debug_prefix} 2. names dict:\n{names}\n\n')

        month_start_day, month_num_days = monthrange(year, month)

        # print(f'DateNameMapper.generate_day_string - year: {year}\tmonth: {month}\tday: {day}')
        # print(f'\tmonth_num_days: {month_num_days}\tday - month_num_days: {day - month_num_days}')
        if 'month_day_name' in self.date_name_map:
            # index has a set, so copy to list to avoid updating the set itself
            names['month_day_name'] = [day for day in self.index_month_day[day]]
            if day - month_num_days == 0:
                # print('\tlast:', [day for day in self.index_month_day[0]])
                names['month_day_name'].extend([day for day in self.index_month_day[0]])
            elif day - month_num_days == -1:
                names['month_day_name'].extend([day for day in self.index_month_day[-1]])
                # print('\tbefore last:', [day for day in self.index_month_day[-1]])
        else:
            suffix = 'sten' if day in {1, 8} or day >= 20 else 'den'
            names['month_day_names'] = [f'{day}{suffix}']
        week_day_names = self.index_week_day[week_day]
        if debug > 0:
            print('generate_day_string - 3. month_names:', names['month_name'])
            print('generate_day_string - 4. month_day_names', names['month_day_name'])
            print('generate_day_string - 5. week_day_names:', names['week_day_name'])
        day_strings = []
        for name_set, set_version in self.date_element_order:
            # print(name_set, set_version)
            if debug > 1:
                print(f'{debug_prefix} - 6. name_set:', name_set)
            if len(day_strings) == 0:
                day_strings = [name for name in names[name_set]]
                if debug > 2:
                    print(f'{debug_prefix} - 7. day_strings:', day_strings)
            else:
                day_strings = [f"{day_string} {name}" for day_string in day_strings for name in names[name_set]]
                if debug > 2:
                    print(f'{debug_prefix} - 7. day_strings:', day_strings)
        return day_strings


class RepublicDate:

    def __init__(self, year: int = None, month: int = None, day: int = None,
                 date_string: str = None,
                 date_mapper: DateNameMapper = None):
        """A Republic date extends the regular datetime.date object with names
        for weekday and month, a date string as used in the session openings,
        and methods for checking whether the current date is a work day, a rest
        day or a holiday.

        :param year: year
        :type year: int
        :param month: month
        :type month: int
        :param day: day
        :type day: int
        :param date_string: date_string
        :type date_string: str
        :param date_mapper: an optional mapper object to map dates to various dates based on the
        type of text, the type of resolutions and the period.
        :type date_mapper: DateNameMapper
        """
        if date_string:
            date = parse(date_string).date()
        else:
            date = datetime.date(year, month, day)

        # print(date, date.year, date.month, date.day)
        self.date_mapper = date_mapper
        self.date = date
        self.year = date.year
        self.month = date.month
        self.day = date.day
        for week_day_name in week_day_names['modern_nl']:
            if week_day_names['modern_nl'][week_day_name] == self.date.weekday():
                self.day_name = week_day_name
        for month_name in month_names['modern_nl']:
            if month_names['modern_nl'][month_name] == self.month:
                self.month_name = month_name
        self.date_string = None
        self.date_year_string = None
        if date_mapper:
            # print(f'RepublicDate - generate_day_string for date {date.isoformat()}')
            self.date_string = date_mapper.generate_day_string(date.year, date.month, date.day, include_year=False)
            if self.date_string is None:
                print(f'RepublicDate - date_string is Noe for date {date.isoformat()}')
            self.date_year_string = date_mapper.generate_day_string(date.year, date.month, date.day,
                                                                    include_year=True)

    def __repr__(self):
        return f'RepublicDate({self.date.strftime("%Y-%m-%d")})'
        # return f'RepublicDate({self.isoformat()})'

    def __add__(self, other: Union[RepublicDate, datetime.date, datetime.timedelta]):
        if isinstance(other, RepublicDate) or other.__class__.__name__ == 'RepublicDate':
            return self.date + other.date
        elif isinstance(other, datetime.timedelta):
            return self.date + other
        elif isinstance(other, datetime.date):
            return self.date + other

    def __sub__(self, other: Union[RepublicDate, datetime.date, datetime.timedelta]):
        if isinstance(other, RepublicDate) or other.__class__.__name__ == 'RepublicDate':
            return self.date - other.date
        elif isinstance(other, datetime.timedelta):
            return self.date - other
        elif isinstance(other, datetime.date):
            return self.date - other
        else:
            print('self:', self, type(self), self.__class__.__name__)
            print('other:', other, type(other), other.__class__.__name__)
            print('type(self) == type(other):', type(self) == type(other))
            raise TypeError(f'other must be RepublicDate, datetime.date or datetime.timedelta, not {type(other)}')

    def __lt__(self, other):
        return self.date < other.date

    def __le__(self, other):
        return self.date <= other.date

    def __gt__(self, other):
        return self.date > other.date

    def __ge__(self, other):
        return self.date >= other.date

    def __eq__(self, other):
        return self.date == other.date

    def __ne__(self, other):
        return self.date != other.date

    # def __cmp__(self, other):
    #     """Override comparison operations to use the date properties for comparison."""
    #     assert(isinstance(other, RepublicDate))
    #     if self.date < other.date:
    #         return -1
    #     elif self.date == other.date:
    #         return 0
    #     else:
    #         return 1

    def as_date_string(self):
        return self.date.strftime("%Y-%m-%d")

    def isoformat(self):
        return self.date.isoformat()

    def is_holiday(self) -> bool:
        """Return boolean whether current date is a holiday."""
        for holiday in get_holidays(self.year, date_mapper=self.date_mapper):
            if self.isoformat() == holiday['date'].isoformat():
                return True
        return False

    def is_rest_day(self) -> bool:
        """Return boolean whether current date is a rest day, either a holiday or a weekend day.
        Before 1754, that only includes Sundays, from 1754, it also includes Saturdays"""
        if is_exception_work_day(self):
            return False
        if self.is_holiday():
            return True
        elif self.year >= 1754 and self.month == 12 and self.day in [23, 27] and self.date.weekday() == 5:
            # this is an exception: after two holidays that are normally work days (Christmas)
            # the SG meets on the Saturday after Christmas if christmas starts on Thursday
            # or if christmas starts on Monday.
            return False
        elif self.year >= 1754 and self.date.weekday() == 5:
            # 5 is Saturday
            return True
        elif self.date.weekday() == 6:
            # 6 is Sunday
            return True
        else:
            return False

    def is_work_day(self) -> bool:
        """Return boolean whether current date is a work day in which the States General meet.
        This is the inverse of is_rest_day."""
        return not self.is_rest_day()


def extract_date_name_map(text_type: str, resolution_type: str,
                          period_start: int, period_end: int) -> Dict[str, any]:
    if text_type not in {'handwritten', 'printed'}:
        raise ValueError(f'invalid text_type "{text_type}", should be "handwritten" or "printed".')
    if resolution_type not in {'ordinaris', 'secreet', 'speciaal'}:
        raise ValueError(f'invalid resolution_type "{resolution_type}", should be "ordinaris", '
                         f'"secreet" or "speciaal".')
    for date_name_map in default_date_name_map:
        if date_name_map['text_type'] != text_type:
            continue
        if date_name_map['resolution_type'] != resolution_type:
            continue
        if date_name_map['period_start'] != period_start:
            continue
        if date_name_map['period_end'] != period_end:
            continue
        return date_name_map
    raise ValueError(f'The default_date_name_map has no mapping with the given text_type "{text_type}", '
                     f'resolution_type "{resolution_type}" and period_start "{period_start}" '
                     f'and period_end "{period_end}"')


def get_holidays(year: int, date_mapper: DateNameMapper) -> List[Dict[str, Union[str, RepublicDate]]]:
    """Return a list of holidays based on given year."""
    easter_monday = easter(year) + datetime.timedelta(days=1)
    ascension_day = easter(year) + datetime.timedelta(days=39)
    pentecost_monday = easter(year) + datetime.timedelta(days=50)
    holidays = [
        {'holiday': 'Nieuwjaarsdag', 'date': RepublicDate(year, 1, 1, date_mapper=date_mapper)},
        {'holiday': 'eerste Kerstdag', 'date': RepublicDate(year, 12, 25, date_mapper=date_mapper)},
        {'holiday': 'tweede Kerstdag', 'date': RepublicDate(year, 12, 26, date_mapper=date_mapper)},
        {'holiday': 'tweede Paasdag', 'date': RepublicDate(year, easter_monday.month, easter_monday.day,
                                                           date_mapper=date_mapper)},
        {'holiday': 'Hemelvaartsdag', 'date': RepublicDate(year, ascension_day.month, ascension_day.day,
                                                           date_mapper=date_mapper)},
        {'holiday': 'tweede Pinksterdag', 'date': RepublicDate(year, pentecost_monday.month,
                                                               pentecost_monday.day, date_mapper=date_mapper)},
    ]
    if year == 1705:
        holidays.append({'holiday': 'Vast- en Bededag', 'date': RepublicDate(year, 6, 24, date_mapper=date_mapper)})
    if year == 1710:
        holidays.append({'holiday': 'Vast- en Bededag', 'date': RepublicDate(year, 5, 14, date_mapper=date_mapper)})
    return holidays


def is_exception_work_day(current_date: RepublicDate):
    date_string = current_date.date.isoformat()
    if date_string not in exception_dates:
        return False
    if 'mistake' not in exception_dates[date_string]:
        return False
    if exception_dates[date_string]['mistake'] == 'this day is a work day':
        return True
    return False


def get_holiday_phrases(year: int, date_mapper: DateNameMapper) -> List[Dict[str, Union[str, int, bool, RepublicDate]]]:
    """Return a list of holiday-specific phrases based on given year."""
    holidays = get_holidays(year, date_mapper=date_mapper)
    year_holiday_phrases: List[Dict[str, Union[str, int, bool, RepublicDate]]] = []
    for holiday in holidays:
        for holiday_phrase in holiday_phrases:
            if holiday['holiday'] in holiday_phrase['phrase']:
                year_holiday_phrase = copy.copy(holiday_phrase)
                year_holiday_phrase['date'] = holiday['date']
                year_holiday_phrases.append(year_holiday_phrase)
    return year_holiday_phrases


def get_coming_holidays_phrases(current_date: RepublicDate,
                                date_mapper: DateNameMapper,
                                debug: int = 0) -> List[Dict[str, Union[str, int, bool, RepublicDate]]]:
    """Return a list of holiday phrases in the next seven days."""
    year_holiday_phrases = get_holiday_phrases(current_date.year, date_mapper=date_mapper)
    coming_holiday_phrases: List[Dict[str, Union[str, int, bool, datetime.date]]] = []
    for holiday_phrase in year_holiday_phrases:
        if debug > 0:
            print("type(current_date):", type(current_date))
            print("type(current_date.date):", type(current_date.date))
            print("type(holiday_phrase['date']):", type(holiday_phrase['date']))
            print("current_date:", current_date)
            print("holiday_phrase['date']:", holiday_phrase['date'])
        if holiday_phrase['date'].__class__.__name__ != 'RepublicDate':
            print('holiday_phrase["date"] must be a RepublicDate:', type(holiday_phrase['date']))
        if current_date.__class__.__name__ != 'RepublicDate':
            print('current_date is not RepublicDate:', type(current_date))
        date_diff = holiday_phrase['date'] - current_date
        if debug > 0:
            print('date_diff:', date_diff)
        if date_diff.days < 7:
            coming_holiday_phrases.append(holiday_phrase)
    return coming_holiday_phrases


def is_session_date_exception(current_date: RepublicDate,
                              unused_exception_dates: Dict[str, Dict[str, any]]) -> bool:
    date = current_date.isoformat()
    return date in unused_exception_dates


def get_date_exception_shift(current_date: RepublicDate,
                             unused_exception_dates: Dict[str, Dict[str, any]]) -> int:
    date = current_date.isoformat()
    return unused_exception_dates[date]["shift_days"]


def get_next_workday(current_date: RepublicDate, date_mapper: DateNameMapper = None,
                     debug: int = 0) -> Union[RepublicDate, None]:
    next_day = get_next_day(current_date, date_mapper)
    if debug > 0:
        print(f"republic_date.get_next_workday - initial current_date: {current_date.isoformat()}")
        print(f"republic_date.get_next_workday - initial next_day: {next_day.isoformat()}")
    loop_count = 0
    while next_day.is_rest_day():
        if loop_count > 7:
            print("STUCK IN WHILE LOOP, BREAKING OUT")
            print("current_date", current_date.isoformat())
            break
        next_day = get_next_day(next_day, date_mapper=date_mapper)
        if next_day.year != current_date.year:
            return None
        loop_count += 1
    if debug > 0:
        print(f"republic_date.get_next_workday - final current_date: {current_date.isoformat()}")
        print(f"republic_date.get_next_workday - final next_day: {next_day.isoformat()}")
    return next_day


def get_previous_workday(current_date: RepublicDate, date_mapper: DateNameMapper = None) -> Union[RepublicDate, None]:
    previous_day = get_previous_day(current_date, date_mapper=date_mapper)
    while previous_day.is_rest_day():
        previous_day = get_previous_day(previous_day, date_mapper=date_mapper)
        if previous_day.year != current_date.year:
            return None
    return previous_day


def get_next_day(current_date: RepublicDate, date_mapper: DateNameMapper = None) -> RepublicDate:
    next_day = current_date.date + datetime.timedelta(days=1)
    return RepublicDate(next_day.year, next_day.month, next_day.day, date_mapper=date_mapper)


def get_previous_day(current_date: RepublicDate, date_mapper: DateNameMapper = None) -> RepublicDate:
    previous_day = current_date.date - datetime.timedelta(days=1)
    return RepublicDate(previous_day.year, previous_day.month, previous_day.day, date_mapper=date_mapper)


def get_next_date_strings(current_date: RepublicDate, date_mapper: DateNameMapper,
                          num_dates: int = 3, include_year: bool = True,
                          loop_year: bool = False, debug: int = 0) -> Dict[str, RepublicDate]:
    debug_prefix = 'republic_date.get_next_date_strings'
    if debug > 0:
        print(f'{debug_prefix} - 1 current_date:', current_date)
    date_strings = {}
    if not current_date:
        # if for some reason current_date is None, return an empty dict
        return date_strings
    loop_date = current_date
    for i in range(0, num_dates):
        if debug > 0:
            print('\tstart - 2. loop_date:', loop_date, type(loop_date.date_string))
        if isinstance(loop_date.date_string, str):
            if include_year:
                date_strings[loop_date.date_year_string] = loop_date
                if debug > 0:
                    print(f'\t - 3. adding loop_date {loop_date.date_year_string}')
            else:
                date_strings[loop_date.date_string] = loop_date
                if debug > 0:
                    print(f'\t - 3. adding loop_date {loop_date.date_string}')
        elif isinstance(loop_date.date_string, list):
            loop_date_strings = loop_date.date_year_string if include_year else loop_date.date_string
            for date_string in loop_date_strings:
                date_strings[date_string] = loop_date
                if debug > 0:
                    print(f'\t - 3. adding loop_date {date_string}')
        loop_date = get_next_day(loop_date, date_mapper)
        if debug > 0:
            print('\tnext_day - 4. loop_date:', loop_date, type(loop_date.date_string))
            print('\t\t - 5. date_strings:', date_strings.keys())
        if not loop_date:
            break
        if loop_year is False and loop_date.year != current_date.year:
            # avoid going beyond December 31 into the next year
            continue
    if debug > 0:
        print('\nget_next_date_strings - 6. current_date:', current_date)
    return date_strings


def is_date_string(date_string: str) -> bool:
    return re.match(r"^\d{4}-\d{2}-\d{2}$", date_string) is not None


def make_republic_date(date_string: str) -> RepublicDate:
    if not is_date_string(date_string):
        raise ValueError("Valid date string is yyyy-mm-dd")
    year, month, day = [int(part) for part in date_string.split("-")]
    return RepublicDate(year=year, month=month, day=day)


def derive_date_from_string(date_string: str, year: int, date_mapper: DateNameMapper) -> RepublicDate:
    """Return a RepublicDate object derived from a session date string."""
    weekday, _, day_num, month_name = date_string.split(' ')
    day_num = int(day_num)
    month = date_mapper.date_name_map['month_name'][month_name]
    date = RepublicDate(year, month, day_num, date_mapper=date_mapper)
    return date


def get_shifted_date(current_date: RepublicDate, day_shift: int, date_mapper: DateNameMapper) -> RepublicDate:
    new_date = current_date.date + datetime.timedelta(days=day_shift)
    return RepublicDate(new_date.year, new_date.month, new_date.day, date_mapper=date_mapper)
