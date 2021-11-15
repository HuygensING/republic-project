#!/usr/bin/env bash

log_status() {
  if [[ ! -f "$1" ]];
    then echo 'usage: ./log-status.sh <log-file>'; return;
  fi

  docker stats importer --no-stream

  printf '\n'
  ls -alh $1

  printf '\n--- RECORDS:\n'
  grep -n 'Import record\|resulted in' $1 | tail -n 1

  printf '\n--- RECORD IMAGES:\n'
  grep -n 'Handling img' $1 | tail -n 1

  printf '\n--- ERRORS:\n'
  grep -n 'ERROR' $1 | wc -l

  printf '\n--- VERSIONS:\n'
  printf 'already existed: '
  grep -n "Version already existed" $1 | wc -l
  printf 'newly created:   '
  grep -n "Created version" $1 | wc -l

  printf '\n--- CACHE CLEANED:\n'
  grep -n 'cache' $1 | wc -l

  printf '\n--- TAIL LOG:\n'
  tail -n 20 $1

}

log_status "$1"
