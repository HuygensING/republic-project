
# DESCRIPTION
#
# This is a tool for performing parrallel fuzzy matches on large lists of 
# keywords. For every main keyword (lemma), multiple synonyms or variant 
# keywords can be given.
#
# The match algorithm is based on edit-distance and allows detailed 
# fine-tuning. Preservation of particular keyword endings can be ensured (i.e. 
# plurals).
#
# You can specify a cache file for speeding up subsequent searches drastically; 
# this allows quick trials of new keywords, for incremental development of your 
# keyword list.
#
# Reports can be generated of (aggregated) matches and of edits made.
#
# The program is memory-intensive: you should count on several dozen gigabytes 
# per thousand keywords.
#
#
# INTERFACE when used as an gawk module (@include "edit-distance")
#
#   fuzzy::add_keyword(lemma, keyword, max_dist)
#
#       lemma    : string (main term)
#       keyword  : string (word to look for)
#       max_dist : optional number (maximal edit distance)
#
#   fuzzy::replace_matches(segments, separators)
#
#       segments   : array (corresponds to feasible starts-of-matches)
#       separators : array (spaces/punctuation between segments)
#
#       edits both arrays & returns re-joined result
#
#   fuzzy::search(segments, separators, result_array, match_array)
#
#       outputs matched lemmas to result_array and matches to match_array
#
#
# PARAMETERS can be given on the command-line as PARAMETER=value
#       or set in a BEGIN block after @include "edit-distance"
#
#   TRESHOLD    default treshold (0.76)
#   ENDINGS     word-final pattern to preserve ("en|s")
#   PAIRS       easily-confused character pairs ("ceyjuvfséeëedtrnzsitnu")
#
#   W_INS       insertion cost, relative to the keyword (1.0)
#   W_DEL       deletion cost (1.0)
#   W_SBS       substitution cost (1.0)
#   W_CAP       case change cost (0.3)
#   W_SPA       space insertion cost (0.7)
#   W_SIM       similar-character substitution cost (0.7)
#
#   CACHE       cache file
#   MODE        cache mode: (0) read-only (1) update (2) expand w/ new keywords
#   MATCHES     detailed replacement log file
#   REPORT      aggregate replacement log file
#   PROVENANCE  provenance log file
#   VERBOSE     status updates ("/dev/stderr")
#
#   PARTIAL_CACHE (experimental)
#               set to 0 for reducing memory usage at the cost of speed
#   FILTER_ON_LENGTH (experimental)
#               exponent of match length to use when comparing simultaneous results
#               (defaults to 0, which disables the feature)
#

@include "provenance"

@namespace "fuzzy"

## parameters

BEGIN { FS=OFS="\t"
    PROCINFO["sorted_in"] = "@ind_num_asc"
    # options
    VERBOSE = "/dev/stderr"
    TRESHOLD = 0.76
    ENDINGS = "en|s"
    PAIRS="ceyjuvfséeëedtrnzsitnu"
    W_INS = 1.0; W_DEL = 1.0; W_SBS = 1.0
    W_CAP = 0.3; W_SPA = 0.7; W_SIM = 0.7
    split("", old_cache[""])
    split("", new_cache[""])
    PARTIAL_CACHE=1
}

BEGINFILE {
    make_pairs()
    if (ENDINGS !~ /\$$/) ENDINGS = "("ENDINGS")$"
}

function make_pairs(    i, a, b) {
    for (i=1;i<length(PAIRS);i+=2) {
        a = substr(PAIRS,i,1)
        b = substr(PAIRS,i+1,1)
        pairs[a]=b; pairs[b]=a
    }
}

## find matches

# results are output to the array `matches`, which has the form
#     matches[from][keyword][distance] = to
# with `from` and `to` indices in the `segments` array

