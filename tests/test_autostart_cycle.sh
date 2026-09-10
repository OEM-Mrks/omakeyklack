#!/usr/bin/env bash
# Der Autostart ueber einen ganzen Lebenszyklus: einrichten, deinstallieren,
# wieder einrichten.
#
# Der Fall, der hier abgesichert wird, ist real aufgetreten: uninstall.sh
# loeschte den Autostart-Eintrag, liess den Merker in der Konfiguration
# aber stehen. Bei der naechsten Installation hiess es dann "schon
# vorbelegt" - und der Autostart blieb fuer immer aus, obwohl ihn nie
# jemand abgewaehlt hatte.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

export XDG_CONFIG_HOME="$WORK/config"
export HOME="$WORK"           # uninstall.sh raeumt ueber $HOME auf
CONFIG="$XDG_CONFIG_HOME/omakeyklack/config.json"
ENTRY="$XDG_CONFIG_HOME/autostart/omakeyklack.desktop"

FAILED=0
ok()   { echo "OK   $1"; }
fail() { echo "FEHL $1"; FAILED=1; }

# Den ersten Start nachstellen, ohne GTK zu brauchen.
erster_start() {
  PYTHONPATH="$REPO/src" python3 - <<'PY'
import gi
gi.require_version("Gtk", "3.0")
from omakeyklack import autostart
from omakeyklack.app import Omakeyklack
from omakeyklack.config import Config


class Fake:
    _apply_autostart_default = Omakeyklack._apply_autostart_default


fake = Fake()
fake.config = Config()
fake._apply_autostart_default()
PY
}

# -- 1. Einrichten ------------------------------------------------------

erster_start
[ -f "$ENTRY" ] && ok "erste Einrichtung legt den Autostart an" \
                || fail "erste Einrichtung legt keinen Autostart an"
grep -q '"autostart_initialized": true' "$CONFIG" \
  && ok "Merker steht" || fail "Merker fehlt"

# -- 2. Zweiter Start aendert nichts -------------------------------------

rm -f "$ENTRY"          # als haette der Anwender das Haekchen genommen
erster_start
[ -f "$ENTRY" ] && fail "abgewaehlter Autostart kam von selbst zurueck" \
                || ok "abgewaehlter Autostart bleibt aus"

# -- 3. Deinstallieren loescht den Merker mit ----------------------------

erster_start            # wieder anlegen, damit es etwas zu entfernen gibt
PREFIX="$WORK/local" bash "$REPO/uninstall.sh" >/dev/null 2>&1
[ -f "$ENTRY" ] && fail "uninstall.sh liess den Autostart-Eintrag stehen" \
                || ok "uninstall.sh entfernt den Autostart-Eintrag"
if grep -q '"autostart_initialized": false' "$CONFIG" 2>/dev/null; then
  ok "uninstall.sh setzt den Merker zurueck"
else
  fail "uninstall.sh liess den Merker stehen - Neuinstallation bliebe stumm"
fi

# -- 4. Neuinstallation richtet ihn wieder ein ---------------------------

erster_start
[ -f "$ENTRY" ] && ok "Neuinstallation legt den Autostart wieder an" \
                || fail "Neuinstallation legt keinen Autostart an"

# -- 5. Die uebrigen Einstellungen haben das ueberlebt -------------------

if grep -q '"pack"' "$CONFIG" && grep -q '"volume"' "$CONFIG"; then
  ok "Pack und Lautstaerke sind erhalten geblieben"
else
  fail "uninstall.sh hat mehr aus der Konfiguration entfernt als den Merker"
fi

# -- 6. Alte Konfiguration ohne den Schluessel bleibt unangetastet -------

# Vor 0.4.1 gab es autostart_initialized nicht. Wer von dort aktualisiert,
# soll nicht ploetzlich einen Autostart bekommen, den er nie wollte - der
# fehlende Schluessel ist etwas anderes als ein zurueckgesetzter.
rm -f "$ENTRY"
printf '{"pack": "nk-cream", "volume": 1.0}\n' > "$CONFIG"
erster_start
[ -f "$ENTRY" ] && fail "Aktualisierung von vor 0.4.1 legte ungefragt einen Autostart an" \
                || ok "alte Konfiguration ohne Merker bleibt unangetastet"

exit "$FAILED"
