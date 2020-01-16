import re
import csv
import os
import copy
from typing import Union, Tuple
from collections import defaultdict
from statistics import median, mean, pstdev, stdev

import republic.parser.republic_base_page_parser as page_parser

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


def count_number_chars(page_hocr: dict) -> int:
    count = 0
    for column_hocr in page_hocr["columns"]:
        for line in column_hocr["lines"]:
            digit_line = re.sub(r"\D+", "", line["line_text"])
            count += len(digit_line)
    return count


def line_has_abbrev_date(line: dict) -> bool:
    # Months are abbreviated, repeated entries for same months use 'dito'
    if re.search(r"\b\d+ (Jan|Feb|Maa|Apr|Mey|Jun|Jul|Aug|Sep|Okt|Nov|Dec|dito)", line["line_text"]):
        return True
    else:
        return False


def fix_repeat_symbols_lines(lines: list) -> list:
    return [fix_repeat_symbols_line(line, line_index) for line_index, line in enumerate(lines)]


def fix_repeat_symbols_line(line: dict, line_index: int) -> dict:
    copy_line = copy.copy(line)
    if has_repeat_symbol(copy_line):
        return copy_line
    first_word = copy_line["words"][0]
    if first_word["left"] > copy_line["left"]:
        print("Gap between line start and first word:", line["left"], first_word["left"], line["line_text"])
    if first_word["width"] > 120 and len(first_word["word_text"]) <= 3:
        #print("possibly misrecognised repeat symbol:", line_index, first_word["width"], first_word["word_text"])
        copy_line["line_text"] = copy_line["line_text"].replace(first_word["word_text"], repeat_symbol, 1)
        if "spaced_line_text" in copy_line:
            copy_line["spaced_line_text"] = copy_line["spaced_line_text"].replace(first_word["word_text"],
                                                                                  repeat_symbol, 1)
        first_word["word_text"] = repeat_symbol
        #if first_word["width"] > avg_repeat_symbol_length:
        #    left_shift = first_word["width"] - avg_repeat_symbol_length
        #    first_word["left"] += left_shift
        #    first_word["width"] = avg_repeat_symbol_length
    return copy_line


def get_repeat_symbol_length(lines: list) -> int:
    repeat_symbol_lengths = []
    for line_index, line in enumerate(lines):
        # print("start:", line["words"][0]["word_text"])
        if has_repeat_symbol(line):
            repeat_symbol_lengths += [line["words"][0]["width"]]
    if len(repeat_symbol_lengths) == 0:
        return 120
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
    if "spaced_line_text" in copy_line:
        copy_line["spaced_line_text"] = re.sub(r"(^ +)(.*)", r"\1" + repeat_symbol["word_text"] + " " + r"\2",
                                           copy_line["spaced_line_text"])
        white_space = " " * round((avg_char_width + avg_repeat_symbol_length) / avg_char_width)
        copy_line["spaced_line_text"] = copy_line["spaced_line_text"].replace(white_space, "")
    return copy_line


def find_missing_repeat_symbols(lines: list) -> list:
    avg_repeat_symbol_length = get_repeat_symbol_length(lines)
    #fixed_lines = []
    fixed_lines = copy.deepcopy(lines)
    for line_index, curr_line in enumerate(fixed_lines):
        neighbour_lines = get_line_neighbourhood_lines(fixed_lines, line_index)
        left_values = [neighbour_line["left"] for neighbour_line in neighbour_lines]
        first_word = curr_line["words"][0]
        mean_left = mean(left_values)
        stdev_left = stdev(left_values)
        low_left = int(mean_left - stdev_left)
        high_left = int(mean_left + stdev_left)
        #print("mean:", mean_left, "stdev:", stdev_left, "min:", low_left)
        #if curr_line["left"] - min(left_values) > 100:
        if curr_line["left"] > high_left and curr_line["left"] - int(mean_left) > 70:
            #print("DEVIATING LINE:", line_index, curr_line["left"], "high value:", high_left, "left values:", left_values, "mean left:", mean_left, curr_line["line_text"])
            fixed_line = add_repeat_symbol(curr_line, avg_repeat_symbol_length, low_left)
            fixed_lines.remove(curr_line)
            fixed_lines.insert(line_index, fixed_line)
            #fixed_lines.append(fixed_line)
            #print("avg_repeat_symbol_length:", avg_repeat_symbol_length)
        elif curr_line["left"] < low_left:
            #print("DEVIATING LINE:", line_index, curr_line["left"], "low value:", low_left, "left values:", left_values, curr_line["line_text"])
            if first_word["word_text"] == repeat_symbol:
                left_shift = low_left - first_word["width"]
                first_word["left"] = low_left
                first_word["width"] = first_word["width"] - left_shift
                curr_line["left"] = low_left
                curr_line["width"] -= left_shift
                #print("This repeat symbol length:", first_word["width"], "left shift:", left_shift)
            #fixed_lines.append(copy.deepcopy(curr_line))
        #else:
            #print("NORMAL LINE:", line_index, curr_line["left"], "low value:", low_left, "left values:", left_values, curr_line["line_text"])
            #fixed_lines.append(copy.deepcopy(curr_line))
    if len(fixed_lines) > len(lines):
        raise IndexError("fixed_lines has more lines than original")
    elif len(fixed_lines) < len(lines):
        raise IndexError("fixed_lines has fewer lines than original")
    return fixed_lines


