import re
from typing import Union


def get_highest_inter_word_space(line: dict) -> int:
    highest_inter_word_space = -1
    for word_index, word in enumerate(line["words"][:-1]):
        next_word = line["words"][word_index + 1]
        inter_word_space = next_word["left"] - word["right"]
        if inter_word_space > highest_inter_word_space:
            highest_inter_word_space = inter_word_space
    return highest_inter_word_space


def has_mid_column_text(line: dict, hocr_page: dict) -> bool:
    for word in line["words"]:
        if word["left"] - hocr_page["left"] > 250 and hocr_page["right"] - word["right"] > 300:
            return True
    return False


def has_left_aligned_text(line: dict, hocr_page: dict) -> bool:
    if line["words"][0]["left"] - hocr_page["left"] > 100:
        return False
    return True


def has_right_aligned_text(line: dict, hocr_page: dict) -> bool:
    if hocr_page["right"] - line["words"][-1]["right"] > 100:
        return False
    return True


def num_line_chars(line: dict) -> int:
    return len(line["line_text"].replace(" ", ""))


def is_header(line: dict, next_line: dict) -> bool:
    if line["top"] > 350:  # if top is above 350, this line is definitely not a header
        return False
    if line["top"] < 150:  # header has some margin form the top of the page, any text in this margin is noise
        return False
    if line["bottom"] > next_line["top"] + 10:  # header has margin with next line
        return True
    if len(line["words"]) == 1:
        return True
    if get_highest_inter_word_space(line) >= 100:  # headers have widely spaced elements
        return True
    return False


def contains_year(line: dict) -> bool:
    for word in line["words"]:
        if looks_like_year(word):
            return True
    return False


def looks_like_year(word: dict) -> bool:
    if re.search(r"\w{6,}", word["word_text"]):  # long alphanumeric word
        return False
    if len(word["word_text"]) < 3:  # very short  word
        return False
    if re.match(r"\d{2,4}", word["word_text"]):  # starting number-like
        return True
    if re.search(r"17\d{1,2}", word["word_text"]):  # containing year string
        return True
    else:
        return False


def is_in_top_margin(line: dict) -> bool:
    if line["top"] < 150:  # index header has some margin form the top of the page
        return True
    return False


def is_full_text_line(line: dict) -> bool:
    return len(line["line_text"].replace(" ", "")) > 25


def is_short_text_line(line: dict) -> bool:
    return len(line["line_text"].replace(" ", "")) < 15


def merge_text_lines(hocr_page: dict) -> str:
    page_text = ""
    for line in hocr_page.lines:
        if line["line_text"][-1] == "-":
            page_text += line["line_text"][:-1]
        else:
            page_text += line["line_text"] + " "
    return page_text


def proper_column_cut(hocr_page: dict) -> bool:
    if hocr_page["width"] < 850:
        return False
    if hocr_page["width"] > 1200:
        return False
    return True


def is_title_page(page_hocr: dict, min_word_height: int = 60, min_char_width: int = 40) -> bool:
    # title page has large word lines in the top half of the page
    # so top of line is below 2000
    large_word_lines = [line for line in get_large_word_lines(page_hocr, min_word_height, min_char_width) if
                        line["top"] < 2000]
    return len(large_word_lines) >= 2


def get_lines(page_hocr: Union[list, dict]) -> list:
    # check what data type is passed for page_hocr: list of lines, a column with lines or a page with columns
    if type(page_hocr) is list and "words" in page_hocr[0]: # list of lines
        return page_hocr
    elif "lines" in page_hocr: # single column with lines
        return page_hocr["lines"]
    elif "columns" in page_hocr: # whole page with columns with lines
        return [line for column in page_hocr["columns"] for line in column["lines"]]
    else:
        return []


def get_large_word_lines(page_hocr: Union[list, dict], min_word_height:int = 100, min_char_width: int = 40) -> iter:
    for line in get_lines(page_hocr):
        num_large_words = 0
        num_words = len(line["words"])
        for word in line["words"]:
            avg_char_width = word["width"] / len(word["word_text"])
            if avg_char_width < min_char_width:
                continue
            if word["height"] >= min_word_height:
                num_large_words += 1
        num_small_words = num_words - num_large_words
        if num_large_words > num_small_words:
            yield line


def get_large_words(page_hocr: dict, min_word_height: int = 100, min_char_width: int = 40) -> iter:
    for line in get_lines(page_hocr):
        for word in line["words"]:
            avg_char_width = word["width"] / len(word["word_text"])
            if avg_char_width < min_char_width:
                continue
            if word["height"] >= min_word_height:
                yield word


def calculate_left_jumps(page_hocr: dict) -> float:
    num_lines = 0
    prev_left = None
    left_jumps = 0
    lefts = []
    for column_hocr in page_hocr["columns"]:
        for line in column_hocr["lines"]:
            if len(line["words"]) == 0:
                continue
            num_lines += 1
            left = line["words"][0]["left"]
            lefts += [left]
            if not prev_left:
                prev_left = left
                continue
            elif abs(left - prev_left) > 200:
                pass
            elif abs(left - prev_left) > 20:
                left_jumps += 1
            prev_left = left
    left_jump_fraction = left_jumps / num_lines
    # print(lefts)
    # print(num_lines, left_jumps, left_jump_fraction)
    return left_jump_fraction


def count_full_text_lines(page_hocr: dict) -> int:
    count = 0
    for column_hocr in page_hocr["columns"]:
        for line in column_hocr["lines"]:
            if is_full_text_line(line):
                count += 1
    return count


def count_short_text_lines(page_hocr: dict) -> int:
    count = 0
    for column_hocr in page_hocr["columns"]:
        for line in column_hocr["lines"]:
            if is_short_text_line(line):
                count += 1
    return count


def get_column_header_line(column_hocr: int) -> Union[dict, None]:
    for line_index, line in enumerate(column_hocr["lines"]):
        if line["top"] > 350:  # if top is above 350, this line is definitely not a header
            break
        next_line = get_next_line(line_index, column_hocr["lines"])
        if is_header(line, next_line):
            return line
    return None


def get_next_line(line_index: int, lines: list) -> Union[dict, None]:
    if len(lines) > line_index + 1:
        return lines[line_index + 1]
    else:
        return None


def get_column_header_lines(page_hocr: dict) -> list:
    return [get_column_header_line(column_hocr) for column_hocr in page_hocr["columns"]]


def get_page_header_words(page_hocr: dict) -> list:
    column_header_lines = get_column_header_lines(page_hocr)
    column_header_lines = [line for line in column_header_lines if line]  # remove None elements
    return [word["word_text"] for line in column_header_lines for word in line["words"]]
