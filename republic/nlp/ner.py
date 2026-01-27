import os.path
import re
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Union

import numpy as np
from flair.data import Corpus
from flair.training_utils import Result
from flair.datasets import ColumnCorpus
from flair.embeddings import WordEmbeddings, StackedEmbeddings, CharLMEmbeddings, FlairEmbeddings
from flair.embeddings import FastTextEmbeddings
from flair.embeddings import TransformerWordEmbeddings
from flair.models import SequenceTagger
from flair.trainers import ModelTrainer
from transformers import RobertaForMaskedLM

from republic.helper.utils import get_project_dir
from settings import ner_base_dir


COLUMNS = {0: 'text', 1: 'ner'}


def make_paragraph(tokens: List[str], as_running_text: bool = False):
    if as_running_text:
        return ' '.join([token.split('\t')[0] for token in tokens])
    else:
        return '\n'.join(tokens) + '\n'


def read_gt_file(gt_file: str, as_running_text: bool = False):
    """Read the labelled tokens of a ground truth file per document and return
    them as a list of texts."""
    tokens = []
    paras = []
    with open(gt_file, 'rt') as fh:
        for line in fh:
            token = line.strip('\n').replace(' ', '\t')
            if token == '':
                para = make_paragraph(tokens, as_running_text=as_running_text)
                paras.append(para)
                tokens = []
                continue
            tokens.append(token)
        if len(tokens) > 0:
            para = make_paragraph(tokens, as_running_text=as_running_text)
            paras.append(para)
    return paras


def make_corpus(data_dir: str, columns: dict = None, test_file='test.txt',
                train_file='train_1.0.txt', dev_file='validate.txt'):
    if columns is None:
        columns = COLUMNS
    return ColumnCorpus(data_dir, columns, train_file=train_file,
                        test_file=test_file, dev_file=dev_file)


def prep_corpus(data_dir: str, layer_name: str, train_size: float):
    train_file = os.path.join(data_dir, f'train_{train_size}.txt')
    test_file = os.path.join(data_dir, 'test.txt')
    validate_file = os.path.join(data_dir, 'validate.txt')
    assert os.path.exists(train_file), f"the train file {train_file} doesn't exist"
    assert os.path.exists(test_file), f"the test file {test_file} doesn't exist"
    assert os.path.exists(validate_file), f"the validate file {validate_file} doesn't exist"

    columns = {0: 'text', 1: 'ner'}

    return ColumnCorpus(data_dir, columns,
                        train_file=f'train_{train_size}.txt',
                        test_file='test.txt',
                        dev_file='validate.txt')


def prep_embeddings(flair_dir: str,
                    use_context: bool = False,
                    use_finetuning: bool = False,
                    use_resolution: bool = False,
                    use_char: bool = False,
                    use_gysbert: bool = False,
                    use_gysbert2: bool = False,
                    use_fasttext: bool = False,
                    model_max_length: int = 512):
    # resolution_bert = RobertaForMaskedLM.from_pretrained('data/models/resolution_bert')
    embedding_types = []
    if use_char:
        char_bw = FlairEmbeddings(f'{flair_dir}/resources/taggers/language_model_bw_char/best-lm.pt')
        char_fw = FlairEmbeddings(f'{flair_dir}/resources/taggers/language_model_fw_char/best-lm.pt')
        embedding_types.extend([char_bw, char_fw])

    if use_fasttext:
        embedding_dir = f'{ner_base_dir}/embeddings/fasttext'
        embedding_binary = 'fasttext-dim_384-window_10-min_count_100-case_lower.bin'
        fasttext_embeddings = FastTextEmbeddings(f'{embedding_dir}/{embedding_binary}')
        embedding_types.append(fasttext_embeddings)

    if use_resolution:
        resolution_embeddings = TransformerWordEmbeddings('data/models/resolution_bert',
                                                          layers='-1',
                                                          subtoken_pooling="first",
                                                          fine_tune=use_finetuning,
                                                          use_context=use_context,
                                                          allow_long_sentences=False,
                                                          model_max_length=model_max_length)
        embedding_types.append(resolution_embeddings)

    if use_gysbert:
        gysbert_embeddings = TransformerWordEmbeddings('emanjavacas/GysBERT',
                                                       layers="-1",
                                                       subtoken_pooling="first",
                                                       fine_tune=use_finetuning,
                                                       use_context=use_context,
                                                       allow_long_sentences=False,
                                                       model_max_length=model_max_length)
        embedding_types.append(gysbert_embeddings)

    if use_gysbert2:
        gysbert2_embeddings = TransformerWordEmbeddings('emanjavacas/GysBERT-v2-2m',
                                                        layers="-1",
                                                        subtoken_pooling="first",
                                                        fine_tune=use_finetuning,
                                                        use_context=use_context,
                                                        allow_long_sentences=False,
                                                        model_max_length=model_max_length)
        embedding_types.append(gysbert2_embeddings)

    if len(embedding_types) == 0:
        return None
    return StackedEmbeddings(embeddings=embedding_types)


