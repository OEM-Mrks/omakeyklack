"""Einstiegspunkt: python3 -m omakeyklack bzw. der installierte Starter."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import __version__

DOCTOR = "omakeyklack-doctor"


def _find_doctor() -> str | None:
    """Das Pruefskript suchen - installiert im PATH, sonst im Quellbaum.

    Beim Entwickeln liegt es nicht in $PATH; dann taugt der Pfad relativ
    zum Paket, solange aus dem Repo heraus gearbeitet wird.
    """
    found = shutil.which(DOCTOR)
    if found:
        return found
    # src/omakeyklack/__main__.py -> ../../bin/omakeyklack-doctor
    candidate = Path(__file__).resolve().parents[2] / "bin" / DOCTOR
    return str(candidate) if candidate.is_file() else None


def _run_doctor(argv: list[str]) -> int:
    doctor = _find_doctor()
    if doctor is None:
        print(
            f"omakeyklack: {DOCTOR} nicht gefunden. Es gehoert neben den "
            "Starter, wird also von install.sh und vom Paket mitgeliefert.",
            file=sys.stderr,
        )
        return 1
    # Alles hinter --check durchreichen, damit "omakeyklack --check --fix"
    # funktioniert.
    rest = [a for a in argv if a not in ("--check",)]
    return subprocess.call([doctor, *rest], env=os.environ.copy())


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv if argv is None else argv
    args = argv[1:]

    # Vor dem Aufbau von Tray und Engine abhandeln - sonst startet die App
    # nur, um sofort wieder zu beenden.
    if "--version" in args or "-v" in args:
        print(f"omakeyklack {__version__}")
        return 0
    if "--check" in args:
        return _run_doctor(args)

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
