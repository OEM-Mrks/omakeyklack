#!/usr/bin/env bash
# install.sh startet die App - aber nur, wo es etwas zu sehen gibt.
#
# Zwei Dinge muessen stimmen: Ohne grafische Sitzung darf nichts gestartet
# werden (im Container oder ueber SSH waere das nur ein Fehlschlag), und
# eine schon laufende Instanz muss vor dem Austausch der Dateien beendet
# werden. Ohne das liefe nach einem Update der alte Stand weiter - und weil
# die App eine Einzelinstanz ist, holte ein Start die alte bloss nach vorn.
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

# -- 1. Ohne Anzeige wird nichts gestartet ------------------------------

ausgabe="$(cd "$REPO" && env -u WAYLAND_DISPLAY -u DISPLAY \
  PREFIX="$WORK/local" HOME="$WORK/home" \
  ./install.sh --no-deps < /dev/null 2>&1)"

if grep -qE 'Gestartet|Neu gestartet' <<< "$ausgabe"; then
  fail "ohne Anzeige wurde trotzdem gestartet"
else
  ok "ohne Anzeige wird nicht gestartet"
fi
grep -q 'Fertig. Starten mit' <<< "$ausgabe" \
  && ok "stattdessen kommt der Hinweis zum Starten von Hand" \
  || fail "der Hinweis zum Starten von Hand fehlt"

# -- 2. Der Prozesshelfer wird mitinstalliert ---------------------------

# omakeyklack-uninstall braucht ihn spaeter; aus dem Quellbaum kann er ihn
# dann nicht mehr holen.
[ -f "$WORK/local/lib/omakeyklack/prozesse.sh" ] \
  && ok "prozesse.sh liegt im lib-Verzeichnis" \
  || fail "prozesse.sh wurde nicht mitinstalliert"

# -- 3. Eine laufende Instanz wird vorher beendet -----------------------

mkdir -p "$WORK/stub/omakeyklack"
cat > "$WORK/stub/omakeyklack/__main__.py" <<'PY'
import time
time.sleep(120)
PY
PYTHONPATH="$WORK/stub" python3 -m omakeyklack --tray &
STUB_PID=$!
sleep 1
kill -0 "$STUB_PID" 2>/dev/null || { echo "Testaufbau: Stellvertreter startete nicht"; exit 2; }

ausgabe="$(cd "$REPO" && env -u WAYLAND_DISPLAY -u DISPLAY \
  PREFIX="$WORK/local" HOME="$WORK/home" \
  ./install.sh --no-deps < /dev/null 2>&1)"

if kill -0 "$STUB_PID" 2>/dev/null; then
  fail "die laufende Instanz lief waehrend des Austauschs weiter"
else
  ok "laufende Instanz wird vor dem Austausch beendet"
fi
grep -q 'Laufende Instanz beendet' <<< "$ausgabe" \
  && ok "das Beenden wird gemeldet" \
  || fail "das Beenden blieb unerwaehnt"

# -- 4. --no-start wird beachtet ----------------------------------------

# Mit vorgetaeuschter Anzeige - sonst greift schon die Pruefung aus 1.
ausgabe="$(cd "$REPO" && env WAYLAND_DISPLAY=wayland-test \
  PREFIX="$WORK/local" HOME="$WORK/home" \
  ./install.sh --no-deps --no-start < /dev/null 2>&1)"
if grep -qE 'Gestartet|Neu gestartet' <<< "$ausgabe"; then
  fail "--no-start wurde uebergangen"
else
  ok "--no-start verhindert den Start"
fi

exit "$FAILED"
