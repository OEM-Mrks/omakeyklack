"""Auswahl in der Soundpack-Liste - mit echten Widgets.

Deckt den Absturz ab, der beim Anklicken einer Zeile auftrat: set_pack()
laeuft aus dem "row-selected"-Signal heraus, und ein Neuaufbau der Liste
gab die Zeile frei, mit der GTK danach weiterarbeitet
(gtk_list_box_update_cursor -> SIGSEGV).

Muss ein echtes Fenster bauen: genau die Lebensdauer der ListBoxRow ist
das, was schiefging - mit Attrappen waere davon nichts zu sehen.
"""

import atexit
import os
import shutil
import sys
import tempfile
from pathlib import Path

TMP = Path(tempfile.mkdtemp(prefix="omakeyklack-test-"))
atexit.register(shutil.rmtree, TMP, ignore_errors=True)
os.environ["XDG_CONFIG_HOME"] = str(TMP / "config")
os.environ["XDG_DATA_HOME"] = str(TMP / "data")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

PACKS = ("pack-alpha", "pack-beta", "pack-gamma")


def make_packs() -> Path:
    packs_dir = TMP / "data" / "wayvibes" / "soundpacks"
    for name in PACKS:
        directory = packs_dir / name
        directory.mkdir(parents=True)
        (directory / "sound.wav").write_bytes(b"")
        (directory / "config.json").write_text('{"name": "%s"}' % name)
    return packs_dir


def build_window(packs_dir: Path):
    from omakeyklack import packs as packs_module
    from omakeyklack.app import Omakeyklack
    from omakeyklack.window import SettingsWindow

    app = Omakeyklack()
    app.config["packs_dir"] = str(packs_dir)
    app.config["pack"] = PACKS[0]
    # Kein Vorhoeren im Test - GStreamer soll hier nichts abspielen.
    app.config["preview_on_select"] = False
    app.config["preview_on_hover"] = False
    app.packs = packs_module.discover(packs_dir)
    assert len(app.packs) == len(PACKS), app.packs

    app.window = SettingsWindow(app)
    app.window.refresh()
    app.window.show_all()
    return app


def activate_row(app, index: int) -> None:
    """Zeile ueber GTKs eigenen Aktivierungspfad auswaehlen.

    "activate-cursor-row" landet in gtk_list_box_select_and_activate_full -
    derselben Funktion, aus der der Klick-Absturz kam.
    """
    listbox = app.window.pack_list
    row = listbox.get_row_at_index(index)
    listbox.set_focus_child(row)
    row.grab_focus()
    del row  # nur noch die ListBox haelt die Zeile, wie in _fill_packs()
    listbox.emit("activate-cursor-row")


def check(name, condition):
    print(("OK   " if condition else "FEHLER ") + name)
    return condition


def main() -> int:
    if not (os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY")):
        print("uebersprungen: keine grafische Sitzung")
        return 0

    packs_dir = make_packs()
    app = build_window(packs_dir)

    # GTK meldet den Zugriff auf eine freigegebene Zeile als CRITICAL. Auf
    # fd-Ebene umleiten, damit auch Ausgaben aus der C-Schicht ankommen.
    log = TMP / "stderr.log"
    saved = os.dup(2)
    fd = os.open(log, os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
    os.dup2(fd, 2)
    try:
        activate_row(app, 1)
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)
    finally:
        os.dup2(saved, 2)
        os.close(fd)
        os.close(saved)

    complaints = [
        line for line in log.read_text(errors="replace").splitlines()
        if "CRITICAL" in line or "assertion" in line
    ]

    ok = True
    ok &= check("Klick ueberlebt ohne GTK-Beschwerde", not complaints)
    for line in complaints:
        print("       " + line.strip())
    ok &= check("Auswahl steht auf der angeklickten Zeile",
                app.config["pack"] == PACKS[1])
    selected = app.window.pack_list.get_selected_row()
    ok &= check("ListBox zeigt dieselbe Zeile ausgewaehlt",
                selected is not None and selected.pack_key == PACKS[1])
    ok &= check("Zeilen sind erhalten geblieben",
                [r.pack_key for r in app.window.pack_list.get_children()] == list(PACKS))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
