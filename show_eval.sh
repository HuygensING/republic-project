#!/bin/sh

result_files=$(ls nohup-ner-*)

for res_file in $result_files; do
    echo "${res_file}"
    lines=$(cat ${res_file} | grep -A 3 "By class:" | grep -E "[A-Z]{3}")
    echo "${lines}"
done
