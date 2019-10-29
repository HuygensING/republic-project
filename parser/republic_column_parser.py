from collections import Counter


def word_gap(curr_word: dict, next_word: dict) -> int:
    return next_word["left"] - curr_word["right"]


def find_large_word_gaps(words: list, column_config: dict) -> list:
    gap_indices = []
    columns = []
    if len(words) < 2:
        return gap_indices
    words = [{"right": 0}] + words # add begin of page boundary]
    words = words + [{"left": column_config["hocr_box"]["right"]}]
    for curr_index, curr_word in enumerate(words[:-1]):
        next_word = words[curr_index+1]
        gap = word_gap(curr_word, next_word)
        if word_gap(curr_word, next_word) >= column_config["column_gap_threshold"]:
            gap_indices += [{"word_index": curr_index+1, "gap": gap, "starts_at": curr_word["right"], "ends_at": next_word["left"]}]
    return gap_indices


def filter_low_confidence_words(words: list, config) -> list:
    return [word for word in words if word["word_conf"] > config["word_conf_threshold"] and word["word_text"] not in config["filter_words"]]


def fulltext_char_ratio(line: dict, fulltext_num_chars: int) -> float:
    line_num_chars = sum([len(word["word_text"]) for word in line["words"]])
    return line_num_chars / fulltext_num_chars


def select_fulltext_lines(lines: list, column_config: dict) -> list:
    max_width = max([line["width"] for line in lines])
    fulltext_num_chars = max_width / column_config["avg_char_width"]
    for line in lines:
        line_num_chars = sum([len(word["word_text"]) for word in line["words"]])
        #print(fulltext_num_chars, max_width, len(line["words"]), line_num_chars, fulltext_char_ratio(line, fulltext_num_chars))
    return [line for line in lines if fulltext_char_ratio(line, fulltext_num_chars) > column_config["fulltext_char_threshold"]]
    #return [line for line in lines if len(line["words"]) > column_config["fulltext_words_threshold"]]


def new_gap_pixel_interval(pixel: int) -> dict:
    return {"start": pixel, "end": pixel}


def determine_freq_gap_interval(pixel_dist: Counter, freq_threshold: int, column_config: dict) -> list:
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
            if curr_interval["end"] - curr_interval["start"] < column_config["column_gap_threshold"]:
                #print("skipping interval:", curr_interval, "\tcurr_pixel:", curr_pixel, "next_pixel:", next_pixel)
                continue
            #print("adding interval:", curr_interval, "\tcurr_pixel:", curr_pixel, "next_pixel:", next_pixel)
            gap_pixel_intervals += [curr_interval]
            curr_interval = new_gap_pixel_interval(next_pixel)
    gap_pixel_intervals += [curr_interval]
    return gap_pixel_intervals


def compute_gap_pixel_dist(lines: list, column_config) -> Counter:
    pixel_dist = Counter()
    for line in lines:
        words = filter_low_confidence_words(line["words"], column_config)
        #print("line", len(line["words"]), len(words))
        for gap in find_large_word_gaps(words, column_config):
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


def determine_column_start_end(doc_hocr: dict, column_config: dict) -> list:
    columns_info = []
    if len(doc_hocr["lines"]) == 0:
        return columns_info
    lines = select_fulltext_lines(doc_hocr["lines"], column_config)
    gap_pixel_freq_threshold = int(len(lines) * column_config["gap_pixel_freq_ratio"])
    #print("num lines:", len(dp_hocr["lines"]), "num fulltext lines:", len(lines), gap_pixel_freq_threshold)
    gap_pixel_dist = compute_gap_pixel_dist(lines, column_config)
    #print("pixel dist:", gap_pixel_dist.items())
    gap_pixel_intervals = determine_freq_gap_interval(gap_pixel_dist, gap_pixel_freq_threshold, column_config)
    #print("intervals:", gap_pixel_intervals)
    for interval_index, curr_interval in enumerate(gap_pixel_intervals[:-1]):
        next_interval = gap_pixel_intervals[interval_index+1]
        columns_info += [{"start": curr_interval["end"], "end": next_interval["start"]}]
    return columns_info


