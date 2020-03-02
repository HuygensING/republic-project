from typing import Dict, List, Union
from collections import Counter

import republic.parser.hocr.republic_column_parser as column_parser
from republic.parser.hocr.republic_paragraph_parser import score_levenshtein_distance
import republic.parser.hocr.republic_base_page_parser as base_parser

index_page_month_words = [
    "Jan.",
    "Febr.",
    "Maart", "Mrt",
    "April", "Apr",
    "Mey",
    "Juny",
    "July",
    "Aug.",
    "Sept.",
    "Oct.",
    "Nov.",
    "Dec.",
    "dito"
]

boundary_symbols = "|![]{}/\\"


def has_digit(word: str) -> bool:
    for i in word[::-1]:
        if i.isdigit():
            return True
    return False


def is_index_page_month_word(word: str) -> bool:
    for month_word in index_page_month_words:
        dist = score_levenshtein_distance(word, month_word)
        if dist <= 1:
            return True
    return False


def line_has_index_page_month_word(words: List[dict]) -> bool:
    for word in words:
        if is_index_page_month_word(word["word_text"]):
            return True
    return False


def starts_with_index_page_month_word(words: List[dict]) -> bool:
    return is_index_page_month_word(words[0]["word_text"])


def find_index_page_central_column(pixel_dist: Counter) -> Dict[str, int]:
    central_column = []
    try:
        max_freq = pixel_dist.most_common(1)[0][1]
        for pixel, freq in sorted(pixel_dist.items()):
            if freq < max_freq * 0.25:
                central_column += [(pixel, freq)]
        central_column = {"left": central_column[0][0], "right": central_column[-1][0]}
    except IndexError:
        # There is no central column
        return None
    print("central column:", central_column)
    return central_column


def split_index_page_table_row(line: dict, central_column: dict, config: dict) -> Dict[str, List[dict]]:
    lemma_words = [word for word in line["words"] if word["right"] <= central_column["left"]]
    central_words = [word for word in line["words"] if
                     word["right"] > central_column["left"] and word["left"] < central_column["right"]]
    # UGLY HACK: replace lemma words in central words if left-most lemma words starts close central column
    if len(lemma_words) > 0 and central_column["left"] - lemma_words[0]["left"] < 70:
        print("Shifting lemma words back to central column")
        print("\t", [word["word_text"] for word in lemma_words])
        central_words = lemma_words + central_words
        lemma_words = []
    ref_words = [word for word in line["words"] if word["left"] >= central_column["right"]]
    # print("ref_words:", " ".join([word["word_text"] for word in ref_words]))
    if len(ref_words) <= 1 and not line_has_index_page_month_word(ref_words):
        ref_words = []
    if len(ref_words) >= 1 and ref_words[0]["left"] - central_column["right"] > 200:
        print(ref_words[0]["left"], central_column["right"], ref_words[0]["left"] - central_column["right"])
        ref_words = []
    central_words, ref_words = check_correct_index_page_reference_column(central_words,
                                                                         ref_words, config)
    # print("corrected ref_words:", " ".join([word["word_text"] for word in ref_words]))
    return {"lemma": lemma_words, "description": central_words, "reference": ref_words}


def has_column_boundary(word: dict) -> bool:
    for boundary_symbol in boundary_symbols:
        if boundary_symbol in word["word_text"]:
            return True
    return False


def get_boundary_symbol(word: dict) -> Union[None, str]:
    for char in word["word_text"][::-1]:
        if char in boundary_symbols:
            return char
    return None


def check_correct_index_page_reference_column(central_words: List[dict], ref_words: List[dict], config: dict) -> tuple:
    if len(ref_words) == 0 or not starts_with_index_page_month_word(ref_words):
        return central_words, ref_words
    if len(central_words) == 0 or not has_column_boundary(central_words[-1]):
        return central_words, ref_words
    boundary_symbol = get_boundary_symbol(central_words[-1])
    split_index = central_words[-1]["word_text"].index(boundary_symbol)
    day_word = central_words[-1]["word_text"][split_index + 1:]
    central_words[-1]["word_text"] = central_words[-1]["word_text"][:split_index]
    if has_digit(day_word):
        ref_word = {
            "right": central_words[-1]["right"],
            "left": central_words[-1]["right"] - len(day_word) * config["avg_char_width"],
            "top": ref_words[0]["top"],
            "bottom": ref_words[0]["bottom"],
            "height": ref_words[0]["height"],
            "width": len(day_word) * config["avg_char_width"],
            "word_text": day_word
        }
        ref_words = [ref_word] + ref_words
    return central_words, ref_words


