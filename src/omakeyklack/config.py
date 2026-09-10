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

# Das Pack, mit dem eine frische Installation startet. nk-cream liegt dem
# wayvibes-Projekt bei, wird also mitgeliefert, wenn der Doctor die Packs
# holt - und klingt gedaempft genug, um niemanden zu erschrecken, der die
# App zum ersten Mal oeffnet. Fehlt es, nimmt reload_packs das erste
# vorhandene Pack.
DEFAULT_PACK = "nk-cream"
# Bei 2.0 war der erste Anschlag lauter als noetig. 1.0 ist wayvibes'
# eigener Normalwert und laesst sich nach oben wie unten nachregeln.
DEFAULT_VOLUME = 1.0

DEFAULTS = {
    "pack": DEFAULT_PACK,  # Verzeichnisname; unbekannt -> erstes gefundenes
    "volume": DEFAULT_VOLUME,  # wayvibes -v, linearer Faktor 0.0 - 10.0
    "device": "",         # exakter Eingabegeraet-Name, "" = wayvibes fragt selbst
    "enabled": True,      # Sounds beim Start aktivieren
    "packs_dir": str(DEFAULT_PACKS_DIR),
    "preview_on_select": True,
    "preview_on_hover": True,
    # Einmaliger Merker: Der Autostart wurde schon einmal vorbelegt. Ohne
    # den wuerde jeder Start ein abgeschaltetes Autostart wieder anwerfen.
    "autostart_initialized": False,
}

VOLUME_MIN = 0.0
VOLUME_MAX = 10.0


class Config(dict):
    """Dict mit Laden/Speichern und getypten Zugriffen."""

    def __init__(self, path: Path = CONFIG_FILE):
        super().__init__(DEFAULTS)
        self.path = path
        # Vor dem Laden merken: nur ohne Datei ist es wirklich der erste
        # Start. Wer schon eine hat, hat seine Einstellungen selbst getroffen
        # und soll sie nicht durch eine neue Vorbelegung ueberschrieben
        # bekommen.
        self.first_run = not path.exists()
        # Welche Schluessel wirklich in der Datei standen. Ein fehlender
        # Schluessel und einer, der ausdruecklich auf false steht, sehen im
        # Dict sonst gleich aus - fuer autostart_initialized ist das aber
        # der Unterschied zwischen "alte Konfiguration, nicht anfassen" und
        # "von uninstall.sh zurueckgesetzt, bitte neu vorbelegen".
        self.file_keys: set[str] = set()
        self.load()

    def load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if isinstance(raw, dict):
            self.file_keys = set(raw)
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
