from typing import Union, TypeVar, List

Word = TypeVar('Word', bound='HOCRWord')
Line = TypeVar('Line', bound='HOCRLine')
Column = TypeVar('Column', bound='HOCRColumn')
Object = TypeVar('Object', bound='HOCRObject')


def construct_box_from_items(items: List[Object]) -> dict:
    left = min([item.left for item in items])
    right = max([item.right for item in items])
    top = min([item.top for item in items])
    bottom = max([item.bottom for item in items])
    return {
        "left": left,
        "right": right,
        "top": top,
        "bottom": bottom,
        "height": bottom - top,
        "width": right - left,
    }


def construct_line_from_words(words: List[Word], config: Union[dict, None]) -> Line:
    line = construct_box_from_items(words)
    line["words"] = words
    return HOCRLine(line, config)


def filter_low_confidence_words(words: List[Word], conf_threshold: int = 0) -> List[Word]:
    return [word for word in words if word.word_conf >= conf_threshold]


def filter_blacklist_words(words: List[Word], blacklist: List[str]) -> List[Word]:
    return [word for word in words if word.word_text not in blacklist]


def filter_words(words: List[Word], config: dict) -> List[Word]:
    filtered_words = filter_low_confidence_words(words, conf_threshold=config["word_conf_threshold"])
    return filter_blacklist_words(filtered_words, config["filter_words"])


def filter_lines(lines: List[Line], config: dict) -> List[Line]:
    filtered_lines = []
    for line in lines:
        words = filter_words(line["words"], config)
        if len(words) > 0:
            filtered_line = construct_line_from_words(words, config)
            filtered_lines += [filtered_line]
    return filtered_lines


def add_line_distances(lines):
    for curr_index, curr_line in enumerate(lines):
        if curr_index > 0:
            prev_line = lines[curr_index - 1]
            line_gap = curr_line.line_gap(prev_line)
            prev_line.set_line_distance(to_next=line_gap)
            curr_line.set_line_distance(to_prev=line_gap)
        if curr_index < len(lines) - 1:
            next_line = lines[curr_index + 1]
            line_gap = curr_line.line_gap(next_line)
            next_line.set_line_distance(to_prev=line_gap)
            curr_line.set_line_distance(to_next=line_gap)


class HOCRObject:

    def __init__(self, hocr_data: dict):
        self.width = hocr_data["width"]
        self.height = hocr_data["height"]
        self.left = hocr_data["left"]
        self.right = hocr_data["right"]
        self.top = hocr_data["top"]
        self.bottom = hocr_data["bottom"]


class HOCRWord(HOCRObject):

    def __init__(self, word: dict):
        HOCRObject.__init__(self, word)
        self.word_text = word["word_text"]
        self.word_conf = word["word_conf"]

    def text(self) -> str:
        return self.word_text

    def word_gap(self, other: Word) -> int:
        if self.left > other.right:
            return self.left - other.right
        elif self.right < other.left:
            return other.left - self.right
        else:
            raise ValueError("word boxes overlap!")


class HOCRLine(HOCRObject):

    def __init__(self, line: dict, config: Union[dict, None]):
        HOCRObject.__init__(self, line)
        self.words = [HOCRWord(word) for word in line["words"]]
        self.num_words = len(self.words)
        self.line_text = " ".join([word.word_text for word in self.words])
        self.distance_to_prev = None
        self.distance_to_next = None
        self.spaced_line_text = None
        if config and "avg_char_width" in config:
            self.set_spaced_line_text(config)

    def set_spaced_line_text(self, config: dict):
        self.spaced_line_text = ""
        for curr_index, curr_word in enumerate(self.words):
            if curr_index > 0:
                word_gap = curr_word.word_gap(self.words[curr_index - 1])
                num_spaces = int(round(word_gap / config["avg_char_width"]))
                self.spaced_line_text += " " * num_spaces
            self.spaced_line_text += curr_word.word_text

    def set_line_distance(self, to_prev: Union[int, None], to_next: Union[int, None]):
        if to_prev:
            self.distance_to_prev = to_prev
        if to_next:
            self.distance_to_next = to_next

    def word_gaps(self, gap_threshold: int = 50) -> List[dict[int, int, int]]:
        gaps = []
        for curr_index, curr_word in enumerate(self.words[1:]):
            prev_word = self.words[curr_index-1]
            if curr_word.word_gap(prev_word) > gap_threshold:
                gaps += [{"gap_size": curr_word.word_gap(prev_word), "from_index": curr_index-1, "to_index": curr_index}]
        return gaps

    def line_gap(self, other: Line) -> int:
        return abs(self.bottom - other.bottom)

    def split_line_on_gaps(self, gaps: List[dict]) -> List[list[Word]]:
        words_from_index = 0
        word_sets = []
        for gap in gaps:
            words_to_index = gap["from_index"]
            words = self.words[words_from_index:words_to_index]
            word_sets += [words]
            words_from_index = gap["to_index"]
        return word_sets


class HOCRColumn(HOCRObject):

    def __init__(self, column: dict, config: Union[dict, None]):
        HOCRObject.__init__(self, column)
        self.lines = [HOCRLine(line, config) for line in column["lines"]]
        self.num_lines = len(self.lines)
        self.num_words = sum([line.num_words for line in self.lines])
        add_line_distances(self.lines)

    def as_text(self) -> str:
        return "\n".join([line.line_text for line in self.lines])


class HOCRParagraph(HOCRObject):

    def __init__(self, lines: List[Line], config: Union[dict, None]):
        box = construct_box_from_items(lines)
        HOCRObject.__init__(self, box)
        self.lines = lines
        self.type = []


class HocrPage(HOCRObject):

    def __init__(self, columns: List[Column] = [], config: Union[dict, None] = None):
        box = construct_box_from_items(columns)
        HOCRObject.__init__(self, box)
        self.columns = columns
        self.num_columns = len(columns)
        self.num_lines = sum([column.num_lines for column in self.columns])
        self.num_words = sum([column.num_words for column in self.columns])
        self.type = "unknown"


class HocrScan(HOCRObject):

    def __init__(self, scan_hocr: dict, scan_id: str, config: Union[dict, None]):
        HOCRObject.__init__(self, scan_hocr)
        self.scan_id = scan_id
        self.lines = []
        self.columns = []
        self.type = ["normal", "double_page"]
        self.filepath = scan_hocr["filepath"]
        if self.width > config["normal_scan_width"] * 1.1:
            self.type = ["special", "extended"]
        elif self.width < config["normal_scan_width"] * 0.9:
            self.type = ["special", "reduced"]
        add_line_distances(self.lines)
        if "lines" in scan_hocr:
            self.lines = [HOCRLine(line, config) for line in scan_hocr["lines"]]
        if "columns" in scan_hocr:
            self.columns = [HOCRColumn(column) for column in scan_hocr["columns"]]
