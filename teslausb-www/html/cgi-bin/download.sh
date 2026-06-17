#!/bin/bash

declare -a urlargs
IFS='&' read -r -a urlargs <<<"$QUERY_STRING" 

declare -i len=${#urlargs[@]}
for ((i=0; i<${len}; i++ ))
do
  val="${urlargs[i]//+/ }"
  urlargs[i]="$(echo -e "${val//%/\\x}")"
  if [[ "${urlargs[i]}" == *".."* ]]; then
    echo "HTTP/1.0 400 Bad Request"
    echo "Content-type: text/plain"
    echo
    echo "Bad request"
    exit 1
  fi
done

for arg in "${urlargs[@]}"; do
  if [[ "$arg" == /* ]] || [[ "$arg" == *".."* ]]; then
    cat << EOF
HTTP/1.0 400 Bad Request
Content-type: text/plain

FAILED
EOF
    exit 0
  fi
done

dir="$DOCUMENT_ROOT/${urlargs[0]}"
file="$DOCUMENT_ROOT/${urlargs[0]}/${urlargs[1]}"
if [[ "$len" == 2 && -d "$dir" && -f "$file" ]]
then
  str=$(file --mime-type "$file")
  mime=${str##*: }
  echo "HTTP/1.0 200 OK"
  echo "Content-type: $mime"
  echo
  cat "$file"
else
  echo "HTTP/1.0 200 OK"
  echo "Content-type: text/plain"
  echo
  echo "Bad request"
fi
