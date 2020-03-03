import re
import datetime
from typing import List, Union, Dict
from republic.model.republic_phrase_model import resolution_phrases, participant_list_phrases
from republic.model.republic_phrase_model import week_day_names, week_day_name_map
from republic.model.republic_phrase_model import month_names_early, month_names_late, month_map_late, month_map_early
from republic.model.republic_hocr_model import HOCRPage, HOCRColumn, HOCRParagraph, HOCRLine, HOCRWord


def is_empty_line(line: HOCRLine) -> bool:
    return line.num_words == 0


def get_page_metadata(hocr_page: HOCRPage) -> Dict[str, int]:
    return {
        "inventory_num": hocr_page.inventory_num,
        "inventory_year": hocr_page.inventory_year,
        "type_page_num": hocr_page.type_page_num,
    }


def initialize_paragraph_metadata(paragraph_lines: list, paragraph_num: int, hocr_page: HOCRPage) -> dict:
    paragraph = {"metadata": get_page_metadata(hocr_page), "lines": paragraph_lines}
    paragraph_text = merge_paragraph_lines(paragraph)
    paragraph["metadata"]["categories"] = set()
    paragraph["text"] = paragraph_text
    paragraph["metadata"]["paragraph_num_on_page"] = paragraph_num
    paragraph["metadata"]["paragraph_id"] = "{}-para-{}".format(hocr_page.page_id, paragraph_num)
    return paragraph


def track_meeting_date(paragraph: dict, matches: list, current_date: dict, config: dict) -> dict:
    if len(matches) == 0 and paragraph_starts_with_centered_date(paragraph, config):
        print("DATE LINE:", paragraph["text"])
        current_date = extract_meeting_date(paragraph, config, current_date)
    if matches_participant_list(matches):
        print("DAY START:", paragraph["text"])
        if paragraph_has_centered_date(paragraph, config):
            current_date = extract_meeting_date(paragraph, config, current_date)
            paragraph["metadata"]["categories"].add("meeting_date")
        paragraph["metadata"]["type"] = "participant_list"
    paragraph["metadata"]["meeting_date_info"] = current_date
    if current_date:
        try:
            paragraph["metadata"]["meeting_date"] = datetime.date(current_date["year"], current_date["month"], current_date["month_day"])
        except ValueError:
            pass
    return current_date


def get_resolution_page_paragraphs(hocr_page: HOCRPage, config: dict) -> tuple:
    paragraphs = []
    header = []
    # TODO: improve to allow paragraphs to run across two subsequent pages
    for column in hocr_page.columns: #page_doc["columns"]:
        paragraph_num = len(paragraphs) + 1
        paragraph_lines = []  # reset paragraph_lines at the beginning of each column
        prev_line_bottom = None
        for line in column.lines:
            boundary = False
            if is_empty_line(line):
                continue
            if prev_line_bottom is None:
                prev_line_bottom = line.bottom
                paragraph_lines.append(line)
                continue
            line_gap = line.top - prev_line_bottom
            if line_gap > 30:  # boundary between top of this line and bottom of previous line
                boundary = True
            elif line_gap > 10 and line_is_centered_date(line, config):
                boundary = True
            if boundary and prev_line_bottom < 400:
                header += paragraph_lines
                paragraph_lines = []  # start new paragraph, ignore header line
            elif boundary:
                paragraph = initialize_paragraph_metadata(paragraph_lines, paragraph_num, hocr_page)
                paragraphs.append(paragraph)
                paragraph_lines = []
            paragraph_lines.append(line)
            prev_line_bottom = line.bottom
        if len(paragraph_lines) > 0:
            paragraph = initialize_paragraph_metadata(paragraph_lines, paragraph_num, hocr_page)
            paragraphs.append(paragraph)
    return paragraphs, header


