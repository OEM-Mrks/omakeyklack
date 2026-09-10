#!/usr/bin/env bash
# Prueft die Einrichtung gegen ein nacktes Arch im Container.
#
#   tests/fresh-install.sh          aktueller Arbeitsstand
#   tests/fresh-install.sh --curl   der veroeffentlichte Einzeiler (boot.sh)
#
# Braucht Docker und eine Netzverbindung und laeuft ein paar Minuten - der
# Container laedt rund 130 MB Pakete und baut wayvibes aus dem Quelltext.
# Darum nicht Teil des normalen Testlaufs.
#
# Dieser Test hat schon zwei Fehler gefunden, die auf der Entwicklermaschine
# unsichtbar waren: ein ungesetztes $USER, das den Doctor mittendrin abbrach,
# und die Rueckfragen, die hinter "curl | bash" ins Leere liefen.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
IMAGE="omakeyklack-test"
MODE="lokal"

[ "${1:-}" = "--curl" ] && MODE="curl"

FAILED=0
ok()   { echo "OK   $1"; }
fail() { echo "FEHL $1"; FAILED=1; }

command -v docker >/dev/null || { echo "Docker fehlt."; exit 2; }

echo "Baue Testbild ($IMAGE) ..."
docker build -q -t "$IMAGE" -f "$HERE/Dockerfile" "$HERE" >/dev/null || {
  echo "Bild liess sich nicht bauen."; exit 2; }

LOG="$(mktemp)"
trap 'rm -f "$LOG"' EXIT

if [ "$MODE" = curl ]; then
  echo "Lauf: veroeffentlichter Einzeiler"
  docker run --rm "$IMAGE" bash -lc '
    curl -fsSL https://raw.githubusercontent.com/OEM-Mrks/omakeyklack/main/boot.sh |
      bash -s -- --yes
    echo "INSTALL-RUECKGABE: $?"
    export PATH="$HOME/.local/bin:$PATH"
    omakeyklack --version
    omakeyklack --check; echo "CHECK-RUECKGABE: $?"
    omakeyklack-uninstall
    ls "$HOME/.local/bin" | grep -c omakeyklack | sed "s/^/RESTE: /"
  ' > "$LOG" 2>&1
else
  echo "Lauf: Arbeitsstand aus $REPO"
  # Nur lesend einhaengen und im Container kopieren - der Lauf soll den
  # Arbeitsbaum nicht anfassen.
  docker run --rm -v "$REPO:/quelle:ro" "$IMAGE" bash -lc '
    cp -r /quelle ~/omakeyklack && cd ~/omakeyklack
    ./install.sh --yes
    echo "INSTALL-RUECKGABE: $?"
    export PATH="$HOME/.local/bin:$PATH"
    omakeyklack --version
    omakeyklack --check; echo "CHECK-RUECKGABE: $?"
    omakeyklack-uninstall
    ls "$HOME/.local/bin" | grep -c omakeyklack | sed "s/^/RESTE: /"
  ' > "$LOG" 2>&1
fi

# -- Auswerten ---------------------------------------------------------

want() {
  local name="$1" pattern="$2"
  if grep -qE -- "$pattern" "$LOG"; then ok "$name"; else fail "$name"; fi
}

want "fehlende Systempakete erkannt"   '✗ fehlt: .*gtk3'
want "Systempakete nachinstalliert"    '✓ nachinstalliert'
want "fehlendes wayvibes erkannt"      '✗ nicht installiert'
want "wayvibes gebaut und installiert" '^  ✓ installiert'
want "Python-Anbindung traegt"         '✓ gi, Gtk 3.0, AyatanaAppIndicator3'
want "Gruppe input eingetragen"        '✓ eingetragen'
want "Soundpacks geholt"               '✓ [0-9]+ Packs nach'
want "install.sh meldet Erfolg"        'INSTALL-RUECKGABE: 0'
want "zweiter Lauf ist gruen"          'CHECK-RUECKGABE: 0'
want "Deinstallation raeumt auf"       'RESTE: 0'

# Der Abbruch, an dem der Doctor frueher stehenblieb.
if grep -q 'unbound variable' "$LOG"; then
  fail "Skript stolpert ueber eine ungesetzte Variable"
else
  ok "keine ungesetzten Variablen"
fi

if [ "$FAILED" != 0 ]; then
  echo
  echo "--- letzte 30 Zeilen des Laufs ---"
  tail -30 "$LOG"
fi
exit "$FAILED"