def align_column_lines(lines_col1: List[dict], lines_col2: List[dict]) -> List[tuple]:
    aligned = []
    for line_col1 in lines_col1:
        for line_col2 in lines_col2:
            overlap = line_vertical_overlap(line_col1, line_col2)
            if overlap > 0.5 * line_col2["height"]:
                aligned += [(line_col1, line_col2)]
    return aligned


def identify_index_page_headers(page_doc: dict) -> None:
    top_lines = []
    for column in page_doc["columns"]:
        top_lines += [base_parser.get_lines_above(column, threshold=450)]
    if len(top_lines) < 2:
        return False
    aligned = align_column_lines(top_lines[0], top_lines[1])
    for line1, line2 in aligned:
        aligned_words = line1["words"] + line2["words"]
        index_letters = [word for word in aligned_words if word["word_text"].lower() in "1indefx"]
        if len(index_letters) > 2:
            # print("index_letters:", [word["word_text"] for word in index_letters])
            line1["is_header"] = True
            line2["is_header"] = True
        # print("aligned words:", [word["word_text"] for word in aligned_words])
        aligned_text = get_spaced_line_text(aligned_words)
        if "datum" in aligned_text:
            line1["is_header"] = True
            line2["is_header"] = True
        # print("aligned_text: ##{}##".format(aligned_text))


def get_spaced_line_text(words: list, offset: int = 0, avg_char_width: int = 20) -> str:
    # use word coordinates to reconstruct spacing between words
    spaced_line_text = ""
    if len(words) == 0:
        return spaced_line_text
    spaced_line_text = " " * int(round(offset / avg_char_width))
    for index, word in enumerate(words[:-1]):
        spaced_line_text += word["word_text"]
        word_gap = words[index + 1]["left"] - word["right"]
        spaced_line_text += " " * int(round(word_gap / avg_char_width))
    spaced_line_text += words[-1]["word_text"]
    return spaced_line_text


def merge_entry_terms(curr_entry: dict, next_entry_line: dict) -> dict:
    # next line has no lemma term, so keep current lemma
    # and only update description and reference
    if len(next_entry_line["lemma"]) == 0:
        curr_entry["description"] += next_entry_line["description"]
        curr_entry["reference"] += next_entry_line["reference"]
        return curr_entry
    entry_bottom = max([word["bottom"] for word in next_entry_line["lemma"]])
    entry_top = min([word["top"] for word in next_entry_line["lemma"]])
    # next line has lemma term, and there is no current lemma
    # or, there is a large vertical gap with current lemma,
    # so this is the start of a new lemma.
    # Reset all current entries elements
    if len(curr_entry["lemma"]) == 0 or entry_top - curr_entry["bottom"] > 30:
        #print("starting -> ",
        #      "next lemma:", " ".join([word["word_text"] for word in next_entry_line["lemma"]]),
        #      "next left", next_entry_line["lemma"][0]["left"], " top:", entry_top, "next bottom:", entry_bottom)
        #print()
        curr_entry["lemma"] = next_entry_line["lemma"]
        curr_entry["description"] = next_entry_line["description"]
        curr_entry["reference"] = next_entry_line["reference"]
        curr_entry["bottom"] = entry_bottom
        curr_entry["top"] = entry_top
        return curr_entry
    # next line has lemma term, and there is a current lemma,
    # and the vertical gap is small, then this line is part of the
    # current lemma
    else:
        #print("merging -> ",
        #      "current lemma:", " ".join([word["word_text"] for word in curr_entry["lemma"]]),
        #      "bottom:", curr_entry["bottom"],
        #      "next lemma:", " ".join([word["word_text"] for word in next_entry_line["lemma"]]),
        #      "next top:", entry_top, "next bottom:", entry_bottom)
        #print()
        curr_entry["lemma"] += next_entry_line["lemma"]
        curr_entry["description"] += next_entry_line["description"]
        curr_entry["reference"] += next_entry_line["reference"]
        if entry_bottom > curr_entry["bottom"]:
            curr_entry["bottom"] = entry_bottom
        return curr_entry


