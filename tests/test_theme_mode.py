"""Erkennung von hellem/dunklem Theme und der Wechsel zur Laufzeit.

Getestet wird gegen echte Dateien in einem Wegwerf-HOME: genau das
Zusammenspiel mit dem Verzeichnis, das Omarchy beim Themewechsel komplett
ersetzt, ist das, was schiefgehen kann.
"""

import atexit
import os
import shutil
import sys
import tempfile
from pathlib import Path

TMP = Path(tempfile.mkdtemp(prefix="omakeyklack-theme-test-"))
atexit.register(shutil.rmtree, TMP, ignore_errors=True)
os.environ["HOME"] = str(TMP)
os.environ.pop("OMAKEYKLACK_ICON_MODE", None)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib

from omakeyklack import theme

CURRENT = TMP / ".local/state/omarchy/current"
THEME_DIR = CURRENT / "theme"


def write_theme(body: str) -> None:
    """Theme setzen, so wie omarchy-theme-set es tut: Ordner ersetzen."""
    staging = CURRENT / "next-theme"
    staging.mkdir(parents=True, exist_ok=True)
    (staging / "colors.toml").write_text(body)
    shutil.rmtree(THEME_DIR, ignore_errors=True)
    staging.rename(THEME_DIR)
    (CURRENT / "theme.name").write_text("test\n")


def settle(ms: int = theme.SETTLE_MS * 4) -> None:
    context = GLib.MainContext.default()
    deadline = GLib.get_monotonic_time() + ms * 1000
    while GLib.get_monotonic_time() < deadline:
        context.iteration(False)


def check(label: str, condition: bool) -> bool:
    print(f"{'ok  ' if condition else 'FAIL'} {label}")
    return condition


def main() -> int:
    ok = True

    # Ohne Omarchy bleibt es bei der dunklen Leiste
    ok &= check("kein Theme -> dark", theme.current_mode() == theme.DARK)

    write_theme('mode = "light"\nbackground = "#ffffff"\n')
    ok &= check("mode = light", theme.current_mode() == theme.LIGHT)

    write_theme('theme_type = "dark"\nbackground = "#ffffff"\n')
    ok &= check("theme_type schlaegt Helligkeit", theme.current_mode() == theme.DARK)

    # Ohne Angabe entscheidet die Helligkeit des Hintergrunds
    write_theme('background = "#ffffff" # weiss\n')
    ok &= check("heller Hintergrund -> light", theme.current_mode() == theme.LIGHT)
    write_theme("background = '#1a1b26'\n")
    ok &= check("dunkler Hintergrund -> dark", theme.current_mode() == theme.DARK)

    # light.mode zaehlt nur, wenn kein Schluessel etwas anderes sagt
    write_theme('background = "#1a1b26"\n')
    (THEME_DIR / "light.mode").touch()
    ok &= check("light.mode -> light", theme.current_mode() == theme.LIGHT)

    os.environ["OMAKEYKLACK_ICON_MODE"] = "dark"
    ok &= check("Umgebungsvariable hat Vorrang", theme.current_mode() == theme.DARK)
    del os.environ["OMAKEYKLACK_ICON_MODE"]

    ok &= check(
        "Symbolnamen",
        theme.icon_name(True, theme.LIGHT) == "omakeyklack-on-light-symbolic"
        and theme.icon_name(False, theme.DARK) == "omakeyklack-muted-on-dark-symbolic",
    )

    # Jeder Name muss eine Datei im Quellbaum treffen - sonst faellt die
    # Leiste auf ein Ersatzsymbol zurueck, ohne sich zu beschweren. Die
    # Endung "-symbolic" gehoert dazu: nur daran erkennt die Leiste, dass
    # sie das Symbol einfaerben darf.
    icons = Path(__file__).resolve().parents[1] / "data/icons/hicolor/scalable/apps"
    missing = [
        name
        for running in (True, False)
        for mode in (theme.DARK, theme.LIGHT)
        for name in [theme.icon_name(running, mode)]
        if not (icons / f"{name}.svg").is_file()
    ]
    ok &= check(f"Symboldateien vorhanden{' - fehlt: ' + ', '.join(missing) if missing else ''}",
                not missing)
    ok &= check(
        "alle Namen auf -symbolic",
        all(theme.icon_name(r, m).endswith("-symbolic")
            for r in (True, False) for m in (theme.DARK, theme.LIGHT)),
    )

    # Wechsel zur Laufzeit: der Waechter muss das mitbekommen, und zwar
    # auch beim zweiten Mal - da haengt sein erster Ordner laengst in der
    # Luft, weil omarchy ihn geloescht hat.
    write_theme('mode = "dark"\n')
    seen: list[str] = []
    watcher = theme.ModeWatcher(seen.append)
    ok &= check("Startmodus", watcher.mode == theme.DARK)

    write_theme('mode = "light"\n')
    settle()
    ok &= check("Wechsel nach light gemeldet", seen == [theme.LIGHT])
    ok &= check("Modus nachgezogen", watcher.mode == theme.LIGHT)

    write_theme('mode = "dark"\n')
    settle()
    ok &= check("zweiter Wechsel gemeldet", seen == [theme.LIGHT, theme.DARK])

    # Gleiches Theme noch einmal setzen ist kein Wechsel
    write_theme('mode = "dark"\n')
    settle()
    ok &= check("unveraenderter Modus meldet nichts", seen == [theme.LIGHT, theme.DARK])

    watcher.stop()
    write_theme('mode = "light"\n')
    settle()
    ok &= check("nach stop() keine Meldung mehr", seen == [theme.LIGHT, theme.DARK])

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
