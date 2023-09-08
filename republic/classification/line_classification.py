import gzip
import json
import os
import pickle
import random
import re
from collections import Counter
from collections import defaultdict
from typing import Dict, Generator, List, Set, Tuple, Union

from flair.data import Sentence
import pagexml.model.physical_document_model as pdm
import torch
from Levenshtein import distance
from pagexml.parser import json_to_pagexml_page

# import republic.model.physical_document_model as pdm
import republic.classification.lstm_line_tagger as line_tagger
import republic.classification.page_features as page_features
from republic.helper.metadata_helper import doc_id_to_iiif_url
from republic.helper.text_helper import SkipgramSimilarity
from republic.parser.logical.paragraph_parser import split_paragraphs


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


class NeuralLineClassifier:

    def __init__(self, model_dir: str):
        lstm_line_tagger, char_to_ix, class_to_ix = load_neural_line_classifier(model_dir)
        self.lstm_line_tagger = lstm_line_tagger
        self.config = self.lstm_line_tagger.config
        self.char_to_ix = char_to_ix
        self.class_to_ix = class_to_ix
        self.ix_to_class = {class_to_ix[class_]: class_ for class_ in class_to_ix}
        self.skip_sim = page_features.get_date_skip_sim()

    def page_to_feature_sequences(self, page_lines, line_fixed_length=100):
        spatial_sequence = []
        char_sequence = []
        # class_sequence = []
        for line in page_lines:
            line_text = page_features.get_line_text(line)
            spatial_features = [float(line[spatial_field]) for spatial_field in SPATIAL_FIELDS]
            padding_size = line_fixed_length - len(line_text)
            text = line_text
            text += ' ' * padding_size
            for c in text:
                if c not in self.char_to_ix:
                    print(line)
            char_features = [self.char_to_ix[c] if c in self.char_to_ix else self.char_to_ix['<unk>'] for c in text]
            spatial_sequence.append(spatial_features)
            char_sequence.append(char_features)
            # class_sequence.append(self.class_to_ix[line['line_class']])

        spatial_tensor = torch.tensor(spatial_sequence, dtype=torch.float32)
        char_tensor = torch.tensor(char_sequence)
        # class_tensor = torch.tensor(class_sequence)
        return spatial_tensor, char_tensor
        # return spatial_tensor, char_tensor, class_tensor

    '''
    def classify_page_lines(self, page: pdm.PageXMLPage):
        with torch.no_grad():
            page_line_features = page_features.get_page_line_features(page, self.skip_sim)
            # spatial_sequence, char_sequence, class_sequence = self.page_to_feature_sequences(page_line_features)
            spatial_sequence, char_sequence = self.page_to_feature_sequences(page_line_features)
            self.lstm_line_tagger.spatial_hidden = self.lstm_line_tagger.init_hidden(self.config['spatial_hidden_dim'])
            class_scores = self.lstm_line_tagger(spatial_sequence, char_sequence)
            predict_scores, predict_classes = torch.max(class_scores, 1)
            predict_labels = [self.ix_to_class[pc.item()] for pc in predict_classes]
            return {line_features['line_id']: line_class for line_features, line_class
                    in zip(page_line_features, predict_labels)}
    '''

    def classify_page_lines(self, page: pdm.PageXMLPage):
        if page.stats['lines'] == 0:
            return {}
        with torch.no_grad():
            page_line_features = page_features.get_page_line_features(page, self.skip_sim)
            # spatial_sequence, char_sequence, class_sequence = self.page_to_feature_sequences(page_line_features)
            features = page_features.page_to_feature_sequences(page_line_features, self.char_to_ix,
                                                               self.class_to_ix,
                                                               line_fixed_length=self.config['char_line_size'])
            if isinstance(self.lstm_line_tagger, line_tagger.LSTMLineTagger):
                self.lstm_line_tagger.spatial_hidden = self.lstm_line_tagger.init_hidden(self.lstm_line_tagger.spatial_hidden_dim)
                class_scores = self.lstm_line_tagger(features['spatial'], features['char'])
            if isinstance(self.lstm_line_tagger, line_tagger.LSTMLineTaggerGysBERT):
                self.lstm_line_tagger.spatial_hidden = self.lstm_line_tagger.init_hidden(self.lstm_line_tagger.spatial_hidden_dim)
                class_scores = self.lstm_line_tagger(features['spatial'], features['char'], features['sentence'])
            predict_scores, predict_classes = torch.max(class_scores, 1)
            predict_labels = [self.ix_to_class[pc.item()] for pc in predict_classes]
            return {line_features['line_id']: line_class for line_features, line_class
                    in zip(page_line_features, predict_labels)}


