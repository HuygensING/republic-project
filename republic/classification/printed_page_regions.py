import re
from typing import List

import pagexml.model.physical_document_model as pdm

from republic.helper.pagexml_helper import make_new_tr
from republic.parser.pagexml.generic_pagexml_parser import copy_page


def is_left_page_number_line(line: pdm.PageXMLTextLine, page: pdm.PageXMLPage) -> bool:
    """Check if line contains the page number of a left-side (verso) page"""
    if page.metadata['page_num'] % 2 == 1:
        return False
    if line.baseline.left < 1000:
        return False
    if line.baseline.right > 1650:
        return False
    return True


def is_right_page_number_line(line: pdm.PageXMLTextLine, page: pdm.PageXMLPage) -> bool:
    """Check if line contains the page number of a right-side (recto) page"""
    if page.metadata['page_num'] % 2 == 0:
        return False
    if line.baseline.left < 3100:
        return False
    if line.baseline.right > 3700:
        return False
    return True


def is_page_number_line(line: pdm.PageXMLTextLine, page: pdm.PageXMLPage) -> bool:
    """Check if line contains the page number of a page"""
    if line.text is None:
        return False
    if len(line.text) > 10:
        return False
    if line.coords.top > 600:
        return False
    if not is_left_page_number_line(line, page) and not is_right_page_number_line(line, page):
        # lines not centre-aligned
        return False
    if re.search(r"\d+", line.text):
        return True
    if line.text.startswith('(') or line.text.endswith(')'):
        return True
    # print(page.metadata['page_num'], page.metadata['page_num'] % 2, mbs(line), line.text)
    return False


def is_date_header_line_left(line: pdm.PageXMLTextLine, page: pdm.PageXMLPage) -> bool:
    if page.metadata['page_num'] % 2 == 1:
        return False
    if line.baseline.left > 700:
        return False
    if line.baseline.right > 1000:
        return False
    return True


def is_date_header_line_right(line: pdm.PageXMLTextLine, page: pdm.PageXMLPage) -> bool:
    if page.metadata['page_num'] % 2 == 0:
        return False
    if line.baseline.left < 3700:
        return False
    if line.baseline.right < 4000:
        return False
    return True


def is_date_header_line(line: pdm.PageXMLTextLine, page: pdm.PageXMLPage) -> bool:
    if line.text is None:
        return False
    if len(line.text) < 6:
        return False
    if len(line.text) > 22:
        return False
    if is_date_header_line_left(line, page) or is_date_header_line_right(line, page):
        if re.search(r"\w+\W*\d+.*?\w+", line.text):
            return True
        # print(f'no date_header, no numbers: {line.text}')
        return False
    # print(page.metadata['page_num'], page.metadata['page_num'] % 2, mbs(line), line.text)
    return False


def is_header_line(line: pdm.PageXMLTextLine, page: pdm.PageXMLPage) -> bool:
    if line.coords.top > 450:
        return False
    if line.text is not None and len(line.text) > 30:
        return False
    if is_page_number_line(line, page):
        return True
    if is_date_header_line(line, page):
        return True
    return False


def remove_line(tr: pdm.PageXMLTextRegion, line: pdm.PageXMLTextLine):
    tr.lines.remove(line)
    if len(tr.lines) > 0:
        tr.coords = pdm.parse_derived_coords(tr.lines)
        tr.set_derived_id(tr.metadata['scan_id'])
    return None


def is_catch_word_left_page(line: pdm.PageXMLTextLine, page: pdm.PageXMLPage) -> bool:
    if page.metadata['page_num'] % 2 == 1:
        return False
    if line.baseline.left < 1800:
        return False
    return is_catch_word(line, page)


def is_catch_word_right_page(line: pdm.PageXMLTextLine, page: pdm.PageXMLPage) -> bool:
    if page.metadata['page_num'] % 2 == 0:
        return False
    if line.baseline.left < 4000:
        return False
    return is_catch_word(line, page)


def has_text_lines_below(line: pdm.PageXMLTextLine, page: pdm.PageXMLPage) -> bool:
    lines_below = [lb for lb in page.get_lines() if lb.is_below(line)]
    if any([lb.text is not None and len(lb.text) > 2 for lb in lines_below]):
        # for l in lines_below:
        #     print(f"{page.metadata['page_num']} LINE: {mbs(line)}\t{line.text}")
        #     print(f"BELOW: {mbs(l)}\t{l.text}")

        # print([l.text for l in lines_below])
        return True
    return False


def is_catch_word(line: pdm.PageXMLTextLine, page: pdm.PageXMLPage) -> bool:
    if line.text is None:
        return False
    if len(line.text) > 20:
        # catch word can't be very long
        return False
    if ' ' in line.text:
        # catch word has no white space
        return False
    if line.baseline.bottom < 3000:
        return False
    if has_text_lines_below(line, page):
        return False
    return True


def is_catch_word_line(line: pdm.PageXMLTextLine, page: pdm.PageXMLPage) -> bool:
    return is_catch_word_left_page(line, page) or is_catch_word_right_page(line, page)


