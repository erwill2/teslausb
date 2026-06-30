#!/bin/bash

# Escape HTML special characters to prevent XSS
MESSAGE=$(printf '%s\n' "$1" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g; s/"/\&quot;/g; s/'\''/\&#39;/g')

cat << EOF
HTTP/1.0 200 OK
Content-type: text/html

<html>
<head>
  <meta http-equiv="refresh" content="3; URL=/" />
</head>
<body>
  <p>$MESSAGE</p>
</body>
</html>
EOF
