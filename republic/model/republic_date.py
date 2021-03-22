from typing import Dict, List, Union
import re
import datetime
from dateutil.easter import easter
from dateutil.parser import parse
import copy

from republic.model.republic_phrase_model import month_names_late, month_names_early
from republic.model.republic_phrase_model import holiday_phrases, week_day_names


exception_dates = {
    # the exception date is the day before the date with the mistake, because in updating to the next date
    # it needs to override the computed day shift
    # "1705-03-31": {"mistake": "next day has wrong month name", "shift_days": 1, "month name": "Maert"},
    "1705-09-11": {"mistake": "next day has wrong week day name", "shift_days": 1},
    "1706-02-01": {"mistake": "next day has wrong week day name", "shift_days": 1},
    "1706-05-21": {"mistake": "next day has wrong week day name", "shift_days": 1},
    "1710-06-07": {"mistake": "next work day is a Sunday", "shift_days": 1},
    "1713-03-13": {"mistake": "next day has wrong week day name", "shift_days": 1},
    "1714-05-03": {"mistake": "next day matches with Martis instead of Veneris", "shift_days": 1},
    "1714-06-07": {"mistake": "next day matches with Martis instead of Veneris", "shift_days": 1},
    "1716-02-27": {"mistake": "next day has wrong week day name", "shift_days": 1},
    "1716-12-07": {"mistake": "next day has wrong week day name", "shift_days": 1},
    "1718-05-23": {"mistake": "next day has wrong week day name", "shift_days": 1},
    "1719-01-26": {"mistake": "next day has wrong week day name", "shift_days": 1},
    "1722-12-28": {"mistake": "avoid jump back", "shift_days": 2},
    "1723-10-01": {"mistake": "next day matches Martis instead of Sabbathi", "shift_days": 1},
    "1730-05-15": {"mistake": "next day has wrong week day name", "shift_days": 1},
    "1732-03-11": {"mistake": "next day has wrong week day name", "shift_days": 1},
    "1732-12-22": {"mistake": "next day is misrecognized", "shift_days": 1},
    "1734-04-15": {"mistake": "next day is misrecognized", "shift_days": 1},
    "1735-10-11": {"mistake": "next day has wrong week day name", "shift_days": 1},
    "1744-03-27": {"mistake": "next day is misrecognized", "shift_days": 1},
    "1747-11-13": {"mistake": "next day is misrecognized (Jovis instead of Martis)", "shift_days": 1},
    "1750-02-07": {"mistake": "next day is misrecognized", "shift_days": 3},
    "1762-11-11": {"mistake": "heavy bleed through on many pages", "shift_days": 11},
    "1765-05-29": {"mistake": "heavy bleed through on many pages", "shift_days": 6},
    "1767-11-04": {"mistake": "bad OCR causes week of sessions missed", "shift_days": 7},
    "1771-07-02": {"mistake": "next day is misrecognized", "shift_days": 2},
    "1777-05-07": {"mistake": "OCR output is missing columns", "shift_days": 16},
    "1777-05-26": {"mistake": "OCR output is missing columns", "shift_days": 7},
    "1777-10-02": {"mistake": "OCR output is missing columns", "shift_days": 7},
    "1777-10-09": {"mistake": "OCR output is missing columns", "shift_days": 5},
    "1778-04-21": {"mistake": "OCR output is missing columns", "shift_days": 9},
    "1778-10-26": {"mistake": "next day has wrong week day name", "shift_days": 1},
    "1780-12-23": {"mistake": "christmas day has session", "shift_days": 2},
    "1780-12-25": {"mistake": "christmas day has session", "shift_days": 1},
    "1787-05-10": {"mistake": "next Saturday is a work day", "shift_days": 2},
    "1787-05-12": {"mistake": "next Sunday is a work day", "shift_days": 1},
    "1788-12-24": {"mistake": "OCR problems, skip whole week", "shift_days": 7},
    "1791-02-15": {"mistake": "next day has wrong week day name", "shift_days": 1},
    "1791-11-30": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1791-12-01": {"mistake": "next Sunday is a work day", "shift_days": 1},
    "1792-03-15": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1792-03-16": {"mistake": "next Sunday is a work day", "shift_days": 1},
    "1794-03-24": {"mistake": "OCR problems, skip whole week", "shift_days": 7},
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
    "1795-01-09": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1795-01-10": {"mistake": "next Sunday is a work day", "shift_days": 1},
    "1795-01-16": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1795-01-17": {"mistake": "next Sunday is a work day", "shift_days": 1},
    "1795-01-23": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1795-01-24": {"mistake": "next Sunday is a work day", "shift_days": 1},
    "1795-03-06": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1795-03-07": {"mistake": "next Sunday is a work day", "shift_days": 1},
    "1795-05-15": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1795-05-16": {"mistake": "next Sunday is a work day", "shift_days": 1},
    "1795-05-29": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1795-05-30": {"mistake": "next Sunday is a work day", "shift_days": 1},
    "1795-06-27": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1795-07-03": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1795-07-10": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1795-07-31": {"mistake": "next Sunday is a work day", "shift_days": 2},
    "1795-08-07": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1795-09-04": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1795-10-30": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1795-11-06": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1795-12-04": {"mistake": "next Saturday is a work day", "shift_days": 1},
    "1795-12-11": {"mistake": "next Sunday is a work day", "shift_days": 2},
}


