"""Soundpacks im Mechvibes-/wayvibes-Format einlesen.

Ein Pack ist ein Verzeichnis mit config.json:

  key_define_type "multi"/"multiple"  ->  defines: {keycode: "datei.wav"}
  key_define_type "single"            ->  defines: {keycode: [offset_ms, dauer_ms]}
                                          plus ein Sprite unter "sound"
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

AUDIO_SUFFIXES = (".wav", ".ogg", ".mp3", ".flac")

# evdev-Keycodes fuer die Demo: k l a c k <space> <enter>
DEMO_KEYCODES = [37, 38, 30, 46, 37, 57, 28]


@dataclass
class Sound:
    """Ein abspielbarer Ausschnitt: ganze Datei oder Sprite-Bereich."""

    path: Path
    offset_ms: int = 0
    duration_ms: int = 0  # 0 = bis zum Ende der Datei

    @property
    def is_slice(self) -> bool:
        return self.duration_ms > 0


@dataclass
class Pack:
    directory: Path
    name: str
    define_type: str = "multi"
    defines: dict = field(default_factory=dict)
    sprite: Path | None = None

    @property
    def key(self) -> str:
        """Stabiler Bezeichner - der Verzeichnisname."""
        return self.directory.name

    @property
    def is_sprite(self) -> bool:
        return self.define_type == "single"

    def sound_for(self, keycode: int) -> Sound | None:
        value = self.defines.get(str(keycode))
        if value is None:
            return None
        if self.is_sprite:
            if self.sprite is None or not isinstance(value, (list, tuple)) or len(value) < 2:
                return None
            try:
                return Sound(self.sprite, int(value[0]), int(value[1]))
            except (TypeError, ValueError):
                return None
        if not isinstance(value, str):
            return None
        path = self.directory / value
        return Sound(path) if path.is_file() else None

    def demo_sounds(self) -> list[Sound]:
        """Kurze Tippsequenz. Faellt auf beliebige Dateien zurueck, wenn
        die Demo-Keycodes im Pack nicht definiert sind."""
        sounds = [s for s in (self.sound_for(kc) for kc in DEMO_KEYCODES) if s]
        if sounds:
            return sounds
        # Fallback 1: irgendwelche definierten Tasten
        for value in list(self.defines.values())[:7]:
            if isinstance(value, str):
                path = self.directory / value
                if path.is_file():
                    sounds.append(Sound(path))
        if sounds:
            return sounds
        # Fallback 2: einfach Audiodateien aus dem Verzeichnis
        files = sorted(
            p for p in self.directory.iterdir()
            if p.is_file() and p.suffix.lower() in AUDIO_SUFFIXES
        )
        return [Sound(p) for p in files[:7]]


def load_pack(directory: Path) -> Pack | None:
    """Ein Pack-Verzeichnis einlesen. None, wenn es keins ist."""
    if not directory.is_dir():
        return None
    config_file = directory / "config.json"
    name = directory.name
    define_type = "multi"
    defines: dict = {}
    sprite = None

    if config_file.is_file():
        try:
            data = json.loads(config_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        if isinstance(data, dict):
            name = str(data.get("name") or directory.name)
            define_type = str(data.get("key_define_type") or "multi")
            raw_defines = data.get("defines")
            if isinstance(raw_defines, dict):
                defines = raw_defines
            sound_file = data.get("sound")
            if isinstance(sound_file, str):
                candidate = directory / sound_file
                if candidate.is_file():
                    sprite = candidate

    # "multiple" ist eine verbreitete Schreibweise von "multi".
    if define_type not in ("single",):
        define_type = "multi"

    pack = Pack(directory, name, define_type, defines, sprite)
    if not pack.demo_sounds():
        return None  # nichts Abspielbares -> kein brauchbares Pack
    return pack


def discover(packs_dir: Path) -> list[Pack]:
    """Alle Packs unterhalb von packs_dir, alphabetisch nach Verzeichnisname."""
    try:
        entries = sorted(packs_dir.iterdir(), key=lambda p: p.name.lower())
    except OSError:
        return []
    packs = [pack for entry in entries if (pack := load_pack(entry))]
    return packs


def find(packs: list[Pack], key: str) -> Pack | None:
    for pack in packs:
        if pack.key == key:
            return pack
    return None
