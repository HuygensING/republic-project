import glob
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

from flair.data import Sentence
from flair.models import SequenceTagger

from republic.extraction.extract_entities import Annotation
from settings import ner_tagger_dir


LAYER_COLOR = {
    'DAT': 'blue',
    'HOE': 'red',
    'LOC': 'green',
    'ORG': 'purple',
    'PER': 'SlateBlue',
    'RES': 'DodgerBlue',
    'COM': 'MediumSeaGreen',
    'NAM': 'Orange'
}


@dataclass
class Token:
    text: str
    tag: str
    char_offset: int
    token_offset: int


@dataclass
class Phrase:
    text: str
    label: str
    token_offset: int
    tokens: List[Token]


@dataclass
class Entity:
    text: str
    tag: str
    char_offset: int
    token_offset: int
    tokens: List[Token]


@dataclass
class Doc:
    id: str
    metadata: Dict[str, any]
    text: str
    tokens: List[Token]
    entities: List[Entity]


def line2token(line: str, char_offset: int, token_offset: int) -> Token:
    word, tag = line.strip('\n').split('\t')
    return Token(word, tag, char_offset, token_offset)


def make_entity(tokens: List[Token]) -> Entity:
    tag_type = tokens[0].tag[2:]
    tagged_text = ' '.join([token.text for token in tokens])
    return Entity(tagged_text, tag_type,
                  tokens[0].char_offset, tokens[0].token_offset,
                  [token for token in tokens])


def extract_tagged_sequences(tokens):
    sequences = []
    sequence = []
    for ti, token in enumerate(tokens):
        if token.tag.startswith('B-'):
            sequence = [token]
        elif token.tag.startswith('I-'):
            sequence.append(token)
        elif token.tag.startswith('O'):
            if len(sequence) > 0:
                sequences.append(sequence)
            sequence = []
        else:
            raise ValueError(f"invalid tag '{token.tag}'.")
    if len(sequence) > 0:
        sequences.append(sequence)
    return sequences


def extract_entities(tokens):
    sequences = extract_tagged_sequences(tokens)
    return [make_entity(sequence) for sequence in sequences]


def read_tagged_file(fname: str) -> Doc:
    with open(fname, 'rt') as fh:
        tokens = []
        char_offset = 0
        for token_offset, line in enumerate(fh):
            token = line2token(line, char_offset, token_offset)
            char_offset = token.char_offset + len(token.text) + 1
            tokens.append(token)
    text = ' '.join([token.text for token in tokens])
    entities = extract_entities(tokens)
    session_id, metadata = parse_filename(fname)
    return Doc(session_id, metadata, text, tokens, entities)


def parse_filename(fname: str) -> Tuple[str, Dict[str, any]]:
    session_id = fname.split('/')[-2][:-4]
    if 'secreet-proef' in fname:
        year, _, _, inv, _, session_num = session_id.split('-')
    else:
        year, _, inv, _, session_num = session_id.split('-')
    metadata = {
        'year': int(year),
        'inventory_num': inv,
        'session_num': int(session_num),
        'source_file': fname
    }
    return session_id, metadata


def make_phrase(tokens: List[Token], label: str):
    phrase_text = ' '.join([token.text for token in tokens])
    return Phrase(phrase_text, label, tokens[0].token_offset, [token for token in tokens])


def get_entity_context(doc: Doc, entity: Entity, context_size: int):
    entity_end = entity.token_offset + len(entity.tokens)
    if entity.token_offset > context_size:
        pre_start = entity.token_offset - context_size
        pre_end = entity.token_offset
        pre_phrase = make_phrase(doc.tokens[pre_start:pre_end], 'prefix')
    else:
        pre_phrase = None
    if entity_end == len(doc.tokens) - 1:
        post_phrase = None
    else:
        post_start = entity_end
        post_end = post_start + context_size
        post_phrase = make_phrase(doc.tokens[post_start:post_end], 'postfix')
    return pre_phrase, post_phrase


