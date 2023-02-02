from typing import Dict, Generator, List, Tuple, Union
import re
from string import punctuation
from collections import Counter
from collections import defaultdict
import pickle

import torch
from torch import nn
import torch.autograd as autograd
import torch.nn.functional as F

import republic.model.physical_document_model as pdm
from republic.model.republic_date import week_day_names, week_day_names_handwritten
from republic.model.republic_date import month_names_early, month_names_late
from republic.helper.text_helper import SkipgramSimilarity


SPATIAL_FIELDS = [
    'left', 'right', 'top', 'bottom',
    'left_base_x', 'left_base_y',
    'dist_to_prev', 'dist_to_next',
    'indent', 'indent_frac',
    # words
    'weekdays', 'months', 'tokens',
    # characters
    'line_break_chars', 'chars', 'digit', 'whitespace', 'quote',
    'punctuation', 'upper_alpha', 'lower_alpha', 'rare_char'
]


class LSTMLineNgramTagger(nn.Module):

    def __init__(self, ngram_embedding_dim,
                 spatial_hidden_dim, ngram_hidden_dim,
                 num_spatial_features, ngram_line_sizes, ngram_vocab_sizes, line_class_size,
                 bidirectional: bool = False):
        super(LSTMLineNgramTagger, self).__init__()
        self.spatial_hidden_dim = spatial_hidden_dim
        self.ngram_hidden_dim = ngram_hidden_dim
        num_ngram_sizes = len(ngram_vocab_sizes)
        self.combined_hidden_dim = spatial_hidden_dim + self.ngram_hidden_dim * num_ngram_sizes

        # Initialise hidden state
        self.spatial_hidden = self.init_hidden(spatial_hidden_dim)
        self.ngram_hidden = {}
        for ngram_size in ngram_vocab_sizes:
            self.ngram_hidden[ngram_size] = self.init_hidden(self.ngram_hidden_dim)
        self.combined_hidden = self.init_hidden(self.combined_hidden_dim)

        # Ngram embedding and encoding into ngram-lvl representation of words (c_w):
        self.ngram_embeddings = {}
        self.ngram_lstm = {}
        for ngram_size in ngram_vocab_sizes:
            self.ngram_embeddings[ngram_size] = nn.Embedding(ngram_vocab_sizes[ngram_size],
                                                             ngram_embedding_dim)
            self.ngram_lstm[ngram_size] = nn.LSTM(ngram_line_sizes[ngram_size] * ngram_embedding_dim,
                                                  ngram_hidden_dim, bidirectional=bidirectional)

        # The spatial model
        self.spatial_linear = nn.Linear(num_spatial_features, spatial_hidden_dim)
        self.spatial_lstm = nn.LSTM(num_spatial_features, spatial_hidden_dim, bidirectional=bidirectional)

        # The combined model
        self.combined_lstm = nn.LSTM(spatial_hidden_dim + self.ngram_hidden_dim * num_ngram_sizes,
                                     self.combined_hidden_dim, bidirectional=bidirectional)

        # The linear layer that maps from hidden state space to word space
        self.hidden2class = nn.Linear(self.combined_hidden_dim, line_class_size)

    @staticmethod
    def init_hidden(size):
        return (autograd.Variable(torch.zeros(1, size)),
                autograd.Variable(torch.zeros(1, size)))

    def forward(self, spatial_features, ngram_features):
        # print(spatial_features.shape)
        # print(self.spatial_hidden)
        # print(spatial_features.view(len(spatial_features), 1, -1))
        # linear_output, self.spatial_hidden = self.spatial_linear(spatial_features, self.spatial_hidden)
        ngram_lstm_output = []
        for ngram_size in self.ngram_embeddings:
            ngram_embeds = self.ngram_embeddings[ngram_size](ngram_features[ngram_size])
            ngram_lstm_output_, self.ngram_hidden[ngram_size] = self.ngram_lstm[ngram_size](ngram_embeds.view(len(ngram_features[ngram_size]), -1))
            ngram_lstm_output.append(ngram_lstm_output_)
        spatial_lstm_output, self.spatial_hidden = self.spatial_lstm(spatial_features, self.spatial_hidden)

        combined_hidden = torch.cat([spatial_lstm_output] + ngram_lstm_output, dim=1)
        combined_lstm_output, self.combined_hidden = self.combined_lstm(combined_hidden)

        # Map word LSTM output to line class space
        class_space = self.hidden2class(combined_lstm_output)
        class_scores = F.log_softmax(class_space, dim=1)
        return class_scores


