#!/usr/bin/env -S gawk -f

# USAGE: gawk -f improve-ner-output.awk ner-output.tsv > enriched-output.tsv
#
# OPTIONS
#
#   FIELDNR=5       Field number of the field to operate on
#   NOFUZZY=1       Disable the fuzzy matching list
#

BEGIN { FS=OFS="\t" }
BEGIN { FIELDNR=5 }

@include "provenance"
@include "edit-distance"

BEGIN { # read data files
    while (1==getline <"../criteria/common/split.tsv") {
        if(/^[ \t]*(#|$)/) continue
        splits["\\<"$1"\\>"] = $2 }
    while (1==getline <"../criteria/common/afkortingen.tsv") {
        if(/^[ \t]*(#|$)/) continue
        for (i=2;i<=NF;i++) abbrevs["\\<"$i"\\>[.:]?"] = $1 }
    while (1==getline <"../criteria/common/simplify.tsv") {
        if(/^[ \t]*(#|$)/) continue
        gsub(/\\b/, "\\y") # gawk idiosyncracy
        simpl[$1] = $2 }
    while (1==getline <"../criteria/common/spelling-regexes.tsv") {
        if(/^[ \t]*(#|$)/) continue
        gsub(/\\b/, "\\y") # gawk idiosyncracy
        spellings[$1] = $2 }
    while (1==getline <"../criteria/common/fuzzy-corrections.tsv") {
        if(/^[ \t]*(#|$)/) continue
        for(i=1;i<=NF;i++) fuzzy::add_keyword($1, $i)
    }
    REPORT = "spelling-report.tsv"
}

BEGINFILE { PROVENANCE = FILENAME
    gsub(/.*[/]|[.]tsv$/, "", PROVENANCE)
    PROVENANCE = PROVENANCE ".provenance.tsv" }

FNR==1 { print $0, "improved_tag_text"; next }

{
    store0 = $0; $0 = $FIELDNR # tag_text
    IGNORECASE=1
    for (p in splits) provenance::replace(p, splits[p], "split words")
    IGNORECASE=0
    for (p in abbrevs) provenance::replace(p, abbrevs[p], "write out abbreviation")
    for (p in simpl) provenance::replace(p, simpl[p], "simplify")
    for (p in spellings) provenance::replace(p, spellings[p], "harmonise spelling")
    gsub(/  +/, " ", $0)
    if (NOFUZZY) {
        print store0, $0
    } else {
        split($0, segments, /[^A-Za-z:-]+/, seps)
        print store0, fuzzy::replace_matches(segments, seps)
    }
}

