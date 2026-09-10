# omakeyklack

Tray-App für mechanische Tastatur-Sounds unter Wayland.

[wayvibes](https://github.com/sahaj-b/wayvibes) spielt beim Tippen Sounds ab,
ist aber ein reines Kommandozeilen-Werkzeug: Soundpack und Lautstärke werden
als Startparameter übergeben, zum Wechseln muss man den Prozess von Hand neu
starten. **omakeyklack** legt eine Oberfläche darüber:

- **Tray-Symbol** (StatusNotifierItem) — Sounds an/aus, Soundpack und
  Lautstärke direkt aus dem Menü; das Symbol nimmt die Farbe der Leiste an
  und geht beim Themewechsel von hell auf dunkel mit
- **Soundpacks vorhören** — im Fenster spielt schon beim Überfahren mit der
  Maus eine kurze Hörprobe, beim Auswählen die volle Tippsequenz. Das Pack
  lässt sich also durchhören, ohne es zu aktivieren
- **Lautstärke per Schieberegler**, mit sofortigem Hörbeispiel
- **Tastatur auswählen**, falls mehrere Eingabegeräte in Frage kommen
- **Autostart** — nach der Einrichtung von selbst aktiv, abschaltbar per Häkchen

Getestet unter Hyprland/[Omarchy](https://omarchy.org/), funktioniert aber mit
jedem Wayland-Desktop, dessen Leiste StatusNotifierItem beherrscht (Waybar,
Quickshell, GNOME mit AppIndicator-Erweiterung, KDE …).

> **English:** GUI and tray for `wayvibes` — pick soundpacks with audio preview,
> set volume, toggle typing sounds. The user interface is currently German only;
> pull requests for translations are welcome.

## Installation

```bash
curl -fsSL https://raw.githubusercontent.com/OEM-Mrks/omakeyklack/main/boot.sh | bash
```

Holt die neueste Fassung, entpackt sie in ein Wegwerf-Verzeichnis und ruft
`install.sh` auf. Braucht nur `curl` und `tar` — kein `git`. Das Terminal wird
dabei an `install.sh` durchgereicht, die Rückfragen gehen also nicht verloren,
nur weil das Skript durch eine Pipe kommt.

`... | bash -s -- --yes` beantwortet alles mit ja,
`OMAKEYKLACK_VERSION=v0.4.2 ... | bash` nimmt eine bestimmte Fassung.

### Lieber erst lesen, dann ausführen

Ein Skript aus dem Netz direkt in die Shell zu leiten, verlangt Vertrauen. Wer
das nicht aufbringen möchte — zu Recht —, macht dieselben zwei Schritte
einzeln:

```bash
curl -fsSLO https://raw.githubusercontent.com/OEM-Mrks/omakeyklack/main/boot.sh
less boot.sh        # 90 Zeilen, lesbar in zwei Minuten
bash boot.sh
```

### Aus dem Quelltext

```bash
git clone https://github.com/OEM-Mrks/omakeyklack.git
cd omakeyklack
./install.sh
```

`install.sh` kopiert die Dateien nach `~/.local` (kein root nötig) und prüft
danach der Reihe nach alles, was zum Laufen gebraucht wird. Was fehlt, wird
auf Nachfrage nachinstalliert: die Arch-Pakete, **wayvibes** aus dem AUR, die
Gruppenmitgliedschaft und, wenn noch keins da ist, ein Satz Soundpacks.

Zum Schluss startet die App von selbst und sitzt im Tray — sofern eine
grafische Sitzung da ist. Über SSH oder im Container passiert nichts, dort
gäbe es weder Fenster noch Leiste; `--no-start` schaltet es generell ab.

Lief schon eine Instanz, wird sie vorher beendet und danach neu gestartet.
Das ist bei einem Update Pflicht: Python hat die alten Module längst im
Speicher, und weil die App eine Einzelinstanz ist, holte ein zweiter Start
bloß die alte nach vorn — das Update sähe aus, als hätte es gewirkt.

Ohne Rückfragen geht es mit `./install.sh --yes`, ohne jede Prüfung mit
`./install.sh --no-deps`. Systemweit:

```bash
PREFIX=/usr/local sudo ./install.sh
```

Deinstallieren mit `./uninstall.sh` — oder mit `omakeyklack-uninstall`, das
neben dem Starter mitinstalliert wird. Wer über den Einzeiler installiert hat,
hat schließlich keinen Quelltext mehr auf der Platte. Eine laufende Instanz
wird dabei beendet; ohne das liefe sie weiter, weil Python die Module beim
Start längst in den Speicher gelesen hat, und zurück bliebe ein Tray-Symbol
ohne Programm.

Die Konfiguration unter `~/.config/omakeyklack` und die Soundpacks bleiben
liegen — beides gehört nicht der App.

### Als Paket

```bash
yay -S --needed wayvibes-git && makepkg -si
```

Das PKGBUILD zieht **wayvibes** als echte Abhängigkeit mit — ohne die Engine
spielt omakeyklack keinen einzigen Ton. Die Gruppe `input` und die Soundpacks
bleiben auch hier übrig; `omakeyklack --check --fix` erledigt beides.

### Nachträglich prüfen

```bash
omakeyklack --check         # nur nachsehen
omakeyklack --check --fix   # fehlendes nachinstallieren
```

Dasselbe Skript, das `install.sh` benutzt. Es meldet für jeden Punkt einzeln,
ob er erfüllt ist, und nennt den Befehl, der weiterhilft.

## Voraussetzungen

Das Übliche erledigt `./install.sh`. Von Hand geht es so:

| Was | Paket unter Arch |
|-----|------------------|
| wayvibes (spielt die Töne) | `wayvibes-git` (AUR) |
| Python 3.10+ mit PyGObject | `python`, `python-gobject` |
| GTK 3 | `gtk3` |
| Tray-Anbindung | `libayatana-appindicator` |
| Wiedergabe der Hörproben | `gstreamer`, `gst-plugins-base`, `gst-plugins-good` |

```bash
sudo pacman -S --needed python python-gobject gtk3 libayatana-appindicator \
    gstreamer gst-plugins-base gst-plugins-good
yay -S wayvibes-git
```

Dazu kommen zwei Dinge, die kein Paket erledigen kann:

**Leserecht auf die Tastatur.** wayvibes lauscht per evdev an `/dev/input`;
ohne die Gruppe startet es zwar, hört aber nie eine Taste — von außen sieht
das aus, als täte die App einfach nichts.

```bash
sudo usermod -aG input "$USER"   # danach neu anmelden
```

**Soundpacks.** wayvibes bringt keine mit, also ist die Liste beim ersten
Start leer. Woher sie kommen, steht im nächsten Abschnitt.

## Wenn etwas nicht geht

| Symptom | Ursache | Abhilfe |
|---------|---------|---------|
| `omakeyklack: Kommando nicht gefunden` | `~/.local/bin` nicht im `PATH` | `export PATH="$HOME/.local/bin:$PATH"` in `~/.bashrc` |
| Fenster geht auf, Liste ist leer | keine Soundpacks | `omakeyklack --check --fix` |
| „wayvibes ist nicht installiert" | AUR-Paket fehlt | `yay -S wayvibes-git` |
| Alles sieht richtig aus, aber es klackt nicht | Gruppe `input` fehlt oder die Sitzung kennt sie noch nicht | `sudo usermod -aG input "$USER"`, dann neu anmelden |
| Kein Tray-Symbol, Meldung auf der Konsole | `libayatana-appindicator` fehlt | `sudo pacman -S libayatana-appindicator` |
| Hörproben bleiben stumm, Sounds gehen | GStreamer-Dekoder fehlen | `sudo pacman -S gst-plugins-good` |
| Leiste zeigt gar kein Tray | Leiste kann kein StatusNotifierItem | Waybar/Quickshell mit Tray-Modul, GNOME braucht die AppIndicator-Erweiterung |

Im Zweifel sagt `omakeyklack --check`, welche Zeile davon zutrifft.

## Soundpacks

omakeyklack liest die Packs, die auch wayvibes benutzt:

```
~/.local/share/wayvibes/soundpacks/<pack>/config.json
```

Das ist das Mechvibes-Format. Beide Varianten werden unterstützt:

- `key_define_type: "multi"` / `"multiple"` — eine Audiodatei pro Taste
- `key_define_type: "single"` — ein Sprite, `defines` enthält
  `[offset_ms, dauer_ms]`

Packs gibt es zum Beispiel bei
[mechvibes.com](https://mechvibes.com/sound-packs/). Entpacken, in den Ordner
oben legen, im Fenster auf **Packs neu einlesen** klicken.

Wer nicht suchen will: das wayvibes-Projekt liefert 22 fertige Packs mit, und
`omakeyklack --check --fix` bietet an, sie zu holen (rund 58 MB Download).

## Bedienung

Ohne Argumente öffnet sich das Einstellungsfenster; das Tray-Symbol läuft
parallel weiter:

```bash
omakeyklack          # Fenster + Tray
omakeyklack --tray   # nur Tray (so startet auch der Autostart)
omakeyklack --check  # Voraussetzungen prüfen (--fix installiert nach)
omakeyklack --version
```

Das Fenster zu schließen beendet die App **nicht** — sie läuft im Tray weiter.
Beenden geht über *Beenden* im Tray-Menü.

Im Tray-Menü spielt die Hörprobe beim **Auswählen** eines Packs. Ein Vorhören
schon beim bloßen Überfahren gibt es dort nicht und kann es auch nicht geben:
Das Tray-Menü läuft über das DBusMenu-Protokoll, das nur *opened*, *closed* und
*clicked* kennt — eine Hover-Meldung ist darin nicht vorgesehen. Gezeichnet wird
das Menü von der Leiste, die App bekommt den Mauszeiger nie zu sehen. Wer durch
die Packs hören will, ohne umzuschalten, nimmt das Fenster (*Einstellungen…*);
dort funktioniert das Überfahren.

## Konfiguration

`~/.config/omakeyklack/config.json`:

```json
{
  "pack": "nk-cream",
  "volume": 1.0,
  "device": "",
  "enabled": true,
  "packs_dir": "/home/du/.local/share/wayvibes/soundpacks",
  "preview_on_select": true,
  "preview_on_hover": true,
  "autostart_initialized": true
}
```

- `volume` ist der lineare Faktor, den wayvibes als `-v` bekommt (0–10);
  vorbelegt ist 1.0, wayvibes' eigener Normalwert
- `pack` ist vorbelegt mit `nk-cream` — das liegt dem wayvibes-Projekt bei
  und klingt gedämpft genug für den ersten Start. Wer es nicht hat, bekommt
  das erste vorhandene Pack
- `device` leer lassen heißt: wayvibes sucht die Tastatur selbst aus
- `packs_dir` darf auf ein beliebiges Verzeichnis zeigen
- `preview_on_hover` steuert die Hörprobe beim Überfahren, `preview_on_select`
  die beim Auswählen und beim Ändern der Lautstärke
- `autostart_initialized` ist nur ein Merker: Der Autostart wurde schon einmal
  vorbelegt. Er sagt nichts darüber aus, ob der Autostart gerade an ist — das
  steht in `~/.config/autostart/omakeyklack.desktop`

## Autostart

Beim allerersten Start legt omakeyklack `~/.config/autostart/omakeyklack.desktop`
an und startet danach mit `--tray` von selbst mit. Eine Tray-App, die nach dem
nächsten Anmelden verschwunden ist, wirkt sonst wie eine, die nicht
funktioniert.

Genau einmal allerdings. Wer das Häkchen *Beim Anmelden starten* wegnimmt,
findet es beim nächsten Start nicht wieder gesetzt vor — der Merker
`autostart_initialized` in der Konfiguration verhindert das. Ebenso wird bei
einem Upgrade nichts angelegt: Wer schon eine Konfiguration hat, hat seine
Wahl getroffen.

Deinstallieren ist dabei etwas anderes als abwählen. `uninstall.sh` löscht den
Autostart-Eintrag und setzt den Merker ausdrücklich auf `false` — eine spätere
Neuinstallation richtet ihn also wieder ein. Ohne das bliebe der Autostart nach
einmaligem Deinstallieren für immer aus, obwohl ihn nie jemand abgewählt hat.

Dass der Merker dabei auf `false` gesetzt und nicht entfernt wird, hat einen
Grund: Ein *fehlender* Schlüssel bedeutet „Konfiguration von vor 0.4.1" und
wird in Ruhe gelassen. Nur ein Schlüssel, der ausdrücklich dasteht und `false`
sagt, heißt „zurückgesetzt, bitte neu vorbelegen".

## Wie es funktioniert

omakeyklack startet `wayvibes` als eigenen Kindprozess und übergibt Pack,
Lautstärke und Gerät als Parameter. Weil wayvibes diese Werte nur beim Start
liest, wird der Prozess bei jeder Änderung kurz neu gestartet — das dauert
wenige Millisekunden und fällt beim Tippen nicht auf.

Die Hörproben spielt omakeyklack dagegen selbst über GStreamer ab, unabhängig
von wayvibes. Nur so lässt sich ein Pack vorhören, ohne es vorher zu
aktivieren.

Beim Überfahren mit der Maus wartet die App 220 ms, bevor sie abspielt, und
kürzt auf drei Anschläge. Sonst würde jedes Durchwischen der Liste ein Dutzend
Hörproben übereinanderlegen. Ein `GtkListBoxRow` hat kein eigenes
Ereignisfenster, deshalb lauscht die Liste selbst auf Mausbewegungen und ordnet
die Position über `get_row_at_y` zu.

Beim Beenden wird wayvibes mitgenommen; zusätzlich sorgt `PR_SET_PDEATHSIG`
dafür, dass kein verwaister Prozess weiterklackert, wenn omakeyklack hart
abgeschossen wird.

### Helles und dunkles Tray-Symbol

Ein Tray-Symbol zeichnet nicht die App, sondern die Leiste — auf einer hellen
Leiste verschwinden helle Striche spurlos. Dagegen hilft zweierlei.

**Der Namenszusatz `-symbolic`.** Nach der Freedesktop-Konvention darf eine
Leiste ein so benanntes Symbol auf ihre eigene Vordergrundfarbe umfärben, und
die Omarchy-Leiste tut das auch (ihr `Tray.qml` prüft genau diese Endung).
Damit trifft das Symbol nicht bloß „hell" oder „dunkel", sondern exakt die
Farbe des Themes — ohne dass die App überhaupt etwas merkt.

**Zwei eingebackene Fassungen** für Leisten, die nicht umfärben:

| Datei | Wofür |
|-------|-------|
| `omakeyklack.svg` | App-Symbol für Fenster und Anwendungsmenü |
| `omakeyklack-on-dark-symbolic.svg` | dunkle Leiste, Sounds an |
| `omakeyklack-muted-on-dark-symbolic.svg` | dunkle Leiste, Sounds aus |
| `omakeyklack-on-light-symbolic.svg` | helle Leiste, Sounds an |
| `omakeyklack-muted-on-light-symbolic.svg` | helle Leiste, Sounds aus |

Welche Fassung gilt, steht unter Omarchy in der `colors.toml` des aktiven
Themes: `mode`, ersatzweise `theme_type`, eine Datei `light.mode` oder — wenn
das Theme dazu nichts sagt — die Helligkeit von `background`. Das ist dieselbe
Reihenfolge wie in `omarchy-theme-color`, damit App und Leiste nie zu
verschiedenen Ergebnissen kommen.

Beim Themewechsel ersetzt Omarchy den ganzen Ordner
`~/.local/state/omarchy/current/theme`; omakeyklack beobachtet deshalb das
Verzeichnis darüber und wechselt das Symbol, ohne dass die App neu starten
muss. Ohne Omarchy — oder wenn die Erkennung danebenliegt — entscheidet
`OMAKEYKLACK_ICON_MODE=light` bzw. `=dark`; ohne jede Auskunft bleibt es bei
der dunklen Leiste.

Dass beide Fassungen gedämpft anders aussehen, liegt nicht an der Farbe,
sondern an der durchgestrichenen Schallwelle — nach dem Umfärben ist die Farbe
in beiden Zuständen dieselbe.

Das Blickfeld (`viewBox`) sitzt eng um die Zeichnung, und die Tastenkappe steht
hochkant. Beides hat denselben Grund: Die Leiste passt das Symbol in ein
Quadrat ein und rechnet dabei über die breitere Seite. Eine flache, breite
Zeichnung mit Rand ringsum wird darin klein — das Symbol maß so nur 14 × 8
Pixel, während die Nachbarn in der Leiste 12 bis 14 Pixel hoch sind. Mit engem
Blickfeld und hochkantiger Kappe sind es 15 × 13. Aus demselben Grund fehlt der
Kappe die Legendenlinie: Bei den zwölf Pixeln, die eine Leiste hergibt, lief
sie mit dem Rand der Kappe zusammen.

Das App-Symbol zeigt dasselbe Motiv, steht aber auf dunklem Grund. Es kann
nämlich als einziges *nicht* mitwechseln: Die `.desktop`-Datei nennt genau
einen Namen, und das Anwendungsmenü färbt nichts um. Der eigene Grund macht es
unabhängig davon, welche Farbe dahinterliegt.

## Bekannte Grenzen

- Die Lautstärke ist nicht stufenlos im laufenden Prozess regelbar, weil
  wayvibes keine Schnittstelle dafür hat — jede Änderung startet ihn neu.
- Die Oberfläche ist bisher nur auf Deutsch.
- Getestet mit einer Tastatur; mehrere gleichzeitig kann wayvibes nicht.

## Tests

```bash
for t in tests/test_*.py; do python3 "$t"; done
bash tests/test_doctor.sh
```

```bash
python3 tests/test_hover.py
```

Prüft den Zustandsautomaten der Hover-Vorschau mit gestellten Widgets — dass
eine Zeile nur einmal spielt, schnelles Durchwischen nur die Zielzeile trifft
und wartende Hörproben beim Verlassen abgebrochen werden.

```bash
python3 tests/test_theme_mode.py
```

Prüft die Hell-/Dunkel-Erkennung gegen echte Dateien in einem Wegwerf-HOME:
die Reihenfolge der Schlüssel in `colors.toml` und dass auch der *zweite*
Themewechsel noch gemeldet wird — da ist der Ordner, den der Wachposten beim
Start bekommen hat, längst gelöscht.

```bash
python3 tests/test_no_tray.py
```

Stellt ein System ohne `libayatana-appindicator`: Der Import muss durchgehen
und die App ohne Tray weiterlaufen, statt mit einem Traceback zu sterben.

```bash
python3 tests/test_autostart_default.py
```

Prüft die Vorbelegung des Autostarts in einem Wegwerf-`XDG_CONFIG_HOME`: dass
der erste Start ihn anlegt, ein abgeschalteter abgeschaltet bleibt und ein
Upgrade die Wahl eines bestehenden Anwenders nicht umwirft.

```bash
bash tests/test_install_starts_app.sh
```

Prüft den Start nach der Installation: dass ohne grafische Sitzung nichts
gestartet wird, dass `--no-start` greift, dass der Prozesshelfer mitinstalliert
wird und dass eine laufende Instanz vor dem Austausch der Dateien beendet wird.

```bash
bash tests/test_boot_pipe.sh
```

Leitet `boot.sh` durch eine Pipe in `bash` — einmal mit echtem Terminal (über
`script`), einmal ohne. Bei `curl | bash` liest bash *das Skript selbst* von
`stdin`; wer diesen Deskriptor ersetzt, nimmt bash den Rest der Datei weg, und
der Anwender sieht überhaupt nichts. Sichtbar ist das ausschließlich mit
Terminal — ohne eines läuft dieselbe Datei tadellos durch. Deshalb braucht es
hier ein Pseudo-Terminal.

```bash
bash tests/test_uninstall_stops_app.sh
```

Startet einen Stellvertreter mit exakt der Kommandozeile der echten App und
prüft, dass `uninstall.sh` ihn beendet — und dabei bis zur Schlusszeile
durchläuft. Ein naives `pkill -f omakeyklack` täte beides nicht: Das Skript
heißt selbst `omakeyklack-uninstall` und träfe sich mit.

```bash
bash tests/test_autostart_cycle.sh
```

Spielt den ganzen Lebenszyklus durch — einrichten, abwählen, deinstallieren,
neu einrichten — und prüft dabei die Unterscheidung zwischen abgewählt,
zurückgesetzt und „alte Konfiguration".

```bash
python3 tests/test_defaults.py
```

Prüft die Vorbelegung einer frischen Installation — nk-cream bei Lautstärke
1.0 —, dass eine bestehende Konfiguration davon unberührt bleibt und dass ohne
nk-cream das erste vorhandene Pack einspringt.

```bash
bash tests/test_doctor.sh
```

Prüft `omakeyklack-doctor` gegen gestellte Umgebungen — leerer Packs-Ordner,
fehlendes wayvibes — und dass `--fix` ohne Terminal nichts ungefragt
herunterlädt.

### Gegen ein nacktes Arch

```bash
tests/fresh-install.sh          # aktueller Arbeitsstand
tests/fresh-install.sh --curl   # der veröffentlichte Einzeiler
```

Baut aus `tests/Dockerfile` ein Arch, das nur `base-devel`, `git`, `sudo`,
`curl` und `tar` kennt — kein GTK, kein GStreamer, kein AUR-Helfer, keine
Soundpacks, keine Gruppe `input` — und lässt die Einrichtung darauf los.
Geprüft wird nicht nur, dass sie durchläuft, sondern jeder einzelne Schritt:
Pakete erkannt und nachinstalliert, wayvibes aus dem Quelltext gebaut, Gruppe
eingetragen, Soundpacks geholt, zweiter Lauf grün, Deinstallation rückstandslos.

Braucht Docker und Netz und läuft ein paar Minuten, ist deshalb nicht Teil des
normalen Testlaufs. Er hat sich trotzdem gelohnt: Zwei Fehler, die auf der
Entwicklermaschine unsichtbar waren, sind erst hier aufgefallen — ein
ungesetztes `$USER`, an dem der Doctor mitten in der Prüfung abbrach, und die
Rückfragen, die hinter `curl | bash` ins Leere liefen. Beides Fehler, die
ausgerechnet den Fall treffen, für den das Ganze gedacht ist: die frische
Maschine.

## Lizenz

MIT — siehe [LICENSE](LICENSE).