def get_resolution_paragraphs(hocr_page: HOCRPage, config: dict) -> List[HOCRParagraph]:
    paragraphs = []
    paragraph_lines = []
    paragraph_num = len(paragraphs) + 1
    paragraph_id = "{}-para-{}".format(hocr_page.page_id, paragraph_num)
    for column in hocr_page.columns:
        for line_index, line in enumerate(column.lines):
            #print(line_index, "({}, {}) ({}-{})".format(line.top, line.bottom, line.distance_to_prev, line.distance_to_next), line.line_text)
            boundary = False
            if is_empty_line(line) or is_header_line(line, column):
                continue
            if line.distance_to_prev and line.distance_to_prev > 80:
                boundary = True
            elif line.distance_to_prev and line.distance_to_prev > 50 and line_is_centered_date(line, config):
                boundary = True
            if boundary and len(paragraph_lines) > 0:
                paragraph = HOCRParagraph(paragraph_lines, paragraph_id, paragraph_num)
                paragraphs.append(paragraph)
                paragraph_lines = []
                paragraph_num = len(paragraphs) + 1
                paragraph_id = "{}-para-{}".format(hocr_page.page_id, paragraph_num)
            paragraph_lines.append(line)
    if len(paragraph_lines) > 0:
        paragraph = HOCRParagraph(paragraph_lines, paragraph_id, paragraph_num)
        paragraphs.append(paragraph)
    return paragraphs


def is_header_line(line: HOCRLine, column: HOCRColumn) -> bool:
    if line.top > 400:
        return False
    if len(line.line_text) > 20:
        return False
    else:
        return True


def line_has_week_day_name(line: HOCRLine) -> bool:
    return line_has_word_from_list(line, week_day_names)


def line_has_month_name(line: HOCRLine, config: dict) -> bool:
    month_names = month_names_late if config['year'] > 1750 else month_names_early
    return line_has_word_from_list(line, month_names)


def word_is_number(word: HOCRWord) -> bool:
    if word.word_text.isdigit():
        return True
        # return int(word["word_text"])
    # TODO: do fuzzy number matching
    match = re.match(r"(\d+)", word.word_text)
    if match:
        return True  # very hacky
        # return match.group(1)
    return False


def get_word_number(word: HOCRWord) -> Union[int, None]:
    if word.word_text.isdigit():
        return int(word.word_text)
    # TODO: do fuzzy number matching
    match = re.match(r"(\d+)", word.word_text)
    if match:
        return int(match.group(1))
    return None


def line_has_month_day(line: HOCRLine, config: dict) -> bool:
    month_names = month_names_late if config['year'] > 1750 else month_names_early
    if len(line.words) < 2:
        return False  # single word lines have no day and month
    try:
        for word_index, word in enumerate(line.words[:-1]):
            next_word = line.words[word_index + 1]
            if word_is_number(word) and word_is_in_list(next_word, month_names):
                return True
    except ValueError:
        print(line)
    return False


def get_month_days_from_line(line: HOCRLine, config: dict) -> List[Dict[str, Union[str, int, float]]]:
    month_names = month_names_late if config['year'] > 1750 else month_names_early
    month_day_words = []
    if len(line.words) < 2:
        return month_day_words  # single word lines have no day and month
    for word_index, word in enumerate(line.words[:-1]):
        next_word = line.words[word_index + 1]
        if word_is_number(word) and word_is_in_list(next_word, month_names):
            month_day_words.append({"word": word, "match": get_word_number(word), "score": 1.0})
    return month_day_words


def get_month_day_from_line(line: HOCRLine, config: dict) -> Dict[str, Union[str, int, None, float]]:
    # HACK: return first month day from line
    try:
        return get_month_days_from_line(line, config)[0]
    except IndexError:
        return {"word": None, "match": None, "score": 0.0}


def get_month_names_from_line(line: HOCRLine, config: dict) -> list:
    month_names = month_names_late if config['year'] > 1750 else month_names_early
    return line_get_words_from_list(line, month_names)


def get_month_name_from_line(line: HOCRLine, config: dict):
    # HACK: return first month_name in line
    return get_month_names_from_line(line, config)[0]


