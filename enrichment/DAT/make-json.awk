#!/usr/bin/env -S gawk -f

# USAGE gawk -f make-json.awk processed_dates.tsv date_provenance.tsv annotations-layer_DAT.tsv
#
#   processed_dates.tsv and date_provenance as produced by process-dates.awk

@include "tsv"

BEGIN {
    main_fmt = "{'reference':{'layer':'%s','inv':'%s','tag_text':'%s','resolution_id':'%s','paragraph_id':'%s','offset':%d,'end':%d,'tag_length':%d},\n'date':'%s',\n'provenance':[%s]}"
    gsub(/'/, "\"", main_fmt)
    prov_fmt = "{'source':'%s','criterium':'%s','outcome':'%s','conclusion':'%s'}"
    gsub(/'/, "\"", prov_fmt)
}

BEGIN { print "[" }
END { print "]" }

1 == ARGIND && $3 ~ /^1[0-9]{3}-[0-9]{2}-[0-9]{2}$/ {
    date[FNR+1]=$3
}

2 == ARGIND {
    if (!($2 in date)) next
    prov[$2] = prov[$2] (prov[$2]?",\n":"") sprintf(prov_fmt, $3, $4, $5, $6)
}

3 == ARGIND {
    if (!(FNR in date)) next
    printf (nofirst?",\n":"") main_fmt, $1, $2, $5, $3, $4, $6, $7, $8, date[FNR], prov[FNR]
    nofirst=1
}

