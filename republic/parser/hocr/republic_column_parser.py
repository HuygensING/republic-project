from collections import Counter
from typing import Union


def word_gap(curr_word: dict, next_word: dict) -> int:
    return next_word["left"] - curr_word["right"]


def find_large_word_gaps(words: list, config: dict) -> list:
    gap_indices = []
    if len(words) < 2:
        return gap_indices
    words = [{"right": 0}] + words # add begin of page boundary]
    right_boundary = 2500 if words[-1]["right"] < 2500 else 4900
    words = words + [{"left": right_boundary}] # add empty word for gap from last word to end of page/column
    for curr_index, curr_word in enumerate(words[:-1]):
        next_word = words[curr_index+1]
        gap = word_gap(curr_word, next_word)
        if word_gap(curr_word, next_word) >= config["column_gap"]["gap_threshold"]:
            gap_indices += [{"word_index": curr_index+1, "gap": gap, "starts_at": curr_word["right"], "ends_at": next_word["left"]}]
    return gap_indices


def filter_low_confidence_words(words: list, config) -> list:
    return [word for word in words if len(word["word_text"]) >= 4 or (word["word_conf"] >= config["word_conf_threshold"] and word["word_text"] not in config["filter_words"])]


def fulltext_char_ratio(line: dict, fulltext_num_chars: int) -> float:
    line_num_chars = sum([len(word["word_text"]) for word in line["words"]])
    return line_num_chars / fulltext_num_chars


def select_fulltext_lines(lines: list, config: dict) -> list:
    max_width = max([line["width"] for line in lines])
    fulltext_num_chars = max_width / config["avg_char_width"]
    for line in lines:
        line_num_chars = sum([len(word["word_text"]) for word in line["words"]])
        # print(fulltext_num_chars, max_width, len(line["words"]), line_num_chars, fulltext_char_ratio(line, fulltext_num_chars))
    return [line for line in lines if fulltext_char_ratio(line, fulltext_num_chars) > config["fulltext_char_threshold"]]


def new_gap_pixel_interval(pixel: int) -> dict:
    return {"start": pixel, "end": pixel}


def determine_freq_gap_interval(pixel_dist: Counter, freq_threshold: int, config: dict) -> list:
    common_pixels = sorted([pixel for pixel, freq in pixel_dist.items() if freq > freq_threshold])
    gap_pixel_intervals = []
    if len(common_pixels) == 0:
        return gap_pixel_intervals
    curr_interval = new_gap_pixel_interval(common_pixels[0])
    for curr_index, curr_pixel in enumerate(common_pixels[:-1]):
        next_pixel = common_pixels[curr_index+1]
        if next_pixel - curr_pixel < 100:
            curr_interval["end"] = next_pixel
        else:
            if curr_interval["end"] - curr_interval["start"] < config["column_gap"]["gap_threshold"]:
                # print("skipping interval:", curr_interval, "\tcurr_pixel:", curr_pixel, "next_pixel:", next_pixel)
                continue
            # print("adding interval:", curr_interval, "\tcurr_pixel:", curr_pixel, "next_pixel:", next_pixel)
            gap_pixel_intervals += [curr_interval]
            curr_interval = new_gap_pixel_interval(next_pixel)
    gap_pixel_intervals += [curr_interval]
    return gap_pixel_intervals


def compute_gap_pixel_dist(lines: list, config) -> Counter:
    pixel_dist = Counter()
    for line in lines:
        words = filter_low_confidence_words(line["words"], config)
        # print("line, all words:", len(line["words"]), "\thigh-confidence words:", len(words), "\t", line["line_text"])
        for gap in find_large_word_gaps(words, config):
            # print("gap:", gap)
            pixel_dist.update([pixel for pixel in range(gap["starts_at"], gap["ends_at"]+1)])
    return pixel_dist
    # print(pixel_dist.most_common(2000))


def split_line_on_column_gaps(line: dict, gap_info: list) -> list:
    words = [word for word in line["words"]]
    columns = []
    for gap_info in sorted(gap_info, key=lambda x: x["word_index"], reverse=True):
        print("gap_index:", gap_info["word_index"], gap_info["gap"])
        column = words[gap_info["word_index"]:]
        print("num words:", len(column))
        words = words[:gap_info["word_index"]]
        columns = [column] + columns
    columns = [words] + columns
    return columns


