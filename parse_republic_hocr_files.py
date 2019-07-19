import json
import os
import re
import copy
from collections import defaultdict
from parse_hocr_files import make_hocr_page, filter_tiny_words_from_lines
from elasticsearch import Elasticsearch

# filename format: NL-HaNA_1.01.02_3780_0016.jpg-0-251-98--0.40.hocr

repeat_symbol = "——"

def get_scan_num(fname):
    return int(fname.split(".")[2].split("_")[2])

def get_column_num(fname):
    return int(fname.split(".")[3].split("-")[1])

def get_scan_page_num(fname):
    page_num = get_scan_num(fname) * 2
    if get_page_side(fname) == "odd":
        page_num += 1
    return page_num

def get_scan_slant(fname):
    parts = fname.split(".")[3].split("-")
    if len(parts) == 6:
        return float(parts[5]) * -1
    elif len(parts) == 5:
        return float(parts[4])
    else:
        raise TypeError("Unexpected structure of filename")

def get_page_side(fname):
    parts = fname.split(".")[3].split("-")
    if int(parts[2]) < 2400:
        return "even"
    else:
        return "odd"

def get_scan_info(fname, root_dir):
    return {
        "scan_num": get_scan_num(fname),
        "scan_column": get_column_num(fname),
        "scan_num_column_num": get_scan_num(fname) + 0.1 * get_column_num(fname),
        "page_id": "scan-{}-{}".format(get_scan_num(fname), get_page_side(fname)),
        "page_num": get_scan_page_num(fname),
        "page_side": get_page_side(fname),
        "slant": get_scan_slant(fname),
        "column_id": "scan-{}-{}-{}".format(get_scan_num(fname), get_page_side(fname), get_column_num(fname)),
        "filepath": os.path.join(root_dir, fname)
    }

def gather_page_columns(scan_files):
    page_info = defaultdict(list)
    for scan_file in scan_files:
        if scan_file["page_id"] not in page_info:
            page_info[scan_file["page_id"]] = {
                "scan_num": scan_file["scan_num"],
                "page_id": scan_file["page_id"],
                "page_num": scan_file["page_num"],
                "page_side": scan_file["page_side"],
                "columns": []
            }
        page_info[scan_file["page_id"]]["columns"] += [scan_file]
    return page_info

def get_page_columns_hocr(page_info, config):
    return {column_info["column_id"]: get_column_hocr(column_info, config) for column_info in page_info["columns"]}

def get_column_hocr(column_info, config):
    hocr_page = make_hocr_page(column_info["filepath"], column_info["column_id"], config=config)
    column_hocr = hocr_page.carea
    column_hocr["lines"] = hocr_page.lines
    if "remove_tiny_words" in config and config["remove_tiny_words"]:
        column_hocr["lines"] = filter_tiny_words_from_lines(hocr_page, config)
    return column_hocr

def get_files(data_dir):
    for root_dir, sub_dirs, filenames in os.walk(data_dir):
        return [get_scan_info(fname, root_dir) for fname in filenames]

def read_hocr_scan(scan_file):
    column_id = "{}-{}".format(scan_file["scan_num"], scan_file["scan_column"])
    hocr_index_page = make_hocr_page(scan_file["filepath"], column_id, remove_line_numbers=False, remove_tiny_words=True, tiny_word_width=6)
    hocr_index_page.scan_info = scan_file
    hocr_index_page.scan_info["num_page_ref_lines"] = count_page_ref_lines(hocr_page)
    return hocr_index_page

def get_highest_inter_word_space(line):
    highest_inter_word_space = -1
    for word_index, word in enumerate(line["words"][:-1]):
        next_word = line["words"][word_index+1]
        inter_word_space = next_word["left"] - word["right"]
        if inter_word_space > highest_inter_word_space:
            highest_inter_word_space = inter_word_space
    return highest_inter_word_space

def has_mid_column_text(line, hocr_page):
    for word in line["words"]:
        if word["left"] - hocr_page["left"] > 250 and hocr_page["right"] - word["right"] > 300:
            return True
    return False

