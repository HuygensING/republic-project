import re
import copy
import republic_base_page_parser as page_parser
from typing import Union

#################################
# Parse and correct index pages #
#################################

repeat_symbol = "——"


def remove_repeat_symbol(line: dict) -> str:
    return line["line_text"].replace(line["words"][0]["word_text"], "")


def count_repeat_symbols_page(page_hocr: dict) -> int:
    return sum([count_repeat_symbols_column(column_hocr) for column_hocr in page_hocr["columns"]])


def count_repeat_symbols_column(column_hocr: dict) -> int:
    count = 0
    for line in column_hocr["lines"]:
        if has_repeat_symbol(line):
            count += 1
    return count


def has_repeat_symbol(line: dict) -> bool:
    if len(line["words"]) == 0:
        return False
    if re.match(r"^[\-_—]+$", line["words"][0]["word_text"]):
        return True
    else:
        return False


def has_page_reference(line: dict) -> bool:
    if re.match(r"^\d+[\.\:\;,]$", line["words"][-1]["word_text"]):
        return True
    else:
        return False


def line_has_page_ref(line: dict) -> bool:
    return re.search(r"\b\d+\.", line["line_text"]) is not None


def count_page_ref_lines(page_hocr: dict) -> int:
    count = 0
    for column_hocr in page_hocr["columns"]:
        for line in column_hocr["lines"]:
            if line_has_page_ref(line):
                count += 1
    return count


def fix_repeat_symbols_lines(lines: list) -> list:
    return [fix_repeat_symbols_line(line) for line in lines]


def fix_repeat_symbols_line(line: dict) -> dict:
    copy_line = copy.copy(line)
    if has_repeat_symbol(copy_line):
        return copy_line
    first_word = copy_line["words"][0]
    if first_word["left"] > copy_line["left"]:
        print("Gap between line start and first word:", line["left"], first_word["left"], line["line_text"])
    if first_word["width"] > 120 and len(first_word["word_text"]) <= 3:
        print("possibly misrecognised repeat symbol:", first_word["width"], first_word["word_text"])
        copy_line["line_text"] = copy_line["line_text"].replace(first_word["word_text"], repeat_symbol, 1)
        copy_line["spaced_line_text"] = copy_line["spaced_line_text"].replace(first_word["word_text"], repeat_symbol, 1)
        first_word["word_text"] = repeat_symbol
    return copy_line


def get_repeat_symbol_length(lines: list) -> int:
    repeat_symbol_lengths = []
    for line_index, line in enumerate(lines):
        # print("start:", line["words"][0]["word_text"])
        if has_repeat_symbol(line):
            repeat_symbol_lengths += [line["words"][0]["width"]]
    return int(sum(repeat_symbol_lengths) / len(repeat_symbol_lengths))


def add_repeat_symbol(line: dict, avg_repeat_symbol_length: int, minimum_start: int) -> dict:
    copy_line = copy.copy(line)
    avg_char_width = 20
    repeat_symbol_start = line["left"] - avg_char_width - avg_repeat_symbol_length
    if repeat_symbol_start < minimum_start:
        repeat_symbol_start = minimum_start
    copy_line["left"] = repeat_symbol_start
    copy_line["width"] += avg_char_width + avg_repeat_symbol_length
    repeat_symbol = {
        "height": 30,
        "width": avg_repeat_symbol_length,
        "left": repeat_symbol_start,
        "right": repeat_symbol_start + avg_repeat_symbol_length,
        "top": line["top"],
        "bottom": line["bottom"],
        "word_text": "——",
        "word_conf": 50
    }
    copy_line["words"] = [repeat_symbol] + copy_line["words"]
    copy_line["line_text"] = repeat_symbol["word_text"] + " " + copy_line["line_text"]
    copy_line["spaced_line_text"] = re.sub(r"(^ +)(.*)", r"\1" + repeat_symbol["word_text"] + " " + r"\2",
                                           copy_line["spaced_line_text"])
    white_space = " " * round((avg_char_width + avg_repeat_symbol_length) / avg_char_width)
    copy_line["spaced_line_text"] = copy_line["spaced_line_text"].replace(white_space, "")
    return copy_line


