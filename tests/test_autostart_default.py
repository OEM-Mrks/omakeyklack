"""Der Autostart wird genau einmal vorbelegt - und danach nicht mehr angefasst.

Eine Tray-App, die nach dem Anmelden weg ist, sieht kaputt aus; darum legt
der erste Start den Autostart an. Wer ihn abschaltet, soll ihn aber nicht
beim naechsten Start wiederfinden, und ein Upgrade darf die Wahl eines
bestehenden Anwenders nicht umwerfen.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

FAILED = 0


def ok(text: str) -> None:
    print(f"OK   {text}")


def fail(text: str) -> None:
    global FAILED
    FAILED = 1
    print(f"FEHL {text}")


def fresh_modules(config_home: Path):
    """config und autostart neu laden - beide lesen XDG_CONFIG_HOME beim Import."""
    os.environ["XDG_CONFIG_HOME"] = str(config_home)
    for name in ("omakeyklack.config", "omakeyklack.autostart", "omakeyklack.app"):
        sys.modules.pop(name, None)
    import importlib

    config = importlib.import_module("omakeyklack.config")
    autostart = importlib.import_module("omakeyklack.autostart")
    app_module = importlib.import_module("omakeyklack.app")
    return config, autostart, app_module


def run_startup(config, app_module):
    """Nur den Teil von do_startup ausfuehren, um den es hier geht."""

    class FakeApp:
        _apply_autostart_default = app_module.Omakeyklack._apply_autostart_default

    fake = FakeApp()
    fake.config = config
    fake._apply_autostart_default()
    return fake


# -- 1. Frische Einrichtung: Autostart wird angelegt --------------------

with tempfile.TemporaryDirectory() as tmp:
    home = Path(tmp)
    config_mod, autostart, app_module = fresh_modules(home)

    cfg = config_mod.Config()
    if not cfg.first_run:
        fail("frische Einrichtung wurde nicht als erster Start erkannt")
    run_startup(cfg, app_module)

    if not autostart.is_enabled():
        fail("erster Start hat keinen Autostart angelegt")
    else:
        ok("erster Start legt den Autostart an")

    # Der Merker muss auf der Platte stehen, nicht nur im Speicher.
    if not config_mod.Config()["autostart_initialized"]:
        fail("Merker wurde nicht gespeichert")
    else:
        ok("Merker steht in der Konfiguration")

    # -- 2. Abgeschaltet bleibt abgeschaltet ---------------------------

    autostart.set_enabled(False)
    run_startup(config_mod.Config(), app_module)
    if autostart.is_enabled():
        fail("abgeschalteter Autostart wurde wieder angeworfen")
    else:
        ok("abgeschalteter Autostart bleibt aus")

# -- 3. Upgrade: bestehende Konfiguration wird nicht umgeworfen ---------

with tempfile.TemporaryDirectory() as tmp:
    home = Path(tmp)
    config_mod, autostart, app_module = fresh_modules(home)

    # Eine Konfiguration aus einer aelteren Fassung - ohne den Merker.
    config_mod.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    config_mod.CONFIG_FILE.write_text('{"volume": 3.0}\n', encoding="utf-8")

    cfg = config_mod.Config()
    if cfg.first_run:
        fail("bestehende Konfiguration wurde als erster Start missdeutet")
    run_startup(cfg, app_module)

    if autostart.is_enabled():
        fail("Upgrade hat ungefragt einen Autostart angelegt")
    else:
        ok("Upgrade laesst den Autostart in Ruhe")

    if not config_mod.Config()["autostart_initialized"]:
        fail("Merker fehlt nach dem Upgrade - der Fall kaeme jedes Mal wieder")
    else:
        ok("Merker wird auch beim Upgrade gesetzt")

    if config_mod.Config()["volume"] != 3.0:
        fail("bestehende Einstellungen gingen verloren")
    else:
        ok("bestehende Einstellungen bleiben erhalten")

raise SystemExit(FAILED)
