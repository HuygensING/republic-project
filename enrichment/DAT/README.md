
# Resolving date references

The main logic for processing dates is contained in
`enrichment/DAT/process-dates.awk`;
regular expressions for matching numbers and month names are listed in
`enrichment/criteria/DAT/date_regexes.tsv`.

The regular expressions in the latter file are used in a two-step process:
first, a list of matches is made, from which the most distinctive and popular
are selected for a second matching based on edit distance.
The idea behind this construction is finding all _unintended_ deviations
(through fuzzy matching) of all _intended_ variants (described by regexes).

Most of the first part `process-dates.awk` script is devoted to
either preparing the date references for this fuzzy matching step
or repairing resulting unwanted outcomes.
Roman numerals are also resolved here,
as those would not benefit from fuzzy matching.

The second part of `process-dates.awk` concerns the resolution
of (relative) date references to actual dates.
Dates are considered relative to the last resolved date in the same resolution.





