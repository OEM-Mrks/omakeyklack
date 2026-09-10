#!/usr/bin/env bash
# omakeyklack installieren. Standard: nach ~/.local, kein root noetig.
#
#   ./install.sh                 Voraussetzungen pruefen (und auf Nachfrage
#                                nachinstallieren), dann installieren
#   ./install.sh --yes           dasselbe ohne Rueckfragen
#   ./install.sh --no-deps       nur Dateien kopieren, nichts pruefen
#   ./install.sh --no-start      danach nicht starten
#   PREFIX=/usr/local sudo ./install.sh
set -euo pipefail

PREFIX="${PREFIX:-$HOME/.local}"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

CHECK_DEPS=1
STARTEN=1
DOCTOR_ARGS=(--fix)
for arg in "$@"; do
  case "$arg" in
    --no-deps) CHECK_DEPS=0 ;;
    --no-start) STARTEN=0 ;;
    --yes|-y) DOCTOR_ARGS+=(--yes) ;;
    --help|-h) sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unbekannte Option: $arg" >&2; exit 2 ;;
  esac
done

# shellcheck source=bin/prozesse.sh
. "$SOURCE_DIR/bin/prozesse.sh"

LIB_DIR="$PREFIX/lib/omakeyklack"
BIN_DIR="$PREFIX/bin"
BIN="$BIN_DIR/omakeyklack"
APPS_DIR="$PREFIX/share/applications"
ICON_DIR="$PREFIX/share/icons/hicolor/scalable/apps"

# -- Dateien ----------------------------------------------------------

echo "Installiere nach $PREFIX"

# Eine laufende Instanz haelt ihre Module im Speicher und liefe nach dem
# Austausch mit dem alten Stand weiter. Schlimmer noch: die App ist eine
# Einzelinstanz, ein Start der neuen Fassung wuerde nur die alte in den
# Vordergrund holen - das Update saehe aus, als haette es gewirkt.
LIEF=0
if [ -n "$(omakeyklack_instanzen)" ]; then
  LIEF=1
  omakeyklack_beenden || true
fi

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

# Ebenso der Weg wieder hinaus. Wer ueber boot.sh installiert hat, hat
# keinen Quelltext mehr auf der Platte - ohne das hier gaebe es dann kein
# uninstall.sh mehr, das man aufrufen koennte.
install -m 755 "$SOURCE_DIR/uninstall.sh" "$BIN_DIR/omakeyklack-uninstall"

# Den Helfer mit: omakeyklack-uninstall braucht ihn spaeter, und aus dem
# Quellbaum laesst er sich dann nicht mehr holen.
install -m 644 "$SOURCE_DIR/bin/prozesse.sh" "$LIB_DIR/prozesse.sh"

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

# -- Starten -----------------------------------------------------------

starten() {
  [ "$STARTEN" = 1 ] || return 1
  # Ohne grafische Sitzung gibt es weder Tray noch Fenster. Beim Bauen im
  # Container oder ueber SSH waere ein Start nur ein Fehlschlag.
  [ -n "${WAYLAND_DISPLAY:-}" ] || [ -n "${DISPLAY:-}" ] || return 1
  # Abgekoppelt, damit install.sh zurueckkehrt und der Start nicht mit dem
  # Terminal endet.
  setsid "$BIN" --tray >/dev/null 2>&1 < /dev/null &
  return 0
}

echo
if [ "$status" -eq 0 ]; then
  if starten; then
    if [ "$LIEF" = 1 ]; then
      echo "Neu gestartet. Das Tray-Symbol ist wieder da."
    else
      echo "Gestartet - omakeyklack laeuft im Tray."
    fi
    echo "Das Einstellungsfenster oeffnet: omakeyklack"
  else
    echo "Fertig. Starten mit: omakeyklack"
  fi
else
  echo "Dateien sind installiert, aber es fehlt noch etwas (siehe oben)."
  echo "Nach dem Nachruesten pruefen mit: omakeyklack --check"
fi
exit "$status"