def save_neural_line_classifier(model_dir: str,
                                model: Union[line_tagger.LSTMLineTagger, line_tagger.LSTMLineTaggerGysBERT],
                                char_to_ix: Dict[str, int], class_to_ix: Dict[str, int]):
    if os.path.exists(model_dir) is False:
        os.mkdir(model_dir)
    model_file = os.path.join(model_dir, 'line_classifier.model.pt')
    torch.save(model.state_dict(), model_file)
    config_file = os.path.join(model_dir, 'line_classifier.config.json')
    with open(config_file, 'wt') as fh:
        model_config = model.config
        model_config['model_file'] = 'line_classifier.model.pt'
        json.dump(model_config, fh)
    char_to_ix_file = os.path.join(model_dir, 'line_classifier.char_to_ix.json')
    with open(char_to_ix_file, 'wt') as fh:
        json.dump(char_to_ix, fh)
    class_to_ix_file = os.path.join(model_dir, 'line_classifier.class_to_ix.json')
    with open(class_to_ix_file, 'wt') as fh:
        json.dump(class_to_ix, fh)


def load_neural_line_classifier(model_dir: str) -> Tuple[Union[line_tagger.LSTMLineTagger,
                                                               line_tagger.LSTMLineTaggerGysBERT],
                                                         Dict[str, int], Dict[str, int]]:
    config_file = os.path.join(model_dir, 'line_classifier.config.json')
    with open(config_file, 'rt') as fh:
        model_config = json.load(fh)
        # if 'model_file' not in model_config:
        model_config['model_file'] = f"{model_dir}/line_classifier.model.pt"
    char_to_ix_file = os.path.join(model_dir, 'line_classifier.char_to_ix.json')
    with open(char_to_ix_file, 'rt') as fh:
        char_to_ix = json.load(fh)
    class_to_ix_file = os.path.join(model_dir, 'line_classifier.class_to_ix.json')
    with open(class_to_ix_file, 'rt') as fh:
        class_to_ix = json.load(fh)
    if model_config['model_class'] == 'LSTMLineTagger':
        model = line_tagger.LSTMLineTagger.load_from_config(model_config)
    elif model_config['model_class'] == 'LSTMLineNgramTagger':
        model = line_tagger.LSTMLineNgramTagger.load_from_config(model_config)
    elif model_config['model_class'] == 'LSTMLineTaggerGysBERT':
        model = line_tagger.LSTMLineTaggerGysBERT.load_from_config(model_config)
    else:
        raise TypeError(f"unknown model class {model_config['model_class']}. "
                        f"Must be one of 'LSTMLineTagger', 'LSTMLineTaggerGysBERT")
    return model, char_to_ix, class_to_ix


def inference_page_line_class_scores(model, features):
    model.spatial_hidden = model.init_hidden(model.spatial_hidden_dim)
    model.char_hidden = model.init_hidden(model.char_hidden_dim)
    if hasattr(model, 'sentence_hidden'):
        model.sentence_hidden = model.init_hidden(model.sentence_hidden_dim)

    if isinstance(model, line_tagger.LSTMLineTaggerGysBERT):
        return model(features['spatial'], features['char'], features['sentence'])
    else:
        return model(features['spatial'], features['char'])