def prep_trainer(corpus: Corpus, hidden_size, embeddings: StackedEmbeddings,
                 use_crf: bool = False,
                 use_rnn: bool = False,
                 reproject_embeddings: bool = False):
    label_type = 'ner'

    label_dict = corpus.make_label_dictionary(label_type=label_type)
    tagger = SequenceTagger(hidden_size=hidden_size,
                            embeddings=embeddings,
                            tag_dictionary=label_dict,
                            tag_type=label_type,
                            use_crf=use_crf,
                            use_rnn=use_rnn,
                            reproject_embeddings=reproject_embeddings)

    return ModelTrainer(tagger, corpus)


def get_flair_dir():
    project_dir = get_project_dir()
    return f'{project_dir}/data/embeddings/flair_embeddings/'


def prep_training(layer_name: str,
                  data_dir: str,
                  train_size: float = 1.0,
                  use_crf: bool = False,
                  use_rnn: bool = False,
                  reproject_embeddings: bool = False,
                  use_context: bool = False,
                  use_finetuning: bool = False,
                  use_resolution: bool = False,
                  use_char: bool = False,
                  use_gysbert: bool = False,
                  use_gysbert2: bool = False,
                  use_fasttext: bool = False,
                  hidden_size=256, model_max_length=512):
    flair_dir = get_flair_dir()
    assert os.path.exists(flair_dir), f"the flair directory {flair_dir} doesn't exist"

    corpus: Corpus = prep_corpus(data_dir, layer_name, train_size)

    embeddings = prep_embeddings(flair_dir,
                                 use_finetuning=use_finetuning,
                                 use_context=use_context,
                                 use_resolution=use_resolution,
                                 use_char=use_char,
                                 use_gysbert=use_gysbert,
                                 use_gysbert2=use_gysbert2,
                                 use_fasttext=use_fasttext,
                                 model_max_length=model_max_length)

    if embeddings is None:
        return None
    return prep_trainer(corpus, hidden_size, embeddings,
                        use_crf=use_crf,
                        use_rnn=use_rnn,
                        reproject_embeddings=reproject_embeddings)


def train(trainer, layer_name: str, train_size: float = 1.0, learning_rate: float = 0.05,
          mini_batch_size: int = 32, max_epochs: int = 10, model_name = None):
    flair_dir = get_flair_dir()
    model_dir = f'{ner_base_dir}/taggers/{model_name}-train_{train_size}-epochs_{max_epochs}'
    results = trainer.train(model_dir,
                            learning_rate=learning_rate,
                            mini_batch_size=mini_batch_size,
                            max_epochs=max_epochs)
    # TODO: finish


###################
# Evaluation code #
###################

def read_pred_tag_file(test_tagged_file: str):
    """Read the tag prediction file for a model, which has two columns:

    1. token
    2. predicted label
    """
    with open(test_tagged_file, 'rt') as fh:
        sent_idx = 0
        token_idx = 0
        for li, line in enumerate(fh):
            parts = line.strip().split(' ')
            if len(parts) == 2:
                token_idx += 1
                yield [sent_idx, token_idx] + parts
            else:
                yield None, None, parts[0], None
                sent_idx += 1
                token_idx = 0
    return None


def read_test_tag_file(test_tagged_file: str):
    """Read the tagged test file for a model, which has three columns:

    1. token
    2. true label
    3. predicted label
    """
    with open(test_tagged_file, 'rt') as fh:
        sent_idx = 0
        token_idx = 0
        for li, line in enumerate(fh):
            parts = line.strip().split(' ')
            if len(parts) == 3:
                token_idx += 1
                yield [sent_idx, token_idx] + parts
            else:
                yield None, None, parts[0], None, None
                sent_idx += 1
                token_idx = 0
    return None


class Token:

    def __init__(self, sent_idx: int, token_idx: int, text: str, label: str):
        self.sent_idx = sent_idx
        self.token_idx = token_idx
        self.text = text
        self.label = label


