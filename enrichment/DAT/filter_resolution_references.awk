#!/usr/bin/env -S gawk -f

# USAGE: gawk -f filter_resolution_references.awk RES-annots.tsv DAT-annots.tsv >filtered-DAT-annots.tsv
#
# only include dates that occur in a reference to another resolution

BEGIN { FS=OFS="\t"
    MARGIN = 5 # max distance between end-of-res-RES and DAT annotation
}

NR==FNR {
    ref[$4][$6] = +$7 # [paragraph_id][offset] = end
    next }

FNR==1 { print $0, "in_reference" }

$4 in ref {
    for (start in ref[$4]) {
        end = ref[$4][start]
        if (end > $6-MARGIN && end < $7+MARGIN) { print $0, 1; next }
    }
}

{ print $0, 0 }