def train_model(model, loss_function, optimizer, train_data, num_epochs,
                char_to_ix, class_to_ix, show_loss_threshold: int = 1.0):
    all_losses = []
    sentence_tensor_map = {}
    if isinstance(model, line_tagger.LSTMLineTaggerGysBERT):
        print('pre-computing sentence embeds for training data')
        for page in train_data:
            line_texts = [line['line_text'] for line in page['lines']]
            line_texts = [line_text if line_text != '' else ' ' for line_text in line_texts]
            sentence_embeds = model.sentence_embeddings.embed([Sentence(line_text) for line_text in line_texts])
            sentence_tensor = torch.stack([sentence.embedding for sentence in sentence_embeds])
            sentence_tensor_map[page['page_id']] = sentence_tensor
    for epoch in range(num_epochs):
        print(f'epoch {epoch}')
        for page in train_data:

            # Step 1. Remember that Pytorch accumulates gradients.
            # We need to clear them out before each instance
            model.zero_grad()

            # Step 2. Get our inputs ready for the network, that is, turn them into
            # Tensors of word indices.
            features = page_features.page_to_feature_sequences(page['lines'],
                                                               char_to_ix,
                                                               class_to_ix)

            # Step 3. Run our forward pass.
            if page['page_id'] in sentence_tensor_map:
                features['sentence'] = sentence_tensor_map[page['page_id']]
            class_scores = inference_page_line_class_scores(model, features)

            # Step 4. Compute the loss, gradients, and update the parameters by
            #  calling optimizer.step()
            loss = loss_function(class_scores, features['class'])
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
            features = page_features.page_to_feature_sequences(page['lines'],
                                                               char_to_ix,
                                                               class_to_ix)
            class_scores = inference_page_line_class_scores(model, features)
            predict_scores, predict_classes = torch.max(class_scores, 1)
            page_score = [pc.item() == tc.item() for pc, tc in zip(features['class'], predict_classes)].count(True)
            line_scores.extend([pc.item() == tc.item() for pc, tc in zip(features['class'], predict_classes)])
            page_scores[page['page_id']] = page_score / len(features['class'])
            for tc, pc in zip(features['class'], predict_classes):
                confusion[ix_to_class[pc.item()]].update([ix_to_class[tc.item()]])

    print(f'micro_avg: {line_scores.count(True) / len(line_scores): >.2f}')
    print(f'macro_avg: {sum(page_scores.values()) / len(page_scores): >.2f}')
    return page_scores, confusion


def classify_lines_with_split_paragraphs(page: pdm.PageXMLPage, debug: int = 0):
    line_class = {}
    page_trs = [tr for column in page.columns + page.extra for tr in column.text_regions]
    if debug > 1:
        for col in page.columns:
            print('COL STATS:', col.stats)
            for tr in col.text_regions:
                print('\tTR STATS:', tr.stats, tr.types)
                for line in tr.lines:
                    print('\t\tLINE:', line.id)
    page_trs += [tr for tr in page.text_regions]
    resolution_trs = [tr for tr in page_trs if 'resolution' in tr.type]
    other_trs = [tr for tr in page_trs if 'resolution' not in tr.type]
    non_res_types = {'attendance', 'date', 'marginalia'}
    for tr in other_trs:
        if len(tr.types.intersection(non_res_types)) > 0:
            for non_res_type in non_res_types:
                if non_res_type in tr.types:
                    if non_res_type == 'date' and tr.coords.bottom > 300 and \
                            sum([len(line.text) for line in tr.lines if line.text]) < 30:
                        non_res_type = 'date_header'
                    for line in tr.lines:
                        line_class[line.id] = non_res_type
        else:
            print('Unexpected tr type:', tr.types)
    res_lines = [line for res_tr in resolution_trs for line in res_tr.get_lines()]
    if debug > 1:
        print('number of res_tr lines:', len(res_lines))
    sum_para_lines = 0
    for res_line in res_lines:
        if res_line.text is None:
            line_class[res_line.id] = 'empty'
    paras_lines = [para_lines for para_lines in split_paragraphs(res_lines, debug=debug)]
    for para_lines in paras_lines:
        if debug > 1:
            for li, line in enumerate(para_lines):
                line_type = 'para_mid'
                if li == 0:
                    line_type = para_lines.start_type
                if li == len(para_lines) - 1:
                    line_type = para_lines.end_type
                print('PARA_LINES:', line.id, line_type)
            for line in para_lines.noise_lines:
                print('PARA_LINES:', line.id, 'noise')
        sum_para_lines += len(para_lines) + len(para_lines.noise_lines)
        first_line = para_lines.first
        last_line = para_lines.last
        mid_lines = [line for line in para_lines if line != first_line and line != last_line and
                     line not in para_lines.insertion_lines]
        line_class[first_line.id] = para_lines.start_type
        line_class[last_line.id] = para_lines.end_type
        for mid_line in mid_lines:
            line_class[mid_line.id] = 'para_mid'
        for line in para_lines.insertion_lines:
            line_class[line.id] = 'insert_omitted'
        for line in para_lines.noise_lines:
            line_class[line.id] = 'noise'
    if debug > 1:
        print('sum_para_lines:', sum_para_lines)
    return line_class


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


