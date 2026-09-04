# omakeyklack

Tray-App für mechanische Tastatur-Sounds unter Wayland.

[wayvibes](https://github.com/SameeBhaii/wayvibes) spielt beim Tippen Sounds ab,
ist aber ein reines Kommandozeilen-Werkzeug: Soundpack und Lautstärke werden
als Startparameter übergeben, zum Wechseln muss man den Prozess von Hand neu
starten. **omakeyklack** legt eine Oberfläche darüber:

- **Tray-Symbol** (StatusNotifierItem) — Sounds an/aus, Soundpack und
  Lautstärke direkt aus dem Menü
- **Soundpacks vorhören** — beim Auswählen spielt eine kurze Tippsequenz,
  man hört das Pack also vor dem Umschalten
- **Lautstärke per Schieberegler**, mit sofortigem Hörbeispiel
- **Tastatur auswählen**, falls mehrere Eingabegeräte in Frage kommen
- **Autostart** per Häkchen

Getestet unter Hyprland/[Omarchy](https://omarchy.org/), funktioniert aber mit
jedem Wayland-Desktop, dessen Leiste StatusNotifierItem beherrscht (Waybar,
Quickshell, GNOME mit AppIndicator-Erweiterung, KDE …).

> **English:** GUI and tray for `wayvibes` — pick soundpacks with audio preview,
> set volume, toggle typing sounds. The user interface is currently German only;
> pull requests for translations are welcome.

## Voraussetzungen

| Was | Paket unter Arch |
|-----|------------------|
| wayvibes | `wayvibes-git` (AUR) |
| Python 3.10+ mit PyGObject | `python-gobject` |
| GTK 3 | `gtk3` |
| Tray-Anbindung | `libayatana-appindicator` |
| Wiedergabe der Hörproben | `gst-plugins-base`, `gst-plugins-good` |

```bash
sudo pacman -S python-gobject gtk3 libayatana-appindicator \
    gst-plugins-base gst-plugins-good
```

Der eigene Benutzer muss die Eingabegeräte lesen dürfen — das verlangt schon
wayvibes selbst:

```bash
sudo usermod -aG input "$USER"   # danach neu anmelden
```

## Installation

```bash
git clone https://github.com/<user>/omakeyklack.git
cd omakeyklack
./install.sh
```

Installiert nach `~/.local` (kein root nötig). Systemweit geht auch:

```bash
PREFIX=/usr/local sudo ./install.sh
```

Deinstallieren mit `./uninstall.sh`.

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

## Bedienung

Ohne Argumente öffnet sich das Einstellungsfenster; das Tray-Symbol läuft
parallel weiter:

```bash
omakeyklack          # Fenster + Tray
omakeyklack --tray   # nur Tray (so startet auch der Autostart)
omakeyklack --version
```

Das Fenster zu schließen beendet die App **nicht** — sie läuft im Tray weiter.
Beenden geht über *Beenden* im Tray-Menü.

## Konfiguration

`~/.config/omakeyklack/config.json`:

```json
{
  "pack": "nk-cream",
  "volume": 2.0,
  "device": "",
  "enabled": true,
  "packs_dir": "/home/du/.local/share/wayvibes/soundpacks",
  "preview_on_select": true
}
```

- `volume` ist der lineare Faktor, den wayvibes als `-v` bekommt (0–10)
- `device` leer lassen heißt: wayvibes sucht die Tastatur selbst aus
- `packs_dir` darf auf ein beliebiges Verzeichnis zeigen

## Wie es funktioniert

omakeyklack startet `wayvibes` als eigenen Kindprozess und übergibt Pack,
Lautstärke und Gerät als Parameter. Weil wayvibes diese Werte nur beim Start
liest, wird der Prozess bei jeder Änderung kurz neu gestartet — das dauert
wenige Millisekunden und fällt beim Tippen nicht auf.

Die Hörproben spielt omakeyklack dagegen selbst über GStreamer ab, unabhängig
von wayvibes. Nur so lässt sich ein Pack vorhören, ohne es vorher zu
aktivieren.

Beim Beenden wird wayvibes mitgenommen; zusätzlich sorgt `PR_SET_PDEATHSIG`
dafür, dass kein verwaister Prozess weiterklackert, wenn omakeyklack hart
abgeschossen wird.

## Bekannte Grenzen

- Die Lautstärke ist nicht stufenlos im laufenden Prozess regelbar, weil
  wayvibes keine Schnittstelle dafür hat — jede Änderung startet ihn neu.
- Die Oberfläche ist bisher nur auf Deutsch.
- Getestet mit einer Tastatur; mehrere gleichzeitig kann wayvibes nicht.

## Lizenz

MIT — siehe [LICENSE](LICENSE).
