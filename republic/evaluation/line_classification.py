import re

import republic.model.physical_document_model as pdm


def get_marginalia_regions(doc):
    if isinstance(doc, pdm.PageXMLPage):
        trs = doc.text_regions + [tr for col in doc.columns for tr in col.text_regions]
    elif isinstance(doc, pdm.PageXMLScan) or isinstance(doc, pdm.PageXMLColumn):
        trs = []
        for tr in doc.text_regions:
            if len(tr.text_regions) > 0:
                trs.extend(tr.text_regions)
            else:
                trs.append(tr)
    else:
        return []
    return [tr for tr in trs if is_marginalia_text_region(tr)]


def is_marginalia_text_region(doc):
    if isinstance(doc, pdm.PageXMLTextRegion):
        return 'marginalia' in doc.type
    else:
        return None


def is_marginalia_column(doc):
    if isinstance(doc, pdm.PageXMLColumn):
        return len(get_marginalia_regions(doc)) > 0
    else:
        return None


def get_marginalia_columns(doc):
    if isinstance(doc, pdm.PageXMLPage):
        return [col for col in doc.columns if is_marginalia_column(doc)]
    else:
        return []


def is_noise_line(line, col):
    if line.text is None:
        return True
    indent = line.coords.left - col.coords.left
    indent_frac = indent / col.coords.width
    return len(line.text) < 4 and indent_frac > 0.8


def is_insert_line(line, col):
    if line.text is None:
        return True
    indent = line.coords.left - col.coords.left
    indent_frac = indent / col.coords.width
    if len(line.text) < 4 and indent_frac > 0.8:
        return None
    return len(line.text) < 14 and indent_frac > 0.7


def get_col_line_base_dist(col):
    lines = [line for tr in col.text_regions for line in sorted(tr.lines)]
    # print('pre num lines', len(lines))
    # for line in lines:
    #    print(is_noise_line(line, col), line.text)
    special_lines = [line for line in sorted(lines) if is_noise_line(line, col) or is_insert_line(line, col)]
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


def classify_line(line, col, base_dist):
    indent = line.coords.left - col.coords.left
    indent_frac = indent / col.coords.width
    # print(line.coords.left, col.coords.left, indent, indent_frac, '\t\t', len(line.text), line.text)
    if line.text is None:
        return 'empty'
    if len(line.text) < 4 and indent_frac > 0.8:
        return 'noise'
    elif len(line.text) < 14 and indent_frac > 0.7:
        return 'insert'
    if indent_frac < 0.10:
        if len(line.text) < 3:
            return 'noise'
        if re.search(r'^[A-Z]\w+ den \w+en. [A-Z]', line.text):
            return 'date'
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


def read_csv(csv_file):
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


def read_page_lines(csv_file):
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


def read_training_data(line_class_csv):
    class_to_ix = {}
    train_data = []
    for page_lines in read_page_lines(line_class_csv):
        for line in page_lines:
            # print(line['page_id'])
            if line['line_class'] not in class_to_ix:
                class_to_ix[line['line_class']] = len(class_to_ix)
            pass
        checked = [line for line in page_lines if line['checked'] == '1']
        if len(checked) != len(page_lines):
            break
        # print(f"adding page {page_lines[0]['page_id']} to training data")
        train_data.append({'page_id': page_lines[0]['page_id'], 'lines': page_lines})
    print('number of training pages:', len(train_data))
    return train_data, class_to_ix