class Span:

    def __init__(self, sent_idx: int, start, end: int, text, label: Union[str, List[str]]):
        self.sent_idx = sent_idx
        self.start = start
        self.end = end
        self.text = text
        self.label = label

    def __repr__(self):
        return (f"{self.__class__.__name__}(sent_idx={self.sent_idx}, start={self.start}, "
                f"end={self.end}, text={self.text}, label={self.label}")

    def has_label(self, label: str):
        return self.label == label if isinstance(self.label, str) else label in self.label

    def get_labels(self):
        if isinstance(self.label, str):
            return [self.label]
        else:
            return list(self.label)

    @property
    def string(self):
        return f'{self.sent_idx}: Span[{self.start}:{self.end}]: "{self.text}"'


def parse_span(span: str, label: str):
    m = re.match(r"(\d+): Span\[(\d+):(\d+)]: \"(.*?)\"", span)
    if m is None:
        raise ValueError(f"invalid span format: {span}")
    sent_idx, start, end, text = m.groups()
    return Span(int(sent_idx), int(start), int(end), text, label)


def make_span(sent_idx, start, end, text):
    return f'{sent_idx}: Span[{start}:{end}]: "{text}"'


def merge_spans(spans: List[Span], label: str = None):
    """Merge a list of Span instances into a single Span. If a label is passed, that is used
    for the merged span, otherwise, the label of the first span is used."""
    merge_texts = []
    merge_start = None
    merge_end = None
    merge_sent = None
    if label is None:
        label = list(set([label for span in spans for label in span.get_labels()]))
    if len(set([span.sent_idx for span in spans])) != 1:
        raise ValueError(f"Not all spans have the same sent_idx: {spans}")
    for span in spans:
        merge_sent = span.sent_idx
        if merge_start is None:
            merge_start = span.start
        merge_end = span.end
        merge_texts.append(span.text)
    # '57: Span[114:121]: "haer Hoogh Mog . Resolutie en bygevoeghde"'
    return Span(merge_sent, merge_start, merge_end, ' '.join(merge_texts), label)


def get_extended_res_spans(pred_spans: List[Span]) -> List[Span]:
    extended_res_spans = []
    for si, curr_span in enumerate(pred_spans):
        if 'RES' not in curr_span.label:
            continue
        res_spans = [curr_span]
        curr_end = curr_span.end
        next_idx = si + 1
        while curr_end is not None:
            if next_idx >= len(pred_spans):
                break
            next_span = pred_spans[next_idx]
            if next_span.sent_idx != curr_span.sent_idx:
                curr_end = None
            elif next_span.label == 'RES':
                curr_end = None
            elif next_span.start != curr_end:
                curr_end = None
            else:
                res_spans.append(next_span)
                curr_end = next_span.end
            next_idx += 1
        merged_span = merge_spans(res_spans)
        extended_res_spans.append(merged_span)
    return extended_res_spans


def have_same_sent(span1: Span, span2: Span) -> bool:
    return span1.sent_idx == span2.sent_idx


def filter_partial_matches(pred_only_spans: Union[Set[Span], List[Span]],
                           true_only_spans: Union[Set[Span], List[Span]]):
    matched = defaultdict(list)
    for pred_only_span in sorted(pred_only_spans, key=lambda s: (s.sent_idx, s.start)):
        if pred_only_span in matched:
            print('pred_only_span already in matched:', pred_only_span)
            pass
        for true_only_span in true_only_spans:
            if have_same_sent(pred_only_span, true_only_span) is False:
                continue
            if pred_only_span.end < true_only_span.start or true_only_span.end < pred_only_span.start:
                continue
            if pred_only_span in matched:
                pass
            matched[pred_only_span].append(true_only_span)
    return matched


def get_true_pred_spans_from_results(results: Result, target_label: str) -> Tuple[List[Span], List[Span]]:
    # extract and parse tagged spans
    true_spans = [parse_span(span, label) for span, label in results.all_true_values.items()]
    pred_spans = [parse_span(span, label) for span, label in results.all_predicted_values.items()]
    # filter by label
    true_spans = [span for span in true_spans if span.has_label(target_label)]
    if target_label == 'RES':
        pred_spans = get_extended_res_spans(pred_spans)
    else:
        pred_spans = [span for span in pred_spans if span.has_label(target_label)]
    return true_spans, pred_spans


def get_matching_spans(true_spans: List[Span], pred_spans: List[Span]) -> Tuple[List[Span], List[Span], List[Span]]:
    true_string_span = {span.string: span for span in true_spans}
    pred_string_spans = {span.string: span for span in pred_spans}
    pred_true_spans = []
    pred_only_spans = []
    true_only_spans = []
    for span in pred_spans:
        if span.string in true_string_span:
            pred_true_spans.append(span)
        else:
            pred_only_spans.append(span)
    for span in true_spans:
        if span.string not in pred_string_spans:
            true_only_spans.append(span)
    return pred_true_spans, true_only_spans, pred_only_spans