def get_line_neighbourhood_lines(lines: list, line_index: int, num_before: int = 4, num_after: int = 4) -> list:
    prev_start, next_end = get_line_neighbourhood(lines, line_index, num_before=num_before, num_after=num_after)
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


def score_index_header(line: object, hocr_page: object, debug: bool = False) -> int:
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


def score_index_page(page_hocr: dict, page_type_info: dict, config: dict) -> Tuple[int, str]:
    index_score = 0
    index_score += page_type_info["index_header_score"]
    index_page_type = "index_page_early_print"
    if config["inventory_num"] < config["index_page_early_print"]["inventory_threshold"]:
        index_early_print_score = score_index_page_early_print(page_type_info, config["index_page_early_print"])
        index_early_print_score += page_type_info["index_header_score"]
        if index_early_print_score > index_score:
            index_score = index_early_print_score
    if config["inventory_num"] > config["index_page_late_print"]["inventory_threshold"]:
        index_late_print_score = score_index_page_late_print(page_hocr, config["index_page_late_print"])
        index_late_print_score += page_type_info["index_header_score"]
        if index_late_print_score > index_score:
            index_score = index_late_print_score
            index_page_type = "index_page_late_print"
    return index_score, index_page_type


def score_index_page_early_print(page_type_info: dict, config: dict) -> int:
    index_score = 0
    if page_type_info["num_page_ref_lines"] >= config["page_ref_line_threshold"]:
        index_score += int(page_type_info["num_page_ref_lines"] / config["page_ref_line_threshold"])
    index_score += page_type_info["num_repeat_symbols"]
    if page_type_info["left_jump_ratio"] > config["left_jump_ratio_threshold"]:
        index_score += page_type_info["left_jump_ratio"] * 5
    return index_score


def score_index_page_late_print(page_hocr: dict, config: dict) -> int:
    lines = [line for column in page_hocr["columns"] for line in column["lines"]]
    line_widths = [line["width"] for line in lines]
    num_lines = len(line_widths)
    num_page_refs = len([line for line in lines if len(line["words"]) > 0 and line["words"][-1]["word_text"].isdigit()])
    num_dates = sum([1 for line in lines if line_has_abbrev_date(line)])
    index_score = 0
    if num_dates >= config["num_dates_threshold"] and num_page_refs >= config["num_page_refs_threshold"]:
        index_score += 5
    lw_median = int(median(line_widths))
    lw_stdev = int(pstdev(line_widths))
    if config["num_lines_min"] <= num_lines <= config["num_lines_max"]:
        if config["num_words_max"] >= page_hocr["num_words"] >= config["num_words_min"]:
            index_score += 5
    if page_hocr["num_words"] > config["num_words_max"]:
        index_score -= 5
    if config["median_line_width_min"] <= lw_median <= config["median_line_width_max"]:
        index_score += 5
    if lw_stdev >= config["stdev_line_width_min"] and lw_median <= config["stdev_line_width_max"]:
        index_score += 5
    #print(index_score, "page num", page_hocr["page_num"], "\tnum words:", page_hocr["num_words"], "\tnum lines:", len(line_widths), "median:", lw_median, "lw_stdev:", lw_stdev, "num_dates:", num_dates, "num_page_refs:", num_page_refs)
    return index_score


