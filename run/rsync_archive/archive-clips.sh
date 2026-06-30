#!/bin/bash -eu

while [ -n "${1+x}" ]
do
  if ! (rsync -avhRL --timeout=60 --remove-source-files --no-perms --omit-dir-times \
        --stats --log-file=/tmp/archive-rsync-cmd.log --ignore-missing-args \
        --files-from="$2" "$1" "$RSYNC_USER@$RSYNC_SERVER:$RSYNC_PATH" &> /tmp/rsynclog || [[ "$?" = "24" ]] )
  then
    cat /tmp/archive-rsync-cmd.log /tmp/rsynclog > /tmp/archive-error.log
    exit 1
  fi
  # WORKAROUND for rsync bug 10494 where it fails to remove symlinks
  (cd "$1" && tr '\n' '\0' < "$2" | xargs -0 -r rm -f)
  shift 2
done
