import datetime
import glob
import gzip
import os
import re
from dateutil.parser import parse as date_parse
from typing import Dict, Tuple


class Transaction:

    def __init__(self, timestamp: datetime.datetime, text_query: str, facets: Dict[str, any],
                 date_from: datetime.date, date_to: datetime.date,
                 res_length_min: int, res_length_max: int, hits_from: int, size: int):
        self.timestamp = timestamp
        self.text_query = text_query
        self.facets = facets
        self.date_from = date_from
        self.date_to = date_to
        self.res_length_min = res_length_min
        self.res_length_max = res_length_max
        self.hits_from = hits_from
        self.size = size

    def __repr__(self):
        timestamp = self.timestamp.isoformat() if self.timestamp else None
        date_from = self.date_from.isoformat() if self.date_from else None
        date_to = self.date_to.isoformat() if self.date_to else None
        return (f"Transaction(\n\ttimestamp={timestamp}"
                f"\n\ttext_query='{self.text_query}'"
                f"\n\tfacets='{self.facets}'"
                f"\n\tdate_range='{date_from} - {date_to}'"
                f"\n\tres_length='{self.res_length_min} - {self.res_length_max}'"
                f"\n\tfrom='{self.hits_from}'"
                f"\n\tsize='{self.size}'"
                f"\n)")

    def json(self):
        return {
            'timestamp': self.timestamp
        }


def parse_date_range(date_range: str) -> Tuple[datetime.date, datetime.date]:
    """Parse the date range of a search query.

    :param date_range: the date range within which all returned resolutions must be selected
    :return: tuple(datetime.date, datetime.date)
    """
    if date_range == '':
        date_from = "1576-01-01"
        date_to = "1796-12-31"
    elif 'undefined' in date_range:
        return None, None
    elif m := re.match(r"sessionDate:\[(\d{4}-\d{2}-\d{2}),(\d{4}-\d{2}-\d{2})]", date_range):
        date_from = m.group(1)
        date_to = m.group(2)
    elif m := re.match(r"created_at:\[(\d{4}-\d{2}-\d{2}),(\d{4}-\d{2}-\d{2})]", date_range):
        date_from = m.group(1)
        date_to = m.group(2)
    else:
        return None, None
        # raise ValueError(f"unexpected date_range format '{date_range}'")
    return date_parse(date_from), date_parse(date_to)


def parse_res_length(res_length: str) -> Tuple[int, int]:
    """

    :param res_length: the length range of resolutions (consisting of the minimum and maximum length)
    :return: a tuple of integers for the minimum and maximum length
    """
    if res_length == '':
        res_length_min = 0
        res_length_max = 66000
    elif m := re.match(r"text.tokenCount:\[(\d+),(\d+)]", res_length):
        res_length_min = int(m.group(1))
        res_length_max = int(m.group(2))
    else:
        return None, None
        # raise ValueError(f"unexpected res_length format '{res_length}'")
    return res_length_min, res_length_max


def parse_facets(facets: str) -> Dict[str, any]:
    """Parse the dictionary of selected facet keys and values into a Python dictionary

    Example: {commissionName=[Zaken van de Oost-Indische Compagnie]}

    :param facets:
    :return:
    """
    if facets == '':
        return {}
    facet_dict = {}
    m = re.match(r"{(.*?)}", facets)
    facets_string = m.group(1)
    for m in re.finditer(r"((\w+)=\[(.*?)])", facets_string):
        facet_key = m.group(2)
        facet_value = m.group(3)
        facet_dict[facet_key] = facet_value
    return facet_dict


def parse_pagination(hits_from: str, size: str) -> Tuple[int, int]:
    if m := re.match(r"from=(\d+)", hits_from):
        hits_from = m.group(1)
    else:
        raise ValueError(f"unexpected hits_from format '{hits_from}'")
    if m := re.match(r"size=(\d+)", size):
        size = m.group(1)
    else:
        raise ValueError(f"unexpected size format '{size}'")
    return hits_from, size


def is_pipe_or(fields: str):
    if len(fields) == 8:
        return False
    if m := re.match(r"(sessionDate|text.tokenCount|created_at)=", fields[2]):
        return False
    if fields[2].isalpha():
        return True


def parse_log_line(log_file: str, line_idx: int, log_line: str):
    fields = log_line.strip('\n').split('|')
    try:
        timestamp, text_query, facets, date_range, res_length, hits_from, size, _ = fields
        if res_length.startswith('sessionDate') or res_length.startswith('created_at') or date_range.startswith('text.tokenCount'):
            date_range, res_length = res_length, date_range
    except ValueError:
        print(f"{log_file}:{line_idx} - {log_line}")
        print(fields)
        raise ValueError(f"Error parsing line {line_idx+1} in file {log_file}, "
                         f"expected 8 fields but received {len(fields)}.")
    try:
        timestamp = date_parse(timestamp)
    except ValueError:
        print(f"{log_file}:{line_idx} - {log_line}")
        print(timestamp)
        raise
    try:
        facets = parse_facets(facets)
        date_from, date_to = parse_date_range(date_range)
        res_length_min, res_length_max = parse_res_length(res_length)
        hits_from, size = parse_pagination(hits_from, size)
    except (ValueError, AttributeError):
        print(f"{log_file}:{line_idx} - {log_line}")
        raise
    return Transaction(timestamp, text_query, facets, date_from, date_to,
                       res_length_min, res_length_max, hits_from, size)


def read_log_file(log_file: str):
    with gzip.open(log_file, 'rt') as fh:
        prev_line = None
        concatenate = False
        for li, log_line in enumerate(fh):
            if 'voorbeeldzoekterm' in log_line and 'created_at' in log_line:
                continue
            if concatenate is True and prev_line is not None:
                log_line = prev_line.strip('\n') + log_line
                concatenate = False
            if log_line.strip('\n')[-1] != '|':
                concatenate = True
                prev_line = log_line
                continue
            try:
                yield parse_log_line(log_file, li, log_line)
            except ValueError:
                pass
    return None


def main():
    log_dir = '../../data/logs/'

    log_files = glob.glob(os.path.join(log_dir, '*'))
    for lf in log_files:
        for ti, transaction in enumerate(read_log_file(lf)):
            print(transaction)
            if (ti + 1) >= 10:
                break


if __name__ == "__main__":
    main()
