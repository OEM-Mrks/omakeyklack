#!/usr/bin/env bash
# omakeyklack lokal installieren (Standard: ~/.local, kein root noetig).
#   ./install.sh              -> nach ~/.local
#   PREFIX=/usr/local sudo ./install.sh
set -euo pipefail

PREFIX="${PREFIX:-$HOME/.local}"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

LIB_DIR="$PREFIX/lib/omakeyklack"
BIN="$PREFIX/bin/omakeyklack"
APPS_DIR="$PREFIX/share/applications"
ICON_DIR="$PREFIX/share/icons/hicolor/scalable/apps"

echo "Installiere nach $PREFIX"

install -d "$LIB_DIR" "$PREFIX/bin" "$APPS_DIR" "$ICON_DIR"

rm -rf "${LIB_DIR:?}/omakeyklack"
cp -r "$SOURCE_DIR/src/omakeyklack" "$LIB_DIR/omakeyklack"
find "$LIB_DIR" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true

cat > "$BIN" <<LAUNCHER
#!/usr/bin/env bash
exec env PYTHONPATH="$LIB_DIR\${PYTHONPATH:+:\$PYTHONPATH}" \\
    python3 -m omakeyklack "\$@"
LAUNCHER
chmod +x "$BIN"

install -m 644 "$SOURCE_DIR/data/omakeyklack.desktop" "$APPS_DIR/omakeyklack.desktop"
install -m 644 "$SOURCE_DIR"/data/icons/hicolor/scalable/apps/*.svg "$ICON_DIR/"

command -v update-desktop-database >/dev/null && update-desktop-database "$APPS_DIR" || true
command -v gtk-update-icon-cache >/dev/null && \
    gtk-update-icon-cache -qtf "$PREFIX/share/icons/hicolor" 2>/dev/null || true

echo "Fertig. Starten mit: omakeyklack"
case ":$PATH:" in
  *":$PREFIX/bin:"*) ;;
  *) echo "Hinweis: $PREFIX/bin liegt nicht in \$PATH." ;;
esac
