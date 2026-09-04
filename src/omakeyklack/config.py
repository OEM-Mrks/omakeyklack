"""Persistente Einstellungen unter ~/.config/omakeyklack/config.json."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

CONFIG_DIR = Path(
    os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
) / "omakeyklack"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_PACKS_DIR = Path(
    os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")
) / "wayvibes" / "soundpacks"

DEFAULTS = {
    "pack": "",           # Verzeichnisname des Soundpacks, "" = erstes gefundenes
    "volume": 2.0,        # wayvibes -v, linearer Faktor 0.0 - 10.0
    "device": "",         # exakter Eingabegeraet-Name, "" = wayvibes fragt selbst
    "enabled": True,      # Sounds beim Start aktivieren
    "packs_dir": str(DEFAULT_PACKS_DIR),
    "preview_on_select": True,
}

VOLUME_MIN = 0.0
VOLUME_MAX = 10.0


class Config(dict):
    """Dict mit Laden/Speichern und getypten Zugriffen."""

    def __init__(self, path: Path = CONFIG_FILE):
        super().__init__(DEFAULTS)
        self.path = path
        self.load()

    def load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if isinstance(raw, dict):
            for key in DEFAULTS:
                if key in raw:
                    self[key] = raw[key]
        self["volume"] = clamp_volume(self["volume"])

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Atomar schreiben, damit ein Absturz die Konfiguration nicht zerlegt.
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".config-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(dict(self), fh, indent=2, ensure_ascii=False)
                fh.write("\n")
            os.replace(tmp, self.path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    @property
    def packs_dir(self) -> Path:
        return Path(self["packs_dir"]).expanduser()


def clamp_volume(value) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return DEFAULTS["volume"]
    return max(VOLUME_MIN, min(VOLUME_MAX, value))