def print_index_entry(index_entry: Dict[str, List[dict]]):
    lemma_text = " ".join([word["word_text"] for word in index_entry["lemma"]])
    description = [" ".join([word["word_text"] for word in index_entry["description"]])]
    reference_text = " ".join([word["word_text"] for word in index_entry["reference"]])
    metadata_string = f"{index_entry['source_page']}, {index_entry['source_column']}"
    print(f"{metadata_string}\tlemma: {lemma_text: <30}\treference: {reference_text}")
    #print("reference:", reference_text)
    #print("lemma:", lemma_text)
    #print("description:", description)
    #print("reference:", reference_text)
    #print("source page:", index_entry['source_page'])
    #print("source scan:", index_entry['source_scan'])
    #print()


def extract_index_page_lemmata(page_hocr: dict, config: dict) -> iter:
    left_margins = get_left_margins(page_hocr)
    add_margins_to_lines(page_hocr, left_margins)
    identify_index_page_headers(page_hocr)
    for ci, column in enumerate(page_hocr["columns"]):
        print("extracting from column", ci, 'with', len(column["lines"]), 'lines')
        curr_entry = {"bottom": 0, "lemma": [], "description": [], "reference": []}
        pixel_dist = column_parser.compute_gap_pixel_dist(column["lines"], config)
        central_column = find_index_page_central_column(pixel_dist)
        if not central_column:
            continue
        shift_left_margins = shift_line_left_to_left_margin(column, central_column)
        for left_margin in shift_left_margins:
            line_info = find_left_margin_merge_line(left_margin, column)
            merge_margin_with_line(column, line_info, left_margin)
        if ci < len(page_hocr["columns"]) - 1:
            shift_right_margins = shift_right_margin_to_left_margin(column, central_column)
            for right_margin in shift_right_margins:
                line_info = find_left_margin_merge_line(right_margin, page_hocr["columns"][ci+1])
                merge_margin_with_line(page_hocr["columns"][ci+1], line_info, right_margin)
        lemma_text = ""
        description = []
        reference_text = ""
        for line_index, line in enumerate(column["lines"]):
            if line["bottom"] < 400:
                continue
            if "is_header" in line and line["is_header"]:
                continue
                # print("bottom:", line["bottom"], "width:", line["width"], line["line_text"])
                # if "datum" in line["line_text"]:
                #     continue
            #print("page:", page_hocr["page_num"], "index line:", ci, "\t", line["bottom"], line["left"], "\t", line["line_text"])
            next_entry_line = split_index_page_table_row(line, central_column, config)
            curr_entry = merge_entry_terms(curr_entry, next_entry_line)
            if len(curr_entry["reference"]) > 0:
                #print(len(curr_entry["reference"]))
                curr_entry['source_page'] = page_hocr['page_num']
                curr_entry['source_scan'] = page_hocr['scan_num']
                curr_entry['source_column'] = ci
                yield curr_entry
                curr_entry = {"bottom": curr_entry["bottom"], "lemma": curr_entry["lemma"], "description": [], "reference": []}


def line_vertical_overlap(line1: dict, line2: dict) -> int:
    lowest_top = max(line1["top"], line2["top"])
    highest_bottom = min(line1["bottom"], line2["bottom"])
    return highest_bottom - lowest_top


#######################
# Identifying margins #
#######################


def shift_line_left_to_left_margin(column: dict, central_column: Dict[str, int]) -> List[dict]:
    shift_left_margins = []
    for li, line in enumerate(column["lines"]):
        left_margin_words = []
        column_words = []
        for wi, word in enumerate(line["words"][:-1]):
            column_gap = central_column["left"] - word["left"]
            if column_gap > 100:
                left_margin_words += [word]
            else:
                column_words += [word]
        if len(left_margin_words) > 0:
            shift_left_margins += [column_parser.construct_line_from_words(left_margin_words)]
            line["words"] = column_words
            line["line_text"] = " ".join([word['word_text'] for word in line["words"]])
    return shift_left_margins


def shift_right_margin_to_left_margin(column: dict, central_column: Dict[str, int]) -> List[dict]:
    shift_right_margins = []
    for li, line in enumerate(column["lines"]):
        for wi, word in enumerate(line["words"][:-1]):
            next_word = line["words"][wi + 1]
            word_gap = next_word["left"] - word["right"]
            column_gap = next_word["left"] - central_column["right"]
            if word_gap > 250 and column_gap > 250:
                #print(li, wi, word_gap, next_word["left"], next_word["word_text"])
                #print("\tcentral column", central_column)
                #print(f'line has {len(line["words"])} words')
                column_words = line["words"][:wi+1]
                right_margin_words = line["words"][wi+1:]
                shift_right_margins += [column_parser.construct_line_from_words(right_margin_words)]
                line["words"] = column_words
                new_line = column_parser.construct_line_from_words(column_words)
                line["line_text"] = " ".join([word['word_text'] for word in line["words"]])
                #print(f'line has {len(line["words"])} words')
                break
    return shift_right_margins