def has_left_aligned_text(line, hocr_page):
    if line["words"][0]["left"] - hocr_page["left"] > 100:
        return False
    return True

def has_right_aligned_text(line, hocr_page):
    if hocr_page["right"] - line["words"][-1]["right"] > 100:
        return False
    return True

#def wide_spaced_words

def num_line_chars(line):
    return len(line["line_text"].replace(" ",""))

def is_header(line):
    if line["top"] > 350: # if top is above 350, this line is definitely not a header
        return False
    if line["top"] < 150: # header has some margin form the top of the page, any text in this margin is noise
        return False
    if get_highest_inter_word_space(line) < 100: # headers have widely spaced elements
        return False
    return True

def is_index_header(line, hocr_page, DEBUG=False):
    # index header has either
    #  year I N D
    #  year D E X
    if not is_header(line):
        return False
    if get_highest_inter_word_space(line) > 500: # if there is only text at the edges of the column, it's not a header
        return False
    if not has_mid_column_text(line, hocr_page): # some of the index header letters are in the middle of the column
        if DEBUG:
            print("\tNO MID_COLUMN_TEXT:", line, hocr_page)
        return False
    index_score = score_index_header(line, hocr_page, DEBUG=DEBUG)
    if index_score > 3:
        if DEBUG:
            print("header_score:", index_score, "line: #{}#".format(line["line_text"]))
        return True
    else:
        return False

def score_index_header(line, hocr_page, DEBUG=False):
    index_score = 0
    if len(line["words"]) <= 5: # index header has few "words"
        index_score += 1
        if DEBUG:
            print("\tIndex test - few words")
    if num_line_chars(line) < 10: # index header has few characters (sometimes year +  I N D or year + D E X)
        index_score += 1
        if DEBUG:
            print("\tIndex test - few chars")
    if line["top"] < 250: # index header is near the top of the page
        index_score += 1
        if DEBUG:
            print("\tIndex test - near top")
    if line["width"] > 250 and num_line_chars(line) < 10: # index header is wide for having few characters
        index_score += 1
        if DEBUG:
            print("\tIndex test - wide")
    if get_highest_inter_word_space(line) > 150: # The I N D E X characters usually have around 200 pixels between them
        index_score += 1
        if DEBUG:
            print("\tIndex test - high inter-word space")
    if index_score > 3:
        if DEBUG:
            print("\tIndex test - index_header_score:", index_score, "line: #{}#".format(line["line_text"]))
    return index_score

def contains_year(line):
    for word in line["words"]:
        if looks_like_year(word):
            return True
    return False

def looks_like_year(word):
    if re.search(r"\w{6,}", word["word_text"]): # long alphanumeric word
        return False
    if len(word["word_text"]) < 3: # very short  word
        return False
    if re.match(r"\d{2,4}", word["word_text"]): # starting number-like
        return True
    if re.search(r"17\d{1,2}", word["word_text"]): # containing year string
        return True
    else:
        return False

def is_resolution_header(line, hocr_page, DEBUG=False):
    # resolution header has either
    # year ( page_number )
    # date ( page_number )
    # ( page_number ) year
    # ( page_number ) date
    if not is_header(line):
        return False
    if get_highest_inter_word_space(line) < 300: # resolution header has widely spaced elements
        return False
    if not has_left_aligned_text(line, hocr_page): # there should always be left-aligned text in a resolution header
        if DEBUG:
            print("\tNO LEFT-ALIGNED TEXT:", line)
        return False
    if not has_right_aligned_text(line, hocr_page): # there should always be left-aligned text in a resolution header
        if DEBUG:
            print("\tNO RIGHT-ALIGNED TEXT:", line)
        return False
    resolution_score = score_resolution_header(line, hocr_page, DEBUG=DEBUG)
    if resolution_score > 3:
        if DEBUG:
            print("resolution_header_score:", resolution_score, "line: #{}#".format(line["line_text"]))
        return True
    else:
        return False
        #print(json.dumps(line, indent=2))


