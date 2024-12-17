#!/usr/bin/env -S gawk -f

# USAGE: gawk -f add_categories.awk ids.tsv match-results.tsv entities.tsv >full-entities.tsv

BEGIN { FS=OFS="\t"
    loc_ids["FullName"] = "Id"
    CAT_LOG = "category_log.tsv"
    # lower bounds for categories to be added
    MIN_COUNT = 2
    MIN_FRACTION = 0.03
    MIN_LOCS = 5 # per category
}

1 == ARGIND {
	# Map between location ids and names
    loc_ids[$1] = $2
    loc_names[$2] = $1
}

2 == ARGIND && $9 {
	# Save categories to loc_cats, indexed by location id
    if ($9 == "NOMATCH") next
    split($9, ids, /; */)
    split($10, cats, /[|] */)
    for (i in ids) {
        id = ids[i]
        totals[id]++
        for (c in cats) {
            cat = cats[c]
			#if (cat in equivs) cat = equivs[cat] # TODO nonfunctional
            loc_cats[id][cat]++
        }
    }
}

BEGINFILE {
	# Note: the for loops only run before the third argument
	# Cull the categories we found:
	#  - must occur MIN_COUNT together w/ every location
	#  - must occur MIN_FRACTION of all locations to the location
    for (id in loc_cats) {
        print id, loc_names[id], totals[id] >CAT_LOG
        for (cat in loc_cats[id]) {
            count = loc_cats[id][cat]
            if (count < MIN_COUNT) continue
            if (count/totals[id] < MIN_FRACTION) continue
            print "", cat, count >CAT_LOG
            ids_per_cat[cat][id]++
            final_cats[id] = (id in final_cats ? final_cats[id]"|" : "") cat
        }
    }
	# Now drop all categories with fewer than MIN_LOCS distinct locations
    for (cat in ids_per_cat) {
        if (length(ids_per_cat[cat]) < MIN_LOCS) for (id in final_cats) {
            delete ids_per_cat[cat]
            cs = final_cats[id]
            gsub("\\<"cat"\\>", "", cs)
            gsub(/[|]+/, "|", cs)
            final_cats[id] = cs
        }
    }
}

3 == ARGIND {
	# Write out the updated entity list
    $1 = loc_ids[$1]
    $9 = FNR==1 ? "Labels" : final_cats[$1]
    if (!$1) print "UNKNOWN ON LINE "FNR >"/dev/stderr"
    print
}

END {
	# Append results to the log
    print "\n-----------\n" >CAT_LOG
    for (cat in ids_per_cat) {
        print cat, length(ids_per_cat[cat]) >CAT_LOG
        for (id in ids_per_cat[cat]) {
            print "", id, loc_names[id] >CAT_LOG
        }
    }
}
