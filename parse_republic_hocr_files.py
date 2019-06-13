import json
import os
import re
from collections import defaultdict
from parse_hocr_files import make_hocr_page
from elasticsearch import Elasticsearch

# filename format: ../hocr/NL-HaNA_1.01.02_3780_0016.jpg-0-251-98--0.40.hocr

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
        "scan_page": "scan-{}-{}".format(get_scan_num(fname), get_page_side(fname)),
        "scan_page_num": get_scan_page_num(fname),
        "page_side": get_page_side(fname),
        "slant": get_scan_slant(fname),
        "scan_id": "scan-{}-{}-{}".format(get_scan_num(fname), get_page_side(fname), get_column_num(fname)),
        "filepath": os.path.join(root_dir, fname)
    }

def get_files(data_dir):
    for root_dir, sub_dirs, filenames in os.walk(data_dir):
        return [get_scan_info(fname, root_dir) for fname in filenames]

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
        if word["left"] - hocr_page.carea["left"] > 250 and hocr_page.carea["right"] - word["right"] > 300:
            return True
    return False

def has_left_aligned_text(line, hocr_page):
    if line["words"][0]["left"] - hocr_page.carea["left"] > 100:
        return False
    return True

def has_right_aligned_text(line, hocr_page):
    if hocr_page.carea["right"] - line["words"][-1]["right"] > 100:
        return False
    return True

#def wide_spaced_words

def num_line_chars(line):
    return len(line["line_text"].replace(" ",""))

def is_header(line):
    if line["top"] > 350: # if top is above 350, this line is definitely not a header
        return False
    if line["top"] < 150: # header has some margin form the top of the page, anything above this margin is noise
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
            print("\tNO MID_COLUMN_TEXT:", line, hocr_page.carea)
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
            print("few words")
    if num_line_chars(line) < 10: # index header has few characters (sometimes year +  I N D or year + D E X)
        index_score += 1
        if DEBUG:
            print("few chars")
    if line["top"] < 250: # index header is near the top of the page
        index_score += 1
        if DEBUG:
            print("near top")
    if line["width"] > 250 and num_line_chars(line) < 10: # index header is wide for having few characters
        index_score += 1
        if DEBUG:
            print("wide")
    if get_highest_inter_word_space(line) > 150: # The I N D E X characters usually have around 200 pixels between them
        index_score += 1
        if DEBUG:
            print("high inter-word space")
    return index_score

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
            print("few words")
    if num_line_chars(line) > 8 and num_line_chars(line) < 25: # page number + date is not too short, not too long
        resolution_score += 1
        if DEBUG:
            print("few chars")
    if line["top"] < 250: # A resolution header is near the top of the page
        resolution_score += 1
        if DEBUG:
            print("near top")
    if line["width"] > 750: # A resolution header is wide
        resolution_score += 1
        if DEBUG:
            print("wide")
    if get_highest_inter_word_space(line) > 450: # A resolution header has a wide empty centre
        resolution_score += 1
        if DEBUG:
            print("high inter-word space")
    if resolution_score > 3:
        if DEBUG:
            print("resolution_header_score:", resolution_score, "line: #{}#".format(line["line_text"]))
        #print(json.dumps(line, indent=2))
    return resolution_score

def is_in_top_margin(line):
    if line["top"] < 150: # index header has some margin form the top of the page
        return True
    return False

def is_full_text_line(line):
    return len(line["line_text"].replace(" ", "")) > 25

def proper_column_cut(hocr_page):
    if hocr_page.carea["width"] < 850:
        return False
        print("Column width is to low:", hocr_page.page_num, hocr_page.carea["width"])
    if hocr_page.carea["width"] > 1200:
        return False
        print("Column width is to high:", hocr_page.page_num, hocr_page.carea["width"])
    return True

def line_has_page_ref(line):
    return re.search(r"\b\d+\.", line["line_text"])

def count_page_ref_lines(hocr_page):
    count = 0
    for line in hocr_page.lines:
        if line_has_page_ref(line):
            count += 1
    return count