def score_resolution_header(line, hocr_page, DEBUG=False):
    resolution_score = 0
    if len(line["words"]) <= 6: # resolution header has few "words"
        resolution_score += 1
        if DEBUG:
            print("\tResolution test - few words")
    if num_line_chars(line) > 8 and num_line_chars(line) < 25: # page number + date is not too short, not too long
        resolution_score += 1
        if DEBUG:
            print("\tResolution test - few chars")
    if line["top"] < 250: # A resolution header is near the top of the page
        resolution_score += 1
        if DEBUG:
            print("\tResolution test - near top")
    if line["width"] > 750: # A resolution header is wide
        resolution_score += 1
        if DEBUG:
            print("\tResolution test - wide")
    if get_highest_inter_word_space(line) > 450: # A resolution header has a wide empty centre
        resolution_score += 1
        if DEBUG:
            print("\tResolution test - high inter-word space")
    if contains_year(line):
        resolution_score += 2
        if DEBUG:
            print("\tResolution test - contains year-like word")
    if resolution_score > 3:
        if DEBUG:
            print("\tResolution test - resolution_header_score:", resolution_score, "line: #{}#".format(line["line_text"]))
        #print(json.dumps(line, indent=2))
    return resolution_score

def is_in_top_margin(line):
    if line["top"] < 150: # index header has some margin form the top of the page
        return True
    return False

def is_full_text_line(line):
    return len(line["line_text"].replace(" ", "")) > 25

def is_short_text_line(line):
    return len(line["line_text"].replace(" ", "")) < 15

def merge_text_lines(hocr_page):
    page_text = ""
    for line in hocr_page.lines:
        if line["line_text"][-1] == "-":
            page_text += line["line_text"][:-1]
        else:
            page_text += line["line_text"] + " "
    return page_text

def proper_column_cut(hocr_page):
    if hocr_page["width"] < 850:
        return False
        print("Column width is to low:", hocr_page.page_num, hocr_page["width"])
    if hocr_page["width"] > 1200:
        return False
        print("Column width is to high:", hocr_page.page_num, hocr_page["width"])
    return True

def line_has_page_ref(line):
    return re.search(r"\b\d+\.", line["line_text"])

def count_page_ref_lines(page_info):
    count = 0
    for column_info in page_info["columns"]:
        for line in column_info["column_hocr"]["lines"]:
            if line_has_page_ref(line):
                count += 1
    return count

def calculate_left_jumps(page_info):
    num_lines = 0
    prev_left = None
    left_jumps = 0
    lefts = []
    for column_info in page_info["columns"]:
        if "column_hocr" not in column_info:
            continue
        for line in column_info["column_hocr"]["lines"]:
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
    #print(lefts)
    #print(num_lines, left_jumps, left_jump_fraction)
    return left_jump_fraction

def count_full_text_lines(page_info):
    count = 0
    for column_info in page_info["columns"]:
        for line in column_info["column_hocr"]["lines"]:
            if is_full_text_line(line):
                count += 1
    return count

def count_short_text_lines(page_info):
    count = 0
    for column_info in page_info["columns"]:
        for line in column_info["column_hocr"]["lines"]:
            if is_short_text_line(line):
                count += 1
    return count

def get_column_header_line(column_hocr):
    for line in column_hocr["lines"]:
        if line["top"] > 350: # if top is above 350, this line is definitely not a header
            break
        if is_header(line):
            return line
    return None

def get_column_header_lines(page_info):
    return [get_column_header_line(column_info["column_hocr"]) for column_info in page_info["columns"]]

def get_page_header_words(page_info):
    column_header_lines = get_column_header_lines(page_info)
    column_header_lines = [line for line in column_header_lines if line] # remove None elements
    return [word["word_text"] for line in column_header_lines for word in line["words"]]