class LSTMLineTagger(nn.Module):

    def __init__(self, char_embedding_dim,
                 spatial_hidden_dim: int, char_hidden_dim: int,
                 num_spatial_features: int,
                 char_line_size: int, char_vocab_size: int, line_class_size: int,
                 bidirectional: bool = False):
        super(LSTMLineTagger, self).__init__()
        self.spatial_hidden_dim = spatial_hidden_dim
        self.char_hidden_dim = char_hidden_dim
        self.combined_hidden_dim = spatial_hidden_dim + char_hidden_dim

        if bidirectional is True:
            self.spatial_hidden_dim = self.spatial_hidden_dim * 2
            self.char_hidden_dim = self.char_hidden_dim * 2
            self.combined_hidden = self.combined_hidden_dim * 2

        # Initialise hidden state
        self.spatial_hidden = self.init_hidden(spatial_hidden_dim)
        self.char_hidden = self.init_hidden(char_hidden_dim)
        self.combined_hidden = self.init_hidden(self.combined_hidden_dim)

        # Char embedding and encoding into char-lvl representation of words (c_w):
        self.char_embeddings = nn.Embedding(char_vocab_size, char_embedding_dim)
        self.char_lstm = nn.LSTM(char_line_size * char_embedding_dim, char_hidden_dim,
                                 bidirectional=bidirectional)

        # The spatial model
        self.spatial_linear = nn.Linear(num_spatial_features, spatial_hidden_dim)
        self.spatial_lstm = nn.LSTM(num_spatial_features, spatial_hidden_dim,
                                    bidirectional=bidirectional)

        # The combined model
        self.combined_lstm = nn.LSTM(spatial_hidden_dim + char_hidden_dim, self.combined_hidden_dim,
                                     bidirectional=bidirectional)

        # The linear layer that maps from hidden state space to word space
        self.hidden2class = nn.Linear(self.combined_hidden_dim, line_class_size)

    @staticmethod
    def init_hidden(size):
        return (autograd.Variable(torch.zeros(1, size)),
                autograd.Variable(torch.zeros(1, size)))

    def forward(self, spatial_features, char_features):
        # print(spatial_features.shape)
        # print(self.spatial_hidden)
        # print(spatial_features.view(len(spatial_features), 1, -1))
        # linear_output, self.spatial_hidden = self.spatial_linear(spatial_features, self.spatial_hidden)
        char_embeds = self.char_embeddings(char_features)
        # print(char_embeds)

        char_lstm_output, self.char_hidden = self.char_lstm(char_embeds.view(len(char_features), -1))
        spatial_lstm_output, self.spatial_hidden = self.spatial_lstm(spatial_features, self.spatial_hidden)

        combined_hidden = torch.cat([spatial_lstm_output, char_lstm_output], dim=1)
        combined_lstm_output, self.combined_hidden = self.combined_lstm(combined_hidden)
        # print(combined_lstm_output.shape)

        # Map word LSTM output to POS tag space
        class_space = self.hidden2class(combined_lstm_output)
        class_scores = F.log_softmax(class_space, dim=1)
        return class_scores


