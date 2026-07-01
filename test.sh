#!/bin/bash -eu

output=$(QUERY_STRING="test&../foo" DOCUMENT_ROOT=/tmp teslausb-www/html/cgi-bin/download.sh || true)

if [[ "$output" != *"HTTP/1.0 400 Bad Request"* ]] || [[ "$output" != *"Bad request"* ]]
then
  echo "$output"
  exit 1
fi
