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

command -v update-desktop-database >/dev/null && \
    update-desktop-database "$PREFIX/share/applications" || true

echo "Entfernt. Konfiguration liegt weiter unter ~/.config/omakeyklack."
