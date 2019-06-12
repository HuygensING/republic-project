# REPUBLIC hOCR Parser

Pyhton code for parsing and extraction information from hOCR files of the Resolutions of the Dutch States General.

## Parsing REPBULIC hOCR Files

The scans of the printed RSG volumes have the following characteristics

- all scans:
  - have two pages per scan
  - have up to 4 columns per scan, 2 per page
  - full scan is around 4800 pixels wide, left page is up to pixel 2400, right page is from pixel 2400 (roughly)
- scans of index pages
  - have no page numbers
- scans of resolution pages
  - have page numbers (left-side page is even, right-side page is odd)

### Columns

The scans are normalized such that the columns are straight. The text width should be around 1000 pixels. Some columns are not cut out properly, resulting in columns that are either to small (some of the column text is missing), or too wide (the hOCR output contains partial texts from two columns)

### Index pages

- start of entry:
  - start left alignment
- end of entry:
  - end of line possibly before end of text column.
  - One or more page numbers


### Resolution pages

- header:
  - next top of page (less than 350 pixels from the top)
  - page has header with:
    - even numbered pages: date page_number year
    - odd numbered pages: year page_number date
  - columns have half of page header, e.g.:
    - even numbered pages:
      - first column: date left aligned and part of page_number right aligned
      - second column: part of page_number left aligned and year right aligned
    - odd numbered pages:
      - first column: year left aligned and part of page_number right aligned
      - second column: part of page_number left aligned and date right aligned



