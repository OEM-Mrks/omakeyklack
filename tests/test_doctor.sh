#!/usr/bin/env bash
# Prueft omakeyklack-doctor gegen gestellte Umgebungen.
#
# Der Doctor ist die Stelle, an der eine frische Installation haengen
# bleibt oder durchlaeuft - er muss fehlende Voraussetzungen wirklich
# melden und darf ungefragt nichts installieren.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCTOR="$HERE/../bin/omakeyklack-doctor"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

FAILED=0
ok()   { echo "OK   $1"; }
fail() { echo "FEHL $1"; FAILED=1; }

check() {
  local name="$1" expect_exit="$2" expect_text="$3" output actual
  shift 3
  output="$("$@" 2>&1)"
  actual=$?
  if [ "$actual" != "$expect_exit" ]; then
    fail "$name (Rueckgabe $actual, erwartet $expect_exit)"
    return
  fi
  if [ -n "$expect_text" ] && ! grep -qi -- "$expect_text" <<< "$output"; then
    fail "$name (Text '$expect_text' fehlt)"
    return
  fi
  ok "$name"
}

# -- 1. Leerer Packs-Ordner wird gemeldet ------------------------------

mkdir -p "$WORK/leer"
check "leerer Packs-Ordner faellt auf" 1 "keine Packs" \
  env OMAKEYKLACK_PACKS_DIR="$WORK/leer" "$DOCTOR"

# -- 2. Ohne Terminal wird nichts installiert --------------------------

# --fix darf ohne Rueckfragemoeglichkeit nicht einfach loslegen; sonst
# laedt ein Skriptaufruf ungefragt 58 MB herunter.
check "--fix ohne Terminal laedt nichts" 1 "keine Packs" \
  env OMAKEYKLACK_PACKS_DIR="$WORK/leer" "$DOCTOR" --fix < /dev/null
if [ -n "$(ls -A "$WORK/leer" 2>/dev/null)" ]; then
  fail "--fix ohne Terminal hat trotzdem geschrieben"
else
  ok "--fix ohne Terminal hat nichts geschrieben"
fi

# -- 3. Fehlendes wayvibes wird gemeldet -------------------------------

# PATH so bauen, dass alles da ist ausser wayvibes.
mkdir -p "$WORK/bin"
for cmd in bash pacman python3 id getent grep sed tr mktemp curl tar sort uniq cat; do
  target="$(command -v "$cmd" 2>/dev/null)" && ln -sf "$target" "$WORK/bin/$cmd"
done
check "fehlendes wayvibes faellt auf" 1 "wayvibes" \
  env PATH="$WORK/bin" OMAKEYKLACK_PACKS_DIR="$WORK/leer" bash "$DOCTOR"

# -- 4. Vorhandene Packs werden gezaehlt -------------------------------

mkdir -p "$WORK/voll/pack-a" "$WORK/voll/pack-b"
check "vorhandene Packs werden gezaehlt" 0 "2 Pack" \
  env OMAKEYKLACK_PACKS_DIR="$WORK/voll" "$DOCTOR"

# -- 5. --help bricht nichts an ----------------------------------------

check "--help beschreibt den Aufruf" 0 "nur pruefen" "$DOCTOR" --help

exit "$FAILED"
