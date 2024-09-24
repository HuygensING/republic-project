
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
#       primitive function for writing a log entry
#
#   replace(pat, repl, conclusion)
#   replace1(pat, repl, conclusion)
#
#       perform a (g)sub operation and log on a match
#
#   start_edit(); ...; commit_edit(criterium);
#
#       write a log entry if $0 has changed. commit_edit() implies a new 
#       start_edit().

@namespace "provenance"

function write(source, criterium, evaluation, conclusion) {
    print FILENAME, FNR, source, criterium, evaluation, conclusion >PROVENANCE
}

function replace1(pat, repl, conclusion,    src) {
    if (match(source, pat)) {
        write($0, pat, substr(source, RSTART, RLENGTH), "regex: "conclusion)
        sub(pat, repl)
        return 1
    }
    return 0
}

function replace(pat, repl, conclusion) {
    while (replace1(pat, repl, conclusion)) { }
}

function start_edit() {
    before_src = $0
}

function commit_edit(criterium) {
    if (before_src != $0)
        write(before_src, criterium, $0, "(edited as shown)")
    before_src = $0
}

