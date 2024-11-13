#!/usr/bin/env -S gawk -f

BEGIN { FS="\t"; OFS=" "; print "["
	PROCINFO["sorted_in"] = "@ind_num_asc" }
END { print "]" }

FILENAME ~ /provenance/ {
	prov[$2][length(prov[$2])+1] = \
	 	"{ " field("source", $3) \
	 	", " field("criterium", $4) \
	 	", " field("outcome", $5) \
	 	", " field("conclusion", $6) " }"
	next
}

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
		print ", "field("tag_text", $5)
		print ", "field("offset", $6)
		print ", "field("end", $7)
		print ", "field("tag_length", $8)
		print "}, " field("entity", m[i])
		print ", \"provenance\": ["
		for (j in prov[FNR]) {
			if (j>1) print ","
			print prov[FNR][j]
		}
		print "] }"
	}
}

function field(n, s) {
	return qt(n)": "qt(s) }

function qt(s) {
	gsub(/"/, "\\\"", s)
	return "\""s"\"" }

