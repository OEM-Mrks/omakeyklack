#!/usr/bin/env bash
# Entfernt, was install.sh angelegt hat. Die Konfiguration unter
# ~/.config/omakeyklack bleibt erhalten.
set -euo pipefail

PREFIX="${PREFIX:-$HOME/.local}"

# -- Laufende Instanz beenden ------------------------------------------

# Ohne das laeuft die App nach der Deinstallation munter weiter: Python hat
# die Module beim Start in den Speicher gelesen, das Loeschen der Dateien
# merkt der Prozess nicht. Zurueck blieb ein Tray-Symbol ohne Programm.
#
# Der Helfer liegt entweder neben diesem Skript (Aufruf aus dem Quellbaum)
# oder im installierten lib-Verzeichnis, das gleich geloescht wird.
HIER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for kandidat in "$HIER/bin/prozesse.sh" "$PREFIX/lib/omakeyklack/prozesse.sh"; do
  if [ -f "$kandidat" ]; then
    # shellcheck source=bin/prozesse.sh
    . "$kandidat"
    break
  fi
done

if declare -F omakeyklack_beenden >/dev/null; then
  omakeyklack_beenden || true
else
  echo "Warnung: prozesse.sh nicht gefunden - eine laufende App laeuft weiter." >&2
fi

rm -rf "$PREFIX/lib/omakeyklack"
rm -f "$PREFIX/bin/omakeyklack"
rm -f "$PREFIX/bin/omakeyklack-doctor"
# Zum Schluss die eigene installierte Kopie. Das Skript liegt zu diesem
# Zeitpunkt schon vollstaendig im Speicher, das Loeschen stoert es nicht.
rm -f "$PREFIX/bin/omakeyklack-uninstall"
rm -f "$PREFIX/share/applications/omakeyklack.desktop"
rm -f "$PREFIX"/share/icons/hicolor/scalable/apps/omakeyklack*.svg
rm -f "$HOME/.config/autostart/omakeyklack.desktop"

# Der Autostart-Eintrag ist gerade geloescht worden - der Merker in der
# Konfiguration darf das nicht ueberleben. Sonst hiesse es bei einer
# spaeteren Neuinstallation "schon vorbelegt", und der Autostart bliebe
# aus, obwohl ihn nie jemand abgewaehlt hat. Deinstallieren ist eben nicht
# dasselbe wie "will ich nicht".
CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/omakeyklack/config.json"
if [ -f "$CONFIG" ] && command -v python3 >/dev/null; then
  python3 - "$CONFIG" <<'MARKER' || true
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except (OSError, ValueError):
    raise SystemExit(0)
# Ausdruecklich auf false, nicht entfernen: nur so unterscheidet der
# naechste Start ein Zuruecksetzen von einer alten Konfiguration.
if isinstance(data, dict) and data.get("autostart_initialized") is not False:
    data["autostart_initialized"] = False
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
MARKER
fi

command -v update-desktop-database >/dev/null && \
    update-desktop-database "$PREFIX/share/applications" || true

echo "Entfernt. Konfiguration liegt weiter unter ~/.config/omakeyklack."
