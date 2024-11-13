
@include "recognise-locations-base"

BEGIN {
    PROVENANCE = "provenance.step3.tsv"
    REPORT = "matchreport.step3.tsv"
    # category keywords
    while (1==getline <"../criteria/LOC/loc-classwords.tsv") {
        for (i=3;i<=NF;i++) fuzzy::add_keyword($2 ? $2 : $1, $i)
    }
}

# pass through matches already made
$9 { print; next }

match($5, /(.*[^ ]) (in|op) (.*)/, m) {
    if (m[1] in direct_keys) make_direct_match(m[1], "X in Y")
    else try_without_category_word(m[1], "CAT X in Y")
    next_if_possible() }

match($5, /(.*[^ ]) en (.*)/, m) {
    if (m[1] in direct_keys) make_direct_match(m[1], "X ende Y")
    else try_without_category_word(m[1], "CAT X ende Y")
    if (m[2] in direct_keys) make_direct_match(m[2], "X ende Y")
    else try_without_category_word(m[2], "CAT X ende Y")
    if ($9 !~ /;/) $9 = "" # only apply if both match
    next_if_possible() }

match($5, /(.+) ([^ ]+) (en|ofte) (.*)/, m) {
    if (m[1] in direct_keys) make_direct_match(m[1], "X ende Y ende Z")
    else try_without_category_word(m[1], "CAT X ende Y ende Z")
    if (m[2] in direct_keys) make_direct_match(m[2], "X ende Y ende Z")
    if (m[4] in direct_keys) make_direct_match(m[4], "X ende Y ende Z")
    else try_without_category_word(m[4], "CAT X ende Y ende Z")
    if ($9 !~ /;/) $9 = "" # only apply if at least two match
    next_if_possible() }

{ print }

function next_if_possible() { if ($9) { print; next } }

function try_without_category_word(key, step,    save5) {
    save5 = $5; $5 = key
    match_keywords_fuzzily()
    remove_keywords_fuzzily()
    key = $5; $5 = save5
    sub(/^(van|in|en|de) +/, "", key)
    if (key in direct_keys) make_direct_match(key, step)
}

function make_direct_match(key, step) {
    totals[step]++
    $9 = ($9?$9";":"") direct_keys[key]
    provenance::write(key, "literal match: "key, "true", "assign entity: "$9)
}