class NeuralLineClassifier:

    def __init__(self, lstm_line_tagger, class_to_ix, char_to_ix, config: Dict[str, any]):
        self.lstm_line_tagger = lstm_line_tagger
        self.char_to_ix = char_to_ix
        self.class_to_ix = class_to_ix
        self.ix_to_class = {class_to_ix[class_]: class_ for class_ in class_to_ix}
        self.config = config
        self.skip_sim = get_date_skip_sim()

    @staticmethod
    def load_from_config(config: Dict[str, any]):
        char_to_ix = read_class_set_mapping(config['charset_file'])
        class_to_ix = read_class_set_mapping(config['line_class_set_file'])
        num_classes = len(class_to_ix)
        charset_size = len(char_to_ix)
        model = LSTMLineTagger(config['char_embedding_dim'],
                               config['spatial_hidden_dim'],
                               config['char_hidden_dim'],
                               config['num_spatial_features'],
                               config['char_line_size'],
                               charset_size,
                               num_classes)
        model.load_state_dict(torch.load(config['model_file']))
        model.eval()
        return NeuralLineClassifier(model, class_to_ix, char_to_ix, config)

    def page_to_feature_sequences(self, page_lines, line_fixed_length=100):
        spatial_sequence = []
        char_sequence = []
        # class_sequence = []
        for line in page_lines:
            line_text = get_line_text(line)
            spatial_features = [float(line[spatial_field]) for spatial_field in SPATIAL_FIELDS]
            padding_size = line_fixed_length - len(line_text)
            text = line_text
            text += ' ' * padding_size
            for c in text:
                if c not in self.char_to_ix:
                    print(line)
            char_features = [self.char_to_ix[c] for c in text]
            spatial_sequence.append(spatial_features)
            char_sequence.append(char_features)
            # class_sequence.append(self.class_to_ix[line['line_class']])

        spatial_tensor = torch.tensor(spatial_sequence, dtype=torch.float32)
        char_tensor = torch.tensor(char_sequence)
        # class_tensor = torch.tensor(class_sequence)
        return spatial_tensor, char_tensor
        # return spatial_tensor, char_tensor, class_tensor

    def classify_page_lines(self, page: pdm.PageXMLPage):
        with torch.no_grad():
            page_line_features = get_page_line_features(page, self.skip_sim)
            # spatial_sequence, char_sequence, class_sequence = self.page_to_feature_sequences(page_line_features)
            spatial_sequence, char_sequence= self.page_to_feature_sequences(page_line_features)
            self.lstm_line_tagger.spatial_hidden = self.lstm_line_tagger.init_hidden(self.config['spatial_hidden_dim'])
            class_scores = self.lstm_line_tagger(spatial_sequence, char_sequence)
            predict_scores, predict_classes = torch.max(class_scores, 1)
            predict_labels = [self.ix_to_class[pc.item()] for pc in predict_classes]
            return {line_features['line_id']: line_class for line_features, line_class
                    in zip(page_line_features, predict_labels)}


def load_neural_line_classifier(model_file: str, charset_file: str,
                                line_class_set_file: str) -> NeuralLineClassifier:
    config = {
        'model_file': model_file,
        'charset_file': charset_file,
        'line_class_set_file': line_class_set_file,
        'char_embedding_dim': 100,
        'spatial_hidden_dim': 22,
        'char_hidden_dim': 100,
        'char_line_size': 100,
        'num_spatial_features': len(SPATIAL_FIELDS),
    }
    return NeuralLineClassifier.load_from_config(config)


def page_to_feature_sequences_char(page_lines, char_to_ix, class_to_ix, line_fixed_length=100):
    spatial_sequence = []
    char_sequence = []
    class_sequence = []
    for line in page_lines:
        spatial_features = [float(line[spatial_field]) for spatial_field in SPATIAL_FIELDS]
        padding_size = line_fixed_length - len(line['line_text'])
        text = line['line_text']
        text += ' ' * padding_size
        for c in text:
            if c not in char_to_ix:
                print(line)
        char_features = [char_to_ix[c] for c in text]
        spatial_sequence.append(spatial_features)
        char_sequence.append(char_features)
        class_sequence.append(class_to_ix[line['line_class']])

    spatial_tensor = torch.tensor(spatial_sequence, dtype=torch.float32)
    char_tensor = torch.tensor(char_sequence)
    class_tensor = torch.tensor(class_sequence)
    return spatial_tensor, char_tensor, class_tensor


def train_model(model, loss_function, optimizer, train_data, num_epochs,
                char_to_ix, class_to_ix, show_loss_threshold: int = 1.0):
    all_losses = []
    for epoch in range(num_epochs):
        for page in train_data:

            # Step 1. Remember that Pytorch accumulates gradients.
            # We need to clear them out before each instance
            model.zero_grad()

            # Step 2. Get our inputs ready for the network, that is, turn them into
            # Tensors of word indices.
            spatial_sequence, char_sequence, class_targets = page_to_feature_sequences_char(page['lines'],
                                                                                            char_to_ix,
                                                                                            class_to_ix)
            model.spatial_hidden = model.init_hidden(model.spatial_hidden_dim)

            # Step 3. Run our forward pass.
            class_scores = model(spatial_sequence, char_sequence)

            # Step 4. Compute the loss, gradients, and update the parameters by
            #  calling optimizer.step()
            loss = loss_function(class_scores, class_targets)
            all_losses.append(loss)
            if loss.item() > show_loss_threshold:
                print(epoch, page['page_id'], loss.item())
            loss.backward() #retain_graph=True
            optimizer.step()
    return all_losses