class RepublicDate:

    def __init__(self, year: int = None, month: int = None, day: int = None, date_string: str = None):
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
        """
        if date_string:
            date = parse(date_string).date()
        else:
            date = datetime.date(year, month, day)
        self.date = date
        self.year = date.year
        self.month = date.month
        self.day = date.day
        self.day_name = week_day_names[self.date.weekday()]
        self.month_name = month_names_early[self.month - 1] if self.year <= 1750 else month_names_late[self.month - 1]
        self.date_string = f"{self.day_name} den {self.day} {self.month_name}"
        self.date_year_string = f"{self.date_string} {self.year}."

    def __repr__(self):
        return f'RepublicDate({self.date.strftime("%Y-%m-%d")})'
        # return f'RepublicDate({self.isoformat()})'

    def __add__(self, other):
        return self.date - other.date

    def __sub__(self, other):
        return self.date - other.date

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

    def __cmp__(self, other):
        """Override comparison operations to use the date properties for comparison."""
        assert(isinstance(other, RepublicDate))
        if self.date < other.date:
            return -1
        elif self.date == other.date:
            return 0
        else:
            return 1

    def as_date_string(self):
        return self.date.strftime("%Y-%m-%m")

    def isoformat(self):
        return self.date.isoformat()

    def is_holiday(self) -> bool:
        """Return boolean whether current date is a holiday."""
        for holiday in get_holidays(self.year):
            if self.isoformat() == holiday['date'].isoformat():
                return True
        return False

    def is_rest_day(self) -> bool:
        """Return boolean whether current date is a rest day, either a holiday or a weekend day.
        Before 1754, that only includes Sundays, from 1754, it also includes Saturdays"""
        if self.is_holiday():
            return True
        elif self.year >= 1754 and self.month == 12 and self.day in [23, 27] and self.day_name == 'Sabbathi':
            # this is an exception: after two holidays that are normally work days (Christmas)
            # the SG meets on the Saturday after Christmas if christmas starts on Thursday
            # or if christmas starts on Monday.
            return False
        elif self.year >= 1754 and self.day_name == 'Sabbathi':
            return True
        elif self.day_name == 'Dominica':
            return True
        else:
            return False

    def is_work_day(self) -> bool:
        """Return boolean whether current date is a work day in which the States General meet.
        This is the inverse of is_rest_day."""
        return not self.is_rest_day()


def get_holidays(year: int) -> List[Dict[str, Union[str, RepublicDate]]]:
    """Return a list of holidays based on given year."""
    easter_monday = easter(year) + datetime.timedelta(days=1)
    ascension_day = easter(year) + datetime.timedelta(days=39)
    pentecost_monday = easter(year) + datetime.timedelta(days=50)
    holidays = [
        {'holiday': 'Nieuwjaarsdag', 'date': RepublicDate(year, 1, 1)},
        {'holiday': 'eerste Kerstdag', 'date': RepublicDate(year, 12, 25)},
        {'holiday': 'tweede Kerstdag', 'date': RepublicDate(year, 12, 26)},
        {'holiday': 'tweede Paasdag', 'date': RepublicDate(year, easter_monday.month, easter_monday.day)},
        {'holiday': 'Hemelvaartsdag', 'date': RepublicDate(year, ascension_day.month, ascension_day.day)},
        {'holiday': 'tweede Pinksterdag', 'date': RepublicDate(year, pentecost_monday.month, pentecost_monday.day)},
    ]
    return holidays


def get_holiday_phrases(year: int) -> List[Dict[str, Union[str, int, bool, RepublicDate]]]:
    """Return a list of holiday-specific phrases based on given year."""
    holidays = get_holidays(year)
    year_holiday_phrases: List[Dict[str, Union[str, int, bool, RepublicDate]]] = []
    for holiday in holidays:
        for holiday_phrase in holiday_phrases:
            if holiday['holiday'] in holiday_phrase['keyword']:
                year_holiday_phrase = copy.copy(holiday_phrase)
                year_holiday_phrase['date'] = holiday['date']
                year_holiday_phrases.append(year_holiday_phrase)
    return year_holiday_phrases


def get_coming_holidays_phrases(current_date: RepublicDate) -> List[Dict[str, Union[str, int, bool, RepublicDate]]]:
    """Return a list of holiday phrases in the next seven days."""
    year_holiday_phrases = get_holiday_phrases(current_date.year)
    coming_holiday_phrases: List[Dict[str, Union[str, int, bool, datetime.date]]] = []
    for holiday_phrase in year_holiday_phrases:
        date_diff = holiday_phrase['date'] - current_date
        if date_diff.days < 7:
            coming_holiday_phrases.append(holiday_phrase)
    return coming_holiday_phrases


def is_session_date_exception(current_date: RepublicDate) -> bool:
    date = current_date.isoformat()
    return date in exception_dates


def get_date_exception_shift(current_date: RepublicDate) -> int:
    date = current_date.isoformat()
    return exception_dates[date]["shift_days"]


def get_next_workday(current_date: RepublicDate) -> Union[RepublicDate, None]:
    next_day = get_next_day(current_date)
    loop_count = 0
    while next_day.is_rest_day():
        if loop_count > 7:
            print("STUCK IN WHILE LOOP, BREAKING OUT")
            print("current_date", current_date.isoformat())
            break
        next_day = get_next_day(next_day)
        if next_day.year != current_date.year:
            return None
        loop_count += 1
    return next_day


def get_previous_workday(current_date: RepublicDate) -> Union[RepublicDate, None]:
    previous_day = get_previous_day(current_date)
    while previous_day.is_rest_day():
        previous_day = get_previous_day(previous_day)
        if previous_day.year != current_date.year:
            return None
    return previous_day


def get_next_day(current_date: RepublicDate) -> RepublicDate:
    next_day = current_date.date + datetime.timedelta(days=1)
    return RepublicDate(next_day.year, next_day.month, next_day.day)


def get_previous_day(current_date: RepublicDate) -> RepublicDate:
    previous_day = current_date.date - datetime.timedelta(days=1)
    return RepublicDate(previous_day.year, previous_day.month, previous_day.day)


def get_next_date_strings(current_date: RepublicDate, num_dates: int = 3, include_year: bool = True) -> List[str]:
    date_strings = []
    if not current_date:
        # if for some reason current_date is None, return an empty list
        return date_strings
    loop_date = current_date
    for i in range(0, num_dates):
        date_strings.append(loop_date.date_year_string if include_year else loop_date.date_string)
        loop_date = get_next_day(loop_date)
        if not loop_date:
            break
        if loop_date.year != current_date.year:
            # avoid going beyond December 31 into the next year
            continue
    return date_strings


def is_date_string(date_string: str) -> bool:
    return re.match(r"^\d{4}-\d{2}-\d{2}$", date_string) is not None


def make_republic_date(date_string: str) -> RepublicDate:
    if not is_date_string(date_string):
        raise ValueError("Valid date string is yyyy-mm-dd")
    year, month, day = [int(part) for part in date_string.split("-")]
    return RepublicDate(year=year, month=month, day=day)


def derive_date_from_string(date_string: str, year: int) -> RepublicDate:
    """Return a RepublicDate object derived from a session date string."""
    weekday, _, day_num, month_name = date_string.split(' ')
    day_num = int(day_num)
    month_names = month_names_early if year <= 1750 else month_names_late
    month = month_names.index(month_name) + 1
    date = RepublicDate(year, month, day_num)
    return date


def get_shifted_date(current_date: RepublicDate, day_shift: int) -> RepublicDate:
    new_date = current_date.date + datetime.timedelta(days=day_shift)
    return RepublicDate(new_date.year, new_date.month, new_date.day)