def classify_line_rule_based(line: pdm.PageXMLTextLine, col: pdm.PageXMLColumn,
                             base_dist: Dict[str, Dict[str, Union[int, float]]],
                             line_score: Dict[str, int]) -> str:
    indent = line.coords.left - col.coords.left
    indent_frac = indent / col.coords.width
    if line.parent is not None:
        for tr_type in ['attendance', 'date']:
            if tr_type in line.parent.type:
                # print('using type', tr_type)
                return tr_type

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
            return 'oara_mid'
    elif len(line.text) > 10:
        return 'para_mid'
    else:
        print('unknown:', line.coords.box, len(line.text), indent_frac, line.text)
        return 'unknown'


def read_csv(csv_file: str) -> Generator[Dict[str, any], None, None]:
    with open(csv_file, 'rt') as fh:
        header_line = next(fh)
        headers = header_line.strip().replace('"', '').split('\t')
        # print(headers)
        # print(len(headers))
        for line in fh:
            row = line.strip().split('\t')
            clean_row = []
            for cell in row:
                if cell.startswith('"') and cell.endswith('"'):
                    cell = cell[1:-1]
                clean_row.append(cell)
            if len(clean_row) == 1:
                continue
            # print(clean_row)
            # print(len(clean_row))
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


def split_ground_truth_data(gt_data: List[Dict[str, any]],
                            random_seed: int = 8643) -> Tuple[List[Dict[str, any]],
                                                              List[Dict[str, any]],
                                                              List[Dict[str, any]]]:
    total = len(gt_data)
    if random_seed is not None:
        print('using random_seed:', random_seed)
        random.seed(random_seed)
    sample_data= random.sample(gt_data, len(gt_data))
    chunk_size = int(total / 10)
    test_data = sample_data[:chunk_size]
    validate_data = sample_data[chunk_size:2*chunk_size]
    train_data = sample_data[2*chunk_size:]

    if len(test_data + validate_data + train_data) != len(gt_data):
        raise IndexError('Invalid split of ground truth data')

    return train_data, validate_data, test_data


def read_ground_truth_data(line_class_files: Union[str, List[str]]) -> List[Dict[str, any]]:
    train_data = []
    found = set()
    for line_class_file in line_class_files:
        for page_lines in read_page_lines(line_class_file):
            if page_lines[0]['page_id'] in found:
                continue
            for line in page_lines:
                # print(line['page_id'])
                pass
            checked = [line for line in page_lines if line['checked'] == '1']
            if len(checked) != len(page_lines):
                # print('LAST CHECKED PAGE ID', page_lines[0]['page_id'])
                # print(len(checked), len(page_lines))
                break
            # print(f"adding page {page_lines[0]['page_id']} to training data")
            train_data.append({'page_id': page_lines[0]['page_id'], 'lines': page_lines})
            found.add(page_lines[0]['page_id'])
    print('number of training pages:', len(train_data))
    return train_data


