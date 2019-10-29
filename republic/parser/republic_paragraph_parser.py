import re
import datetime
from republic.model.republic_phrase_model import resolution_phrases, participant_list_phrases
from republic.model.republic_phrase_model import month_names, week_day_names, month_map, week_day_name_map


def is_empty_line(line):
    return len(line["words"]) == 0


def get_page_metadata(page_doc):
    return {
        "inventory_num": page_doc["inventory_num"],
        "inventory_year": page_doc["inventory_year"],
        "type_page_num": page_doc["type_page_num"],
    }


def get_resolution_page_paragraphs(page_doc):
    paragraphs = []
    header = []
    # TODO: improve to allow paragraphs to run across two subsequent pages
    for column_hocr in page_doc["columns"]:
        paragraph_lines = []  # reset paragraph_lines at the beginning of each column
        prev_line_bottom = None
        for line in column_hocr["lines"]:
            boundary = False
            if is_empty_line(line):
                continue
            if prev_line_bottom == None:
                prev_line_bottom = line["bottom"]
                paragraph_lines.append(line)
                continue
            line_gap = line["top"] - prev_line_bottom
            if line_gap > 30:  # boundary between top of this line and bottom of previous line
                boundary = True
            elif line_gap > 10 and line_is_centered_date(line):
                boundary = True
            if boundary and prev_line_bottom < 400:
                header += paragraph_lines
                paragraph_lines = []  # start new paragraph, ignore header line
            elif boundary:
                paragraphs.append({"metadata": get_page_metadata(page_doc), "lines": paragraph_lines})
                paragraph_lines = []
            paragraph_lines.append(line)
            prev_line_bottom = line["bottom"]
        if len(paragraph_lines) > 0:
            paragraphs.append({"metadata": get_page_metadata(page_doc), "lines": paragraph_lines})
    return paragraphs, header


def line_has_week_day_name(line):
    return line_has_word_from_list(line, week_day_names)


def line_has_month_name(line):
    return line_has_word_from_list(line, month_names)


def word_is_number(word):
    if word["word_text"].isdigit():
        return True
        # return int(word["word_text"])
    # TODO: do fuzzy number matching
    match = re.match(r"(\d+)", word["word_text"])
    if match:
        return True  # very hacky
        # return match.group(1)
    return False


def get_word_number(word):
    if word["word_text"].isdigit():
        return int(word["word_text"])
    # TODO: do fuzzy number matching
    match = re.match(r"(\d+)", word["word_text"])
    if match:
        return int(match.group(1))
    return None


def line_has_month_day(line):
    if len(line["words"]) < 2:
        return False  # single word lines have no day and month
    try:
        for word_index, word in enumerate(line["words"][:-1]):
            next_word = line["words"][word_index + 1]
            if word_is_number(word) and word_is_in_list(next_word, month_names):
                return True
    except ValueError:
        print(line)
    return False


def get_month_days_from_line(line):
    month_day_words = []
    if len(line["words"]) < 2:
        return month_day_words  # single word lines have no day and month
    for word_index, word in enumerate(line["words"][:-1]):
        next_word = line["words"][word_index + 1]
        if word_is_number(word) and word_is_in_list(next_word, month_names):
            month_day_words.append({"word": word, "match": get_word_number(word), "score": 1.0})
    return month_day_words


def get_month_day_from_line(line):
    # HACK: return first month day from line
    try:
        return get_month_days_from_line(line)[0]
    except IndexError:
        return {"word": None, "match": None, "score": 0.0}


def get_month_names_from_line(line):
    return line_get_words_from_list(line, month_names)


def get_month_name_from_line(line):
    # HACK: return first month_name in line
    return get_month_names_from_line(line)[0]


def get_week_day_names_from_line(line):
    return line_get_words_from_list(line, week_day_names)


def get_week_day_name_from_line(line):
    # HACK: return first week_day_name in line
    return get_week_day_names_from_line(line)[0]


def get_date_from_line(line, year):
    return {
        "month_day": get_month_day_from_line(line)["match"],
        "month_name": get_month_name_from_line(line)["match"],
        "month": month_map[get_month_name_from_line(line)["match"]],
        "week_day_name": get_week_day_name_from_line(line)["match"],
        "year": year,
    }