def evaluate_model(model, test_data, validate_data, char_to_ix: Dict[str, int], class_to_ix: Dict[str, int]):
    ix_to_class = {class_to_ix[c]: c for c in class_to_ix}

    confusion = defaultdict(Counter)

    line_scores = []
    page_scores = {}

    with torch.no_grad():
        for page in test_data + validate_data:
            spatial_sequence, char_sequence, class_targets = page_to_feature_sequences_char(page['lines'],
                                                                                            char_to_ix,
                                                                                            class_to_ix)
            model.spatial_hidden = model.init_hidden(model.spatial_hidden_dim)
            class_scores = model(spatial_sequence, char_sequence)
            predict_scores, predict_classes = torch.max(class_scores, 1)
            page_score = [pc.item() == tc.item() for pc, tc in zip(class_targets, predict_classes)].count(True)
            line_scores.extend([pc.item() == tc.item() for pc, tc in zip(class_targets, predict_classes)])
            page_scores[page['page_id']] = page_score / len(class_targets)
            for pc, tc in zip(class_targets, predict_classes):
                confusion[ix_to_class[pc.item()]].update([ix_to_class[tc.item()]])

    print(f'micro_avg: {line_scores.count(True) / len(line_scores): >.2f}')
    print(f'macro_avg: {sum(page_scores.values()) / len(page_scores): >.2f}')
    return page_scores, confusion


def evaluate_line_type(confusion, target_type):
    total_lines = sum(confusion[target_type].values())
    correct_lines = confusion[target_type][target_type]
    predicted_lines = sum([confusion[predicted_type][target_type] for predicted_type in confusion])
    if total_lines > 0:
        precision = correct_lines / total_lines
    else:
        precision = 0
    if predicted_lines > 0:
        recall = correct_lines / predicted_lines
    else:
        recall = 0
    return precision, recall


def write_class_set_file(class_set, class_set_file):
    with open(class_set_file, 'wb') as fh:
        pickle.dump(class_set, fh)


def read_class_set_file(class_set_file):
    with open(class_set_file, 'rb') as fh:
        return pickle.load(fh)


def read_class_set_mapping(class_set_file: str):
    class_set = read_class_set_file(class_set_file)
    class_to_ix = {}
    for class_ in class_set:
        class_to_ix[class_] = len(class_to_ix)
    return class_to_ix


def get_line_char_ngrams(line: Union[pdm.PageXMLTextLine, Dict[str, any], str], ngram_size: int,
                   padding_char: str = ' ', use_padding: bool = True):
    padding = padding_char * (ngram_size - 1)
    line_text = get_line_text(line)
    if use_padding:
        line_text = f'{padding}{line_text}{padding}'
    for i in range(0, len(line_text) - (ngram_size-1)):
        ngram = line_text[i:i+ngram_size]
        yield ngram


def get_line_text(line: Union[pdm.PageXMLTextLine, Dict[str, any], str]) -> str:
    if isinstance(line, str):
        return line
    elif hasattr(line, 'text'):
        return line.text
    elif 'text' in line:
        return line['text']
    elif 'line_text' in line:
        return line['line_text']
    else:
        raise TypeError('Unknown line type')


def tokenise(line: Union[pdm.PageXMLTextLine, Dict[str, any], str]) -> List[str]:
    line_text = get_line_text(line)
    if line_text is None or len(line_text) == 0:
        return []
    return [t for t in re.split(r'\W+', line_text) if t != '']


def get_skip_sim_terms(tokens: List[str], skip_sim: SkipgramSimilarity) -> List[Tuple[str, str, float]]:
    return [(token, sim_term, sim_score) for token in tokens for sim_term, sim_score in
            skip_sim.rank_similar(token, top_n=1)]


def get_weekday_tokens(tokens: List[str], skip_sim: SkipgramSimilarity) -> List[Tuple[str, str, float]]:
    return get_skip_sim_terms(tokens, skip_sim)


def get_month_tokens(tokens: List[str], skip_sim: SkipgramSimilarity) -> List[Tuple[str, str, float]]:
    return get_skip_sim_terms(tokens, skip_sim)


def count_line_break_chars(tokens: List[str]) -> int:
    if len(tokens) == 0:
        return 0
    else:
        first_token = tokens[0]
        last_token = tokens[-1]
        return [last_token[-1] in {'-', '„'}, first_token[0] == '„'].count(True)


