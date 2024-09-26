#!/usr/bin/env -S awk -f
# USAGE: awk -f generate-ids.awk PREFIX=P id-list.tsv <entity-names
BEGIN { FS=OFS="\t" }
1==NR { list=FILENAME }
FNR==NR { ids[$2]=$1
    if ($1>maxid) maxid=$1
    next }
{
    if(!($0 in ids))
        print ids[$0]=sprintf("%07d", ++maxid), $0 >>list
    print $0, PREFIX ids[$0]
}