def find_missing_repeat_symbols(lines: list) -> list:
    avg_repeat_symbol_length = get_repeat_symbol_length(lines)
    fixed_lines = []
    for line_index, curr_line in enumerate(lines):
        neighbour_lines = get_line_neighbourhood_lines(lines, line_index)
        left_values = [neighbour_line["left"] for neighbour_line in neighbour_lines]
        if curr_line["left"] - min(left_values) > 100:
            print("DEVIATING LINE:", curr_line["left"], left_values, curr_line["line_text"])
            fixed_line = add_repeat_symbol(curr_line, avg_repeat_symbol_length, min(left_values))
            fixed_lines.append(fixed_line)
            print("avg_repeat_symbol_length:", avg_repeat_symbol_length)
        # if curr_line["left"] -
        else:
            fixed_lines.append(copy.deepcopy(curr_line))
    return fixed_lines


def get_line_neighbourhood_lines(lines: list, line_index: int) -> list:
    prev_start, next_end = get_line_neighbourhood(lines, line_index)
    return [lines[index] for index in range(prev_start, next_end)]


def get_line_neighbourhood(lines: list, line_index: int, num_before: int = 4, num_after: int = 4) -> tuple:
    num_lines = len(lines)
    prev_start = line_index - num_before if line_index >= num_before else 0
    next_end = line_index + (num_after + 1) if line_index < num_lines - (num_after + 1) else num_lines
    return prev_start, next_end


def is_page_reference(word: dict) -> bool:
    return re.match(r"^\d+[\.\:\;,]$", word["word_text"]) is not None


def get_page_reference(word: dict) -> int:
    return int(re.sub(r"\D", "", word["word_text"]))


def get_page_references(line: dict) -> list:
    page_refs = []
    for word in line["words"]:
        if is_page_reference(word):
            page_ref = get_page_reference(word)
            page_refs += [page_ref]
    return page_refs


def remove_page_references(line: dict) -> str:
    line_text = line["line_text"]
    for word in line["words"]:
        if is_page_reference(word):
            line_text = line_text.replace(word["word_text"], "").rstrip()
    return line_text


def is_index_header(line: dict, hocr_page: dict, debug: bool = False) -> bool:
    # index header has either
    #  year I N D
    #  year D E X
    next_line = page_parser.get_next_line(hocr_page["lines"].index(line), hocr_page["lines"])
    if not page_parser.is_header(line, next_line):
        return False
    if len(line["words"]) > 1 and page_parser.get_highest_inter_word_space(
            line) > 500:  # if there is only text at the edges of the column, it's not a header
        return False
    if not page_parser.has_mid_column_text(line,
                                           hocr_page):  # some of the index header letters are in the middle of the column
        if debug:
            print("\tNO MID_COLUMN_TEXT:", line, hocr_page)
        return False
    index_score = score_index_header(line, hocr_page, debug=debug)
    if index_score > 3:
        if debug:
            print("header_score:", index_score, "line: #{}#".format(line["line_text"]))
        return True
    else:
        return False


def score_index_header(line: object, hocr_page: object, debug: bool = False) -> object:
    index_score = 0
    if not line:
        return index_score
    if len(line["words"]) <= 5:  # index header has few "words"
        index_score += 1
        if debug:
            print("\tIndex test - few words")
    if page_parser.num_line_chars(
            line) < 10:  # index header has few characters (sometimes year +  I N D or year + D E X)
        index_score += 1
        if debug:
            print("\tIndex test - few chars")
    if line["top"] < 250:  # index header is near the top of the page
        index_score += 1
        if debug:
            print("\tIndex test - near top")
    if line["width"] > 250 and page_parser.num_line_chars(line) < 10:  # index header is wide for having few characters
        index_score += 1
        if debug:
            print("\tIndex test - wide")
    if page_parser.get_highest_inter_word_space(
            line) > 150:  # The I N D E X characters usually have around 200 pixels between them
        index_score += 1
        if debug:
            print("\tIndex test - high inter-word space")
    if index_score > 3:
        if debug:
            print("\tIndex test - index_header_score:", index_score, "line: #{}#".format(line["line_text"]))
    return index_score


def check_lemma(line: dict) -> bool:
    first_main_word_index = 0
    if has_preceeding_stopwords(line):
        first_main_word_index = find_first_main_word(line)
    main_word = line["words"][first_main_word_index]
    if main_word["word_text"][0].isupper():
        print("HAS LEMMA:", line["line_text"])
        return True
    else:
        return False