def determine_column_start_end(doc_hocr: dict, config: dict) -> list:
    columns_info = []
    if len(doc_hocr['textregions']) > 0:
        # columns already split
        return columns_info
    if len(doc_hocr["textregions"][0]["lines"]) == 0:
        # this page is empty, there are no columns
        return columns_info
    lines = select_fulltext_lines(doc_hocr["textregions"][0]["lines"], config)
    if len(lines) == 0:
        # if there are no fulltext lines, use all lines and hope for the best
        lines = doc_hocr["textregions"][0]["lines"]
    gap_pixel_freq_threshold = int(len(lines) * config["column_gap"]["gap_pixel_freq_ratio"])
    # print("num lines:", len(doc_hocr["lines"]), "num fulltext lines:", len(lines), gap_pixel_freq_threshold)
    gap_pixel_dist = compute_gap_pixel_dist(lines, config)
    # print("pixel dist:", gap_pixel_dist.items())
    gap_pixel_intervals = determine_freq_gap_interval(gap_pixel_dist, gap_pixel_freq_threshold, config)
    # print("intervals:", gap_pixel_intervals)
    for interval_index, curr_interval in enumerate(gap_pixel_intervals[:-1]):
        next_interval = gap_pixel_intervals[interval_index+1]
        columns_info += [{"start": curr_interval["end"], "end": next_interval["start"]}]
    if len(doc_hocr["textregions"][0]["lines"]) > 0 and len(columns_info) == 0:
        try:
            columns_info += [{"start": doc_hocr["left"], "end": doc_hocr["right"]}]
        except KeyError:
            print(doc_hocr)
            raise
    return columns_info


def is_column_gap(gap: dict, columns_info: list, config: dict) -> bool:
    for column_info in columns_info:
        if abs(gap["starts_at"] - column_info["start"]) < config["column_gap"]["gap_threshold"]:
            return True
        if abs(gap["ends_at"] - column_info["start"]) < config["column_gap"]["gap_threshold"]:
            return True
        if gap["starts_at"] < column_info["start"] < gap["ends_at"]:
            return True
    return False


def filter_margin_noise(words: list) -> list:
    if len(words) == 0:
        return words
    if words[-1]["right"] < 2400:
        left_margin_threshold = 300
    else:
        left_margin_threshold = 2500
    return [word for word in words if word["left"] > left_margin_threshold]


def split_line_on_columns(line: dict, column_info: list, config: dict) -> list:
    # print("line text:", line["line_text"])
    words = filter_low_confidence_words(line["words"], config)
    words = filter_margin_noise(words)
    # print("words word_text:", [word["word_text"] for word in words])
    # print("words left:", [word["left"] for word in words])
    # print("words right:", [word["right"] for word in words])
    gaps = find_large_word_gaps(words, config)
    column_gaps = [gap for gap in gaps if is_column_gap(gap, column_info, config)]
    # print("column gaps:", column_gaps)
    line_columns = []
    left_margin = None
    from_index = 0
    num_line_column_words = 0
    for gap in column_gaps:
        to_index = gap["word_index"] - 1
        if to_index > from_index:
            line_column = construct_line_from_words(words[from_index:to_index])
            if line_column["right"] < column_info[0]["start"]:
                # skip margin noise before first column starts
                num_line_column_words += len(line_column["words"])
                from_index = to_index
                left_margin = line_column
                continue
            line_columns += [line_column]
            num_line_column_words += len(line_column["words"])
        from_index = to_index
    if len(words) > from_index:
        line_column = construct_line_from_words(words[from_index:])
        if line_column["right"] < column_info[0]["start"]:
            # skip margin noise before first column starts
            left_margin = line_column
        else:
            # add remaining words as additional column
            line_columns += [line_column]
        num_line_column_words += len(line_column["words"])
    if num_line_column_words != len(words):
        for line_column in line_columns:
            print("line column len:", len(line_column["words"]))
        raise IndexError("Not all words selected!")
    if left_margin:
        if len(line_columns) == 0:
            line_columns += [make_margin_only_line(left_margin)]
        line_columns[0]["left_margin"] = left_margin
    return line_columns


