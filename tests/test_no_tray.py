"""Ohne libayatana-appindicator muss die App trotzdem starten.

Frueher flog der Import in tray.py bis in die Konsole durch: der Anwender
sah einen Python-Traceback statt der einen Zeile, die ihm gesagt haette,
welches Paket fehlt. Hier wird der Fall gestellt, indem gi.require_version
fuer genau diesen Namensraum scheitert.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import gi  # noqa: E402

FAILED = 0


def ok(text: str) -> None:
    print(f"OK   {text}")


def fail(text: str) -> None:
    global FAILED
    FAILED = 1
    print(f"FEHL {text}")


def load_tray_without_appindicator():
    """tray.py neu laden, waehrend AyatanaAppIndicator3 nicht aufzutreiben ist."""
    original = gi.require_version

    def blocked(namespace, version):
        if namespace == "AyatanaAppIndicator3":
            raise ValueError("Namespace AyatanaAppIndicator3 not available")
        return original(namespace, version)

    gi.require_version = blocked
    for name in ("omakeyklack.tray", "omakeyklack.app"):
        sys.modules.pop(name, None)
    try:
        return importlib.import_module("omakeyklack.tray")
    finally:
        gi.require_version = original


try:
    tray = load_tray_without_appindicator()
except Exception as exc:  # noqa: BLE001
    fail(f"Import von tray.py knallt weiterhin: {exc!r}")
    raise SystemExit(1)

ok("tray.py laesst sich ohne AppIndicator importieren")

if not tray.UNAVAILABLE:
    fail("UNAVAILABLE ist leer - der Ausfall wird nicht gemeldet")
elif "libayatana-appindicator" not in tray.UNAVAILABLE:
    fail(f"Meldung nennt das fehlende Paket nicht: {tray.UNAVAILABLE!r}")
else:
    ok("Meldung nennt Paket und Abhilfe")

# app.py importiert tray auf Modulebene - auch das muss durchgehen.
sys.modules.pop("omakeyklack.app", None)
try:
    app_module = importlib.import_module("omakeyklack.app")
except Exception as exc:  # noqa: BLE001
    fail(f"Import von app.py knallt: {exc!r}")
    raise SystemExit(1)
ok("app.py laesst sich ebenfalls importieren")


class FakeApp:
    """Nur so viel Omakeyklack, wie _build_tray anfasst."""

    tray = None
    last_error = ""

    _build_tray = app_module.Omakeyklack._build_tray


fake = FakeApp()
fake._build_tray()

if fake.tray is not None:
    fail("es wurde ein Tray gebaut, obwohl AppIndicator fehlt")
elif "libayatana-appindicator" not in fake.last_error:
    fail(f"last_error hilft nicht weiter: {fake.last_error!r}")
else:
    ok("_build_tray meldet den Ausfall und laeuft weiter")

# Aufraeumen, damit ein nachfolgender Import wieder das echte Modul holt.
for name in ("omakeyklack.tray", "omakeyklack.app"):
    sys.modules.pop(name, None)

raise SystemExit(FAILED)
