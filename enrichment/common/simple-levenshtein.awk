
function levenshtein(a, b,
        ca, cb, la, lb,
        m, n, i, j,
        sbs, del, ins) {
    # edge cases
    la = length(a); lb=length(b)
    if (!la || !lb) return 0
    if (la == lb && a==b) return 1
    # initialise starting vectors
    split(a, ca, "")
    split(b, cb, "")
    for (i=0;i<=la;i++) m[i] = i
    # fill matrix, only remembering the last two rows
    for (i=1;i<=lb;i++) {
        n = m[0]; m[0] = i
        for (j=1;j<=la;j++) {
            sbs = n + (ca[j]!=cb[i])
            ins = m[j] + 1
            del = m[j-1] + 1
            n = m[j]
            m[j] = min3(sbs, ins, del)
        }
    }; return 1-m[la]/la
}

function min3(a,b,c) { return b<a ? (c<b?c:b) : (c<a?c:a) }