def spans_match(span1: Span, span2: Span) -> bool:
    if span1.string != span2.string:
        return False
    labels1 = set(span1.label)
    labels2 = set(span2.label)
    return labels1 == labels2


def score_strict_lenient(true_spans: List[Span] = None, pred_spans: List[Span] = None,
                         result: Result = None, label: str = None) -> Dict[str, any]:
    if result is not None:
        true_spans, pred_spans = get_true_pred_spans_from_results(result, label)
    pred_true_spans, true_only_spans, pred_only_spans = get_matching_spans(true_spans, pred_spans)
    if label is None:
        label = true_spans[0].label

    partial_matches = filter_partial_matches(pred_only_spans, true_only_spans)
    pred_partial = len(partial_matches)
    true_partial = sum([len(true_parts) for _, true_parts in partial_matches.items()])

    # print(f"true_spans: {len(true_spans)}\t"
    #       f"pred_only_spans: {len(pred_only_spans)}\t"
    #       f"true_only_spans: {len(true_only_spans)}")
    # print(f"exact_matches: {len(pred_true_spans)}\tpartial_matches: {len(partial_matches)}")
    if len(true_spans) == 0:
        strict_rec = np.nan
        lenient_rec = np.nan
    else:
        strict_rec = len(pred_true_spans) / len(true_spans)
        lenient_rec = (len(pred_true_spans) + true_partial) / len(true_spans)

    if len(pred_spans) == 0:
        if len(true_spans) == 0:
            strict_prec = np.nan
            lenient_prec = np.nan
        else:
            strict_prec = 0.0
            lenient_prec = 0.0
    else:
        strict_prec = len(pred_true_spans) / len(pred_spans)
        lenient_prec = (len(pred_true_spans) + pred_partial) / len(pred_spans)

    if len(true_spans) == 0:
        strict_f1 = np.nan
        lenient_f1 = np.nan
    else:
        strict_f1 = 0.0 if len(pred_true_spans) == 0 else 2 * strict_prec * strict_rec / (strict_prec + strict_rec)
        lenient_f1 = 0.0 if (lenient_prec + lenient_rec) == 0.0 else 2 * lenient_prec * lenient_rec / (
                    lenient_prec + lenient_rec)
    # else:
    #     strict_f1 = 2 * strict_prec * strict_rec / (strict_prec + strict_rec)
    #     lenient_f1 = 2 * lenient_prec * lenient_rec / (lenient_prec + lenient_rec)

    scores = {
        'label': label,
        'support': len(true_spans),
        'true_pred': len(pred_true_spans),
        'true_only': len(true_only_spans),
        'pred_only': len(pred_only_spans),
        'true_partial': true_partial,
        'pred_partial': pred_partial,
        'precision_strict': strict_prec,
        'precision_lenient': lenient_prec,
        'recall_strict': strict_rec,
        'recall_lenient': lenient_rec,
        'f1_strict': strict_f1,
        'f1_lenient': lenient_f1,
    }

    # print(f"prec. strict: {strict_prec: >6.3f}\tlenient: {lenient_prec: >6.3f}")
    # print(f"recall strict: {strict_rec: >6.3f}\tlenient: {lenient_rec: >6.3f}")
    # print(f"F-1 strict: {strict_f1: >6.3f}\tlenient: {lenient_f1: >6.3f}")
    return scores


def get_span_from_tokens(tokens: List[Token]) -> Span:
    sent = tokens[0].sent_idx
    start = tokens[0].token_idx
    end = tokens[-1].token_idx + 1
    label = list(set([token.label for token in tokens]))
    text = ' '.join([token.text for token in tokens])
    span = Span(sent, start, end, text, label)
    return span


def get_spans(test_tag_file: str, label_col: str) -> List[Span]:
    spans = []
    tokens = []
    for sent_idx, token_idx, text, true_label, pred_label in read_test_tag_file(test_tag_file):
        label = true_label if label_col == 'true' else pred_label
        if label is None:
            tokens = []
            # print('\n', token_idx, token, label, '\n')
            continue
        if label == 'O' or label.startswith('B'):
            if len(tokens) > 0:
                span = get_span_from_tokens(tokens)
                spans.append(span)
                # print()
            tokens = []
        if label.startswith('B') or label.startswith('I'):
            label_type = label[2:]
            if len(tokens) > 0 and tokens[-1].label != label_type:
                span, layer = get_span_from_tokens(tokens)
                spans.append(span)
                # print()
                tokens = []
            tokens.append(Token(sent_idx, token_idx, text, label_type))
        if label != 'O':
            # print(token_idx, token, label, tokens)
            pass
    if len(tokens) > 0:
        span = get_span_from_tokens(tokens)
        spans.append(span)
        # print()
    return spans
