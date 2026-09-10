#!/usr/bin/env bash
# omakeyklack installieren. Standard: nach ~/.local, kein root noetig.
#
#   ./install.sh                 Voraussetzungen pruefen (und auf Nachfrage
#                                nachinstallieren), dann installieren
#   ./install.sh --yes           dasselbe ohne Rueckfragen
#   ./install.sh --no-deps       nur Dateien kopieren, nichts pruefen
#   PREFIX=/usr/local sudo ./install.sh
set -euo pipefail

PREFIX="${PREFIX:-$HOME/.local}"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

CHECK_DEPS=1
DOCTOR_ARGS=(--fix)
for arg in "$@"; do
  case "$arg" in
    --no-deps) CHECK_DEPS=0 ;;
    --yes|-y) DOCTOR_ARGS+=(--yes) ;;
    --help|-h) sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unbekannte Option: $arg" >&2; exit 2 ;;
  esac
done

LIB_DIR="$PREFIX/lib/omakeyklack"
BIN_DIR="$PREFIX/bin"
BIN="$BIN_DIR/omakeyklack"
APPS_DIR="$PREFIX/share/applications"
ICON_DIR="$PREFIX/share/icons/hicolor/scalable/apps"

# -- Dateien ----------------------------------------------------------

echo "Installiere nach $PREFIX"

install -d "$LIB_DIR" "$BIN_DIR" "$APPS_DIR" "$ICON_DIR"

rm -rf "${LIB_DIR:?}/omakeyklack"
cp -r "$SOURCE_DIR/src/omakeyklack" "$LIB_DIR/omakeyklack"
find "$LIB_DIR" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true

cat > "$BIN" <<LAUNCHER
#!/usr/bin/env bash
exec env PYTHONPATH="$LIB_DIR\${PYTHONPATH:+:\$PYTHONPATH}" \\
    python3 -m omakeyklack "\$@"
LAUNCHER
chmod +x "$BIN"

# Der Doctor wird mitinstalliert: "omakeyklack --check" ruft ihn auf, und
# wer spaeter etwas kaputt macht, kann ihn direkt starten.
install -m 755 "$SOURCE_DIR/bin/omakeyklack-doctor" "$BIN_DIR/omakeyklack-doctor"

install -m 644 "$SOURCE_DIR/data/omakeyklack.desktop" "$APPS_DIR/omakeyklack.desktop"
install -m 644 "$SOURCE_DIR"/data/icons/hicolor/scalable/apps/*.svg "$ICON_DIR/"

command -v update-desktop-database >/dev/null && update-desktop-database "$APPS_DIR" || true
command -v gtk-update-icon-cache >/dev/null && \
    gtk-update-icon-cache -qtf "$PREFIX/share/icons/hicolor" 2>/dev/null || true

# -- Voraussetzungen --------------------------------------------------

# Erst jetzt, damit "omakeyklack-doctor" schon an seinem Platz liegt und
# der PATH-Hinweis auf die fertige Installation zeigt.
status=0
if [ "$CHECK_DEPS" = 1 ]; then
  echo
  PREFIX="$PREFIX" "$BIN_DIR/omakeyklack-doctor" "${DOCTOR_ARGS[@]}" || status=$?
else
  echo
  echo "Voraussetzungen uebersprungen (--no-deps)."
  echo "Spaeter pruefen mit: omakeyklack --check"
fi

echo
if [ "$status" -eq 0 ]; then
  echo "Fertig. Starten mit: omakeyklack"
else
  echo "Dateien sind installiert, aber es fehlt noch etwas (siehe oben)."
  echo "Nach dem Nachruesten pruefen mit: omakeyklack --check"
fi
exit "$status"
