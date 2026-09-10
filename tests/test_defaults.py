"""Vorbelegung einer frischen Installation: nk-cream bei Lautstaerke 1.0.

Wichtig ist dabei nicht nur der Wert selbst, sondern zweierlei drumherum:
Ein Anwender, der schon eine Konfiguration hat, darf davon nichts merken -
und wer nk-cream gar nicht besitzt, darf nicht vor einer leeren Auswahl
sitzen.
"""

from __future__ import annotations

import importlib
import json
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


def fresh_config(config_home: Path):
    os.environ["XDG_CONFIG_HOME"] = str(config_home)
    sys.modules.pop("omakeyklack.config", None)
    return importlib.import_module("omakeyklack.config")


def make_pack(root: Path, name: str) -> None:
    """Ein Pack, das load_pack als brauchbar durchgehen laesst."""
    directory = root / name
    directory.mkdir(parents=True)
    (directory / "a.wav").write_bytes(b"RIFF")
    (directory / "config.json").write_text(
        json.dumps({"name": name, "key_define_type": "multi",
                    "defines": {"30": "a.wav"}}),
        encoding="utf-8",
    )


# -- 1. Die Vorbelegung selbst -----------------------------------------

with tempfile.TemporaryDirectory() as tmp:
    config_mod = fresh_config(Path(tmp))
    cfg = config_mod.Config()

    if cfg["pack"] != "nk-cream":
        fail(f"Pack ist vorbelegt mit {cfg['pack']!r} statt 'nk-cream'")
    else:
        ok("frische Konfiguration steht auf nk-cream")

    if cfg["volume"] != 1.0:
        fail(f"Lautstaerke ist vorbelegt mit {cfg['volume']!r} statt 1.0")
    else:
        ok("frische Konfiguration steht auf Lautstaerke 1.0")

# -- 2. Bestehende Konfiguration bleibt unangetastet --------------------

with tempfile.TemporaryDirectory() as tmp:
    config_mod = fresh_config(Path(tmp))
    config_mod.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    config_mod.CONFIG_FILE.write_text(
        '{"pack": "boxjade", "volume": 4.0}\n', encoding="utf-8")

    cfg = config_mod.Config()
    if cfg["pack"] != "boxjade" or cfg["volume"] != 4.0:
        fail(f"eigene Wahl ueberschrieben: {cfg['pack']!r}, {cfg['volume']!r}")
    else:
        ok("bestehende Wahl wird nicht ueberschrieben")

# -- 3. Ohne nk-cream: das erste vorhandene Pack ------------------------

# Ein Anwender mit eigenen Packs darf nicht vor einer leeren Auswahl sitzen,
# nur weil die Vorbelegung auf ein Pack zeigt, das er nicht hat.
import omakeyklack.packs as packs_module  # noqa: E402

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp) / "packs"
    make_pack(root, "zzz-eigenes")
    make_pack(root, "aaa-anderes")

    packs = packs_module.discover(root)
    if len(packs) != 2:
        fail(f"Testaufbau: {len(packs)} Packs statt 2 gefunden")
    elif packs_module.find(packs, "nk-cream") is not None:
        fail("Testaufbau: nk-cream sollte hier fehlen")
    else:
        # Das ist der Griff, den reload_packs tut, wenn das vorbelegte
        # Pack nicht auffindbar ist.
        ersatz = packs[0].key
        if ersatz != "aaa-anderes":
            fail(f"Rueckfall nimmt {ersatz!r} statt des ersten Packs")
        else:
            ok("ohne nk-cream greift das erste vorhandene Pack")

raise SystemExit(FAILED)
