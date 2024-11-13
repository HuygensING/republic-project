#!/usr/bin/env -S gawk -f

BEGINFILE {
    "date -u -Iseconds" | getline timestamp
    sub(/+00:00/, "Z", timestamp)
    "git rev-parse HEAD" | getline commit_id
    commit_url = "https://github.com/HuygensING/republic-project/commit/" commit_id
    prov_insert_before = qt("provenance")": { " \
        field("where", "https://annotation.republic-caf.diginfra.org/") ", " \
        field("when", timestamp) ", " \
        field("how", commit_url) ", " \
        field("why", "REPUBLIC Entity Enrichment") ", " \
        qt("source") ": [ "qt("file:annotations-layer_"TYPE".tsv")" ], " \
        qt("source_rel") ": [ "qt("primary")" ], " \
        qt("target") ": [ "qt("file:"TYPE"-annotations.json")", "qt("file:"TYPE"-entities.json")" ], " \
        qt("target_rel") ": [ "qt("primary")", "qt("primary")" ]"
    if(!DROP) prov_insert_before = prov_insert_before \
        ", "qt("why_provenance_schema")": { " field("format", "decision_log")", " qt("decisions")": ["
}

/"provenance": \[/ {
    print prov_insert_before;
    in_provenance = 1
    next }

in_provenance && /^    +],?$/ {
    if (DROP) sub(/\]/, "")
    else sub(/\]/, "]}}")
    in_provenance = 0 }

in_provenance && DROP { next }

1 # prints

function field(n, s) {
    return qt(n)": "qt(s) }
function qt(s) {
    gsub(/"/, "\\\"", s)
    return "\""s"\"" }

