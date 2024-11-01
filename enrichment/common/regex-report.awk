#!/usr/bin/env -S gawk -f

# USAGE: regex-report regexes.tsv strings.txt >keywords.tsv
#
#   This program produces lists of matches from regex patterns. The resulting 
#   lists can be used as input for a fuzzy keyword search. For the latter 
#   purpose, the regex match list will only include terms that occur multiple 
#   times that deviate significantly from more-often occuring variants.
#
# OPTIONS
# 
#   MIN_FOUND       minimum occurrence for a variant (2)
#   TRESHOLD        levenshtein treshold score (0.85)
#
# INPUT
#
#   regexes.tsv     <replacement text> <tab> <regex>
#   strings.txt     <free text>
#
# OUTPUT
#
#   <replacement> <tab> <most common match> <tab> <first variant> <tab> ...
#

@include "simple-levenshtein"

BEGIN { FS=OFS="\t"
    PROCINFO["sorted_in"] = "@val_num_desc"
	MIN_FOUND = 2
	TRESHOLD = 0.85
}

# reading the regexes

FNR==NR { if(NF==2) pats["\\<"$2"\\>"]=$1 }

# matching the regexes

FNR<NR {
    for(p in pats) {
        repl = pats[p]
        while(match($0, p)) {
            matches[repl][substr($0, RSTART, RLENGTH)]++
            sub(p, "") # here, perform a simple delete
        }
    }
}

# printing the report

END {
    for(r in matches) {
		print "Variants of", r, length(matches[r]) >"/dev/stderr"
		delete seen
        printf r
        for (m in matches[r]) {
            if (matches[r][m] < MIN_FOUND) continue
			# filter out close variants
			p=1; for (s in seen) {
				if (levenshtein(s,m)>TRESHOLD) {
					p=0; continue
				}
			}
			# print remaining variants
			if (p) {
				seen[m] = length(seen)
				printf OFS m
			}
        }
        printf "\n"
    }
}

