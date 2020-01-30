# Created by: Marijn Koolen
# Created on: 2018-08-13
# Context: parsing digitized charter books to extract geographic attestations and dates
from bs4 import BeautifulSoup as bsoup
from typing import Union


def set_carea(hocr_doc_soup):
    try:
        hocr_carea_soup = get_hocr_carea_soup(hocr_doc_soup)
        return get_hocr_box(hocr_carea_soup)
    except TypeError:
        return None


class HOCRDoc(object):

    def __init__(self, hocr_doc_soup, doc_id=None, config={}):
        """
        Action: parses a hOCR document based on HTML parser Beautiful Soup
        Input: a Beautiful Soup object of the hOCR document
        Output: a HOCRDoc object with paragraphs, lines and words and their document positions
                as well as a representation of the lines with whitespace restored based on
                word positioning.

        Three optional input arguments:

        1. doc_id: set a document id for this doc

        2. minimum_paragraph_gap: is used to estimate line skips between paragraphs
        as boundaries. Default value is based on OHZ charter books, for others
        it's possibly higher or lower.

        3. avg_char_width: is used to estimate width of whitespaces between words
        default value is based on averaging over pixel width and character
        length of recognised words in OHZ charter books.

        """
        self.tag = hocr_doc_soup.name
        self.doc_id = doc_id
        self.class_ = hocr_doc_soup['class']
        self.attributes = get_hocr_title_attributes(hocr_doc_soup)
        self.box = get_hocr_box(hocr_doc_soup)
        self.carea = set_carea(hocr_doc_soup)
        self.lines = []
        self.paragraphs = []
        self.minimum_paragraph_gap = 10
        if "minimum_paragraph_gap" in config:
            self.minimum_paragraph_gap = config["minimum_paragraph_gap"]
        self.avg_char_width = 20
        if "avg_char_width" in config:
            self.avg_char_width = config["avg_char_width"]
        self.remove_tiny_words = False
        if "remove_tiny_words" in config:
            self.remove_tiny_words = config["remove_tiny_words"]
        self.tiny_word_width = 10
        if "tiny_word_width" in config:
            self.tiny_word_width = config["tiny_word_width"]

    def set_paragraphs(self, hocr_soup):
        line_count = 0
        for hocr_paragraph_soup in get_hocr_pars(hocr_soup):
            paragraph = make_empty_paragraph(hocr_paragraph_soup)
            for hocr_line_soup in get_hocr_lines(hocr_paragraph_soup):
                line_count += 1
                paragraph["line_numbers"] += [line_count]
            self.paragraphs.append(paragraph)

    def merge_paragraph_lines(self):
        for paragraph in self.paragraphs:
            text = ""
            for line in paragraph["line_texts"]:
                if len(line) == 0:
                    continue
                if line[-1] == "-":
                    # Crude but quick. TODO more proper line break hyphenation analysis
                    text += line[:-1].strip()
                else:
                    text += line.strip() + " "
            paragraph["merged_text"] = text

    def is_even_side(self):
        if self.doc_id % 2 == 0:
            return True
        else:
            return False

    def set_lines(self, hocr_doc_soup):
        # store all lines separately as:
        # line_text:        simple text representation
        # spaced_line_text: whitespace maintained representation (for indentation, column spacing, margins, ...)
        # words:            keep individual words and their coordinates
        for hocr_line_soup in get_hocr_lines(hocr_doc_soup):
            line = get_hocr_box(hocr_line_soup)
            line["words"] = get_words(hocr_line_soup)
            line["line_text"] = " ".join([word["word_text"] for word in line["words"]])
            # line["line_text"] = hocr_line_soup.get_text().replace("\n", " ")
            line["spaced_line_text"] = self.get_spaced_line_text(line["words"])
            # occasionally, lines only contain a pipe char based on edge shading in scan
            # skip those lines.
            if line["line_text"].strip() == "|" or line["line_text"].strip() == "|" or len(line["line_text"]) == 1:
                continue
            self.lines.append(line)

    def get_spaced_line_text(self, words):
        # use word coordinates to reconstruct spacing between words
        spaced_line_text = ""
        if len(words) == 0:
            return spaced_line_text
        offset = words[0]["bbox"][0] - self.carea["left"]
        spaced_line_text = " " * int(round(offset / self.avg_char_width))
        for index, word in enumerate(words[:-1]):
            spaced_line_text += word["word_text"]
            spaced_line_text += self.get_spaces(word, words[index + 1])
        spaced_line_text += words[-1]["word_text"]
        return spaced_line_text

    def get_spaces(self, word1, word2):
        # Simple computation based on word coordinates to determine
        # white spacing between them.
        space_to_next = word2["left"] - word1["right"]
        spaces = int(round(space_to_next / self.avg_char_width))
        if spaces == 0:
            spaces = 1
        return " " * spaces