def get_week_day_names_from_line(line: HOCRLine) -> List[Dict[str, Union[HOCRWord, str, float]]]:
    return line_get_words_from_list(line, week_day_names)


def get_week_day_name_from_line(line: HOCRLine) -> Dict[str, Union[HOCRWord, str, float]]:
    # HACK: return first week_day_name in line
    return get_week_day_names_from_line(line)[0]


def get_date_from_line(line: HOCRLine, config: dict) -> dict:
    month_map = month_map_early if config['year'] <= 1750 else month_map_late
    return {
        "month_day": get_month_day_from_line(line, config)["match"],
        "month_name": get_month_name_from_line(line, config)["match"],
        "month": month_map[get_month_name_from_line(line, config)["match"]],
        "week_day_name": get_week_day_name_from_line(line)["match"],
        "year": config['year'],
    }


def word_is_in_list(word: HOCRWord, word_list: List[str]):
    best_match = None
    best_score = 1
    for list_word in word_list:
        score = score_levenshtein_distance(word.word_text, list_word)
        relative_score = score / len(list_word)
        if relative_score < 0.4:
            if relative_score < best_score:
                best_match = list_word
                best_score = relative_score
    if best_match:
        # print("#{}# #{}#".format(line_word["word_text"], best_match), best_score)
        return True
    return False


def line_get_words_from_list(line: HOCRLine, word_list: List[str]) -> List[Dict[str, Union[HOCRWord, str, float]]]:
    line_words_from_list = []
    for line_word in line.words:
        best_match = None
        best_score = 1
        for list_word in word_list:
            score = score_levenshtein_distance(line_word.word_text, list_word)
            relative_score = score / len(list_word)
            if relative_score < 0.4:
                if relative_score < best_score:
                    best_match = list_word
                    best_score = relative_score
        if best_match:
            line_words_from_list.append({"word": line_word, "match": best_match, "score": best_score})
    return line_words_from_list


def line_has_word_from_list(line: HOCRLine, word_list: List[str]) -> bool:
    for line_word in line.words:
        best_match = None
        best_score = 1
        for list_word in word_list:
            score = score_levenshtein_distance(line_word.word_text, list_word)
            relative_score = score / len(list_word)
            if relative_score < 0.4:
                if relative_score < best_score:
                    best_match = list_word
                    best_score = relative_score
        if best_match:
            # print("#{}# #{}#".format(line_word["word_text"], best_match), best_score)
            return True
    return False


def line_is_centered_text(line: HOCRLine, left_offset: int=200, right_offset: int=800) -> bool:
    return line.words[0].left >= left_offset and line.words[-1].right <= right_offset


def line_has_date(line: HOCRLine, config: dict) -> bool:
    if line_has_week_day_name(line) and line_has_month_name(line, config):
        # print("\n\tCentered date line (based on week_day month pattern):\t", line["line_text"])
        return True
    if line_has_week_day_name(line) and line_has_month_day(line, config):
        # print("\n\tCentered date line (based on day month pattern):\t", line["line_text"])
        return True
    # line has week_day den number month
    return False


def line_is_centered_date(line: HOCRLine, config: dict) -> bool:
    # line is centered
    if not line_is_centered_text(line):
        return False
    if line_has_week_day_name(line) and line_has_month_name(line, config):
        # print("\n\tCentered date line (based on week_day month pattern):\t", line["line_text"])
        return True
    if line_has_week_day_name(line) and line_has_month_day(line, config):
        # print("\n\tCentered date line (based on day month pattern):\t", line["line_text"])
        return True
    # line has week_day den number month
    return False


def paragraph_has_date(paragraph, config):
    for line in paragraph["lines"]:
        if line_has_date(line, config):
            return True
    return False


def paragraph_has_centered_date(paragraph: dict, config: dict) -> bool:
    for line in paragraph["lines"]:
        if line_is_centered_date(line, config):
            return True
    return False