def determine_page_type(hocr_page, DEBUG=False):
    page_type = "other"
    if not proper_column_cut(hocr_page):
        page_type = "bad_page"
        return page_type
    index_score, resolution_score = 0, 0
    for line in hocr_page.lines:
        line = line["filtered"]
        if not is_header(line):
            continue
        resolution_score = score_resolution_header(line, hocr_page, DEBUG=DEBUG)
        index_score = score_index_header(line, hocr_page, DEBUG=DEBUG)
        if is_index_header(line, hocr_page):
            page_type = "index_page"
        if is_resolution_header(line, hocr_page, DEBUG=DEBUG):
            if page_type != "index_page" or resolution_score > index_score:
                page_type = "resolution_page"
    return page_type



def get_page_types(scan_files, min_scan_num=0, max_scan_num=70):
    index_scans = set()
    resolution_scans = set()
    for scan_file in scan_files:
        if scan_file["scan_num"] > max_scan_num:
            continue
        print("scan:", scan_file["scan_num"], "\tscan_id:", scan_file["scan_id"])
        if scan_file["scan_page"] in index_scans:
            print("DERIVED")
            continue
        hocr_page = make_hocr_page(scan_file["filepath"], scan_file["scan_id"], remove_line_numbers=False, remove_tiny_words=True, tiny_word_width=15)
        page_type = determine_page_type(hocr_page)
        if page_type == "bad_page":
            print("\tCOLUMN IMPROPERLY CUT")
        elif page_type == "index_page":
            print("\tINDEX PAGE")
            #print(line)
            index_scans.add(scan_file["scan_num_column_num"])
        elif page_type == "resolution_page":
            print("\tRESOLUTION PAGE")
            resolution_scans.add(scan_file["scan_num_column_num"])
        else:
            print("OTHER PAGE")
    return index_scans, resolution_scans

def check_lemma(line):
    if line["filtered"]["words"][0]["word_text"][0].isupper():
        print("HAS LEMMA:", line["filtered"]["line_text"])
        return True

def has_repeat_symbol(line):
    if re.match(r"^[\-_—]+$", line["filtered"]["words"][0]["word_text"]):
        return True
    else:
        return False

def has_page_reference(line):
    if re.match(r"^\d+[\.\:\;,]$", line["filtered"]["words"][-1]["word_text"]):
        return True
    else:
        return False

def fix_repeat_symbols(lines):
    for line_index, line in enumerate(lines):
        if has_repeat_symbol(line):
            continue
        first_word = line["filtered"]["words"][0]
        if first_word["left"] > line["left"]:
            print(line_index, "Gap between line start and first word:", line["left"], first_word["left"], line["filtered"]["line_text"])
        if first_word["width"] > 120 and len(first_word["word_text"]) <= 3:
            print(line_index, "possibly misrecognised repeat symbol:", first_word["width"], first_word["word_text"])
            line["filtered"]["line_text"] = line["filtered"]["line_text"].replace(first_word["word_text"], repeat_symbol, 1)
            line["filtered"]["spaced_line_text"] = line["filtered"]["spaced_line_text"].replace(first_word["word_text"], repeat_symbol, 1)
            first_word["word_text"] = repeat_symbol

def get_repeat_symbol_length(lines):
    repeat_symbol_lengths = []
    for line_index, line in enumerate(lines):
        #print("start:", line["filtered"]["words"][0]["word_text"])
        if has_repeat_symbol(line):
            repeat_symbol_lengths += [line["filtered"]["words"][0]["width"]]
    return int(sum(repeat_symbol_lengths) / len(repeat_symbol_lengths))

def add_repeat_symbol(line, avg_repeat_symbol_length, minimum_start):
    avg_char_width = 20
    repeat_symbol_start = line["filtered"]["left"] - avg_char_width - avg_repeat_symbol_length
    if repeat_symbol_start < minimum_start:
        repeat_symbol_start = minimum_start
    line["filtered"]["left"] = repeat_symbol_start
    line["filtered"]["width"] += avg_char_width + avg_repeat_symbol_length
    repeat_symbol = {
        "height": 30,
        "width": avg_repeat_symbol_length,
        "left": repeat_symbol_start,
        "right":  repeat_symbol_start + avg_repeat_symbol_length,
        "top": line["filtered"]["top"],
        "bottom": line["filtered"]["bottom"],
        "word_text": "——",
        "word_conf": 50
    }
    line["filtered"]["words"] = [repeat_symbol] + line["filtered"]["words"]
    line["filtered"]["line_text"] = repeat_symbol["word_text"] + " " + line["filtered"]["line_text"]
    line["filtered"]["spaced_line_text"] = re.sub(r"(^ +)(.*)", r"\1" + repeat_symbol["word_text"] + " " + r"\2", line["filtered"]["spaced_line_text"])
    white_space = " " * round((avg_char_width + avg_repeat_symbol_length) / avg_char_width)
    line["filtered"]["spaced_line_text"] = line["filtered"]["spaced_line_text"].replace(white_space, "")

