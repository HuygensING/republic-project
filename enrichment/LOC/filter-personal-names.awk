#!/usr/bin/env -S gawk -f

# USAGE gawk -f filter-personal-names.awk personal-names.tsv LOC-annotations.tsv

BEGIN { FS=OFS="\t" }

NR==FNR { nam[$1][$2] = $3; next }

{
    if ($4 in nam)
    for (s in nam[$4]) {
        s = +s; e = +nam[$4][s]
        if (s > $7 || e < $6) continue
        next
    }

}

1 # prints
