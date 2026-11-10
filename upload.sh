#!/bin/bash
# Upload staged episodes as GitHub release assets, skipping ones already there.
# Usage: ./upload.sh STAGE_DIR   (STAGE_DIR/<lang>/<asset>.mp3, made by build_feeds.py --stage)
# Safe to re-run: it resumes where it left off.
set -u
REPO="yairraz89/pedsboards-podcast"
STAGE="$1"

for lang in en he; do
  gh release view "$lang" -R "$REPO" >/dev/null 2>&1 || \
    gh release create "$lang" -R "$REPO" --title "Peds Boards – $lang" --notes "Audio files for the $lang feed." || exit 1
  existing=$(gh release view "$lang" -R "$REPO" --json assets -q '.assets[].name')
  batch=()
  flush() {
    [ ${#batch[@]} -eq 0 ] && return
    for try in 1 2 3; do
      gh release upload "$lang" -R "$REPO" --clobber "${batch[@]}" && break
      echo "retry $try for ${batch[*]}"; sleep 10
    done
    echo "$(date +%T) $lang uploaded through $(basename "${batch[${#batch[@]}-1]}")"
    batch=()
  }
  for f in "$STAGE/$lang"/*.mp3; do
    grep -qx "$(basename "$f")" <<<"$existing" && continue
    batch+=("$f")
    [ ${#batch[@]} -ge 10 ] && flush
  done
  flush
done
echo "ALL DONE"
