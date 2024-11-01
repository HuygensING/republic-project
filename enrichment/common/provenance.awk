
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

function write(source, criterium, evaluation, conclusion) {
    print FILENAME, FNR, source, criterium, evaluation, conclusion >PROVENANCE }

function replace(pat, repl, conclusion,    count,    matched) {
    if (!count) count = "g"
    if (!conclusion) conclusion = "regex-replacement"
    if (match($0, pat)) {
        matched = substr($0, RSTART, RLENGTH)
        if (matched!=repl) write($0, pat, matched, conclusion": "repl)
        $0 = awk::gensub(pat, repl, count)
        return 1
    } return 0 }

function replace1(pat, repl, conclusion,    nr) {
    return replace(pat, repl, conclusion, 1) }

function start_edit() {
    before_src = $0 }

function commit_edit(criterium) {
    if (before_src != $0)
        write(before_src, criterium, $0, "(edited as shown)")
    before_src = $0 }