function list_matches(cache, segments, seps, matches,
        i, j, segment, dist, scor) {
    for (i in segments) {
        segment = ""
        for (j=i; j<=length(segments); j++) {
            segment = segment (j==i ? "" : seps[j-1]) segments[j]
            if (segment in cache) cache_hits++
            else { cache_misses++; update_cache(cache, segment) }
            # retrieve results
            for (keyword in cache[segment]) {
                if ((keyword ~ ENDINGS) != (segment ~ ENDINGS)) continue
                dist = cache[segment][keyword][length(keyword)]
                scor = 1 - dist/length(keyword)
                if (scor < get_treshold(keyword)) continue
                matches[i][keyword][dist] = j
                if (MATCHES) {
                    print FILENAME, FNR, segment, lemmas[keyword], keyword, dist, scor >MATCHES
                }
            }
        }
    }
}

function update_cache(cache, segment,
        prefix, suffix, keyword, k, ls, lk) {
    ls = length(segment)
    for (k=ls; k>=0; k--)
        if (substr(segment,1,k) in cache) break
    prefix = substr(segment, 1, k)
    suffix = substr(segment, k+1)
    for (keyword in cache[prefix])
        advance_rows(cache, keyword, segment, prefix, suffix)
}

function advance_rows(cache, keyword, segment, prefix, suffix, partial,
        row, min, ll, i, li, n, cs, ci, c, kc, ins, del, sbs) {
    # initialisation
    for (i in cache[prefix][keyword]) row[i] = cache[prefix][keyword][i]
    ll = length(keyword)
    split(suffix, cs, "")
    partial = prefix
    # advance the calculation
    for (ci in cs) { c = cs[ci] # loop over input characters (vertical)
        partial = partial c
        if (PARTIAL_CACHE) if (!(partial in cache)) split ("", cache[partial])
        n = row[0]; row[0]+=W_INS; min = ll
        for (li=1;li<=ll;li++) { # loop over the keyword (horizontal)
            ins = row[li] + (c~/[– .:-]/ ? W_SPA : W_INS)
            del = row[li-1] + W_DEL 
            sbs = n + ((kc=chars[keyword][li]) != c) * W_SBS
            if (sbs>n) {
                if (tolower(kc) == tolower(c)) sbs = n + W_CAP
                else if (pairs[c] == kc) sbs = n + W_SIM
            }
            n = row[li]
            row[li] = min3(sbs,ins,del)
            min = min2(min, row[li])
        }
        # abort if the treshold is passed (values can only grow)
        if (1 - min/ll < get_treshold(keyword)) return
        else if (PARTIAL_CACHE) {
            cache_adds++
            for (i in row) cache[partial][keyword][i] = row[i]
        }
    }
    if (!PARTIAL_CACHE) {
        cache_adds++
        for (i in row) cache[partial][keyword][i] = row[i]
    }
}

function status_report() {
    #cache_hits /= 1000
    #cache_misses /= 1000
    #cache_adds /= 1000
    printf "Cache hits/misses/adds: %d / %d / %d\n", cache_hits, cache_misses, cache_adds >VERBOSE
    cache_hits = cache_misses = cache_adds = 0
}

## replacements

function filter_matches(matches,
        i, k, d, e, s, ci, cl, cd, ce, cs) {
    for (i in matches) for (k in matches[i]) for (d in matches[i][k]) {
        i = +i; d=+d; s = filter_score(d, length(k))
        e = +matches[i][k][d]
        if (i > ce) { # no overlap
            ci=i; cl=k; cd=d; cs=s; ce=e
        } else if (s > cs) { # compare scores
            delete matches[ci][cl][cd]
            ci=i; cl=k; cd=d; cs=s; ce=e
        } else {
            delete matches[i][k][d]
        }
    }
}

function filter_score(d, l) {
    if (FILTER_ON_LENGTH)
        return (1-d/l)*((l-d)^FILTER_ON_LENGTH)
    else
        return (1-d/l)
}

function replace_matches(segments, seps,
        matches, i, k, l, d, j, n, w,
        orig, res) {
    delete matches
    if (PROVENANCE) orig = zipjoin(segments, seps)
    list_matches(old_cache, segments, seps, matches)
    list_matches(new_cache, segments, seps, matches)
    filter_matches(matches)
    for (i in matches) for (k in matches[i]) for (d in matches[i][k]) {
        j = +matches[n=+i][k][d]
        w = segments[n]
        l = segments[n] = lemmas[k]
        if (substr(w,1,1) substr(l,1,1) ~ /[A-Z][a-z]/) l = segments[n] = toupper(substr(l,1,1)) substr(l,2) # preserve initial capital
        while (++n<=j) {
            w = w seps[n-1] segments[n]
            seps[n-1] = segments[n] = ""
        }
        if (REPORT) replacements[l][k][w]++
        total_matches++
        if (PROVENANCE && l != w) {
            provenance::write(orig, k, w, "fuzzy match: "l)
        }
    }
    return zipjoin(segments, seps)
}

