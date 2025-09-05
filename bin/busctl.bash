#!/usr/bin/env bash
set -euo pipefail
# ROOTL:„k-šUŒfDjD4oþ(nÇ£ì¯Èê’(
# .ai-app-studio/…gŸLUŒ‹Sh’óš
ROOT=${ROOT:-$(pwd)}
MBOX="$ROOT/mbox"
mkdir -p "$MBOX"

ts() { date -u +%Y%m%dT%H%M%S.%3NZ; }
rand() { hexdump -n 6 -v -e '/1 "%02x"' /dev/urandom; }
write_json() {
  local dest="$1"; shift
  local tmp="$dest/.tmp-$(ts)-$(rand).json"
  mkdir -p "$dest"
  printf '%s\n' "$*" > "$tmp"
  mv "$tmp" "$dest/$(ts)-$(rand).json"
}

case "${1:-}" in
  spawn)
    shift; # --task T001 --cwd work/T001 --frame ... --goal ... --branch ...
    while [[ $# -gt 0 ]]; do case $1 in
      --task) TASK=$2; shift 2;; --cwd) CWD=$2; shift 2;; --frame) FRAME=$2; shift 2;;
      --goal) GOAL=$2; shift 2;; --branch) BR=$2; shift 2;; *) echo "unknown $1"; exit 1;; esac; done
    [[ -n "${TASK:-}" ]] || { echo "--task required"; exit 1; }
    write_json "$MBOX/bus/in" "{\"id\":\"$(ts)-$(rand)\",\"ts\":$(date +%s%3N),\"from\":\"pmai\",\"to\":\"bus\",\"type\":\"spawn\",\"task_id\":\"$TASK\",\"data\":{\"cwd\":\"${CWD:-work/$TASK}\",\"frame\":\"${FRAME:-}\",\"goal\":\"${GOAL:-}\",\"branch\":\"${BR:-feat/$TASK}\"}}"
    ;;
  send)
    shift; while [[ $# -gt 0 ]]; do case $1 in
      --to) TO=$2; shift 2;; --type) T=$2; shift 2;; --data) D=$2; shift 2;; *) echo "unknown $1"; exit 1;; esac; done
    [[ -n "${TO:-}" ]] || { echo "--to required"; exit 1; }
    [[ -n "${T:-}" ]] || { echo "--type required"; exit 1; }
    [[ -n "${D:-}" ]] || { echo "--data required"; exit 1; }
    AG=$(echo "$TO" | tr ':' '-')
    write_json "$MBOX/$AG/in" "{\"id\":\"$(ts)-$(rand)\",\"ts\":$(date +%s%3N),\"from\":\"pmai\",\"to\":\"$TO\",\"type\":\"$T\",\"task_id\":\"${TO#impl:}\",\"data\":$D}"
    ;;
  post)
    shift; while [[ $# -gt 0 ]]; do case $1 in
      --from) FROM=$2; shift 2;; --type) T=$2; shift 2;; --task) TASK=$2; shift 2;; --data) D=$2; shift 2;; *) echo "unknown $1"; exit 1;; esac; done
    [[ -n "${FROM:-}" ]] || { echo "--from required"; exit 1; }
    [[ -n "${T:-}" ]] || { echo "--type required"; exit 1; }
    [[ -n "${TASK:-}" ]] || { echo "--task required"; exit 1; }
    [[ -n "${D:-}" ]] || { echo "--data required"; exit 1; }
    write_json "$MBOX/pmai/in" "{\"id\":\"$(ts)-$(rand)\",\"ts\":$(date +%s%3N),\"from\":\"$FROM\",\"to\":\"pmai\",\"type\":\"$T\",\"task_id\":\"$TASK\",\"data\":$D}"
    ;;
  *) echo "usage: busctl spawn|send|post ..."; exit 1;;
esac