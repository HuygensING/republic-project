
# USAGE: gawk -f recognise-locations.awk LOC-annotations.tsv

# In this first step, we do the following:
#   - recognise category keywords
#   - try direct matches with location keywords
#   - on unresolved references, simplify the string and try a direct match again

@include "recognise-locations-base"

BEGIN {
    PROVENANCE = "provenance.step1.tsv"
    REPORT = "matchreport.step1.tsv"
    MATCH_COUNTS = "match_counts.tsv"
    # category keywords
    while (1==getline <"../criteria/LOC/loc-classwords.tsv") {
        for (i=3;i<=NF;i++) fuzzy::add_keyword($2 ? $2 : $1, $i)
    }
    # simplification regexes
    i=0; while (1==getline <"../criteria/LOC/regex-simplification.tsv") {
        gsub(/\\b/, "\\y", $1) # gawk idiosyncracy
        simple_regexes[++i] = $1
        simple_subs[i] = $2
    }
}

{
    $5 = tolower($5)
    # assign categories to $10
    match_keywords_fuzzily()
    for (i in fuzz_results) if (fuzz_results[i] != "NOMATCH") $10 = ($10?$10"|":"") fuzz_results[i]
}

no_direct_match("immediate") {
    # try various spelling variation reductions
    provenance::start_edit()
    for (i in simple_regexes) {
        $5 = gensub(simple_regexes[i], simple_subs[i], "g", $5)
    }
    provenance::commit_edit("simplify string")
}

no_direct_match("simplified") {
    sub(/^[.:'] +/, "", $5)
    # try and remove class words for unmatched lines
    save5 = $5 # this is temporary
    match_keywords_fuzzily()
    for (i in fuzz_results) if (fuzz_results[i] != "NOMATCH" && $10 !~ fuzz_results[i]) $10 = ($10?$10"|":"") fuzz_results[i]
    remove_keywords_fuzzily()
    sub(/^(van|in|en|de) +/, "", $5)
}

# prints unmatched lines
no_direct_match("category removed") { $5 = save5; print }

