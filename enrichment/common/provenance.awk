
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

BEGIN {
    "date -u -Iseconds" | getline timestamp
    sub(/+00:00/, "Z", timestamp)
    "git rev-parse HEAD" | getline commit_id
    commit_url = "https://github.com/HuygensING/republic-project/commit/" commit_id
    # decision log format
    prov_fmt = "{'source':'%s','criterium':'%s','outcome':'%s','conclusion':'%s'}"
    gsub(/'/, "\"", prov_fmt)
}

function append_decision(cur, src, crit, outc, concl) {
    return (cur?cur",\n":"") sprintf(prov_fmt, src, crit, outc, concl) }

function make_record(in_file_nr, out_file_nr, entity_id, decisions) {
    return "{" \
        fld("source", "["qt(in_file_nr)"]")                                                       ","\
        fld("source_rel", "["qt("primary")"]")                                                    ","\
        fld("target", "["qt(out_file_nr)(entity_id?","qt("urn:republic:entity:"entity_id):"")"]") ","\
        fld("target_rel", "["qt("primary")(entity_id?","qt("primary"):"")"]")                     ","\
        fld("where", qt("https://annotation.republic-caf.diginfra.org/"))                         ","\
        fld("when", qt(timestamp)) "," fld("how", qt(commit_url))                                 ","\
        fld("why", qt("REPUBLIC Entity Enrichment"))                                              ","\
        qt("why_provenance_schema")": {" fld("format", qt("decision_log"))                        ","\
            qt("decisions")": [" decisions "] } }" }

function fld(n, s) { return qt(n)": "s }
function qt(s) { gsub(/"/, "\\\"", s); return "\""s"\"" }