def get_line_text_features(line: Union[pdm.PageXMLTextLine, Dict[str, any]],
                           skip_sims: Dict[str, SkipgramSimilarity]) -> Dict[str, int]:
    line_text = get_line_text(line)
    tokens = tokenise(line_text) if line_text is not None else []
    score = {
        'weekdays': len(get_weekday_tokens(tokens, skip_sims['weekdays'])),
        'months': len(get_weekday_tokens(tokens, skip_sims['months'])),
        'tokens': len(tokens),
        'line_break_chars': count_line_break_chars(tokens),
        'chars': len(line_text) if line_text is not None else 0,
        'digit': 0,
        'whitespace': 0,
        'quote': 0,
        'punctuation': 0,
        'upper_alpha': 0,
        'lower_alpha': 0,
        'rare_char': 0,
    }
    if line_text is not None:
        for c in line_text:
            if c.isdigit():
                score['digit'] += 1
            elif c == ' ':
                score['whitespace'] += 1
            elif c in punctuation:
                score['punctuation'] += 1
            elif c.islower():
                score['lower_alpha'] += 1
            elif c.isupper():
                score['upper_alpha'] += 1
            elif c in {'"', "'", '„'}:
                score['quote'] += 1
            else:
                score['rare_char'] += 1
    return score


def get_date_skip_sim() -> Dict[str, SkipgramSimilarity]:
    months = set(month_names_early + month_names_late)
    months.add('Decembris')
    weekdays = set(week_day_names + week_day_names_handwritten)
    weekdays.add('Jouis')
    skip_sim = {
        'weekdays': SkipgramSimilarity(ngram_length=3, skip_length=1),
        'months': SkipgramSimilarity(ngram_length=3, skip_length=1)
    }

    skip_sim['weekdays'].index_terms(list(weekdays))
    skip_sim['months'].index_terms(list(months))
    return skip_sim


def get_main_columns(doc: pdm.PageXMLDoc) -> List[pdm.PageXMLColumn]:
    if hasattr(doc, 'columns'):
        cols = [column for column in doc.columns if 'extra' not in column.type]
        cols = [column for column in cols if 'marginalia' not in column.type]
        return cols
    else:
        return []


def get_marginalia_regions(doc: pdm.PageXMLTextRegion) -> List[pdm.PageXMLTextRegion]:
    if isinstance(doc, pdm.PageXMLPage) or doc.__class__.__name__ == 'PageXMLPage':
        trs = doc.text_regions + [tr for col in doc.columns for tr in col.text_regions]
    elif isinstance(doc, pdm.PageXMLScan) or isinstance(doc, pdm.PageXMLColumn) \
            or doc.__class__.__name__ in {'PageXMLScan', 'PageXMLColumn'}:
        trs = []
        for tr in doc.text_regions:
            if len(tr.text_regions) > 0:
                trs.extend(tr.text_regions)
            else:
                trs.append(tr)
    else:
        return []
    return [tr for tr in trs if is_marginalia_text_region(tr)]


def is_marginalia_text_region(doc: pdm.PageXMLTextRegion) -> bool:
    if isinstance(doc, pdm.PageXMLTextRegion) or doc.__class__.__name__ == 'PageXMLTextRegion':
        return 'marginalia' in doc.type
    else:
        return False


def is_marginalia_column(doc: pdm.PageXMLColumn) -> bool:
    if isinstance(doc, pdm.PageXMLColumn) or doc.__class__.__name__ == 'PageXMLColumn':
        return len(get_marginalia_regions(doc)) > 0
    else:
        return False


def get_marginalia_columns(doc: pdm.PageXMLDoc) -> List[pdm.PageXMLColumn]:
    if isinstance(doc, pdm.PageXMLPage) or doc.__class__.__name__ == 'PageXMLPage':
        return [col for col in doc.columns if is_marginalia_column(col)]
    else:
        return []


def is_noise_line(line: pdm.PageXMLTextLine, col: pdm.PageXMLColumn) -> bool:
    if line.text is None:
        return True
    indent = line.coords.left - col.coords.left
    indent_frac = indent / col.coords.width
    return len(line.text) < 4 and indent_frac > 0.8


