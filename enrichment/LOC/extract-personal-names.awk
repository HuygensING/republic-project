#!/usr/bin/env -S gawk -f

# USAGE gawk -f extract-personal-names.awk HOE-annotations.tsv PER-annotations.tsv

BEGIN { FS=OFS="\t" }

NR==FNR { hoe[$4][$6] = $7; next }

{
    if ($4 in hoe) {
        if ($4 in hoe && $7 == +hoe[$4][$6]) { } # name and attribution coincide (likely a title)
        else for (s in hoe[$4]) { s = +s
            e = +hoe[$4][s]
            if (s > $7 || e < $6) continue
            else if (s <= $6 && e >= $7) next
            else if (s > $6) { $7 = s; $5 = substr($5, 1, $7-$6) }
            else { $5 = substr($5, e-$6+1); $6 = e }
        }
    }
    print $4, $6, $7, $5
}