def check_lemma(line: dict) -> bool:
    first_main_word_index = 0
    if has_preceeding_stopwords(line):
        first_main_word_index = find_first_main_word(line)
    if first_main_word_index is None:
        return False
    main_word = line["words"][first_main_word_index]
    if main_word["word_text"][0].isupper():
        #print("HAS LEMMA:", line["line_text"])
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
        #print("LEMMA:", match.group(1))
        lemma = match.group(1).strip()
    else:
        main_word_index = find_first_main_word(line)
        lemma = " ".join([word["word_text"] for word in line["words"][:main_word_index+1]])
        #lemma = line["words"][0]["word_text"]
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
        neighbour_lines = get_line_neighbourhood_lines(hocr_index_page["lines"], line_index, num_before=10)
        avg_left = sum([line["left"] for line in neighbour_lines]) / len(neighbour_lines)
        if in_body and line["left"] < avg_left + 300 and len(line["words"]) > 0:
            index_entry_lines += [line]
            # in_body = True
    return index_entry_lines


def fix_repeat_symbols(lines: list) -> list:
    fixed_lines = fix_repeat_symbols_lines(lines)
    return find_missing_repeat_symbols(fixed_lines)


def find_index_lemmata(page_doc: dict, lemma_index: dict, curr_lemma: str) -> str:
    description = ""
    for column_hocr in page_doc["columns"]:
        lines = get_index_entry_lines(column_hocr)
        if len(lines) == 0:
            return curr_lemma
        try:
            fixed_lines = fix_repeat_symbols(lines)
        except ZeroDivisionError:
            print(page_doc["page_id"])
            print(len(column_hocr["lines"]))
            print(len(lines))
            for line in column_hocr["lines"]:
                print(line["left"], line["right"], line["line_text"])
            raise
        for line_index, line in enumerate(fixed_lines):
            if len(line["words"]) == 0:
                continue
            values_left = [line["left"] for line in get_line_neighbourhood_lines(fixed_lines, line_index)]
            sum_left = sum(values_left)
            avg_left = int(sum_left / len(values_left))
            prev_start = None
            if line_index > 0:
                prev_start = fixed_lines[line_index-1]["left"]
            #print(prev_start, line_index, sum_left, avg_left, values_left)
            diff = line["left"] - avg_left
            line["line_type"] = "start"
            if diff > -10:
                line["line_type"] = "continue"
                # description += " " + line["line_text"]
            if has_page_reference(line):
                line["line_type"] += "_stop"
                page_refs = get_page_references(line)
                description += " " + remove_page_references(line)
                #print("\tPAGE_REFS:", page_refs, "\tCURR LEMMA:", curr_lemma)
                if curr_lemma:
                    lemma_index[curr_lemma] += [{"page_refs": page_refs, "description": description,
                                                 "source_page": page_doc["page_id"]}]
                    description = ""
            if line["line_type"].startswith("start") and check_lemma(line):
                curr_lemma = get_lemma(line)
                #print("setting lemma:", get_lemma(line))
                description += " " + remove_lemma(curr_lemma, line)
                lemma_index[curr_lemma] = []
            elif line["line_type"].startswith("start") and has_repeat_symbol(line):
                description += " " + remove_repeat_symbol(line)
            #print(line_index, line["left"], diff, line["line_type"], "\t", line["spaced_line_text"])
    return curr_lemma


def write_index_to_csv(inventory_num, lemma_index, data_type: str, config: dict):
    if data_type not in ["hocr", "pagexml"]:
        raise ValueError("data_type should be 'hocr' or 'pagexml'")
    fname = f"index-{inventory_num}-{data_type}.csv"
    outfile = os.path.join(config["csv_dir"], fname)
    with open(outfile, 'wt') as fh:
        csv_writer = csv.writer(fh, delimiter="\t")
        headers = ["inventory_num", "source_page", "lemma", "description", "page_refs"]
        csv_writer.writerow(headers)
        for lemma in lemma_index:
            for entry in lemma_index[lemma]:
                page_refs = ",".join([str(page_ref) for page_ref in entry["page_refs"]])
                csv_writer.writerow([inventory_num, entry["source_page"],
                                    lemma, entry["description"], page_refs])


def parse_inventory_index_pages(pages: list) -> dict:
    lemma_index = defaultdict(list)
    curr_lemma = None
    for page_doc in sorted(pages, key = lambda x: x["page_num"]):
        #print("\n\n", page_doc["page_id"])
        if "index_page" not in page_doc["page_type"]:
            print("skipping non-index page")
            continue
        page_doc["num_page_ref_lines"] = count_page_ref_lines(page_doc)
        curr_lemma = find_index_lemmata(page_doc, lemma_index, curr_lemma)
        #print("returned lemma:", curr_lemma)
    return lemma_index


