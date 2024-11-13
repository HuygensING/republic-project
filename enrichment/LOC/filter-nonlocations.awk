#!/usr/bin/env -S gawk -f

@include "provenance"

BEGIN { FS=OFS="\t"
    PROVENANCE = "nonlocs.provenance.tsv" }

NR==FNR {
    for (i=2;i<=NF;i++) { kw[$i] = $1 }
    next }

FNR==1 { print $0, "reduced_text"; next }

{
    old0 = $0; $0 = $NF
    provenance::start_edit()
    for (n in kw) gsub("\\<"n"\\>", " - ")
    gsub(/ +- +(- +)*/, " ")
    gsub(/^ +| +$/, "")
    provenance::commit_edit("Remove irrelevant words")
    print old0, $0
}


