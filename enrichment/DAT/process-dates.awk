#!/usr/bin/env -S gawk -f

# USAGE gawk -f process-dates.awk date_variants.tsv annotations-layer_DAT.tsv

@include "provenance"
@include "edit-distance"

BEGIN { FS=OFS="\t"
    PROVENANCE = "provenance.tsv"
    ENDINGS = " en"
    FILTER_ON_LENGTH = 1
}

NR==FNR { # read the date variants
    for (i=2;i<=NF;i++) {
        fuzzy::add_keyword($1, $i)
    }
    next
}

BEGIN { # read session dates
    while (1 == getline <"../ner-output/session_dates.tsv") {
        sessiondates[$1] = $2
    }
}

FNR==1 {
    fuzzy::cache_info()
    next # skip header
}


{
	in_RES = +$9
    resolution = sdate = $3 # resolution_id
    gsub(/-resolution-.*/, "", sdate) # |-> session_id
    if (sdate in sessiondates) sdate = sessiondates[sdate]
    else print "No date known for session "sdate >"/dev/stderr"
    if (match(sdate, /([0-9]+)-0?([0-9]+)-0?([0-9]+)/, m)) {
        syear = strtonum(m[1])
        smonth = strtonum(m[2])
        sday = strtonum(m[3])
    }
    source = $0 = $5 # select tag_text
    # Contaminations
    provenance::start_edit()
    gsub(/honder|deser/, " &")
    gsub(/\<den/, "den ")
    gsub(/[A-Z]/, " &")
    gsub(/[0-9]+/, " &")
    gsub(/  +/, " ")
    gsub(/^[ .,:-]+/, "")
    provenance::commit_edit("Insert missing spaces")
    # Case has no relevance for dates
    $0 = tolower($0)
    # Remove *some* interpunction
    gsub(/[‘’]/, "'")
    # Resolve broken lines
    gsub(/ *[.,]*[=„][,.]* */,"")
    gsub(/[.:] /, " ")
    provenance::commit_edit("Simplify punctuation")
    # Suffixes to numbers
    $0 = gensub(/\<([mdcx]*[lxvxij]+|[0-9]+)[.-]?(en?)?\>[.]?/, "\\1", "g")
    provenance::commit_edit("Remove ordinal suffixes")
    # Roman numerals
    gsub(/ c\>/, "c")
    gsub(/\<xvc\>/, "15 hondert")
    gsub(/\<xv[ij]c\>/, "16 hondert")
    gsub(/\<xv[ij][ij]c\>/, "17 hondert")
    gsub(/^c /, "a ")
    provenance::commit_edit("Write out abbreviated centuries")
    while(/\<[clxvxij]+\>/) {
        match($0, /\<[clxvxij]+\>/)
        orig = repl = substr($0, RSTART, RLENGTH)
        gsub(/j/, "i", repl)
        gsub(/il/, "ii", repl)
        gsub(/ix|viiii/, "9", repl)
        gsub(/xc|lxxxx/, "9_", repl)
        gsub(/lxxx/, "8_", repl)
        gsub(/lxx/, "7_", repl)
        gsub(/lx/, "6_", repl)
        gsub(/l/, "5_", repl)
        gsub(/xl|xxxx/, "4_", repl)
        gsub(/xxx/, "3_", repl)
        gsub(/xx/, "2_", repl)
        gsub(/x/, "1_", repl)
        gsub(/iv/, "4", repl)
        gsub(/viiii?/, "8", repl)
        gsub(/vii/, "7", repl)
        gsub(/vi/, "6", repl)
        gsub(/v|iiiii/, "5", repl)
        gsub(/iiii/, "4", repl)
        gsub(/iii/, "3", repl)
        gsub(/ii/, "2", repl)
        gsub(/i/, "1", repl)
        gsub(/_$/, "0", repl)
        gsub(/_/, "", repl)
        if(length(repl)>2||repl=="c") repl = "[[X"orig"X]]"
        $0 = substr($0, 1, RSTART-1) repl substr($0, RSTART+RLENGTH)
    }
    provenance::commit_edit("Write out roman numerals")
    # Some abbreviations
    gsub(/\<jan?(\>|[:.])/, "januari")
    gsub(/\<febr?(\>|[:.])/, "februari")
    gsub(/\<7t?be?r[:.]?/, "september")
    gsub(/\<8t?be?r[:.]?/, "october")
    gsub(/\<9m?be?r[:.]?/, "november")
    gsub(/\<augti\>/, "augusti")
    gsub(/emb: /, "ember ")
    gsub(/tob: /, "tober ")
    provenance::commit_edit("Write out abbreviated months")
    # Likely-unintended spaces
    $0 = gensub(/^([0-9]) ([0-9]) /, "\\1\\2 ", 1)
    # Remove some more interpunction
    $0 = gensub(/([0-9])[:.]+/, "\\1", "g")
    $0 = gensub(/([0-9])[/] /, "\\1 ", "g")
    provenance::commit_edit("Improve punctuation (guess)")
    # Fuzzy matching part
    gsub(/berse+ven/, "ber seven") # surprisingly common mistake
    patsplit($0, segments, "[a-z]+", seps)
    $0 = fuzzy::replace_matches(segments, seps)
    # Repair errors and omissions from fuzzy matching
    provenance::start_edit()
    gsub(/MONTH03 MONTH/, "MONTH") # likely maent -> maert
    gsub(/tot en MONTH05/, "tot en met") # likely met -> mey
    gsub(/twee+n 20/, "22")
    gsub(/agt en /, "8 ")
    gsub(/janvier|janr[ijy]+/, "MONTH01")
    sub(/^[0-9]{1,2}$/, "& MONTH==")
    sub(/ (lest|jongst)l?$/, " PREVIOUS")
    provenance::commit_edit("Fix fuzzy matching errors")
    $0 = gensub(/(^| )([1-9]) ([23])[01]( |$)/, "\\1\\3\\2\\4", "g")
    $0 = gensub(/^([0-9]{1,2}) den MONTH/, "\\1 MONTH", 1)
    gsub(/ma[ae]n[dt]+ MONTH/, "MONTH")
    gsub(/NEXT ma[ae]n[dt]+$/, "MONTH+1")
    gsub(/PREVIOUS ma[ae]n[dt]+$/, "MONTH-1")
    $0 = gensub(/MONTH-1 (MONTH[0-9]{2})/, "\\1 PREVIOUS", "g") # voorlede maent <month>
    gsub(/ de[rs] /, " ")
    provenance::commit_edit("Fix double matches of months")
    # Calendar markers
    julian = /JULIAN/
    gsub(/ *(JUL|GREGOR)IAN$/, "")
    gsub(/ *(JUL|GREGOR)IAN */, " ")
    # Written-out centuries
    gsub(/15 100 /, "15")
    gsub(/16 100 /, "16")
    gsub(/17 100 /, "17")
    gsub(/15 100$/, "1500")
    gsub(/16 100$/, "1600")
    gsub(/17 100$/, "1700")
    if (source !~ /^[^ ]+[td]en en/) $0 = gensub(/^([1-9]) en ([23])0 /, "\\2\\1 ", 1)
    $0 = gensub(/1([567])([0-9]) en ([2-9])0($| )/, "1\\1\\3\\2\\4", "g")
    $0 = gensub(/ 1([567])([1-9])($| |,)/, " 1\\10\\2\\3", "g")
    $0 = gensub(/ (1[567]) ([0-9])$/, " \\10\\2", "g")
    $0 = gensub(/ (1[567]) ([0-9]{2})$/, " \\1\\2", "g")
    $0 = gensub(/\<([0-9]) en ([23])0 MONTH/, "\\2\\1 MONTH", "g")
    provenance::commit_edit("Resolve arithmetic")
    # Calendar markers
    gsub(/ *stil[oe] n[uo][a-z]{1,3}/, "")
    # Resolve dates relative to other dates
    sub(/ (dit+o|der gemelde ma[ae]n[dt]+)$/, " RELATIVE")
    sub(/ (der voorl|te vo+ren)$/, " RELATIVE PREVIOUS")
    gsub(/ van RELATIVE/, " RELATIVE")
    if (last_resolution == resolution && /RELATIVE/) {
        provenance::write($0, "contains RELATIVE", "Set reference date to last resolved", \
             sprintf("%04d-%02d-%02d -> %04d-%02d-%02d", syear, smonth, sday, last_year, last_month, last_day))
        sday = last_day
        smonth = last_month
        syear = last_year
    }
    gsub(/RELATIVE MONTH/, "MONTH")
    gsub(/RELATIVE PREVIOUS/, "PREVIOUS")
    gsub(/RELATIVE NEXT/, "NEXT")
    gsub(/RELATIVE/, "MONTH==")
    provenance::commit_edit("Resolve date relative to last recognised")
    # Simplify relative dates
    gsub(/ mede /, " ")
    gsub(/(der )?voorschreven? /, " ")
    gsub(/ de+[zs]e[rsn]$/, " MONTH==")
    gsub(/MONTH== PREVIOUS/, "MONTH-1")
    gsub(/MONTH== NEXT/, "MONTH+1")
    $0 = gensub(/(MONTH[0-9]{2}) MONTH==/, "\\1", "g")
    gsub(/ma[ae]n[dt]+( van)? MONTH/, "MONTH")
    gsub(/MONTH== MONTH/, "MONTH")
    provenance::commit_edit("Simplify relative dates")
    # Resolve months
    gsub(/MONTH==/, "MONTH"sprintf("%02d", smonth))
    $0 = gensub(/^([0-9][0-9]?) PREVIOUS$/, "\\1 MONTH-1", 1)
    $0 = gensub(/^([0-9][0-9]?) NEXT$/, "\\1 MONTH+1", 1)
    if (smonth < 12) gsub(/MONTH\+1/, "MONTH"sprintf("%02d", smonth+1))
    if (smonth > 1) gsub(/MONTH-1/, "MONTH"sprintf("%02d", smonth-1))
    if (match($0, /NEXT MONTH([0-9]{2})/, m)) {
        month = strtonum(m[2])
        if (smonth > month) sub(m[0], "MONTH"m[1]" NEXT")
        else sub(m[0], "MONTH"m[1])
    }
    if (match($0, /PREVIOUS MONTH([0-9]{2})/, m)) {
        month = strtonum(m[2])
        if (smonth < month) sub(m[0], "MONTH"m[1]" PREVIOUS")
        else sub(m[0], "MONTH"m[1])
    }
    if (match($0, /MONTH0?([0-9]+) PREVIOUS$/, m)) {
        month = strtonum(m[1])
        sub(/PREVIOUS$/, month <= smonth ? "YEAR==" : "YEAR-1")
    }
    if (match($0, /MONTH0?([0-9]+) NEXT$/, m)) {
        month = strtonum(m[1])
        sub(/NEXT$/, month >= smonth ? "YEAR==" : "YEAR+1")
    }
    sub(/MONTH\+1( YEAR\+1)?$/, "MONTH01 YEAR+1")
    sub(/MONTH-1$( YEAR-1)?$/, "MONTH01 YEAR-1")
    sub(/MONTH[0-9][0-9]$/, "& YEAR==")
    provenance::commit_edit("Resolve month relative to "sdate)
    # Resolve years
    gsub(/NEXT ja[ae]+r[ens]*/, "YEAR+1")
    gsub(/ ((in|van) ?den ja[ae]?re?|van het) /, " ")
    gsub(/be[ijy]+den? /, "")
    $0 = gensub(/YEAR.. (1[0-9]{3})/, "\\1", "g")
    gsub(/YEAR==/, syear)
    gsub(/YEAR-1/, syear-1)
    gsub(/YEAR\+1/, syear+1)
    provenance::commit_edit("Resolve year relative to "sdate)
    # Resolve days
    if (match($0, /ULTIMO MONTH02 ([0-9]{4})/, m)) {
        year = strtonum(m[1])
        sub(/ULTIMO MONTH02/, year%2==0 && year!=1600 ? "29" : "28")
    }
    $0 = gensub(/ULTIMO MONTH(0[469]|11)/, "30 MONTH\\1", "g")
    gsub(/ULTIMO/, 31)
    provenance::commit_edit("Resolve day of month")
    # Determining the date
    gsub(/ & /, " en ")
    gsub(/ van (de[a-z]* )?MONTH/, " MONTH")
    gsub(/tot( en met)?( den)?|totten/, "tot")
    gsub(/ *(tot|van|u[ijy]+t) [a-z]+/, "") # likely a location
    $0 = gensub(/(MONTH[0-9]+),? tot (.*) (1[0-9]{3})$/, "\\1 \\3 tot \\2 \\3", 1)
    $0 = gensub(/(.*) tot (.*)/, "\\1 en \\2 RANGE", 1)
    $0 = gensub(/(MONTH[0-9]+),? en(de)? (MONTH[0-9]+) (1[0-9]{3})/, "\\1 \\4 en \\3 \\4", "g")
    #            1    2              3     4            5               6
    $0 = gensub(/(^| )([0-9]{1,2}),? en(de)? ([0-9]{1,2}) (MONTH[0-9]{2}) (1[567][0-9]{2})/, "\\1\\2 \\5 \\6 en \\4 \\5 \\6", 1)
    #            1    2            3                 4     5            6               7
    $0 = gensub(/(^| )([0-9]{1,2}) (MONTH[0-9]{2}),? en(de)? ([0-9]{1,2}) (MONTH[0-9]{2}) (1[567][0-9]{2})/, "\\1\\2 \\3 \\7 en \\5 \\6 \\7", 1)
    provenance::commit_edit("Split double dates")
    resolved = last_resolution = ""
    list = $0
    while(1) {
        if (match(list, /^ *([0-9]+) MONTH0?([0-9]+) (1[567][0-9]{2})/, m)) {
            last_day = strtonum(m[1])
            last_month = strtonum(m[2])
            last_year = strtonum(m[3])
            if (julian) {
                jul_date = last_day"/"last_month
                last_day -= last_year < 1600 || (last_year == 1600 && last_month <= 2) ? 10 : 11
                if (last_day < 1) {
                    last_month--
                    if (last_month < 1) {
                        last_year--
                        last_month = 12
                    }
                    last_day += month_length(last_year, last_month)
                }
                provenance::write($0, "Shift to Julian calendar", jul_date, "->"last_day"/"last_month)
            }
            new_date = last_year"-"sprintf("%02d", last_month) "-"sprintf("%02d", last_day)
            resolved = resolved "\t" new_date
            last_resolution = resolution
        } else if (match(list, /^ *(lo+pend[en]* )?(ja[ae]*r[ens]* )?(1[0-9]{3})/, m)) {
            resolved = resolved "\t" m[3]
        } else if (match(list, /^(la?et?sten|ma[ae]nden)? *(van )?MONTH0?([0-9]+) (1[0-9]{3})/, m)) {
            resolved = resolved "\t" m[4]"-"sprintf("%02d", m[3])
        } else break
        list = substr(list, RLENGTH+1)
        sub(/^,?( en(de)?)? */, "", list)
    }
    gsub(/^\t/, "", resolved)
    if (list ~ / ?RANGE/) sub(resolved, /\t/, "--")
    # Print results
    if (in_RES) print source, $0, resolved ? resolved : ""
}

function month_length(year, month_nr) {
    if (month_nr==2)
        return year%2==0 && year!=1600 ? "29" : "28"
    else if (month_nr==4 || month_nr==6 || month_nr==9 || month_nr==11)
        return 30
    return 31
}

