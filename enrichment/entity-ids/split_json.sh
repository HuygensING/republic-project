#!/usr/bin/env bash
set -eu -o pipefail

# USAGE: bash split_json.sh H HOE combined_file.json
#
# Splits entity names from entity annotations and assigns identifiers.
#
# Outputs to current directory.

combined="$3"
prefix=$1
idlist=$2-ids.tsv
annotations=$2-annotations.json
entities=$2-entities.json

echo "Generating ids to $idlist..."
<"$combined" jq -rc '.[].entity.name' | sort | uniq |\
    gawk -f ../entity-ids/generate-ids.awk PREFIX=$prefix ../entity-ids/id-list.tsv - \
    >"$idlist"
echo "Writing entities to $entities..."
<"$combined" jq -rc '.[].entity' | sort | uniq |\
    gawk -itsv 'NR==FNR{id[$1]=$2;next}{n=gensub(/^."name":"([^"]+)".*/,"\\1",1);gsub(/^./,"{\"id\":\""id[n]"\",")}1' "$idlist" - |\
    gawk 'BEGIN{print"["}END{print"]"}NR>1{print ","}1' |\
    jq >"$entities"
echo "Writing annotations to $annotations..."
<"$combined" jq 'del(.[].comment)' | jq -r '.[].entity |= .name' |\
    gawk -itsv '
        NR==FNR { id[$1]=$2; next }
        match($0, /(.*"entity": ")([^"]+)(".*)/, m) { $0=m[1] id[m[2]] m[3] }
        match($0, /(.*)"TARGET_ANNOT"(.*)/, m) { $0 = m[1] "\"file:'"$annotations"'#" ++rnr "\"" m[2] }
        match($0, /(.*)"TARGET_ENT:(.*)"(.*)/, m) { $0 = m[1] "\"urn:republic:entity:"id[m[2]]"\"" m[3] }
    1' "$idlist" - \
    >"$annotations"

