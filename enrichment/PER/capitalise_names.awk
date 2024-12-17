#!/usr/bin/env -S gawk -f

match($0, /"name" *: *"/) {
    n = substr($0, RSTART+RLENGTH)
    split(n, m)
    $0 = substr($0, 1, RSTART+RLENGTH-1)
    for (i in m) {
        n = m[i]; u = substr(n,1,1)
        if (i == 1 || n !~ /^(van|de.?|du|tot|l[ae])$/)
            u = toupper(u)
        $0 = $0 (i==1?"":" ") u substr(n,2)
    }
}

1 # prints
