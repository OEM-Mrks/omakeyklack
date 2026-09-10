#!/usr/bin/env bash
# omakeyklack in einem Schritt installieren:
#
#   curl -fsSL https://raw.githubusercontent.com/OEM-Mrks/omakeyklack/main/boot.sh | bash
#
# Holt die neueste Fassung, entpackt sie in ein Wegwerf-Verzeichnis und
# ruft install.sh auf. Braucht nur curl und tar - kein git.
#
#   ... | bash -s -- --yes       ohne Rueckfragen
#   OMAKEYKLACK_VERSION=v0.4.2 ... | bash    eine bestimmte Fassung
set -euo pipefail

REPO="OEM-Mrks/omakeyklack"
VERSION="${OMAKEYKLACK_VERSION:-latest}"

if [ -t 1 ]; then
  GREEN=$'\033[32m'; RED=$'\033[31m'; DIM=$'\033[2m'; OFF=$'\033[0m'
else
  GREEN=""; RED=""; DIM=""; OFF=""
fi

die() { printf '%sAbbruch:%s %s\n' "$RED" "$OFF" "$1" >&2; exit 1; }
say() { printf '%s\n' "$1"; }

# Hinter "curl | bash" haengt stdin am Skripttext selbst: bash liest von
# dort die naechsten Zeilen, die es noch ausfuehren soll.
#
# Genau darum darf hier NIEMALS "exec < /dev/tty" stehen. Das ersetzt den
# Deskriptor, aus dem bash das Skript liest - der Rest der Datei kommt dann
# vom Terminal, also nie. Sichtbar ist das ausschliesslich mit echtem
# Terminal; ohne eines wird die Zeile uebersprungen und alles scheint zu
# gehen. Siehe tests/test_boot_pipe.sh.
#
# Das Terminal bekommt stattdessen nur das Kind, weiter unten beim Aufruf
# von install.sh. Der eigene stdin bleibt, wo er ist.

command -v curl >/dev/null || die "curl fehlt."
command -v tar >/dev/null || die "tar fehlt."

# Als root landete alles unter /root/.local - fast nie gemeint.
if [ "$(id -u)" = 0 ]; then
  die "Bitte als normaler Benutzer starten, nicht als root.
       install.sh fragt selbst nach, wo es root braucht."
fi

# -- Fassung bestimmen -------------------------------------------------

if [ "$VERSION" = "latest" ]; then
  say "Suche die neueste Fassung ..."
  # Ohne jq: der Tag steht als erstes "tag_name"-Feld in der Antwort.
  VERSION="$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" 2>/dev/null |
    sed -n 's/.*"tag_name": *"\([^"]*\)".*/\1/p' | head -1)"
  # Kein Release erreichbar (GitHub-Ausfall, Ratelimit)? Dann main nehmen,
  # statt hier stehenzubleiben.
  [ -n "$VERSION" ] || { VERSION="main"; say "Kein Release gefunden - nehme main."; }
fi

say "Installiere omakeyklack $VERSION"

# -- Holen und auspacken -----------------------------------------------

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

curl -fsSL "https://codeload.github.com/$REPO/tar.gz/$VERSION" -o "$TMP/quelle.tar.gz" ||
  die "Download fehlgeschlagen - gibt es die Fassung '$VERSION'?"

tar -xzf "$TMP/quelle.tar.gz" -C "$TMP" || die "Archiv liess sich nicht entpacken."

# Das Archiv enthaelt genau ein Verzeichnis, dessen Name die Fassung traegt.
SOURCE="$(find "$TMP" -maxdepth 1 -type d -name 'omakeyklack-*' | head -1)"
[ -n "$SOURCE" ] || die "Archiv sieht nicht aus wie erwartet."
[ -x "$SOURCE/install.sh" ] || die "install.sh fehlt im Archiv."

# -- Uebergeben --------------------------------------------------------

printf '%s\n' "${DIM}Quelltext liegt voruebergehend in $SOURCE${OFF}"
say ""
cd "$SOURCE"
# "set -e" wuerde hier abbrechen, bevor der Rueckgabewert ausgewertet ist -
# und die Abschlusszeilen kaemen nie.
status=0
if [ -t 0 ]; then
  # Regulaerer Aufruf: stdin ist schon das Terminal.
  ./install.sh "$@" || status=$?
elif : 2>/dev/null < /dev/tty; then
  # Hinter der Pipe: dem Kind das Terminal geben, damit Rueckfragen
  # ankommen. Nur dem Kind - der eigene stdin traegt noch den Skripttext.
  ./install.sh "$@" < /dev/tty || status=$?
else
  # Weder Terminal noch Rueckfragemoeglichkeit. Nicht den Skripttext
  # weiterreichen: install.sh wuerde sonst die eigenen naechsten Zeilen
  # lesen.
  ./install.sh "$@" < /dev/null || status=$?
fi

say ""
if [ "$status" -eq 0 ]; then
  printf '%somakeyklack ist eingerichtet.%s\n' "$GREEN" "$OFF"
fi
printf '%sDeinstallieren spaeter mit: omakeyklack-uninstall%s\n' "$DIM" "$OFF"
exit "$status"
