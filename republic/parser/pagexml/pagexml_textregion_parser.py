from typing import Union
import copy


def get_textregion_text(textregion):
    text = ''
    for line in textregion['lines']:
        if not 'text' in line or not line['text']:
            continue
        if line['text'][-1] in ['-']:
            text += line['text'][:-1]
        else:
            text += line['text'] + ' '
    return text


def stream_resolution_page_lines(pages: list) -> Union[None, iter]:
    """Iterate over list of pages and return a generator that yields individuals lines.
    Iterator iterates over columns and textregions.
    Assumption: lines are returned in reading order."""
    for page in sorted(pages, key=lambda x: x['metadata']['page_num']):
        merge = {}
        columns = copy.copy(page['columns'])
        for ci1, column1 in enumerate(columns):
            for ci2, column2 in enumerate(columns):
                if ci1 == ci2:
                    continue
                if column1['coords']['left'] >= column2['coords']['left'] and column1['coords']['right'] <= column2['coords']['right']:
                    # print(f'MERGE COLUMN {ci1} INTO COLUMN {ci2}')
                    merge[ci1] = ci2
        for merge_column in merge:
            # merge contained column in container column
            columns[merge[merge_column]]['textregions'] += columns[merge_column]['textregions']
        for ci, column in enumerate(columns):
            if ci in merge:
                # skip contained column
                continue
            # print('column coords:', column['coords'])
            lines = []
            for ti, textregion in enumerate(column['textregions']):
                # print('textregion coords:', textregion['coords'])
                if 'lines' not in textregion or not textregion['lines']:
                    continue
                for li, line in enumerate(textregion['lines']):
                    if not line['text']:
                        # skip non-text lines
                        continue
                    if line['coords']['left'] > textregion['coords']['left'] + 600:
                        # skip short lines that are bleed through from opposite side of page
                        # they are right aligned
                        continue
                    line = {
                        'id': page['metadata']['page_id'] + f'-col-{ci}-tr-{ti}-line-{li}',
                        'inventory_num': page['metadata']['inventory_num'],
                        'scan_id': page['metadata']['scan_id'],
                        'scan_num': page['metadata']['scan_num'],
                        'page_id': page['metadata']['page_id'],
                        'page_num': page['metadata']['page_num'],
                        'column_index': ci,
                        'column_id': page['metadata']['page_id'] + f'-col-{ci}',
                        'textregion_index': ti,
                        'textregion_id': page['metadata']['page_id'] + f'-col-{ci}-tr-{ti}',
                        'line_index': li,
                        'coords': line['coords'],
                        'text': line['text']
                    }
                    # page_num = page['metadata']['page_num']
                    # left_right = f"{line['coords']['left']} <-> {line['coords']['right']}"
                    # top_bottom = f"{line['coords']['top']} <-> {line['coords']['bottom']}"
                    # print(page_num, ci, ti, '\t', left_right, '\t', top_bottom, '\t', line['text'])
                    lines += [line]
            # sort lines to make sure they are in reading order (assuming column has single text column)
            # some columns split their text in sub columns, but for meeting date detection this is not an issue
            for line in sorted(lines, key=lambda x: x['coords']['bottom']):
                yield line
    return None