def is_column_gap(gap: dict, columns_info: list, column_config: dict) -> bool:
    for column_info in columns_info:
        if abs(gap["starts_at"] - column_info["start"]) < column_config["column_gap_threshold"]:
            return True
        if abs(gap["ends_at"] - column_info["start"]) < column_config["column_gap_threshold"]:
            return True
        if gap["starts_at"] < column_info["start"] and gap["ends_at"] > column_info["start"]:
            return True
    return False


def split_line_on_columns(line: dict, column_info: list, column_config: dict) -> list:
    words = filter_low_confidence_words(line["words"], column_config)
    gaps = find_large_word_gaps(words, column_config)
    column_gaps = [gap for gap in gaps if is_column_gap(gap, column_info, column_config)]
    line_columns = []
    from_index = 0
    for gap in column_gaps:
        to_index = gap["word_index"] - 1
        if to_index > from_index:
            line_column = construct_line_from_words(words[from_index:to_index])
            #print(from_index, to_index, gap)
            if line_column["right"] < column_info[0]["start"]: # skip margin noise before first column starts
                from_index = to_index
                continue
            line_columns += [line_column]
        from_index = to_index
    if len(words) > from_index+1:
        line_columns += [construct_line_from_words(words[from_index:])]
    return line_columns


def compute_interval_overlap(start1: int, end1: int, start2: int, end2: int) -> int:
    if end1 < start2: # interval 1 before interval 2, no overlap
        return 0
    if start1 > end2: # interval 1 after interval 2, no overlap
        return 0
    start_overlap = start1 if start1 > start2 else start2
    end_overlap = end1 if end1 < end2 else end2
    return end_overlap - start_overlap


def find_column_number(line_column: dict, columns_info: list, hocr_box) -> int:
    left = line_column["left"]
    right = line_column["right"]
    for column_index, column_info in enumerate(columns_info):
        column_start = column_info["start"]
        column_end = column_info["end"]
        next_start = columns_info[column_index+1] if len(columns_info) > column_index+1 else hocr_box["right"] # end of page
        #print(column_index, column_start, next_start, left, right)
        overlap = compute_interval_overlap(column_start, column_end, left, right)
        #print(left, right, overlap, overlap / (right - left))
        if overlap > 0.5:
            return column_index
        if abs(left - column_start) < 50:
            return column_index
        elif left > column_start and column_end and right < column_end:  # for center aligned text
            return column_index
        elif abs(left - column_start) < 100 and column_end and right > column_end: # for full page width text
            return column_index
        elif right < column_start + 50 and column_index > 0:
            return column_index
    return len(columns_info)-1


def set_column_stats(column: dict):
    column["num_lines"] = len(column["lines"])
    column["num_words"] = sum([len(line["words"]) for line in column["lines"]])
    column["left"] = min([line["left"] for line in column["lines"]])
    column["right"] = max([line["right"] for line in column["lines"]])
    column["width"] = column["right"] - column["left"]
    column["top"] = column["lines"][0]["top"]
    column["bottom"] = column["lines"][-1]["bottom"]


def split_lines_on_columns(sp_hocr: dict, columns_info: list, column_config: dict) -> dict:
    columns_hocr = {"columns": [{"lines": []} for _ in columns_info]}
    for line in sp_hocr["lines"]:
        line_columns = split_line_on_columns(line, columns_info, column_config)
        for line_column in line_columns:
            column_index = find_column_number(line_column, columns_info, column_config["hocr_box"])
            line_column["column_num"] = column_index + 1
            columns_hocr["columns"][column_index]["lines"] += [line_column]
    for column in columns_hocr["columns"]:
        set_column_stats(column)
    return columns_hocr


def construct_line_from_words(words):
    left = words[0]["left"]
    right = words[-1]["right"]
    top = max([word["top"] for word in words])
    bottom =  max([word["bottom"] for word in words])
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


def parse_hocr_columns(sp_hocr: dict, columns_info: list, column_config: dict) -> dict:
    return split_lines_on_columns(sp_hocr, columns_info, column_config)