def is_insert_line(line: pdm.PageXMLTextLine, col: pdm.PageXMLColumn) -> bool:
    if line.text is None:
        return True
    indent = line.coords.left - col.coords.left
    indent_frac = indent / col.coords.width
    if len(line.text) < 4 and indent_frac > 0.8:
        return False
    return len(line.text) < 14 and indent_frac > 0.7


def get_col_line_base_dist(col: pdm.PageXMLColumn) -> Dict[str, any]:
    lines = sorted(col.lines + [line for tr in col.text_regions for line in tr.lines])
    # print('pre num lines', len(lines))
    # for line in lines:
    #    print(is_noise_line(line, col), line.text)
    special_lines = [line for line in lines if is_noise_line(line, col) or is_insert_line(line, col)]
    base_dist = {}
    for curr_line in special_lines:
        indent = curr_line.coords.left - col.coords.left
        indent_frac = indent / col.coords.width
        if is_noise_line(curr_line, col):
            dist_to_prev = 0
            dist_to_next = 70
        elif is_insert_line(curr_line, col):
            dist_to_prev = 0
            dist_to_next = 70
        else:
            dist_to_prev = 0
            dist_to_next = 70
        base_dist[curr_line.id] = {
            'dist_to_prev': dist_to_prev, 'dist_to_next': dist_to_next,
            'indent': indent, 'indent_frac': indent_frac
        }

    lines = [line for line in lines if line not in special_lines]
    lines.sort(key=lambda x: x.baseline.top)
    for li, curr_line in enumerate(lines):
        indent = curr_line.coords.left - col.coords.left
        indent_frac = indent / col.coords.width
        if li == 0:
            dist_to_prev = 2000
        else:
            prev_line = lines[li - 1]
            prev_base_left = sorted(prev_line.baseline.points)[0]
            curr_base_left = sorted(curr_line.baseline.points)[0]
            # print(curr_line.id, prev_base_left, curr_base_left, curr_base_left[1] - prev_base_left[1], curr_line.text)
            dist_to_prev = curr_base_left[1] - prev_base_left[1]
        if li == len(lines) - 1:
            dist_to_next = 2000
        else:
            next_line = lines[li + 1]
            next_base_left = sorted(next_line.baseline.points)[0]
            curr_base_left = sorted(curr_line.baseline.points)[0]
            # print(curr_line.id, prev_base_left, curr_base_left, curr_base_left[1] - prev_base_left[1], curr_line.text)
            dist_to_next = next_base_left[1] - curr_base_left[1]
        #         if prev_line:
        #             print(f"{prev_line.coords.y: >4}\t{prev_base_left}\t", prev_line.text)
        #         print(f"{curr_line.coords.y: >4}\t{curr_base_left}\t{dist_to_prev}\t{dist_to_next}\t", curr_line.text)
        #         if next_line:
        #             print(f"{next_line.coords.y: >4}\t{next_base_left}\t", next_line.text)
        #         print()
        base_dist[curr_line.id] = {
            'dist_to_prev': dist_to_prev, 'dist_to_next': dist_to_next,
            'indent': indent, 'indent_frac': indent_frac
        }
    return base_dist


def classify_line_rule_based(line: pdm.PageXMLTextLine, col: pdm.PageXMLColumn,
                             base_dist: Dict[str, Dict[str, Union[int, float]]],
                             line_score: Dict[str, int]) -> str:
    indent = line.coords.left - col.coords.left
    indent_frac = indent / col.coords.width
    # print(line.coords.left, col.coords.left, indent, indent_frac, '\t\t', len(line.text), line.text)
    if line.text is None:
        return 'empty'
    if len(line.text) < 4 and indent_frac > 0.8:
        return 'noise'
    elif len(line.text) < 14 and indent_frac > 0.7:
        return 'noise'
    if indent_frac < 0.10:
        if len(line.text) < 3:
            return 'noise'
        if re.search(r'^[A-Z]\w+ den \w+en. [A-Z]', line.text) and \
                (line_score['weekdays'] > 0 or line_score['months'] > 0):
            return 'date'
        elif line_score['months'] > 0 and line.coords.top < 500 and len(line.text) < 20:
            return 'date_header'
        elif line.text.startswith('Nihil') or line.text.startswith('nihil') or ' actum' in line.text:
            return 'date'
        if len(line.text) < 40:
            return 'para_end'
        elif base_dist[line.id]['dist_to_prev'] == 2000:
            if line.baseline.points[0][1] - line.coords.top > 150:
                return 'para_start'
            # print(base_dist[line.id], line.baseline.points[0][1], line.coords.top, line.text)
            else:
                return 'para_mid'
        elif base_dist[line.id]['dist_to_prev'] > 120:
            # print(base_dist[line.id], line.baseline.points[0][1], line.coords.top, line.text)
            return 'para_start'
        else:
            return 'para_mid'
    elif 0.2 < indent_frac < 0.7 and len(line.text) >= 4:
        if ' den ' in line.text:
            return 'date'
        elif 'Nihil' in line.text or 'nihil' in line.text or ' act' in line.text:
            return 'date'
        elif line.text.isdigit():
            return 'date'
        else:
            return 'attendance'
    else:
        print('unknown:', line.coords.box, len(line.text), indent_frac, line.text)
        return 'unknown'


