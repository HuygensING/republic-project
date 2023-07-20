import os

from flair.data import Sentence
from flair.models import SequenceTagger

from republic.extraction.extract_entities import Annotation


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


def load_tagger(model_dir: str) -> SequenceTagger:
    return SequenceTagger.load(os.path.join(model_dir, 'final-model.pt'))


def tag_resolution(res_text: str, res_id: str, model: SequenceTagger, as_annotations: bool = True):
    text = res_text
    sentence = Sentence(res_text)
    model.predict(sentence)
    tagged_positions = get_tagged_positions(sentence)
    annotations = []
    for tagged_position in tagged_positions:
        start, end = tagged_position
        tag_type = tagged_positions[tagged_position]
        anno = Annotation(tag_type, text[start:end], start, res_id)
        annotations.append(anno)
        if as_annotations is False:
            text = text[:start] + f'<{tag_type}>' + text[start:end] + f'</{tag_type}>' + text[end:]
    if as_annotations:
        return annotations[::-1]
    else:
        return text


def get_layer_test_file(layer_name, repo_dir: str):
    gt_dir = os.path.join(repo_dir, 'ground_truth/entities/tag_de_besluiten')
    layer_gt_dir = os.path.join(gt_dir, f'flair_training_{layer_name}')
    return os.path.join(layer_gt_dir, 'test.txt')


def get_token_tag(line):
    if line == '\n':
        return '', '<S>'
    token, tag = line.strip().split(' ')
    return token, tag


def get_tokens_tags(test_file):
    with open(test_file, 'rt') as fh:
        tokens_tags = []
        docs = []
        for line in fh:
            if line == '\n':
                if len(tokens_tags) > 0:
                    docs.append(tokens_tags)
                tokens_tags = []
            tokens_tags.append(get_token_tag(line))
    return docs


def get_tag_positions(tokens_tags):
    text = ''
    tag_position = {}
    in_tag = False
    start_pos, end_pos, tag_type = None, None, None
    prev_tag_type = None
    for token, tag in tokens_tags:
        tag_type = tag[2:] if len(tag) > 2 else None
        if tag_type != prev_tag_type:
            if start_pos and prev_tag_type is not None:
                end_pos = len(text)
                tag_position[(start_pos, end_pos)] = prev_tag_type
            start_pos = len(text) if tag_type is not None else 0
            end_pos = None
        if tag.startswith('B-'):
            tag_type = tag[2:]
            start_pos = len(text)
            end_pos = None
        elif tag == 'O':
            if start_pos and prev_tag_type is not None:
                end_pos = len(text)
                tag_position[(start_pos, end_pos)] = prev_tag_type
            start_pos, end_pos, tag_type = None, None, None
        prev_tag_type = tag_type
        text = f'{text} {token}'
    return tag_position


def read_test_file(test_file):
    docs = get_tokens_tags(test_file)
    for doc_tokens_tags in docs:
        tokens = [token for token, tag in doc_tokens_tags]
        text = ' '.join(tokens)
        tag_position = get_tag_positions(doc_tokens_tags)
        yield {'text': text, 'tag_position': tag_position, 'filename': test_file}


def get_tagged_positions(sentence):
    tagged_position = {}
    tagged_ranges = [(label.data_point.start_position, label.data_point.end_position, label.value) for label in
                     sentence.labels]
    for tagged_range in tagged_ranges[::-1]:
        start, end, tag_type = tagged_range
        tagged_position[(start, end)] = tag_type
    return tagged_position


def highlight_tagged_text_positions(text, tag_position):
    for start, end in sorted(tag_position.keys(), key=lambda x: x[1], reverse=True):
        tag_type = tag_position[(start, end)]
        color = LAYER_COLOR[tag_type]
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
