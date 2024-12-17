#!/usr/bin/env bash
set -eu

# SUMMARY
#
#   Compare versions of entity annotations
#
# USAGE
#
#   bash compare-annotations.sh OLD-annotations.json NEW-annotations.json 
#
# OUTPUT
#
#   This script outpus three lists:
#
#   1) A list of entity references resolved in the second file, but not in the 
#      first (newly-recognised);
#   2) A list of entity references resolved in the first file, but not in the 
#      second (dropped);
#   3) A list of entity references resolved to different entities.
#
#   All are preceded by the number of occurrences.

jqparams=".[] | [.reference.paragraph_id,.reference.offset,.entity] | @tsv"

diff -y <(<"$1" jq -r "$jqparams" | sort) <(<"$2" jq -r "$jqparams" | sort) | grep '[<|>]' | gawk '
BEGIN { FS=OFS="\t" }
NR==FNR { name[$1]=$2; next }
{
    gsub(/[ \t]+/, "\t")
    gsub(/^\t[<|>]/, "\t\t&")
    $3 = name[substr($3, 2)] " ("$3")"
    $7 = name[substr($7, 2)] " ("$7")"
}
$4==">" { n++; add[$7]++ }
$4=="<" { o++; drp[$3]++ }
$4=="|" { c++; cha[$3"\t"$7]++ }
END {
    print "Newly recognised:\n"
    for (k in add) print add[k], k
    print "\nDropped entities:\n"
    for (k in drp) print drp[k], k
    print "\nChanges (old -> new)\n"
    for (k in cha) print cha[k], k
    printf "\n%d new, %d dropped, %d changed\n", n, o, c
}
' $(dirname $0)/entity-ids/id-list.tsv -