def filter_tiny_words_from_lines(hocr_doc, config):
    return [filter_tiny_words_from_line(hocr_doc, line, config) for line in hocr_doc.lines]


def set_lines(hocr_doc, hocr_doc_soup):
    # store all lines separately as:
    # line_text:        simple text representation
    # spaced_line_text: whitespace maintained representation (for indentation, column spacing, margins, ...)
    # words:            keep individual words and their coordinates
    for hocr_line_soup in get_hocr_lines(hocr_doc_soup):
        line = get_hocr_box(hocr_line_soup)
        line["words"] = get_words(hocr_line_soup)
        line["line_text"] = " ".join([word["word_text"] for word in line["words"]])
        # line["line_text"] = hocr_line_soup.get_text().replace("\n", " ")
        line["spaced_line_text"] = get_spaced_line_text(hocr_doc, line["words"])


def get_spaced_line_text(hocr_doc, words, config):
    # use word coordinates to reconstruct spacing between words
    spaced_line_text = ""
    if len(words) == 0:
        return spaced_line_text
    offset = words[0]["bbox"][0] - hocr_doc.carea["left"]
    spaced_line_text = " " * int(round(offset / config["avg_char_width"]))
    for index, word in enumerate(words[:-1]):
        spaced_line_text += word["word_text"]
        spaced_line_text += get_spaces(word, words[index + 1], config["avg_char_width"])
    spaced_line_text += words[-1]["word_text"]
    return spaced_line_text


def get_spaces(word1, word2, avg_char_width):
    # Simple computation based on word coordinates to determine
    # white spacing between them.
    space_to_next = word2["left"] - word1["right"]
    spaces = int(round(space_to_next / avg_char_width))
    if spaces == 0:
        spaces = 1
    return " " * spaces


def make_empty_paragraph(hocr_soup):
    paragraph = get_hocr_box(hocr_soup)
    paragraph["type"] = None
    paragraph["line_numbers"] = []
    paragraph["line_texts"] = []
    if "lang" in hocr_soup.attrs:
        paragraph["lang"] = hocr_soup["lang"]
    return paragraph
    # return {
    #    "type": None,
    #    "line_texts": [],
    #    "line_numbers": [],
    # }


def get_hocr_box(hocr_soup):
    # extract hocr bounding box, compute size and explicate offsets
    element_bbox = get_hocr_bbox(hocr_soup)
    box_size = get_bbox_size(element_bbox)
    return {
        "bbox": element_bbox,
        "width": box_size[0],
        "height": box_size[1],
        "left": element_bbox[0],
        "right": element_bbox[2],
        "top": element_bbox[1],
        "bottom": element_bbox[3]
    }


def get_hocr_content(hocr_file):
    with open(hocr_file, 'rt') as fh:
        return bsoup(fh, 'lxml')


def get_hocr_doc_soup(hocr_soup):
    return hocr_soup.find("div", class_="ocr_page")


def get_hocr_carea_soup(hocr_soup):
    return hocr_soup.find("div", class_="ocr_carea")


def get_hocr_pars(hocr_soup):
    return hocr_soup.find_all("p", class_="ocr_par")


