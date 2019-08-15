import re
import copy
import republic_base_page_parser as page_parser

#################################
# Parse and correct index pages #
#################################

repeat_symbol = "——"

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

def line_has_page_ref(line):
    return re.search(r"\b\d+\.", line["line_text"])

def count_page_ref_lines(page_info):
    count = 0
    for column_info in page_info["columns"]:
        for line in column_info["column_hocr"]["lines"]:
            if line_has_page_ref(line):
                count += 1
    return count

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

def is_index_header(line, hocr_page, DEBUG=False):
    # index header has either
    #  year I N D
    #  year D E X
    next_line = page_parser.get_next_line(hocr_page["lines"].index(line), hocr_page["lines"])
    if not page_parser.is_header(line, next_line):
        return False
    if len(line["words"]) > 1 and page_parser.get_highest_inter_word_space(line) > 500: # if there is only text at the edges of the column, it's not a header
        return False
    if not page_parser.has_mid_column_text(line, hocr_page): # some of the index header letters are in the middle of the column
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
    if not line:
        return index_score
    if len(line["words"]) <= 5: # index header has few "words"
        index_score += 1
        if DEBUG:
            print("\tIndex test - few words")
    if page_parser.num_line_chars(line) < 10: # index header has few characters (sometimes year +  I N D or year + D E X)
        index_score += 1
        if DEBUG:
            print("\tIndex test - few chars")
    if line["top"] < 250: # index header is near the top of the page
        index_score += 1
        if DEBUG:
            print("\tIndex test - near top")
    if line["width"] > 250 and page_parser.num_line_chars(line) < 10: # index header is wide for having few characters
        index_score += 1
        if DEBUG:
            print("\tIndex test - wide")
    if page_parser.get_highest_inter_word_space(line) > 150: # The I N D E X characters usually have around 200 pixels between them
        index_score += 1
        if DEBUG:
            print("\tIndex test - high inter-word space")
    if index_score > 3:
        if DEBUG:
            print("\tIndex test - index_header_score:", index_score, "line: #{}#".format(line["line_text"]))
    return index_score

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
    if not page_parser.proper_column_cut(hocr_index_page):
        if (DEBUG):
            print("\tCOLUMN IMPROPERLY CUT")
        return index_entry_lines
    for line_index, line in enumerate(hocr_index_page["lines"]):
        next_line = page_parser.get_next_line(line_index, hocr_index_page["lines"])
        if page_parser.is_in_top_margin(line):
            if (DEBUG):
                print("\tIS IN TOP MARGIN")
            continue
        if not in_body and is_index_header(line, hocr_index_page, DEBUG=False):
            if (DEBUG):
                print("\tIS INDEX HEADER:", line_index, line["top"], "\t##", line["spaced_line_text"])
            in_body = True
            continue
        if not in_body and page_parser.is_full_text_line(line):
            if (DEBUG):
                print("\tFIRST BODY LINE:", line_index, line["top"], "\t##", line["spaced_line_text"])
            in_body = True
            #continue
        if not in_body and page_parser.is_header(line, next_line):
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

