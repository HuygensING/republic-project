#!/usr/bin/env -S gawk -f

@include "provenance"

BEGIN { FS="\t"; OFS=" "; print "["
	PROCINFO["sorted_in"] = "@ind_num_asc" }
END { print "]" }

FILENAME ~ /provenance/ {
	prov[$2] = provenance::append_decision(prov[$2], $3, $4, $5, $6)
	next }

FNR == 1 { next } # ignore header on last file

!$9 || $9 ~ /NOMATCH/ { next }

{
	split($9, m, / *; */)
	for (i in m) {
		if (comma) print ","
		comma = 1
		print "{ \"reference\": {"
		print field("layer", "LOC")
		print ", "field("inv", $2)
		print ", "field("resolution_id", $3)
		print ", "field("paragraph_id", $4)
		print ", "field("tag_text", $11)
		print ", "field("offset", $6)
		print ", "field("end", $7)
		print ", "field("tag_length", $8)
		print "}, " field("entity", m[i])
		print ", \"provenance\": "
        print provenance::make_record("annotations-layer_LOC.tsv#"(FNR-1), "LOC-entities.json#"(++outnr), m[i], prov[FNR])
		print "}"
	}
}

function field(n, s) {
	return qt(n)": "qt(s) }

function qt(s) {
	gsub(/"/, "\\\"", s)
	return "\""s"\"" }

