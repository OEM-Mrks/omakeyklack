#!/usr/bin/env bash
# uninstall.sh muss eine laufende Instanz beenden - und dabei sich selbst
# verschonen.
#
# Beides ist real schiefgegangen: Ohne das Beenden lief die App nach der
# Deinstallation weiter, weil Python die Module laengst im Speicher hatte;
# zurueck blieb ein Tray-Symbol ohne Programm. Und ein naiver
# "pkill -f omakeyklack" trifft dieses Skript mit, denn es heisst selbst
# omakeyklack-uninstall.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
WORK="$(mktemp -d)"

FAILED=0
ok()   { echo "OK   $1"; }
fail() { echo "FEHL $1"; FAILED=1; }

aufraeumen() {
  [ -n "${STUB_PID:-}" ] && kill -KILL "$STUB_PID" 2>/dev/null
  rm -rf "$WORK"
}
trap aufraeumen EXIT

# Ein Stellvertreter mit exakt der Kommandozeile der echten App:
# "python3 -m omakeyklack". Auf die kommt es an - der Name als eigenes
# Argument, nicht irgendwo in einem Pfad.
mkdir -p "$WORK/stub/omakeyklack"
cat > "$WORK/stub/omakeyklack/__main__.py" <<'PY'
import time
time.sleep(120)
PY
PYTHONPATH="$WORK/stub" python3 -m omakeyklack --tray &
STUB_PID=$!
sleep 1

kill -0 "$STUB_PID" 2>/dev/null || { echo "Testaufbau: Stellvertreter startete nicht"; exit 2; }
ok "Stellvertreter laeuft (PID $STUB_PID)"

# Die echte installierte Anordnung nachstellen: der Uninstaller liegt in
# bin, der Prozesshelfer in lib. Genau von dort muss er ihn finden - nackt
# kopiert wuerde der Test etwas pruefen, das es so nie gibt.
export HOME="$WORK/home"
mkdir -p "$HOME" "$WORK/local/bin" "$WORK/local/lib/omakeyklack"
cp "$REPO/uninstall.sh" "$WORK/local/bin/omakeyklack-uninstall"
chmod +x "$WORK/local/bin/omakeyklack-uninstall"
cp "$REPO/bin/prozesse.sh" "$WORK/local/lib/omakeyklack/prozesse.sh"
ausgabe="$(PREFIX="$WORK/local" "$WORK/local/bin/omakeyklack-uninstall" 2>&1)"
rueckgabe=$?

if [ "$rueckgabe" != 0 ]; then
  fail "uninstall.sh brach ab (Rueckgabe $rueckgabe) - hat es sich selbst getroffen?"
else
  ok "uninstall.sh lief bis zum Ende durch"
fi

grep -q 'Entfernt' <<< "$ausgabe" \
  && ok "die Schlusszeile kam noch" \
  || fail "die Schlusszeile fehlt - das Skript starb unterwegs"

if kill -0 "$STUB_PID" 2>/dev/null; then
  fail "laufende Instanz lebt nach der Deinstallation weiter"
else
  ok "laufende Instanz wurde beendet"
fi

grep -q 'Laufende Instanz beendet' <<< "$ausgabe" \
  && ok "das Beenden wird auch gemeldet" \
  || fail "das Beenden blieb unerwaehnt"

# Der erste Lauf hat den Uninstaller mitgenommen - richtig so, er entfernt
# ja auch sich selbst. Fuer den zweiten Lauf also neu hinlegen.
if [ -e "$WORK/local/bin/omakeyklack-uninstall" ]; then
  fail "uninstall.sh hat sich selbst nicht entfernt"
else
  ok "uninstall.sh entfernt auch sich selbst"
fi
mkdir -p "$WORK/local/bin" "$WORK/local/lib/omakeyklack"
cp "$REPO/uninstall.sh" "$WORK/local/bin/omakeyklack-uninstall"
chmod +x "$WORK/local/bin/omakeyklack-uninstall"
cp "$REPO/bin/prozesse.sh" "$WORK/local/lib/omakeyklack/prozesse.sh"

# Ohne laufende Instanz darf es keine Meldung und keinen Fehler geben.
ausgabe2="$(PREFIX="$WORK/local" "$WORK/local/bin/omakeyklack-uninstall" 2>&1)"
rueckgabe2=$?
if [ "$rueckgabe2" != 0 ]; then
  fail "zweiter Lauf ohne laufende Instanz schlug fehl"
elif grep -q 'Laufende Instanz' <<< "$ausgabe2"; then
  fail "zweiter Lauf meldet eine Instanz, die es nicht gibt"
else
  ok "zweiter Lauf ohne Instanz bleibt still"
fi

exit "$FAILED"
