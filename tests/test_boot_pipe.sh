#!/usr/bin/env bash
# boot.sh muss hinter einer Pipe durchlaufen - auch und gerade mit echtem
# Terminal.
#
# Der Fehler, den dieser Test abdeckt, war unsichtbar: "exec < /dev/tty" in
# boot.sh ersetzte den Deskriptor, aus dem bash das Skript selbst liest.
# Der Rest der Datei kam dann vom Terminal, also nie - und der Anwender sah
# nach "curl ... | bash" ueberhaupt nichts. Ohne Terminal wurde die Zeile
# uebersprungen, weshalb weder der normale Testlauf noch der Container je
# etwas gemerkt haben. Darum hier ein Pseudo-Terminal ueber "script".
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOOT="$HERE/../boot.sh"

FAILED=0
ok()   { echo "OK   $1"; }
fail() { echo "FEHL $1"; FAILED=1; }

command -v script >/dev/null || { echo "util-linux (script) fehlt."; exit 2; }

# Eine Fassung, die es nicht gibt: dann ueberspringt boot.sh die Abfrage
# nach dem neuesten Release und scheitert gleich am Download. Uns
# interessiert nur, ob es ueberhaupt bis dorthin kommt.
lauf() {
  timeout 60 script -qec \
    "OMAKEYKLACK_VERSION=v0.0.0-gibtsnicht bash -c 'cat \"$BOOT\" | bash'" \
    /dev/null < /dev/null 2>&1
}

ausgabe="$(lauf)"
rueckgabe=$?

if [ "$rueckgabe" = 124 ]; then
  fail "boot.sh blieb mit Terminal haengen (Zeitueberschreitung)"
elif ! grep -q 'Installiere omakeyklack' <<< "$ausgabe"; then
  fail "boot.sh gab mit Terminal nichts aus - liest bash das Skript noch?"
  echo "    erhalten: ${ausgabe:0:200}"
else
  ok "boot.sh laeuft hinter der Pipe mit Terminal durch"
fi

# Es muss auch bis zur Fehlerbehandlung kommen, nicht nur bis zur ersten
# Ausgabe - sonst waere das Skript irgendwo dazwischen stehengeblieben.
if grep -qE 'Abbruch|Download fehlgeschlagen' <<< "$ausgabe"; then
  ok "boot.sh erreicht seine eigene Fehlerbehandlung"
else
  fail "boot.sh kam nicht bis zur Fehlerbehandlung"
fi

# Und ohne Terminal darf sich nichts geaendert haben.
ohne="$(OMAKEYKLACK_VERSION=v0.0.0-gibtsnicht bash -c "cat '$BOOT' | bash" 2>&1)"
if grep -q 'Installiere omakeyklack' <<< "$ohne"; then
  ok "boot.sh laeuft auch ohne Terminal durch"
else
  fail "boot.sh gibt ohne Terminal nichts aus"
fi

# Der Griff nach /dev/tty darf weiterhin still bleiben.
if grep -q '/dev/tty' <<< "$ohne"; then
  fail "erfolgloser Griff nach /dev/tty meldet sich lautstark"
else
  ok "kein Laerm, wenn /dev/tty fehlt"
fi

exit "$FAILED"