def load_tagger(layer_name: str = None, model_dir: str = None) -> SequenceTagger:
    if layer_name is not None:
        tagger_dir = os.path.join(ner_tagger_dir, f'ner_tagger-layer_{layer_name}')
        try:
            return SequenceTagger.load(os.path.join(tagger_dir, 'best-model.pt'))
        except Exception as err:
            print('entities.load_tagger - tagger_dir:', tagger_dir)
            raise
    elif model_dir:
        return SequenceTagger.load(os.path.join(model_dir, 'best-model.pt'))
    else:
        raise ValueError("must pass either 'layer_name' or 'model_name'.")


def get_best_tagger_dirs(project_dir: str):
    flair_dir = os.path.join(project_dir, 'data/embeddings/flair_embeddings')
    taggers_dir = os.path.join(flair_dir, "best_taggers")
    tagger_dirs = glob.glob(os.path.join(taggers_dir, 'tdb_best_ner-layer*'))
    tagger = {}
    for tagger_dir in tagger_dirs:
        tagger_model_name = os.path.split(tagger_dir)[-1]
        if m := re.match(r'tdb_best_ner-layer_({[A-Z_]+})-', tagger_model_name):
            layer = m.group(1)
            tagger[layer] = tagger_dir
    return tagger


def tag_resolution(res_text: str, doc_id: str, model: SequenceTagger, as_annotations: bool = True):
    text = res_text
    sentence = Sentence(res_text)
    model.predict(sentence)
    tagged_positions = get_tagged_positions(sentence)
    annotations = []
    for tagged_position in tagged_positions:
        start, end = tagged_position
        tag_type = tagged_positions[tagged_position]
        anno = Annotation(tag_type, text[start:end], start, doc_id)
        annotations.append(anno)
        if as_annotations is False:
            text = text[:start] + f'<{tag_type}>' + text[start:end] + f'</{tag_type}>' + text[end:]
    if as_annotations:
        return annotations[::-1]
    else:
        return text


def get_layer_test_file(layer_name, ground_truth_dir: str):
    gt_dir = os.path.join(ground_truth_dir, 'flair_training')
    layer_gt_dir = os.path.join(gt_dir, f'flair_training_{layer_name}')
    return os.path.join(layer_gt_dir, 'test.txt')


def get_token_tag(line: str, separator: str, num_splits: int = 1, debug: int = 0):
    if line == '\n':
        space_layers = ['<S>'] * num_splits
        return [''] + space_layers
    token_tags = line.strip().split(separator, num_splits)
    if debug > 2:
        token, tags = token_tags[0], token_tags[1:]
        print(f"entities.get_token_tag - token: {token}\ttag: {tags}")
    return token_tags


def get_test_tokens_tags(test_file: str, separator: str, num_splits: int = 1, debug: int = 0):
    with open(test_file, 'rt') as fh:
        tokens_tags = []
        docs = []
        for line in fh:
            if line == '\n':
                if len(tokens_tags) > 0:
                    docs.append(tokens_tags)
                    # print(tokens_tags)
                    if debug > 0:
                        print(f'entities.get_test_tokens_tags - adding doc with {len(tokens_tags)} tokens and tags')
                tokens_tags = []
            try:
                tokens_tags.append(get_token_tag(line, separator, num_splits=num_splits, debug=debug))
            except Exception:
                print(f'using separator: #{separator}#')
                print('invalid tag line:', line)
                raise
        if len(tokens_tags) > 0:
            docs.append(tokens_tags)
            if debug > 0:
                print(f'entities.get_test_tokens_tags - adding doc with {len(tokens_tags)} tokens and tags')
    return docs


