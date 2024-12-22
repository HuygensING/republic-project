#!/usr/bin/env -S gawk -f

match($0, /"name" *: *"/) {
    n = substr($0, RSTART+RLENGTH)
    split(n, m)
    $0 = substr($0, 1, RSTART+RLENGTH-1)
    for (i in m) {
        n = m[i]; u = substr(n,1,1)
        # Capitalise after a hyphen
        while (match(n, /-[a-z]/)) {
            n = substr(n, 1, RSTART) toupper(substr(n, RSTART+1, 1)) substr(n, RSTART+2)
        }
        # Capitalise all word-initial except prepositions
        if (n !~ /^(v[ao]n|de.?|du|tot|te|la|les?)$/)
            u = toupper(u)
        $0 = $0 (i==1?"":" ") u substr(n,2)
    }
    # Re-order prepositions
    $0 = gensub(/("name" *: *")([a-z][a-z ]*[a-z]) ([A-Z][^"]+)(".*)/, "\\1\\3, \\2\\4", 1)
}

1 # prints
