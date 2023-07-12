import json
import os
import re
from typing import Callable, Dict, List, Tuple, Union

from fuzzy_search.tokenization.token import Doc
from fuzzy_search.tokenization.token import Token

from republic.helper.utils import get_project_dir


REWRITE_FILES = {
    'spelling_variants': 'data/phrase_lists/spelling_variants.json',
    'ngram_replace': 'data/phrase_lists/ngram_replacement_words.json',
    'abbreviations': 'data/phrase_lists/abbreviations.json',
    'pre_tokenise_abbreviations': 'data/phrase_lists/pre_tokenise_abbreviations.json',
    'merge': 'data/phrase_lists/merge_words.json',
    'split': 'data/phrase_lists/split_words.json'
}


def check_dict_name_exists(dict_name: str) -> bool:
    if dict_name not in REWRITE_FILES:
        print(f"unknown dictionary {dict_name}, choose on from")
        for dict_name in REWRITE_FILES:
            print(f"\t'{dict_name}'")
        return False
    else:
        return True


def write_rewrite_dict(rewrite_dict: Dict[str, str], dict_name: str = None, dict_file: str = None):
    project_dir = get_project_dir()
    if dict_name:
        if not check_dict_name_exists(dict_name):
            raise KeyError(f'unknown dictionary name {dict_name}')
        dict_file = os.path.join(project_dir, REWRITE_FILES[dict_name])
    with open(dict_file, 'wt') as fh:
        json.dump(rewrite_dict, fh, indent=4)
    return None


def read_rewrite_dict(dict_name: str = None, dict_file: str = None) -> Dict[str, str]:
    project_dir = get_project_dir()
    if dict_name:
        if not check_dict_name_exists(dict_name):
            raise KeyError(f'unknown dictionary name {dict_name}')
        dict_file = os.path.join(project_dir, REWRITE_FILES[dict_name])
    with open(dict_file, 'rt') as fh:
        rewrite_dict = json.load(fh)
    return rewrite_dict


def make_pre_tokeniser_rewrite_func(rewrite_dict: Dict[str, str]) -> Callable:
    def rewrite_func(text: str):
        new_text = text
        for abbrev in rewrite_dict:
            new_text = new_text.replace(abbrev, rewrite_dict[abbrev])
        return new_text
    return rewrite_func


def rewrite_abbrevs_pre_tokenisation(text: str, abbrev_dict: Dict[str, str]) -> str:
    new_text = text
    for abbrev in abbrev_dict:
        new_text = new_text.replace(abbrev, abbrev_dict[abbrev])
    return new_text


def split_token(token: Union[Token, str], split_dict: Dict[str, str]) -> List[str]:
    # print(token.n)
    # split_tokens = split_dict[token.n.lower()].split(' ')
    token_string = token.n if isinstance(token, Token) else token
    split_tokens = re.split(r"( )", split_dict[token_string.lower()])
    # split_tokens = [first, ' ', second]
    if token_string[0].isupper():
        split_tokens[0] = split_tokens[0].title()
    # print(split_tokens)
    return split_tokens


def make_bigram(curr_token: Token, next_token: Token) -> Union[str, None]:
    if next_token is None:
        return None
    if curr_token and curr_token.char_index + len(curr_token.t) < next_token.char_index:
        if next_token.n[0].isupper():
            return f"{curr_token.n} {next_token.n}"
        else:
            return f"{curr_token.n} {next_token.n}".lower()
    else:
        return f"{curr_token.n}{next_token.n}"


def merge_tokens(curr_token: Token, bi_gram: str, merge_dict: Dict[str, str]) -> str:
    merged_token = merge_dict[bi_gram]
    if curr_token.n[0].isupper():
        merged_token = merged_token.title()
    return merged_token


def apply_split_merge(doc: Doc, merge_dict: Dict[str, str], split_dict: Dict[str, str]):
    merge_count, split_count = 0, 0
    new_tokens = []
    token_merged = set()
    prev_token = None
    for curr_token in doc:
        if curr_token in token_merged:
            prev_token = curr_token
            continue
        if prev_token and prev_token.char_index + len(prev_token.t) < curr_token.char_index:
            # add whitespace
            new_tokens.append(' ')
            pass
        next_token = doc.tokens[curr_token.i + 1] if len(doc) > curr_token.i + 1 else None
        bi_gram = make_bigram(curr_token, next_token)
        if curr_token.n.lower() in split_dict:
            tokens = split_token(curr_token, split_dict)
            new_tokens.extend(tokens)
            split_count += 1
        elif bi_gram in merge_dict:
            # print(f"\n\nTO MERGE: {bi_gram}")
            merge_count += 1
            merged_token = merge_tokens(curr_token, bi_gram, merge_dict)
            new_tokens.append(merged_token)
            token_merged.add(next_token)
        else:
            new_tokens.append(curr_token.n)
        prev_token = curr_token
    return new_tokens, merge_count, split_count


def apply_rewrite_dict(doc: Doc, rewrite_dict: Dict[str, str]) -> Tuple[List[str], int]:
    change_count = 0
    new_tokens = []
    token_merged = set()
    prev_token = None
    for curr_token in doc:
        if curr_token in token_merged:
            prev_token = curr_token
            continue
        if prev_token and prev_token.char_index + len(prev_token.t) < curr_token.char_index:
            # add whitespace
            new_tokens.append(' ')
            pass
        if curr_token.n in rewrite_dict:
            new_token = rewrite_dict[curr_token.n]
            new_tokens.extend(new_token)
            change_count += 1
        else:
            new_tokens.append(curr_token.n)
        prev_token = curr_token
    return new_tokens, change_count
