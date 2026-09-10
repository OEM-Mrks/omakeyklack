#!/usr/bin/env bash
# Entfernt, was install.sh angelegt hat. Die Konfiguration unter
# ~/.config/omakeyklack bleibt erhalten.
set -euo pipefail

PREFIX="${PREFIX:-$HOME/.local}"

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