def get_line_features(line, col, skip_sim: Dict[str, SkipgramSimilarity], base_dist) -> Dict[str, any]:
    lc = line.coords
    cc = col.coords
    line_score = get_line_text_features(line, skip_sim)
    left_base = sorted(line.baseline.points)[0]
    doc = {
        'line_id': line.id,
        'left': lc.left - cc.left,
        'right': cc.right - lc.right,
        'top': lc.top - cc.top,
        'bottom': cc.bottom - lc.bottom,
        'text': line.text,
        'left_base_x': left_base[0],
        'left_base_y': left_base[1],
        'dist_to_prev': base_dist['dist_to_prev'],
        'dist_to_next': base_dist['dist_to_next'],
        'indent': base_dist['indent'],
        'indent_frac': base_dist['indent_frac'],
    }
    for field in line_score:
        doc[field] = line_score[field]
    return doc


def get_page_line_features(page: pdm.PageXMLPage,
                           skip_sim: Dict[str, SkipgramSimilarity]) -> List[Dict[str, any]]:
    rows = []
    for col in page.columns:
        trs = [tr for tr in col.text_regions if 'marginalia' not in tr.type]
        base_dist = get_col_line_base_dist(col)
        for tr in sorted(trs):
            for line in sorted(tr.lines):
                doc = get_line_features(line, col, skip_sim, base_dist[line.id])
                rows.append(doc)
    return rows


def read_csv(csv_file: str) -> Generator[Dict[str, any], None, None]:
    with open(csv_file, 'rt') as fh:
        header_line = next(fh)
        headers = header_line.strip().replace('"', '').split('\t')
        # print(headers)
        for line in fh:
            row = line.strip().split('\t')
            clean_row = []
            for cell in row:
                if cell.startswith('"') and cell.endswith('"'):
                    cell = cell[1:-1]
                clean_row.append(cell)
            # print(clean_row)
            yield {header: clean_row[hi] for hi, header in enumerate(headers)}


def read_page_lines(csv_file: str) -> Generator[List[Dict[str, any]], None, None]:
    prev_page_id = None
    page_lines = []
    for row in read_csv(csv_file):
        if row['page_id'] != prev_page_id:
            if len(page_lines) > 0:
                yield page_lines
                page_lines = []
        page_lines.append(row)
        prev_page_id = row['page_id']
    if len(page_lines) > 0:
        yield page_lines


def split_ground_truth_data(gt_data: List[Dict[str, any]]) -> Tuple[List[Dict[str, any]], List[Dict[str, any]], List[Dict[str, any]]]:
    total = len(gt_data)
    import random
    random.shuffle(gt_data)
    chunk_size = int(total / 10)
    test_data = gt_data[:chunk_size]
    validate_data = gt_data[chunk_size:2*chunk_size]
    train_data = gt_data[2*chunk_size:]

    if len(test_data + validate_data + train_data) != len(gt_data):
        raise IndexError('Invalid split of ground truth data')

    return train_data, validate_data, test_data


def read_ground_truth_data(line_class_csv: str) -> List[Dict[str, any]]:
    train_data = []
    for page_lines in read_page_lines(line_class_csv):
        for line in page_lines:
            # print(line['page_id'])
            pass
        checked = [line for line in page_lines if line['checked'] == '1']
        if len(checked) != len(page_lines):
            break
        # print(f"adding page {page_lines[0]['page_id']} to training data")
        train_data.append({'page_id': page_lines[0]['page_id'], 'lines': page_lines})
    print('number of training pages:', len(train_data))
    return train_data
