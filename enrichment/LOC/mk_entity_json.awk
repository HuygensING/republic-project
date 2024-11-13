#!/usr/bin/env -S gawk -f

BEGIN { FS="\t"; OFS=" "; print "[" }
FNR == 1 { next } # ignore header
FNR > 2 { print "," }
END { print "]" }

{
    res = "{ " field("id", $1)
    res = res ", " field("name", $2)
    if ($3) res = res ", " field("comment", $3)
    res = res ", \"geo_data\": { "
    if ($4) res = res field("region", $4)
    if ($5) res = res ", " field("modern_country", $5)
    if ($6) res = res ", " field("modern_province", $6)
    if ($8) res = res ", " field("coordinates", "("$8")")
    res = res " }"
    if ($7) res = res ", \"links\": [ { " field("type", "geonames_id") ", " field("target",$7) " } ]"
    if ($9) {
        gsub(/ *[|] */, "\", \"", $9)
        res = res ", \"labels\": [ \""$9"\" ]"
    }
    gsub(/[{] *, */, "{ ", res)
    print res " }"
}

function field(n, s) { return qt(n)": "qt(s) }
function qt(s) { return "\""s"\"" }