END {
    if (REPORT) print_aggregates()
    printf "Number of matches: %d\n", total_matches >VERBOSE
}

function print_aggregates(    l, k, w, srt) {
    for (l in replacements) {
        for (k in replacements[l]) {
            srt = PROCINFO["sorted_in"]
            PROCINFO["sorted_in"] = "@val_num_desc"
            for (w in replacements[l][k]) {
                print l, k, w, +replacements[l][k][w] >REPORT
            }
            PROCINFO["sorted_in"] = srt } } }

## search

function search(segments, seps, found, matched,
        matches, n,m,i,j,d,kw,w) {
    delete matches
    list_matches(old_cache, segments, seps, matches)
    list_matches(new_cache, segments, seps, matches)
    filter_matches(matches)
    if (PROVENANCE) orig = zipjoin(segments, seps)
    m = 0
    for (i in matches) for (kw in matches[i]) for (d in matches[i][kw]) {
        found[++m] = lemmas[kw]
        j = +matches[i][kw][d]
        w = segments[i] j
        for (n=1+i;n<=j;n++) w = w seps[n-1] segments[n]
        matched[m] = w
        if (REPORT) replacements[lemmas[kw]][kw][w]++
        total_matches++
        if (PROVENANCE && l != w) {
            provenance::write(orig, kw, w, "fuzzy match: "l)
        }
    }
}

## adding keywords

function add_keyword(lemma, keyword,    dist,    n) {
    lemmas[keyword] = lemma # replacement text
    if (dist) maxdists[keyword] = dist # custom maximal distance
    split(keyword, chars[keyword], "") # character array
    if (!(keyword in old_cache)) {
        for (n=0; n<=length(keyword);n++) {
            # fill zeroth matrix row
            new_cache[""][keyword][n] = n*W_DEL
        }
    }
}

function get_treshold(keyword) {
    return keyword in maxdists ? 1 - maxdists[keyword]/length(keyword) : TRESHOLD
}

## saving and reading the cache

NR==1 { read_cache() }
END { write_cache() }

function read_cache(    m, i) {
    if (!CACHE) return
    while (0 < getline <CACHE) {
        if (1==NF) {
            if (!($1 in old_cache)) split("", old_cache[$1])
        } else {
            split($3, m, "|")
            for (i in m) old_cache[$1][$2][i-1] = +m[i]
        }
    }
}

function write_cache(    segment, keyword, i, min) {
    if (!MODE || !CACHE) return
    for (segment in old_cache) {
        print segment >CACHE
        for (keyword in old_cache[segment])
            print segment, keyword, join(old_cache[segment][keyword],"|") >CACHE
        if (MODE==2) for (keyword in new_cache[segment])
            print segment, keyword, join(new_cache[segment][keyword],"|") >CACHE
    }
}

function cache_info() {
    print "Cached keywords: "length(old_cache[""]) >VERBOSE
    print "Trial keywords: "length(new_cache[""]) >VERBOSE
    printf "W_INS %.2f, W_SBS %.2f, W_DEL %.2f\n", W_INS, W_SBS, W_DEL >VERBOSE
    printf "W_CAP %.2f, W_SPA %.2f, W_SIM %.2f\n", W_CAP, W_SPA, W_SIM >VERBOSE
}

## auxiliary functions

function min2(a,b) { return b<a ?  b : a }

function min3(a,b,c) { return b<a ? (c<b?c:b) : (c<a?c:a) }

function join(arr, sep,    i, r) {
    r = "" arr[0 in arr ? i+0 : ++i]
    while (++i in arr) r = r sep arr[i]
    return r }

function zipjoin(arr, seps,    i, r) {
    r = "" seps[i+0]
    while(++i in arr || i in seps)
        r = r arr[i] seps[i]
    return r }

