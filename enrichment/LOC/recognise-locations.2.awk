
@include "recognise-locations-base"

# In this second step, we try and simplify location references by removing 
# irrelevant words. On the resulting string, again, a direct match is 
# attempted.

BEGIN {
    PROVENANCE = "provenance.step2.tsv"
    REPORT = "matchreport.step2.tsv"
    TRESHOLD = 0.85 # be very conservative with the fuzzy matches
    while (1==getline <"../criteria/LOC/nonlocations.tsv") {
        if ($1=="Particle") continue
        fuzzy::add_keyword($1, $2)
    }
}

# pass through matches already made
$9 { print; next }

{
    provenance::start_edit()
    match_keywords_fuzzily()
    remove_keywords_fuzzily()
    provenance::commit_edit("remove nonlocation words (fuzzily)")
}

!$5 || $5 ~ /^die van / { # reference consists of nonlocations
    totals["dropped: no location"]++
    $9 = "NOMATCH"
    print
    next
}

# print unmatched lines
no_direct_match("nonlocations removed") { print }