def find_missing_repeat_symbols(lines):
    avg_repeat_symbol_length = get_repeat_symbol_length(lines)
    for line_index, curr_line in enumerate(lines):
        neighbour_lines = get_line_neighbourhood_lines(lines, line_index)
        left_values = [neighbour_line["filtered"]["left"] for neighbour_line in neighbour_lines]
        if curr_line["filtered"]["left"] - min(left_values) > 100:
            print("DEVIATING LINE:", curr_line["filtered"]["left"], left_values, curr_line["filtered"]["line_text"])
            add_repeat_symbol(curr_line, avg_repeat_symbol_length, min(left_values))
            print("avg_repeat_symbol_length:", avg_repeat_symbol_length)
        #if curr_line["left"] -

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
    for word in line["filtered"]["words"]:
        if is_page_reference(word):
            page_ref = get_page_reference(word)
            page_refs += [page_ref]
    return page_refs

def get_lemma(line):
    lemma = None
    match = re.match(r"(.*?)[\,;\.„]", line["filtered"]["line_text"])
    if match:
        print("LEMMA:", match.group(1))
        lemma = match.group(1).strip()
    return lemma

def get_index_entry_lines(hocr_index_page):
    in_body = False
    index_entry_lines = []
    print(hocr_index_page.scan_info["scan_num_column_num"])
    if not proper_column_cut(hocr_index_page):
        print("\tCOLUMN IMPROPERLY CUT")
        return index_entry_lines
    for line_index, line in enumerate(hocr_index_page.lines):
        if is_in_top_margin(line["filtered"]):
            print("\tIS IN TOP MARGIN")
            continue
        if not in_body and is_index_header(line["filtered"], hocr_index_page, DEBUG=False):
            print("\tIS INDEX HEADER:", line_index, line["filtered"]["top"], "\t##", line["filtered"]["spaced_line_text"])
            in_body = True
            continue
        if not in_body and is_full_text_line(line["filtered"]):
            print("\tFIRST BODY LINE:", line_index, line["filtered"]["top"], "\t##", line["filtered"]["spaced_line_text"])
            in_body = True
            #continue
        if not in_body and is_header(line["filtered"]):
            print("Header:", line["filtered"]["spaced_line_text"])
            print("\tscan:", hocr_index_page.page_num, "line:", line_index, "top:", line["filtered"]["top"], line["filtered"]["left"], line["filtered"]["right"], line["filtered"]["width"])
            #in_body = True
        if in_body and line["filtered"]["left"] < 300:
            index_entry_lines += [line]
            #in_body = True
    return index_entry_lines

def index_lemmata(scan_id, lines, lemma_index, curr_lemma):
    if len(lines) == 0:
        return True
    fix_repeat_symbols(lines)
    find_missing_repeat_symbols(lines)
    for line_index, line in enumerate(lines):
        values_left = [line["filtered"]["left"] for line in get_line_neighbourhood_lines(lines, line_index)]
        sum_left = sum(values_left)
        avg_left = int(sum_left / len(values_left))
        #print(prev_start, line_index, next_end, sum_left, avg_left, values_left)
        diff = line["filtered"]["left"] - avg_left
        line["line_type"] = "start"
        if diff > 0:
            line["line_type"] = "continue"
        if has_page_reference(line):
            line["line_type"] += "_stop"
            page_refs = get_page_references(line)
            print("\tPAGE_REFS:", page_refs)
            if curr_lemma:
                lemma_index[curr_lemma] += page_refs
        if line["line_type"].startswith("start") and check_lemma(line):
            curr_lemma = get_lemma(line)
            lemma_index[curr_lemma] = []
        print(line_index, line["filtered"]["left"], diff, line["line_type"], "\t", line["filtered"]["spaced_line_text"])


