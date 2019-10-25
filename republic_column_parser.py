import json
from collections import Counter
import republic_page_parser as page_parser


def word_gap(curr_word: dict, next_word: dict) -> int:
    return next_word["left"] - curr_word["right"]


def find_large_word_gaps(words: list, gap_threshold: int = 200) -> list:
    gap_indices = []
    columns = []
    if len(words) < 2:
        return gap_indices
    words = [{"right": 0}] + words # add begin of page boundary
    for curr_index, curr_word in enumerate(words[:-1]):
        next_word = words[curr_index+1]
        gap = word_gap(curr_word, next_word)
        if word_gap(curr_word, next_word) >= gap_threshold:
            gap_indices += [{"word_index": curr_index+1, "gap": gap, "starts_at": curr_word["right"], "ends_at": next_word["left"]}]
    return gap_indices


def filter_low_confidence_words(words: list, config) -> list:
    return [word for word in words if word["word_conf"] > config["word_conf_threshold"] and word["word_text"] not in config["filter_words"]]


def select_fulltext_lines(lines: list, column_config: dict) -> list:
    return [line for line in lines if len(line["words"]) > column_config["fulltext_words_threshold"]]


def new_gap_pixel_interval(pixel: int) -> dict:
    return {"start": pixel, "end": pixel}


def determine_freq_gap_interval(pixel_dist: Counter, freq_threshold: int) -> list:
    common_pixels = sorted([pixel for pixel, freq in  pixel_dist.items() if freq > freq_threshold])
    gap_pixel_intervals = []
    if len(common_pixels) == 0:
        return gap_pixel_intervals
    curr_interval = new_gap_pixel_interval(common_pixels[0])
    for curr_index, curr_pixel in enumerate(common_pixels[:-1]):
        next_pixel = common_pixels[curr_index+1]
        if next_pixel - curr_pixel < 100:
            curr_interval["end"] = next_pixel
        else:
            gap_pixel_intervals += [curr_interval]
            curr_interval = new_gap_pixel_interval(next_pixel)
    gap_pixel_intervals += [curr_interval]
    return gap_pixel_intervals


def compute_gap_pixel_dist(lines: list, column_config) -> Counter:
    pixel_dist = Counter()
    for line in lines:
        words = filter_low_confidence_words(line["words"], column_config)
        #print("line", len(line["words"]), len(words))
        for gap in find_large_word_gaps(words, gap_threshold=column_config["column_gap_threshold"]):
            pixel_dist.update([pixel for pixel in range(gap["starts_at"], gap["ends_at"]+1)])
    return pixel_dist
    #print(pixel_dist.most_common(2000))


def split_line_on_column_gaps(line: dict, gap_info: list) -> list:
    words = [word for word in line["words"]]
    for gap_info in sorted(gap_info, lambda x: x["word_index"], reverse=True):
        print("gap_index:", gap_info["word_index"], gap_info["gap"])
        column = words[gap_info["word_index"]:]
        print("num words:", len(column))
        words = words[:gap_info["word_index"]]
        columns = [column] + columns
    columns = [words] + columns
    return columns


def determine_column_starts(dp_hocr: dict, column_config: dict) -> list:
    lines = select_fulltext_lines(dp_hocr["lines"], column_config)
    column_config["gap_pixel_freq_threshold"] = int(len(lines)* column_config["gap_pixel_freq_ratio"])
    #print("num lines:", len(dp_hocr["lines"]), "num fulltext lines:", len(lines), column_config["gap_pixel_freq_threshold"])
    gap_pixel_dist = compute_gap_pixel_dist(lines, column_config)
    gap_pixel_intervals = determine_freq_gap_interval(gap_pixel_dist, column_config["gap_pixel_freq_threshold"])
    column_starts = [interval["end"] for interval in gap_pixel_intervals]
    return column_starts


def is_column_gap(gap: dict, column_starts: list, column_config: dict) -> bool:
    for column_start in column_starts:
        if abs(gap["starts_at"] - column_start) < column_config["column_gap_threshold"]:
            return True
        if abs(gap["ends_at"] - column_start) < column_config["column_gap_threshold"]:
            return True
        if gap["starts_at"] < column_start and gap["ends_at"] > column_start:
            return True
    return False


def make_line_column(words):
    return {
        "left": words[0]["left"],
        "right": words[-1]["right"],
        "top": max([word["top"] for word in words]),
        "bottom": max([word["bottom"] for word in words]),
        "words": words
    }


def split_line_on_columns(line: dict, column_starts: list, column_config: dict) -> list:
    words = filter_low_confidence_words(line["words"], column_config)
    gaps = find_large_word_gaps(words, gap_threshold=column_config["column_gap_threshold"])
    column_gaps = [gap for gap in gaps if is_column_gap(gap, column_starts, column_config)]
    line_columns = []
    from_index = 0
    for gap in column_gaps:
        to_index = gap["word_index"] - 1
        if to_index > from_index:
            line_column = make_line_column(words[from_index:to_index])
            #print(from_index, to_index, gap)
            if line_column["right"] < column_starts[0]: # skip margin noise before first column starts
                from_index = to_index
                continue
            line_columns += [line_column]
        from_index = to_index
    if len(words) > from_index+1:
        line_columns += [make_line_column(words[from_index:])]
    return line_columns


def compute_interval_overlap(start1: int, end1: int, start2: int, end2: int) -> int:
    if end1 < start2: # interval 1 before interval 2, no overlap
        return 0
    if start1 > end2: # interval 1 after interval 2, no overlap
        return 0
    start_overlap = start1 if start1 > start2 else start2
    end_overlap = end1 if end1 < end2 else end2
    return end_overlap - start_overlap


def find_column_number(line_column: dict, column_starts: list) -> int:
    left = line_column["left"]
    right = line_column["right"]
    for column_index, column_start in enumerate(column_starts):
        next_start = column_starts[column_index+1] if len(column_starts) > column_index+1 else 4800 # end of page
        #print(column_index, column_start, next_start, left, right)
        overlap = compute_interval_overlap(column_start, next_start, left, right)
        #print(left, right, overlap, overlap / (right - left))
        if overlap > 0.5:
            return column_index
        if abs(left - column_start) < 50:
            return column_index
        elif left > column_start and next_start and right < next_start:  # for center aligned text
            return column_index
        elif abs(left - column_start) < 100 and next_start and right > next_start: # for full page width text
            return column_index
        elif right < column_start + 50 and column_index > 0:
            return column_index
    return len(column_starts)-1


def split_lines_on_columns(dp_hocr: dict, column_starts: list, column_config: dict) -> dict:
    columns_hocr = {"columns": [{"lines": []} for _ in column_starts]}
    for line in dp_hocr["lines"]:
        line_columns = split_line_on_columns(line, column_starts, column_config)
        for line_column in line_columns:
            column_index = find_column_number(line_column, column_starts)
            line_column["column_num"] = column_index + 1
            columns_hocr["columns"][column_index]["lines"] += [line_column]
            #print("column {}, line: ({}, {})\t".format(line_column["column_num"], line_column["left"], line_column["right"]), " ".join([word["word_text"] for word in line_column["words"]]))
    return columns_hocr


def parse_hocr_columns(scan_info, inventory_config, column_config):
    dp_hocr = page_parser.get_double_page_hocr(scan_info, inventory_config)
    column_starts = determine_column_starts(dp_hocr, column_config)
    print(column_starts)
    return split_lines_on_columns(dp_hocr, column_starts, column_config)


