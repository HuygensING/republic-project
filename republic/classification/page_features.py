import re
from string import punctuation
from typing import Dict, List, Set, Tuple, Union

import pagexml.model.physical_document_model as pdm
import torch

# import republic.model.physical_document_model as pdm
from republic.helper.text_helper import SkipgramSimilarity
from republic.model.republic_date_phrase_model import week_day_names
from republic.model.republic_date_phrase_model import month_names_early, month_names_late


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


def page_to_feature_sequences(page_lines, char_to_ix, class_to_ix,
                              line_fixed_length=100):
    spatial_sequence = []
    char_sequence = []
    class_sequence = []
    sentence_sequence = []
    for line in page_lines:
        spatial_features = [float(line[spatial_field]) for spatial_field in SPATIAL_FIELDS]
        line_text = line['text'] if 'text' in line else line['line_text']
        if line_text is None:
            line_text = ''
        if len(line_text) > line_fixed_length:
            # DIRTY HACK
            # TODO: increase fixed length
            line_text = line_text[:line_fixed_length]
        padding_size = line_fixed_length - len(line_text)
        text = line_text
        text += ' ' * padding_size
        for c in text:
            if c not in char_to_ix:
                print(line)
        char_features = [char_to_ix[c] if c in char_to_ix else char_to_ix['<unk>'] for c in text]
        spatial_sequence.append(spatial_features)
        char_sequence.append(char_features)
        if 'line_class' in line:
            class_sequence.append(class_to_ix[line['line_class']])
        sent_text = ' ' if line_text is None or line_text == '' else line_text
        sentence_sequence.append(sent_text)

    spatial_tensor = torch.tensor(spatial_sequence, dtype=torch.float32)
    char_tensor = torch.tensor(char_sequence)
    class_tensor = torch.tensor(class_sequence) if len(class_sequence) > 0 else None
    # text_tensor = torch.tensor(sentence_sequence)
    return {
        'spatial': spatial_tensor,
        'char': char_tensor,
        'class': class_tensor,
        'sentence': sentence_sequence
    }


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
    weekdays = set([week_day_name for name_set in week_day_names for week_day_name in week_day_names[name_set]])
    # weekdays = set(week_day_names['printed_early'] + week_day_names['printed_late'] + week_day_names['handwritten'])
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


def is_noise_line(line: pdm.PageXMLTextLine, tr: pdm.PageXMLTextRegion) -> bool:
    if line.text is None:
        return True
    if line.coords.width == 0 or tr.coords.width == 0:
        return True
    indent = line.coords.left - tr.coords.left
    indent_frac = indent / tr.coords.width
    return len(line.text) < 4 and indent_frac > 0.8


def is_insert_line(line: pdm.PageXMLTextLine, tr: pdm.PageXMLTextRegion) -> bool:
    if line.text is None:
        return True
    indent = line.coords.left - tr.coords.left
    indent_frac = indent / tr.coords.width
    if len(line.text) < 4 and indent_frac > 0.8:
        return False
    return len(line.text) < 14 and indent_frac > 0.7


def get_line_base_dist(line1: pdm.PageXMLTextLine, line2: pdm.PageXMLTextLine) -> int:
    left1 = sorted(line1.baseline.points)[0]
    left2 = sorted(line2.baseline.points)[0]
    return abs(left1[1] - left2[1])


def get_lines_base_dist(lines: List[pdm.PageXMLTextLine], tr: pdm.PageXMLTextRegion) -> Dict[str, any]:
    # lines = sorted(tr.lines + [line for tr in tr.text_regions for line in tr.lines])
    # print('pre num lines', len(lines))
    # for line in lines:
    #    print(is_noise_line(line, tr), line.text)
    special_lines = [line for line in lines if is_noise_line(line, tr) or is_insert_line(line, tr)]
    base_dist = {}
    for curr_line in special_lines:
        indent = curr_line.coords.left - tr.coords.left
        indent_frac = indent / tr.coords.width if tr.coords.width > 0 else -1
        if is_noise_line(curr_line, tr):
            dist_to_prev = 0
            dist_to_next = 70
        elif is_insert_line(curr_line, tr):
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
        indent = curr_line.coords.left - tr.coords.left
        indent_frac = indent / tr.coords.width
        if li == 0:
            dist_to_prev = 2000
        else:
            prev_line = lines[li - 1]
            dist_to_prev = get_line_base_dist(prev_line, curr_line)
        if li == len(lines) - 1:
            dist_to_next = 2000
        else:
            next_line = lines[li + 1]
            dist_to_next = get_line_base_dist(curr_line, next_line)
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


def get_line_features(line, col, skip_sim: Dict[str, SkipgramSimilarity], base_dist) -> Dict[str, any]:
    lc = line.coords
    cc = col.coords
    line_score = get_line_text_features(line, skip_sim)
    left_base = sorted(line.baseline.points)[0]
    if 'dist_to_prev' not in base_dist:
        print(line.id, base_dist)
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
    trs = [tr for col in page.columns for tr in col.text_regions]
    trs.extend([tr for tr in page.extra if tr not in trs])
    trs.extend([tr for tr in page.text_regions if tr not in trs])
    for tr in trs:
        if 'marginalia' in tr.type:
            continue
        lines = [line for line in tr.get_lines()]
        base_dist = get_lines_base_dist(lines, tr)
        for line in sorted(tr.lines):
            doc = get_line_features(line, tr, skip_sim, base_dist=base_dist[line.id])
            rows.append(doc)
    for col in page.columns:
        trs = [tr for tr in col.text_regions if 'marginalia' not in tr.type]
        lines = [line for tr in trs for line in tr.lines]
        base_dist = get_lines_base_dist(lines, col)
        for tr in sorted(trs):
            for line in sorted(tr.lines):
                doc = get_line_features(line, col, skip_sim, base_dist[line.id])
                rows.append(doc)
    return rows


def make_line(line_dict: Dict[str, any]) -> pdm.PageXMLTextLine:
    x, y, w, h = [int(coord) for coord in line_dict['line_id'].split('-')[-4:]]
    points = [(x, y), (x, y + h), (x + w, y), (x + w, y + h)]
    coords = pdm.Coords(points)
    return pdm.PageXMLTextLine(doc_id=line_dict['line_id'], coords=coords, text=line_dict['line_text'])


def get_page_lines(page: pdm.PageXMLPage, gt_page_ids: Set[str]) -> List[pdm.PageXMLTextLine]:
    main_col = None
    max_words = 0
    for col in page.columns:
        if col.stats['words'] > max_words:
            max_words = col.stats['words']
            main_col = col
    if page.id in gt_page_ids:
        print(page.metadata['iiif_url'])
    all_trs = [tr for col in page.columns for tr in col.text_regions]
    print('number of textregions:', len(all_trs))
    main_trs = [tr for col in page.columns for tr in col.text_regions if is_marginalia_text_region(tr) is False]
    coords = pdm.parse_derived_coords(main_trs)
    col = pdm.PageXMLColumn(doc_id=main_col.id, text_regions=main_trs, coords=coords)
    return col.lines + [line for tr in col.text_regions for line in tr.lines]