def get_tag_positions(tokens_tags: List[Tuple[str, str]], debug: int = 0):
    text = ''
    tag_position = {}
    in_tag = False
    start_pos, end_pos, tag_type = None, None, None
    prev_tag_type = None
    if debug > 1:
        print('entities.get_tag_positions - len(tokens_tags):', len(tokens_tags))
    for token, tag in tokens_tags:
        tag_type = tag[2:] if len(tag) > 2 and tag != '<S>' else None
        added = False
        if tag_type != prev_tag_type:
            if start_pos is not None and prev_tag_type is not None:
                end_pos = len(text)
                if debug > 1:
                    print('entities.get_tag_positions - curr != prev - adding tag_position:', (start_pos, end_pos), prev_tag_type)
                tag_position[(start_pos, end_pos)] = prev_tag_type
                added = True
            start_pos = len(text) if tag_type is not None else 0
            end_pos = None
        if tag.startswith('B-'):
            tag_type = tag[2:]
            start_pos = len(text)
            end_pos = None
        elif tag == 'O':
            if start_pos is not None and prev_tag_type is not None and added is False:
                end_pos = len(text)
                tag_position[(start_pos, end_pos)] = prev_tag_type
                if debug > 1:
                    print('entities.get_tag_positions - tag == "O" - adding tag_position:', (start_pos, end_pos),
                          prev_tag_type)
            start_pos, end_pos, tag_type = None, None, None
        prev_tag_type = tag_type
        text = f'{text} {token}'
        if debug > 1:
            print('entities.get_tag_positions - start_pos:', start_pos)
            print('entities.get_tag_positions - end_pos:', end_pos)
            print('entities.get_tag_positions - tag:', tag)
            print('entities.get_tag_positions - tag_type:', tag_type)
            print('entities.get_tag_positions - prev_tag_type:', prev_tag_type)
            print('entities.get_tag_positions - tag_position:', tag_position)
            print('entities.get_tag_positions - len(text):', len(text))
            print('entities.get_tag_positions - text:', text)
            print('\n')
            if len(text) > 1000:
                # continue
                break
    return tag_position


def read_test_file(test_file, separator: str = ' ', num_splits: int = 1, debug: int = 0):
    docs = get_test_tokens_tags(test_file, separator, num_splits=num_splits, debug=debug)
    if debug > 0:
        print(f"entities.read_test_file - read {len(docs)}, of which {len([doc for doc in docs if len(doc) > 0])} non-empty.")
    for doc_tokens_tags in docs:
        tokens = [token for token, *tags in doc_tokens_tags]
        text = ' '.join(tokens)
        tag_positions = []
        if debug > 1:
            print('doc_tokens_tags:', doc_tokens_tags[:10])
        for split in range(0, num_splits):
            split_doc_tokens_tags = []
            for token, *tags in doc_tokens_tags:
                split_doc_tokens_tags.append((token, tags[split]))
            if debug > 1:
                print('split_doc_tokens_tags:', split_doc_tokens_tags[:10])
            split_tag_position = get_tag_positions(split_doc_tokens_tags, debug=debug)
            if debug > 1:
                print('split_tag_position:', split_tag_position)
            tag_positions.append(split_tag_position)
        if len(tag_positions) == 1:
            tag_positions = tag_positions[0]
        yield {'text': text, 'tag_position': tag_positions, 'filename': test_file}


def get_tagged_positions(sentence):
    tagged_position = {}
    tagged_ranges = [(label.data_point.start_position, label.data_point.end_position, label.value) for label in
                     sentence.labels]
    for tagged_range in tagged_ranges[::-1]:
        start, end, tag_type = tagged_range
        tagged_position[(start, end)] = tag_type
    return tagged_position


def highlight_tagged_text_positions(text, tag_position, layer_color: Dict[str, str] = None,
                                    debug: int = 0):
    if layer_color is None:
        layer_color = LAYER_COLOR
    for start, end in sorted(tag_position.keys(), key=lambda x: x[1], reverse=True):
        tag_type = tag_position[(start, end)]
        if debug > 1:
            print('entities.highlight_tagged_text_positions - (start, end):', (start, end))
        color = layer_color[tag_type]
        before, tag, after = text[:start], text[start:end], text[end:]
        text = f"{before}<font color='{color}'>{tag}</font>{after}"
    return f"<p>{text}</p>"


def tag_text(text, model):
    tagged_text = Sentence(text)
    model.predict(tagged_text)
    return tagged_text


def highlight_tagged_text(tagged_text):
    tagged_position = get_tagged_positions(tagged_text)
    return highlight_tagged_text_positions(tagged_text.text, tagged_position)
