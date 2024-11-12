
# SUMMARY
#
# The purpose of this gawk library is keeping track of edits made. Every log 
# entry consists of four tab-separated parts:
#
#   source          the text operated on
#   criterium       the criterium or test applied
#   evaluation      the result (match) of the test
#   conclusion      a description of the operation
#
# The variable PROVENANCE should hold the location of the log file.
#
# The variable provenance::field holds the string field number (default 0, i.e. the entire line).
#
# INTERFACE
#
#   write(source, criterium, evaluation, conclusion)
#
#       Primitive function for writing a log entry.
#
#   replace(pat, repl, conclusion)
#   replace1(pat, repl, conclusion)
#
#       Perform a (repeated) gensub operation on $0 and log on a match. Returns 
#       number of replacements made.
#
#   start_edit(); ...; commit_edit(criterium);
#
#       Write a log entry if $0 has changed. commit_edit() implies a new 
#       start_edit().

@namespace "provenance"

BEGIN { field = 0 }

function write(source, criterium, evaluation, conclusion) {
    print FILENAME, FNR, source, criterium, evaluation, conclusion >PROVENANCE }

function replace(pat, repl, conclusion,    count,    matched) {
    if (!count) count = "g"
    if (!conclusion) conclusion = "regex-replacement"
    if (match($field, pat)) {
        matched = substr($field, RSTART, RLENGTH)
        if (matched!=repl) write($field, pat, matched, conclusion": "repl)
        $field = awk::gensub(pat, repl, count, $field)
        return 1
    } return 0 }

function replace1(pat, repl, conclusion,    nr) {
    return replace(pat, repl, conclusion, 1) }

function start_edit() {
    before_src = $field }

function commit_edit(criterium) {
    if (before_src != $field)
        write(before_src, criterium, $field, "(edited as shown)")
    before_src = $field }

