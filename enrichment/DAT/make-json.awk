#!/usr/bin/env -S gawk -f

# USAGE gawk -f make-json.awk processed_dates.tsv date_provenance.tsv annotations-layer_DAT.tsv
#
#   processed_dates.tsv and date_provenance as produced by process-dates.awk

@include "tsv"
@include "provenance"

BEGIN {
    main_fmt = "{'reference':{'layer':'%s','inv':'%s','tag_text':'%s','resolution_id':'%s','paragraph_id':'%s','offset':%d,'end':%d,'tag_length':%d},\n'date':'%s',\n'provenance':%s}"
    gsub(/'/, "\"", main_fmt)
}

BEGIN { print "[" }
END { print "]" }

1 == ARGIND && $3 ~ /^1[0-9]{3}-[0-9]{2}-[0-9]{2}$/ {
    # results of the date recognition step
    date[FNR+1]=$3
}

2 == ARGIND {
    # read the decision log for the provenance field
    if (!($2 in date)) next
    prov[$2] = provenance::append_decision(prov[$2], $3, $4, $5, $6)
}


3 == ARGIND {
    # read the input again and write out recognised lines
    if (!(FNR in date)) next
    p = provenance::make_record("annotations_layer_DAT.tsv#"(FNR-1), "DAT-annotations.json#"(++outnr), "", prov[FNR])
    printf (nofirst?",\n":"") main_fmt, $1, $2, $5, $3, $4, $6, $7, $8, date[FNR], p
    nofirst=1
}