def word_is_in_list(word, word_list):
    best_match = None
    best_score = 1
    for list_word in word_list:
        score = score_levenshtein_distance(word["word_text"], list_word)
        relative_score = score / len(list_word)
        if relative_score < 0.4:
            if relative_score < best_score:
                best_match = list_word
                best_score = relative_score
    if best_match:
        # print("#{}# #{}#".format(line_word["word_text"], best_match), best_score)
        return True
    return False


def line_get_words_from_list(line, word_list):
    line_words_from_list = []
    for line_word in line["words"]:
        best_match = None
        best_score = 1
        for list_word in word_list:
            score = score_levenshtein_distance(line_word["word_text"], list_word)
            relative_score = score / len(list_word)
            if relative_score < 0.4:
                if relative_score < best_score:
                    best_match = list_word
                    best_score = relative_score
        if best_match:
            line_words_from_list.append({"word": line_word, "match": best_match, "score": best_score})
    return line_words_from_list


def line_has_word_from_list(line, word_list):
    for line_word in line["words"]:
        best_match = None
        best_score = 1
        for list_word in word_list:
            score = score_levenshtein_distance(line_word["word_text"], list_word)
            relative_score = score / len(list_word)
            if relative_score < 0.4:
                if relative_score < best_score:
                    best_match = list_word
                    best_score = relative_score
        if best_match:
            # print("#{}# #{}#".format(line_word["word_text"], best_match), best_score)
            return True
    return False


def line_is_centered_text(line, left_offset=200, right_offset=800):
    return line["words"][0]["left"] >= left_offset and line["words"][-1]["right"] <= right_offset


def line_is_centered_date(line):
    # line is centered
    if not line_is_centered_text(line):
        return False
    if line_has_week_day_name(line) and line_has_month_name(line):
        # print("\n\tCentered date line (based on week_day month pattern):\t", line["line_text"])
        return True
    if line_has_week_day_name(line) and line_has_month_day(line):
        # print("\n\tCentered date line (based on day month pattern):\t", line["line_text"])
        return True
    # line has week_day den number month
    return False


def paragraph_starts_with_centered_date(paragraph):
    if line_is_centered_date(paragraph["lines"][0]):
        return True
    return False


def merge_paragraph_lines(paragraph):
    paragraph_text = ""
    for line in paragraph["lines"]:
        if line["line_text"][-1] == "-":
            paragraph_text += line["line_text"][:-1]
        else:
            paragraph_text += line["line_text"] + " "
    return paragraph_text


def extract_meeting_date(paragraph, year, previous_date):
    for line in paragraph["lines"]:
        if line_is_centered_date(line):
            current_date = get_date_from_line(line, year)
            break
    if current_date["month_day"] == None:
        print("DERIVING MEETING DATE FROM PREVIOUS DATE")
        current_date = derive_month_day_from_previous_date(previous_date, current_date)
        print(current_date)
    return current_date


def derive_month_day_from_previous_date(previous_date, current_date):
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


def get_day_shift(curr_week_day, prev_week_day):
    day_shift = week_day_name_map[curr_week_day] - week_day_name_map[prev_week_day]
    if day_shift < 0:
        day_shift += 7
    elif day_shift == 0:
        raise ValueError(
            "Too large gap between subsequent meeting dates!\n\tprevious weekday: {}\n\tcurrent weekday: {}".format(
                prev_week_day, curr_week_day))
    return day_shift


def shift_date(previous_date, day_shift):
    return generate_meeting_date(previous_date) + datetime.timedelta(days=day_shift)


def generate_meeting_date(current_date):
    return datetime.date(current_date["year"], current_date["month"], current_date["month_day"])


def matches_resolution_phrase(matches):
    for match in matches:
        if match["match_term"] in resolution_phrases:
            return True
    return False


def matches_participant_list(matches):
    for match in matches:
        if match["match_term"] in participant_list_phrases:
            return True
    return False


def score_levenshtein_distance(s1, s2):
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
