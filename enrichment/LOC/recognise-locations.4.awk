
@include "recognise-locations-base"

# In the final step, try and match place names to unresolved location 
# references fuzzily.

BEGIN {
    PROVENANCE = "provenance.step4.tsv"
    REPORT = "matchreport.step4.tsv"
	MATCH_COUNTS = 0
    fuzzy::PARTIAL_CACHE = 0
    # category keywords
    while (1==getline <"../criteria/LOC/loc-fuzzy-variants.tsv") fuzzy::add_keyword($1, $2)
}

# pass through matches already made
$9 { print; next }

{
    match_keywords_fuzzily()
    for (i in fuzz_results) if (fuzz_results[i] != "NOMATCH") {
        $9 = ($9?$9";":"") fuzz_results[i]
    }
}

$9 { totals["fuzzy"]++; print; next }

{ totals["no matches"]++; print }

