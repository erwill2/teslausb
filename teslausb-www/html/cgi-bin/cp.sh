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

cd "$DOCUMENT_ROOT/${urlargs[0]}"

cat << EOF
HTTP/1.0 200 OK
Content-type: text/plain

EOF
if cp "${urlargs[@]:1}"  &> /dev/null
then
  echo OK
else
  echo FAILED
fi
