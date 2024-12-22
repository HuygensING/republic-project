
@include "provenance"
@include "edit-distance"
@include "simple-levenshtein"

BEGIN { FS=OFS="\t"
    provenance::field = 5
    ENDINGS = "$" }

BEGIN {
    while (1==getline <"loc-variants.tsv") {
        for (i=2;i<=NF;i++) direct_keys[$i] = $1
    }
    close("loc-variants.tsv")
}

# the header line
FNR == 1 {
    if (NF>8) print
    else print $0, "match", "categories", "orig_tag_text"
    next }

function match_keywords_fuzzily() {
    delete fuzz_results
    delete fuzz_matches
    split($5, segments, /[^a-z']+/, seps)
    fuzzy::search(segments, seps, fuzz_results, fuzz_matches)
}
function remove_keywords_fuzzily() {
    # note: provenance must be added by the caller
    for (i in fuzz_matches) if (fuzz_results[i] != "NOMATCH") {
        sub(fuzz_matches[i], "-", $5)
    }
    gsub(/^[- ]+|[- ]+$/, "", $5)
    gsub(/ +- +[- ]*/, "", $5)
    gsub(/ [- ]+/, " ", $5)
}

# a direct match at the end of every step
function no_direct_match(step) {
    if ($5 in direct_keys) {
        if (step) totals[step]++
        $9 = direct_keys[$5]
        match_counts[$9OFS$5]++
        provenance::write($5, "literal match: "$5, "true", "assign entity: "$9)
        print $0
        next
    } else return 1
}

END {
    for (step in totals) printf "Total matches in step (%s): %d\n", step, totals[step] >"/dev/stderr"
    if (MATCH_COUNTS) for (k in match_counts) print k, match_counts[k] >MATCH_COUNTS
}
