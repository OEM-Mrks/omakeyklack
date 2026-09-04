"""Zustandsautomat der Hover-Vorschau, ohne echte Widgets.

Getestet wird genau das, was beim Ueberfahren der Liste schiefgehen kann:
mehrfaches Abspielen derselben Zeile und haengende Timer.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib

from omakeyklack.window import HOVER_DELAY_MS, SettingsWindow

ROW_HEIGHT = 50
ROWS = ["alpha", "beta", "gamma"]


class FakeListBox:
    """Liefert Zeilen nach y-Position, wie Gtk.ListBox.get_row_at_y."""

    def __init__(self, width=300, height=ROW_HEIGHT * len(ROWS)):
        self.allocation = SimpleNamespace(width=width, height=height)

    def get_row_at_y(self, y):
        index = y // ROW_HEIGHT
        if 0 <= index < len(ROWS):
            return SimpleNamespace(pack_key=ROWS[index])
        return None

    def get_allocation(self):
        return self.allocation


def make_window(hover_enabled=True):
    window = SettingsWindow.__new__(SettingsWindow)
    window._updating = 0
    window._hover_timer = None
    window._hovered_key = None
    window.played = []
    window.app = SimpleNamespace(
        config={"preview_on_hover": hover_enabled},
        preview_pack=lambda key, limit=None: window.played.append((key, limit)),
    )
    return window


def motion(window, listbox, y):
    window._on_pack_motion(listbox, SimpleNamespace(y=y))


def leave(window, listbox, x, y, detail=Gdk.NotifyType.ANCESTOR):
    window._on_pack_leave(listbox, SimpleNamespace(x=x, y=y, detail=detail))


def settle():
    """Wartende Timer ablaufen lassen."""
    deadline = GLib.get_monotonic_time() + (HOVER_DELAY_MS + 120) * 1000
    context = GLib.MainContext.default()
    while GLib.get_monotonic_time() < deadline:
        context.iteration(False)


def check(name, condition):
    print(("OK   " if condition else "FEHLER ") + name)
    return condition


def main():
    ok = True
    listbox = FakeListBox()

    # Bewegung innerhalb einer Zeile spielt genau einmal vor
    window = make_window()
    for y in (10, 20, 30, 40):
        motion(window, listbox, y)
    settle()
    ok &= check("Bewegung in einer Zeile -> eine Vorschau", window.played == [("alpha", 3)])

    # Zeilenwechsel spielt die neue Zeile
    motion(window, listbox, 60)
    settle()
    ok &= check("Zeilenwechsel -> zweite Vorschau",
                window.played == [("alpha", 3), ("beta", 3)])

    # Schnelles Durchwischen: nur die Zeile, auf der der Zeiger stehen bleibt
    window = make_window()
    for y in (10, 60, 110):
        motion(window, listbox, y)
    settle()
    ok &= check("schnelles Durchwischen -> nur die letzte Zeile",
                window.played == [("gamma", 3)])

    # Verlassen-Ereignis mit Zeiger noch ueber der Liste darf nichts zuruecksetzen
    window = make_window()
    motion(window, listbox, 10)
    settle()
    leave(window, listbox, 50, 20)          # noch innerhalb
    motion(window, listbox, 12)             # gleiche Zeile
    settle()
    ok &= check("Schein-Verlassen -> keine Wiederholung", window.played == [("alpha", 3)])

    # Echtes Verlassen und Zurueckkommen spielt wieder
    leave(window, listbox, 500, 20)         # ausserhalb der Breite
    motion(window, listbox, 12)
    settle()
    ok &= check("echtes Verlassen -> danach wieder Vorschau",
                window.played == [("alpha", 3), ("alpha", 3)])

    # Abgeschaltete Option spielt nichts
    window = make_window(hover_enabled=False)
    motion(window, listbox, 10)
    settle()
    ok &= check("Option aus -> keine Vorschau", window.played == [])

    # Verlassen raeumt einen wartenden Timer weg
    window = make_window()
    motion(window, listbox, 10)
    leave(window, listbox, 500, 20)
    settle()
    ok &= check("Verlassen bricht wartende Vorschau ab", window.played == [])

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