def is_fold_number_line(line: pdm.PageXMLTextLine, page: pdm.PageXMLPage) -> bool:
    if page.metadata['page_num'] % 2 == 0:
        return False
    if line.text is None:
        return False
    if line.baseline.bottom < 3000:
        return False
    if line.coords.left < 3700:
        return False
    if line.coords.right > 4100:
        return False
    if len(line.text) > 5:
        return False
    if has_text_lines_below(line, page):
        return False
    if re.search(r"\d{1,2} ?[A-Z]", line.text):
        return True
    if re.match(r"([A-Z]|\d{1,2})", line.text):
        return True
    # print(page.metadata['page_num'], page.metadata['page_num'] % 2, mbs(line), line.text)
    return False


def classify_page_margins(page, title_page_nums: List[int] = None, remove_empty_lines: bool = False, debug: int = 0):
    """Classify text lines in the margins of a printed page.
    Classes include date headers, page numbers, catch words and fold numbers."""
    page = copy_page(page)
    header_lines = []
    footer_lines = []
    title_lines = []
    cols = [col for col in page.columns]
    for col in cols:
        trs = [tr for tr in sorted(col.text_regions, key=lambda t: t.coords.top)]
        for tr in trs:
            lines = sorted(tr.lines, key=lambda l: l.baseline.bottom)
            for line in lines:
                # print("CHECKING LINE", line.text)
                if remove_empty_lines and line.text is None:
                    remove_line(tr, line)
                    continue
                if is_page_number_line(line, page):
                    line.metadata['line_class'] = 'page_number'
                    header_lines.append(line)
                    remove_line(tr, line)
                    continue
                if is_date_header_line(line, page):
                    line.metadata['line_class'] = 'date_header'
                    header_lines.append(line)
                    remove_line(tr, line)
                    continue
                if is_catch_word_line(line, page):
                    line.metadata['line_class'] = 'catch_word'
                    footer_lines.append(line)
                    remove_line(tr, line)
                    continue
                if is_fold_number_line(line, page):
                    line.metadata['line_class'] = 'fold_number'
                    footer_lines.append(line)
                    remove_line(tr, line)
                    continue
                if is_title_line(line, page, title_page_nums):
                    line.metadata['line_class'] = 'title'
                    title_lines.append(line)
                    remove_line(tr, line)
                    continue
                # print("\tNO MARGIN LINE")
            if len(tr.lines) == 0:
                # print('removing text region')
                col.text_regions.remove(tr)
        if len(col.text_regions) == 0:
            page.columns.remove(col)
    if len(header_lines) > 0:
        header_tr = make_margin_tr(page, header_lines, 'header', debug=debug)
        page.extra.append(header_tr)
    if len(footer_lines) > 0:
        footer_tr = make_margin_tr(page, footer_lines, 'footer', debug=debug)
        page.extra.append(footer_tr)
    if len(title_lines) > 0:
        title_tr = make_margin_tr(page, title_lines, 'title', debug=debug)
        page.extra.append(title_tr)
    return page


def is_title_line(line: pdm.PageXMLTextLine, page: pdm.PageXMLPage,
                  title_page_nums: List[int] = None, debug: int = 0) -> bool:
    if title_page_nums is None:
        if debug > 0:
            print('printed_page_regions.is_title_line - False - no title page nums given')
        return False
    if page.metadata['page_num'] not in title_page_nums:
        if debug > 0:
            print('printed_page_regions.is_title_line - False - page is no title page')
        # print('NO TITLE PAGE ')
        return False
    if line.baseline.bottom < 1500:
        if debug > 0:
            print('printed_page_regions.is_title_line - True - line.baseline.bottom < 1500')
        # print('HIGH TITLE', line.text)
        return True
    if line.baseline.top > 1800:
        if debug > 0:
            print('printed_page_regions.is_title_line - False - line.baseline.top > 1800')
        # print('LOW NON TITLE', line.text)
        return False
    main_text_left = min([col.coords.left for col in page.columns])
    main_text_right = max([col.coords.right for col in page.columns])
    left_indent = line.baseline.left - main_text_left
    right_indent = main_text_right - line.baseline.right
    if min([left_indent, right_indent]) > 200:
        if debug > 0:
            print('printed_page_regions.is_title_line - True - minimum of left_indent and right_indent > 200')
        return True
    indent_ratio = min([left_indent, right_indent]) / max([left_indent, right_indent])
    if debug > 0:
        print('printed_page_regions.is_title_line')
        print(f"\tmain_text_left: {main_text_left}\tmain_text_right: {main_text_right}")
        print(f"\tleft_indent: {left_indent}\tright_indent: {right_indent}")
        print(f"\tindent_ratio: {indent_ratio}")
    if indent_ratio < 0.9:
        if debug > 0:
            print('printed_page_regions.is_title_line - False - True - indent_ratio > 0.9')
        # print('NON TITLE:', line.baseline.bottom, line.text)
        return False
    return True


def make_margin_tr(page, margin_lines, tr_type, debug: int = 0):
    parent_tr = margin_lines[0].parent
    if isinstance(parent_tr, pdm.PageXMLTextRegion):
        margin_tr = make_new_tr(margin_lines, parent_tr)
        margin_tr.remove_type(['resolutions', 'main'])
        margin_tr.add_type(['margin', 'extra', tr_type])
        if debug > 1:
            print('adding margin_tr with types', margin_tr.type)
    else:
        print(f"classification.printed_page_regions.make_margin_tr - page {page.id}")
        raise TypeError(f"Parent of PageXMLTextLine must be a PageXMLTextRegion, not {type(parent_tr)}")
    return margin_tr