def make_margin_only_line(left_margin: dict) -> dict:
    return {
        "words": [],
        "left": left_margin["right"],
        "right": left_margin["right"],
        "top": left_margin["top"],
        "bottom": left_margin["bottom"],
        "height": left_margin["height"],
        "width": 0,
        "line_text": "",
        "left_margin": left_margin
    }


def compute_interval_overlap(start1: int, end1: int, start2: int, end2: int) -> int:
    if end1 < start2:
        # interval 1 before interval 2, no overlap
        return 0
    if start1 > end2:
        # interval 1 after interval 2, no overlap
        return 0
    start_overlap = start1 if start1 > start2 else start2
    end_overlap = end1 if end1 < end2 else end2
    return end_overlap - start_overlap


def find_column_number(line_column: dict, columns_info: list, page_hocr) -> int:
    left = line_column["left"]
    right = line_column["right"]
    for column_index, column_info in enumerate(columns_info):
        column_start = column_info["start"]
        column_end = column_info["end"]
        # end of page
        _next_start = columns_info[column_index+1] if len(columns_info) > column_index+1 else page_hocr["right"]
        # print(column_index, column_start, next_start, left, right)
        overlap = compute_interval_overlap(column_start, column_end, left, right)
        # print(left, right, overlap, overlap / (right - left))
        if overlap > 0.5:
            return column_index
        if abs(left - column_start) < 50:
            return column_index
        elif left > column_start and column_end and right < column_end:  # for center aligned text
            return column_index
        elif abs(left - column_start) < 100 and column_end and right > column_end:
            # for full page width text
            return column_index
        elif right < column_start + 50 and column_index > 0:
            return column_index
    return len(columns_info)-1


def set_column_stats(column: dict):
    lines = column["textregions"][0]["lines"]
    column["metadata"]["num_lines"] = len(lines)
    column["metadata"]["num_words"] = sum([len(line["words"]) for line in lines])
    if len(lines) > 0:
        column["coords"]["left"] = min([line["left"] for line in lines])
        column["coords"]["right"] = max([line["right"] for line in lines])
        column["coords"]["top"] = lines[0]["top"]
        column["coords"]["bottom"] = lines[-1]["bottom"]
        column["coords"]["width"] = column["coords"]["right"] - column["coords"]["left"]
        column["coords"]["height"] = column["coords"]["bottom"] - column["coords"]["top"]


def split_lines_on_columns(sp_hocr: dict, columns_info: list, config: dict) -> dict:
    # print("splitting lines on columns")
    columns_hocr = {"textregions": [{"lines": []} for _ in columns_info]}
    for line in sp_hocr["textregions"][0]["lines"]:
        # print("line left", line["left"], "line right:", line["right"], line["line_text"])
        line_columns = split_line_on_columns(line, columns_info, config)
        prev_column_index = None
        for line_column in line_columns:
            column_index = find_column_number(line_column, columns_info, sp_hocr)
            # print("\t\tcolumn_index:", column_index)
            if prev_column_index and prev_column_index == column_index:
                # line_column belongs to the same column as the previous line_column, so merge them
                prev_line = columns_hocr["textregions"][column_index]["lines"][-1]
                words = prev_line["words"] + line_column["words"]
                line_column = construct_line_from_words(words)
                if "left_margin" in prev_line:
                    line_column["left_margin"] = prev_line["left_margin"]
                    columns_hocr["textregions"][column_index]["lines"][-1] = line_column
            else:
                line_column["column_num"] = column_index + 1
                columns_hocr["textregions"][column_index]["lines"] += [line_column]
            prev_column_index = column_index
    for column in columns_hocr["textregions"]:
        set_column_stats(column)
    return columns_hocr


def construct_line_from_words(words):
    left = words[0]["left"]
    right = words[-1]["right"]
    top = max([word["top"] for word in words])
    bottom = max([word["bottom"] for word in words])
    return {
        "width": right - left,
        "height": bottom - top,
        "left": left,
        "right": right,
        "top": top,
        "bottom": bottom,
        "words": words,
        "line_text": " ".join([word["word_text"] for word in words])
    }


def parse_hocr_columns(sp_hocr: dict, columns_info: list, config: dict) -> dict:
    return split_lines_on_columns(sp_hocr, columns_info, config)