def is_stopword(word: dict) -> bool:
    return word["word_text"].lower() in ["de", "den", "der", "een", "het", "van", "in", "aan", "op"]


def has_preceeding_stopwords(line: dict) -> bool:
    return is_stopword(line["words"][0])


def find_first_main_word(line: dict) -> Union[int, None]:
    for word_index, word in enumerate(line["words"]):
        if is_stopword(word):
            continue
        return word_index
    return None


def remove_lemma(curr_lemma: str, line: dict) -> str:
    return line["line_text"].replace(curr_lemma, "")


def get_lemma(line: dict) -> str:
    match = re.match(r"(.*?)[\,;\.„]", line["line_text"])
    if match:
        print("LEMMA:", match.group(1))
        lemma = match.group(1).strip()
    else:
        lemma = line["words"][0]["word_text"]
    return lemma


def get_index_entry_lines(hocr_index_page: dict, debug: bool = False) -> list:
    in_body = False
    index_entry_lines = []
    if not page_parser.proper_column_cut(hocr_index_page):
        if (debug):
            print("\tCOLUMN IMPROPERLY CUT")
        return index_entry_lines
    for line_index, line in enumerate(hocr_index_page["lines"]):
        next_line = page_parser.get_next_line(line_index, hocr_index_page["lines"])
        if page_parser.is_in_top_margin(line):
            if (debug):
                print("\tIS IN TOP MARGIN")
            continue
        if not in_body and is_index_header(line, hocr_index_page, debug=False):
            if (debug):
                print("\tIS INDEX HEADER:", line_index, line["top"], "\t##", line["spaced_line_text"])
            in_body = True
            continue
        if not in_body and page_parser.is_full_text_line(line):
            if (debug):
                print("\tFIRST BODY LINE:", line_index, line["top"], "\t##", line["spaced_line_text"])
            in_body = True
            # continue
        if not in_body and page_parser.is_header(line, next_line):
            if (debug):
                print("Header:", line["spaced_line_text"])
                print("\tscan:", "don't know", "line:", line_index, "top:", line["top"], line["left"], line["right"],
                      line["width"])
            # in_body = True
        if in_body and line["left"] < 300 and len(line["words"]) > 0:
            index_entry_lines += [line]
            # in_body = True
    return index_entry_lines


def fix_repeat_symbols(lines: list) -> list:
    fixed_lines = fix_repeat_symbols_lines(lines)
    return find_missing_repeat_symbols(fixed_lines)


def index_lemmata(column_id: str, lines: list, lemma_index: dict, curr_lemma: str) -> str:
    if len(lines) == 0:
        return curr_lemma
    description = ""
    fixed_lines = fix_repeat_symbols(lines)
    for line_index, line in enumerate(fixed_lines):
        if len(line["words"]) == 0:
            continue
        values_left = [line["left"] for line in get_line_neighbourhood_lines(fixed_lines, line_index)]
        sum_left = sum(values_left)
        avg_left = int(sum_left / len(values_left))
        # print(prev_start, line_index, next_end, sum_left, avg_left, values_left)
        diff = line["left"] - avg_left
        line["line_type"] = "start"
        if diff > 0:
            line["line_type"] = "continue"
            # description += " " + line["line_text"]
        if has_page_reference(line):
            line["line_type"] += "_stop"
            page_refs = get_page_references(line)
            description += " " + remove_page_references(line)
            print("\tPAGE_REFS:", page_refs, "\tCURR LEMMA:", curr_lemma)
            if curr_lemma:
                lemma_index[curr_lemma] += [{"page_refs": page_refs, "description": description}]
                description = ""
        if line["line_type"].startswith("start") and check_lemma(line):
            curr_lemma = get_lemma(line)
            print("setting lemma:", get_lemma(line))
            description += " " + remove_lemma(curr_lemma, line)
            lemma_index[curr_lemma] = []
        elif line["line_type"].startswith("start") and has_repeat_symbol(line):
            description += " " + remove_repeat_symbol(line)
        print(line_index, line["left"], diff, line["line_type"], "\t", line["spaced_line_text"])
    return curr_lemma
