#!/bin/bash -eu

if [ "${BASH_SOURCE[0]}" != "$0" ]
then
  echo "${BASH_SOURCE[0]} must be executed, not sourced"
  return 1 # shouldn't use exit when sourced
fi

if [ "${FLOCKED:-}" != "$0" ]
then
  mkdir -p /backingfiles/snapshots
  if FLOCKED="$0" flock -E 99 /backingfiles/snapshots "$0" "$@" || case "$?" in
  99) echo "failed to lock snapshots dir"
      exit 99
      ;;
  *)  exit $?
      ;;
  esac
  then
    # success
    exit 0
  fi
fi

function manage_free_space {
  echo -n manage_free_space > /proc/self/comm

  # Try to make free space equal to 500 MB plus three percent of the total
  # available space. This deletes old snapshots just before running out
  # of space and thus make better use of space.
  local reserve=524288000
  local threepctoftotalspace
  threepctoftotalspace=$(eval "$(stat --file-system --format="echo \$((%b*%S/33))" /backingfiles/cam_disk.bin)")
  reserve=$((reserve+threepctoftotalspace))

  while true
  do
    local freespace
    freespace=$(eval "$(stat --file-system --format="echo \$((%f*%S))" /backingfiles/cam_disk.bin)")
    if [ "$freespace" -gt "$reserve" ]
    then
      sleep 30
      continue
    fi
    if ! stat /backingfiles/snapshots/snap-*/snap.bin > /dev/null 2>&1
    then
      log "Warning: low space for new snapshots, but no snapshots exist."
      log "Please use a larger storage medium or reduce CAM_SIZE"
      sleep 30
      continue
    fi
    # if there's only one snapshot then we likely just took it, so don't immediately delete it
    if [ "$(find /backingfiles/snapshots/ -name snap.bin 2> /dev/null | wc -l)" -lt 2 ]
    then
      # there's only one snapshot and yet we're low on space
      log "Warning: low space for new snapshots, but only one snapshot exists."
      log "Please use a larger storage medium or reduce CAM_SIZE"
      sleep 30
      continue
    fi

    oldest=$(find /backingfiles/snapshots -maxdepth 1 -name 'snap-*' | sort | head -1)
    log "low space, deleting $oldest"
    /root/bin/release_snapshot.sh "$oldest"
    rm -rf "$oldest"
  done
}

manage_free_space