def paragraph_starts_with_centered_date(paragraph: dict, config: dict) -> bool:
    if line_is_centered_date(paragraph["lines"][0], config):
        return True
    return False


def merge_paragraph_lines(paragraph: dict) -> str:
    paragraph_text = ""
    for line in paragraph["lines"]:
        if line.line_text[-1] == "-":
            paragraph_text += line.line_text[:-1]
        else:
            paragraph_text += line.line_text + " "
    return paragraph_text


def extract_meeting_date(paragraph: dict, config: dict,
                         previous_date: Dict[str, Union[int, str]]) -> dict:
    current_date = None
    for line in paragraph["lines"]:
        if line_has_date(line, config):
            current_date = get_date_from_line(line, config)
            break
    if not current_date:
        raise ValueError("Cannot locate meeting date in this paragaraph")
    if current_date["month_day"] is None:
        print("DERIVING MEETING DATE FROM PREVIOUS DATE")
        current_date = derive_month_day_from_previous_date(previous_date, current_date)
        print(current_date)
    return current_date


def derive_month_day_from_previous_date(previous_date: Dict[str, Union[int, str]],
                                        current_date: Dict[str, Union[int, str]]) -> Dict[str, Union[str, int, datetime.date]]:
    day_shift = get_day_shift(current_date["week_day_name"], previous_date["week_day_name"])
    curr_date = shift_date(previous_date, day_shift)
    if curr_date.month != current_date["month"]:
        raise (
            "Date derivation error. Derived month '{}' is not the same as extracted month '{}'".format(curr_date.month,
                                                                                                       current_date[
                                                                                                           "month"]))
    if curr_date.year != current_date["year"]:
        raise ("Date derivation error. Derived year '{}' is not the same as extracted year '{}'".format(curr_date.year,
                                                                                                        current_date[
                                                                                                            "year"]))
    return {
        "month_day": curr_date.day,
        "month_name": current_date["month_name"],
        "month": current_date["month"],
        "week_day_name": current_date["week_day_name"],
        "year": current_date["year"]
    }


def get_day_shift(curr_week_day: str, prev_week_day: str) -> int:
    day_shift = week_day_name_map[curr_week_day] - week_day_name_map[prev_week_day]
    if day_shift < 0:
        day_shift += 7
    elif day_shift == 0:
        raise ValueError(
            "Too large gap between subsequent meeting dates!\n\tprevious weekday: {}\n\tcurrent weekday: {}".format(
                prev_week_day, curr_week_day))
    return day_shift


def shift_date(previous_date: Dict[str, int], day_shift: int) -> datetime.date:
    return generate_meeting_date(previous_date) + datetime.timedelta(days=day_shift)


def generate_meeting_date(current_date: Dict[str, int]) -> datetime.date:
    return datetime.date(current_date["year"], current_date["month"], current_date["month_day"])


def matches_resolution_phrase(matches: List[Dict[str, Union[str, int, float, None]]]) -> bool:
    for match in matches:
        if match["match_keyword"] in resolution_phrases:
            return True
    return False


def matches_participant_list(matches: List[Dict[str, Union[str, int, float, None]]]) -> bool:
    for match in matches:
        if match["match_keyword"] in participant_list_phrases:
            return True
    return False


def score_levenshtein_distance(s1: str, s2: str) -> int:
    if len(s1) > len(s2):
        s1, s2 = s2, s1
    distances = range(len(s1) + 1)
    for i2, c2 in enumerate(s2):
        distances_ = [i2 + 1]
        for i1, c1 in enumerate(s1):
            if c1 == c2:
                distances_.append(distances[i1])
            else:
                distances_.append(1 + min((distances[i1], distances[i1 + 1], distances_[-1])))
        distances = distances_
    return distances[-1]


def initialize_current_date(inventory_config: dict) -> dict:
    year = inventory_config["year"]
    current_date = {
        "month_day": 1,
        "month_name": "Januarii",
        "month": 1,
        "week_day_name": None,
        "year": year
    }
    return current_date