def get_left_margins(page_hocr: dict) -> List[dict]:
    left_margins = []
    for column in page_hocr["columns"]:
        for line in column["lines"]:
            if "left_margin" in line:
                left_margin = filter_margin_noise(line["left_margin"])
                if left_margin:
                    left_margins += [left_margin]
    return left_margins


def find_left_margin_merge_column(left_margin: dict, page_hocr: dict) -> dict:
    # column_lefts = [column["left"] for column in page_hocr["columns"]]
    column_rights = [column["right"] for column in page_hocr["columns"]]
    # for ci, column_left in enumerate(column_lefts):
    #    if left_margin["left"] < column_left:
    #        break
    for ci, column_right in enumerate(column_rights):
        if left_margin["right"] < column_right:
            break
    # print("column_lefts:", column_lefts)
    # print("column_rights:", column_rights)
    return page_hocr["columns"][ci]


def find_left_margin_merge_line(left_margin: dict, merge_column: dict) -> dict:
    margin_line_index = None
    margin_add_type = None
    max_overlap = 0
    for li, line in enumerate(merge_column["lines"]):
        if len(line["words"]) == 0:
            continue
        first_word = line["words"][0]
        # print(left_margin["top"], left_margin["bottom"], line["top"], line["bottom"], max_overlap, line["line_text"])
        if first_word["bottom"] < left_margin["top"]:
            continue
        elif first_word["top"] > left_margin["bottom"]:
            if max_overlap == 0:
                margin_line_index = li
                margin_add_type = "insert"
            break
        elif first_word["bottom"] > left_margin["top"]:
            overlap = line_vertical_overlap(left_margin, first_word)
            if overlap > first_word["height"] / 2 and overlap > max_overlap:
                margin_line_index = li
                margin_add_type = "merge"
                max_overlap = overlap
    return {"line_index": margin_line_index, "add_type": margin_add_type}


def filter_margin_noise(left_margin: dict) -> Union[dict, None]:
    if left_margin["left"] < 2300:
        left_margin_threshold = 300
    else:
        left_margin_threshold = 2500
    filtered_words = [word for word in left_margin["words"] if word["left"] > left_margin_threshold]
    if len(filtered_words) == 0:
        return None
    else:
        return column_parser.construct_line_from_words(filtered_words)


def add_margins_to_lines(page_hocr: dict, left_margins: List[dict]) -> None:
    for left_margin in left_margins:
        merge_column = find_left_margin_merge_column(left_margin, page_hocr)
        line_info = find_left_margin_merge_line(left_margin, merge_column)
        merge_margin_with_line(merge_column, line_info, left_margin)


def merge_margin_with_line(merge_column: dict, line_info: dict, left_margin: dict) -> None:
    #print("left_margin:", [word["left"] for word in left_margin["words"]], "bottoms:", [word["bottom"] for word in left_margin["words"]])
    #print("left_margin:", [word["word_text"] for word in left_margin["words"]])
    #print(line_info["add_type"])
    if line_info["add_type"] == "merge":
        merge_line = merge_column["lines"][line_info["line_index"]]
        merge_line["words"] = left_margin["words"] + merge_line["words"]
        merge_line = column_parser.construct_line_from_words(merge_line["words"])
        merge_column["lines"][line_info["line_index"]] = merge_line
    elif line_info["add_type"] == "insert":
        pre_lines = merge_column["lines"][:line_info["line_index"]]
        post_lines = merge_column["lines"][line_info["line_index"]:]
        merge_column["lines"] = pre_lines + [left_margin] + post_lines
        merge_line = merge_column["lines"][line_info["line_index"]]
    #print("merged line text:", merge_line["line_text"])
    #print("merged line top:", [word["top"] for word in merge_line["words"]])
    #print("merged line left:", [word["left"] for word in merge_line["words"]])
    #print("merged line bottom:", [word["bottom"] for word in merge_line["words"]])
    #print()

