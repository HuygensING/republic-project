#!/usr/bin/env -S gawk -f

# USAGE: gawk -f extract-entities.awk locations.tsv > loc-entities.tsv

BEGIN { FS=OFS="\t"
    split("Flevoland|Drenthe|Utrecht|Overijssel|Friesland|Noord-Holland|Zuid-Holland|Groningen|Limburg|Gelderland|Zeeland|Noord-Brabant", svorp, /[|]/)
	for (i in svorp) provs[svorp[i]] = i
    }

NR==1 { next }

{
    split($1, ms, /; */)
    split($2, rs, /; */)
    split($3, cs, /; */)
    split($4, gs, /; */)
    gsub(/[]], [[]/, "]; [", $5)
    gsub(/[][]/, "", $5)
    split($5, ls, /; */)
    for (i in ms) {
        n = ms[i]
        gsub(/[~]/, "/", n)
        ents[n] = FNR
        r = set_maybe($2, rs, i)
        c = set_maybe($3, cs, i)
        g = set_maybe($4, gs, i)
        l = set_maybe($5, ls, i)
        p = 0
        if (r in provs) {
            p = r
            r = "Europa"
        }
        check_set(e_reg, n, r)
        check_set(e_cou, n, c)
        check_set(e_pro, n, p)
        check_set(e_gid, n, g)
        check_set(e_loc, n, l)
    }
}

function set_maybe(val, arr, ind) {
    if (length(arr)>1) return arr[ind]
    if (val && val != "0") return val
    return 0 }

function check_set(arr, ind, val) {
    if (!val) return
    if (ind in arr && val != arr[ind]) printf "CONFLICT on %s: (%s) and (%s)\n", ind, arr[ind], val >"/dev/stderr"
    else arr[ind] = val }

END {
    print "FullName", "Name", "Comment", "Region", "ModernCountry", "ModernProvince", "GeonamesId", "Coords"
    for (n in ents) {
        name = comm = n
        gsub(/ *[/].*/, "", name)
        gsub(/^[^/]*[/]? */, "", comm)
        if (comm) comm = "Ook als: "comm
        print n, name, comm, e_reg[n], e_cou[n], e_pro[n], e_gid[n], e_loc[n]
    }
}