def get_overlap_lines(gt_page_lines: List[pdm.PageXMLTextLine],
                      page_lines: List[pdm.PageXMLTextLine],
                      debug: int = 0) -> List[Tuple[pdm.PageXMLTextLine, pdm.PageXMLTextLine]]:
    line_pairs = []
    gt_paired = set()
    page_paired = set()
    for gt_page_line in gt_page_lines:
        for page_line in page_lines:
            if pdm.is_horizontally_overlapping(gt_page_line, page_line, threshold=0.5) is False:
                continue
            if pdm.is_vertically_overlapping(gt_page_line, page_line, threshold=0.5) is False:
                continue
            if gt_page_line.text is None or page_line.text is None:
                continue
            if abs(len(gt_page_line.text) - len(page_line.text)) > 18:
                # print('GT_LINE:', gt_page_line.id, gt_page_line.text)
                # print('PAGE_LINE:', page_line.id, page_line.text)
                continue
            if distance(gt_page_line.text, page_line.text) > 18:
                # print('GT_LINE:', gt_page_line.id, gt_page_line.text)
                # print('PAGE_LINE:', page_line.id, page_line.text)
                # print('\t', distance(gt_page_line.text, page_line.text))
                continue
            if debug > 0:
                if gt_page_line in gt_paired:
                    print('DOUBLE GT LINE')
                    print('\t', gt_page_line.text)
                if page_line in page_paired:
                    print('DOUBLE PAGE LINE')
                    print('\t', page_line.text)
            line_pairs.append((gt_page_line, page_line))
            gt_paired.add(gt_page_line)
            page_paired.add(page_line)
    for gt_page_line in gt_page_lines:
        if debug > 0:
            if gt_page_line not in gt_paired:
                print('GT UNPAIRED:', gt_page_line.id)
                print('\t', gt_page_line.text)
    for page_line in page_lines:
        if debug > 0:
            if page_line not in page_paired:
                print('PAGE UNPAIRED:', page_line.id)
                print(doc_id_to_iiif_url(page_line.id))
                print('\t', page_line.text)
    print(len(line_pairs))
    return line_pairs


def read_page_json(gt_page_json_file):
    with gzip.open(gt_page_json_file, 'rt') as fh:
        gt_pages_json = [json.loads(line.strip()) for line in fh]
        gt_pages = [json_to_pagexml_page(page_json) for page_json in gt_pages_json]
    return gt_pages


def load_ground_truth():
    gt_dir = '../../ground_truth/line_classification'
    charset_file = os.path.join(gt_dir, 'republic_charset.pcl')
    line_class_set_file = os.path.join(gt_dir, 'republic_line_class_set.pcl')
    line_class_csv_marijn = os.path.join(gt_dir, 'htr_classified_lines_marijn.csv')
    line_class_csv_rosalie = os.path.join(gt_dir, 'htr_classified_lines_rosalie.csv')
    gt_page_data = read_ground_truth_data([line_class_csv_marijn, line_class_csv_rosalie])

    gt_page_json_file = f'{gt_dir}/htr_page_json.jsonl.gz'
    gt_pages = read_page_json(gt_page_json_file)

    class_to_ix = read_class_set_mapping(line_class_set_file)
    char_to_ix = read_class_set_mapping(charset_file)
    gt_page_ids = [page['page_id'] for page in gt_page_data]
    gt_line_ids = [line['line_id'] for page in gt_page_data for line in page['lines']]
    gt_line_page_map = {line['line_id']: page['page_id'] for page in gt_page_data for line in page['lines']}
    return {
        'gt_page_data': gt_page_data,
        'gt_pages': gt_pages,
        'char_to_ix': char_to_ix,
        'class_to_ix': class_to_ix,
        'gt_page_ids': gt_page_ids,
        'gt_line_ids': gt_line_ids,
        'gt_line_page_map': gt_line_page_map
    }