def get_hocr_lines(hocr_soup):
    return hocr_soup.find_all("span", class_="ocr_line")


def get_hocr_words(hocr_soup):
    return hocr_soup.find_all("span", class_="ocrx_word")


def get_hocr_bbox(hocr_element):
    attributes = get_hocr_title_attributes(hocr_element)
    return [int(coord) for coord in attributes["bbox"].split(" ")]


def get_hocr_title_attributes(hocr_element):
    return {part.split(" ", 1)[0]: part.split(" ", 1)[1] for part in hocr_element['title'].split("; ")}


def get_bbox_size(hocr_bbox):
    return hocr_bbox[2] - hocr_bbox[0], hocr_bbox[3] - hocr_bbox[1]


def get_word_conf(hocr_word):
    if "ocrx_word" in hocr_word['class']:
        attributes = get_hocr_title_attributes(hocr_word)
        if attributes and "x_wconf" in attributes:
            return int(attributes["x_wconf"])
    return None


def is_tiny_word(word, tiny_word_width, tiny_word_height):
    return word["width"] <= tiny_word_width and word["height"] <= tiny_word_height


def filter_words(words, tiny_word_width=10):
    words = [word for word in words if not is_tiny_word(word, tiny_word_width, tiny_word_width)]
    return words


def get_words(hocr_line):
    return [get_word(hocr_word) for hocr_word in get_hocr_words(hocr_line)]


def get_word(hocr_word_soup):
    # Extract all word information, including bounding box and confidence
    #word_bbox = get_hocr_bbox(hocr_word_soup)
    word = get_hocr_box(hocr_word_soup)
    word["word_text"] = hocr_word_soup.get_text()
    word["word_conf"] = get_word_conf(hocr_word_soup)
    #bbox_size = get_bbox_size(word_bbox)
    return word


def filter_tiny_words_from_line(hocr_doc, line, config):
    filtered_words = filter_words(line["words"], tiny_word_width=config["tiny_word_width"])
    filtered_line = {
        "words": filtered_words,
        "line_text": " ".join([word["word_text"] for word in filtered_words]),
        "spaced_line_text": get_spaced_line_text(hocr_doc, filtered_words, config)
    }
    span_filtered_line(line, filtered_line)
    return filtered_line


def span_filtered_line(line, filtered_line):
    if len(filtered_line["words"]) == 0:
        filtered_line["top"] = line["top"]
        filtered_line["bottom"] = line["top"]
        filtered_line["left"] = line["left"]
        filtered_line["right"] = line["left"]
    else:
        filtered_line["top"] = min([word["top"] for word in filtered_line["words"]])
        filtered_line["bottom"] = max([word["bottom"] for word in filtered_line["words"]])
        filtered_line["left"] = filtered_line["words"][0]["left"]
        filtered_line["right"] = filtered_line["words"][-1]["right"]
    filtered_line["height"] = filtered_line["bottom"] - filtered_line["top"]
    filtered_line["width"] = filtered_line["right"] - filtered_line["left"]


def make_hocr_doc(filepath: str, hocr_data: Union[str, None] = None,
                  doc_id: Union[str, None] = None, config: dict = {}):
    """
    make_hocr_doc takes as input a filepath to a hOCR file and generates various textual representations of
    the hOCR data. For explanation of the optional arguments, see the HOCRPAGE class above.
    """
    if hocr_data:
        hocr_soup = bsoup(hocr_data, "lxml")
    else:
        hocr_soup = get_hocr_content(filepath)
    hocr_doc_soup = get_hocr_doc_soup(hocr_soup)
    try:
        hocr_doc = HOCRDoc(hocr_doc_soup, doc_id=doc_id, config=config)
    except TypeError:
        return None
    carea = set_carea(hocr_doc_soup)
    if not carea:
        return None
    hocr_doc.set_lines(hocr_doc_soup)
    hocr_doc.set_paragraphs(hocr_doc_soup)
    hocr_doc.merge_paragraph_lines()
    return hocr_doc
