#!/usr/bin/env -S gawk -f

# USAGE: <input ./sample.awk n=100

# Simple reservoir sampling.
# Preserves input order.

BEGIN { srand() }

BEGINFILE { if (!n) n = 20 }

{ m = NR <= n ? NR : int(rand()*NR) + 1 }

m <= n {
    pool[m] = $0
    sort[m] = NR
}

END {
    PROCINFO["sorted_in"] = "@val_num_asc"
    for (i in sort) print pool[i]
}

