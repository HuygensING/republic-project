from collections import Counter
import republic.parser.republic_base_page_parser as base_parser


def is_respect_page(page_hocr: dict, config: dict) -> bool:
    if page_hocr["num_words"] > 350:
        return False
    if page_hocr["num_columns"] < config["respect_page"]["column_min_threshold"]:
        return False
    if page_hocr["num_columns"] > config["respect_page"]["column_max_threshold"]:
        return False
    if page_hocr["num_words"] < 50:
        # if there is little text, it should be concentrated in the top of the page
        num_top_words = len(base_parser.get_words_above(page_hocr, threshold=800))
        if num_top_words / page_hocr["num_words"] < 0.8:
            return False
    capitals = get_capital_word_initials(page_hocr)
    count = len(capitals)
    cap_freq = Counter(capitals)
    #print("count:", count, "capitals:", capitals)
    top_three_capitals_freq = sum([freq for _, freq in cap_freq.most_common(3)])
    if count > page_hocr["num_words"] * 0.3 and top_three_capitals_freq > count * 0.5:
        return True
    else:
        return False


def get_one_capitalized_word_line_words(page_hocr: dict) -> iter:
    stops = ["de", "den", "der", "van", "vanden", "tot", "in", "le", "la", "op"]
    for column in page_hocr["columns"]:
        for line in column["lines"]:
            if len(line["words"]) == 1:
                word = line["words"][0]
                if word["word_text"][0].isupper():
                    yield word
            if len(line["words"]) <= 3:
                filtered_words = [word for word in line["words"] if word["word_text"] not in stops]
                if len(filtered_words) == 1 and filtered_words[0]["word_text"][0].isupper():
                    yield filtered_words[0]


def get_capital_word_initials(page_hocr: dict) -> list:
    capitals = []
    for word in get_one_capitalized_word_line_words(page_hocr):
        capitals += [word["word_text"][0]]
    return capitals