def get_page_type(page_info, config, DEBUG=False):
    resolution_score = 0
    index_score = 0
    for column_info in page_info["columns"]:
        column_hocr = column_info["column_hocr"]
        if not proper_column_cut(column_hocr):
            page_type = "bad_page"
            return page_type
        column_header_line = get_column_header_line(column_hocr)
        if not column_header_line:
            print("\t\tNO HEADER LINE for column id", column_info["column_id"])
            continue
        resolution_score += score_resolution_header(column_header_line, column_hocr, DEBUG=DEBUG)
        index_score += score_index_header(column_header_line, column_hocr, DEBUG=DEBUG)
    if count_page_ref_lines(page_info) >= 10:
        index_score += int(count_page_ref_lines(page_info) / 10)
        if DEBUG:
            print("\tIndex test - many page references:", count_page_ref_lines(page_info))
    if count_repeat_symbols_page(page_info) == 0:
        resolution_score += 1
    else:
        index_score += count_repeat_symbols_page(page_info)
    if calculate_left_jumps(page_info) < 0.3:
        resolution_score += (1 - calculate_left_jumps(page_info)) * 10
        if (DEBUG):
            print("\tfew left jumps")
    elif calculate_left_jumps(page_info) > 0.5:
        if (DEBUG):
            print("\tmany left jumps")
        index_score += calculate_left_jumps(page_info) * 10
    if DEBUG:
        print("res_score:", resolution_score, "ind_score:", index_score)
        print(" ".join(get_page_header_words(page_info)))
    if resolution_score >= 5 and resolution_score > index_score:
        return "resolution_page"
    elif index_score >= 4 and index_score > resolution_score:
        return "index_page"
    else:
        return "unknown_page_type"

def remove_repeat_symbol(line):
    return line["line_text"].replace(line["words"][0]["word_text"], "")

def count_repeat_symbols_page(page_info):
    return sum([count_repeat_symbols_column(column_info["column_hocr"])for column_info in page_info["columns"]])

def count_repeat_symbols_column(column_hocr):
    count = 0
    for line in column_hocr["lines"]:
        if has_repeat_symbol(line):
            count += 1
    return count

def has_repeat_symbol(line):
    if len(line["words"]) == 0:
        return False
    if re.match(r"^[\-_—]+$", line["words"][0]["word_text"]):
        return True
    else:
        return False

def has_page_reference(line):
    if re.match(r"^\d+[\.\:\;,]$", line["words"][-1]["word_text"]):
        return True
    else:
        return False

def fix_repeat_symbols_lines(lines):
    return [fix_repeat_symbols_line(line) for line in lines]

def fix_repeat_symbols_line(line):
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

def get_repeat_symbol_length(lines):
    repeat_symbol_lengths = []
    for line_index, line in enumerate(lines):
        #print("start:", line["words"][0]["word_text"])
        if has_repeat_symbol(line):
            repeat_symbol_lengths += [line["words"][0]["width"]]
    return int(sum(repeat_symbol_lengths) / len(repeat_symbol_lengths))

def add_repeat_symbol(line, avg_repeat_symbol_length, minimum_start):
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
        "right":  repeat_symbol_start + avg_repeat_symbol_length,
        "top": line["top"],
        "bottom": line["bottom"],
        "word_text": "——",
        "word_conf": 50
    }
    copy_line["words"] = [repeat_symbol] + copy_line["words"]
    copy_line["line_text"] = repeat_symbol["word_text"] + " " + copy_line["line_text"]
    copy_line["spaced_line_text"] = re.sub(r"(^ +)(.*)", r"\1" + repeat_symbol["word_text"] + " " + r"\2", copy_line["spaced_line_text"])
    white_space = " " * round((avg_char_width + avg_repeat_symbol_length) / avg_char_width)
    copy_line["spaced_line_text"] = copy_line["spaced_line_text"].replace(white_space, "")
    return copy_line

def find_missing_repeat_symbols(lines):
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
        #if curr_line["left"] -
        else:
            fixed_lines.append(copy.deepcopy(curr_line))
    return fixed_lines

def get_line_neighbourhood_lines(lines, line_index):
    prev_start, next_end = get_line_neighbourhood(lines, line_index)
    return [lines[index] for index in range(prev_start, next_end)]

