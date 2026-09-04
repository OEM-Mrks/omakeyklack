"""Einstiegspunkt: python3 -m omakeyklack bzw. der installierte Starter."""

from __future__ import annotations

import sys

from . import __version__


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv if argv is None else argv
    # Vor dem Aufbau von Tray und Engine abhandeln - sonst startet die App
    # nur, um sofort wieder zu beenden.
    if "--version" in argv[1:] or "-v" in argv[1:]:
        print(f"omakeyklack {__version__}")
        return 0

    from gi.repository import GLib

    # Unter Wayland leitet GTK die app_id aus dem Programmnamen ab. Ohne das
    # hier hiesse das Fenster "__main__.py" und bekaeme weder Symbol noch
    # Zuordnung zur .desktop-Datei.
    GLib.set_prgname("omakeyklack")
    GLib.set_application_name("omakeyklack")

    from .app import Omakeyklack

    return Omakeyklack().run(argv)


if __name__ == "__main__":
    raise SystemExit(main())