def get_line_neighbourhood(lines, line_index, num_before=4, num_after=4):
    num_lines = len(lines)
    prev_start = line_index - num_before if line_index >= num_before else 0
    next_end = line_index + (num_after+1) if line_index < num_lines - (num_after+1) else num_lines
    return prev_start, next_end

def is_page_reference(word):
    return re.match(r"^\d+[\.\:\;,]$", word["word_text"])

def get_page_reference(word):
    return int(re.sub(r"\D", "", word["word_text"]))

def get_page_references(line):
    page_refs = []
    for word in line["words"]:
        if is_page_reference(word):
            page_ref = get_page_reference(word)
            page_refs += [page_ref]
    return page_refs

def remove_page_references(line):
    page_refs = []
    line_text = line["line_text"]
    for word in line["words"]:
        if is_page_reference(word):
            line_text = line_text.replace(word["word_text"], "").rstrip()
    return line_text

def check_lemma(line):
    if line["words"][0]["word_text"][0].isupper():
        print("HAS LEMMA:", line["line_text"])
        return True

def remove_lemma(curr_lemma, line):
    return line["line_text"].replace(curr_lemma, "")

def get_lemma(line):
    lemma = None
    match = re.match(r"(.*?)[\,;\.„]", line["line_text"])
    if match:
        print("LEMMA:", match.group(1))
        lemma = match.group(1).strip()
    else:
        lemma = line["words"][0]["word_text"]
    return lemma

def get_index_entry_lines(hocr_index_page, DEBUG=False):
    in_body = False
    index_entry_lines = []
    if not proper_column_cut(hocr_index_page):
        if (DEBUG):
            print("\tCOLUMN IMPROPERLY CUT")
        return index_entry_lines
    for line_index, line in enumerate(hocr_index_page["lines"]):
        if is_in_top_margin(line):
            if (DEBUG):
                print("\tIS IN TOP MARGIN")
            continue
        if not in_body and is_index_header(line, hocr_index_page, DEBUG=False):
            if (DEBUG):
                print("\tIS INDEX HEADER:", line_index, line["top"], "\t##", line["spaced_line_text"])
            in_body = True
            continue
        if not in_body and is_full_text_line(line):
            if (DEBUG):
                print("\tFIRST BODY LINE:", line_index, line["top"], "\t##", line["spaced_line_text"])
            in_body = True
            #continue
        if not in_body and is_header(line):
            if (DEBUG):
                print("Header:", line["spaced_line_text"])
                print("\tscan:", "don't know", "line:", line_index, "top:", line["top"], line["left"], line["right"], line["width"])
            #in_body = True
        if in_body and line["left"] < 300 and len(line["words"]) > 0:
            index_entry_lines += [line]
            #in_body = True
    return index_entry_lines

def fix_repeat_symbols(lines):
    fixed_lines = fix_repeat_symbols_lines(lines)
    return find_missing_repeat_symbols(fixed_lines)

def index_lemmata(column_id, lines, lemma_index, curr_lemma):
    if len(lines) == 0:
        return True
    description = ""
    fixed_lines = fix_repeat_symbols(lines)
    for line_index, line in enumerate(fixed_lines):
        if len(line["words"]) == 0:
            continue
        values_left = [line["left"] for line in get_line_neighbourhood_lines(fixed_lines, line_index)]
        sum_left = sum(values_left)
        avg_left = int(sum_left / len(values_left))
        #print(prev_start, line_index, next_end, sum_left, avg_left, values_left)
        diff = line["left"] - avg_left
        line["line_type"] = "start"
        if diff > 0:
            line["line_type"] = "continue"
            #description += " " + line["line_text"]
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
            description += " " + remove_lemma(curr_lemma, line)
            lemma_index[curr_lemma] = []
        elif line["line_type"].startswith("start") and has_repeat_symbol(line):
            description += " " + remove_repeat_symbol(line)
        print(line_index, line["left"], diff, line["line_type"], "\t", line["spaced_line_text"])
    return curr_lemma

