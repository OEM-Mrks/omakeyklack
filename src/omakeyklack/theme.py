"""Hell oder dunkel: welchen Anstrich das Tray-Symbol gerade braucht.

Ein Tray-Symbol zeichnet nicht die App, sondern die Leiste - und die kann
jede Farbe haben. Die hellen Striche des Symbols verschwinden auf einer
hellen Leiste spurlos.

Erste Verteidigungslinie ist der Namenszusatz "-symbolic": nach der
Freedesktop-Konvention faerbt die Leiste ein so benanntes Symbol auf ihre
eigene Vordergrundfarbe um. Die Omarchy-Leiste tut das (Tray.qml prueft
genau diese Endung), und damit trifft das Symbol die Themefarbe exakt.

Zweite Linie fuer Leisten, die nicht einfaerben: die eingebackene
Strichfarbe. Dafuer wird hier ermittelt, ob das aktive Theme hell oder
dunkel ist. Omarchy legt das in der colors.toml des Themes ab; die
Reihenfolge (mode, theme_type, light.mode, Helligkeit des Hintergrunds) ist
dieselbe wie in omarchy-theme-color, damit App und Leiste nie zu
verschiedenen Ergebnissen kommen.
"""

from __future__ import annotations

import os
from pathlib import Path

from gi.repository import Gio, GLib

DARK = "dark"
LIGHT = "light"

# Omarchy zeigt mit diesem Verzeichnis auf das gerade aktive Theme.
OMARCHY_CURRENT = Path.home() / ".local/state/omarchy/current"
THEME_DIR = OMARCHY_CURRENT / "theme"
COLORS_FILE = THEME_DIR / "colors.toml"
LIGHT_MARKER = THEME_DIR / "light.mode"

ENV_OVERRIDE = "OMAKEYKLACK_ICON_MODE"

# Ein Themewechsel loest mehrere Dateiereignisse aus (Verzeichnis ersetzt,
# theme.name neu geschrieben) - erst danach wird einmal nachgesehen.
SETTLE_MS = 250

# Summe der drei Kanaele, ab der ein Hintergrund als hell gilt (wie in
# omarchy-theme-color: r + g + b > 382, also gut die Haelfte von 765).
LIGHT_THRESHOLD = 382


def current_mode() -> str:
    """"dark" oder "light" - im Zweifel "dark", der haeufigere Fall."""
    override = os.environ.get(ENV_OVERRIDE, "").strip().lower()
    if override in (DARK, LIGHT):
        return override
    return _omarchy_mode() or DARK


def icon_name(running: bool, mode: str) -> str:
    """Name des Tray-Symbols - immer auf "-symbolic", siehe Modulkopf."""
    variant = "" if running else "-muted"
    suffix = LIGHT if mode == LIGHT else DARK
    return f"omakeyklack{variant}-on-{suffix}-symbolic"


def _omarchy_mode() -> str | None:
    values = _read_colors()
    for key in ("mode", "theme_type"):
        value = values.get(key, "").lower()
        if value in (DARK, LIGHT):
            return value
    if LIGHT_MARKER.is_file():
        return LIGHT
    brightness = _brightness(values.get("background", ""))
    if brightness is None:
        return None
    return LIGHT if brightness > LIGHT_THRESHOLD else DARK


def _read_colors() -> dict[str, str]:
    """colors.toml als flache Tabelle - Anfuehrungszeichen und Kommentare raus."""
    try:
        text = COLORS_FILE.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}

    values: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip().strip("\"'")
        value = value.strip()
        if value[:1] in ("\"", "'"):
            quote = value[0]
            end = value.find(quote, 1)
            value = value[1:end] if end > 0 else value[1:]
        else:
            value = value.split("#", 1)[0].strip()
        if key:
            values[key] = value
    return values


def _brightness(color: str) -> int | None:
    color = color.strip().lstrip("#")
    if len(color) != 6:
        return None
    try:
        return sum(int(color[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return None


class ModeWatcher:
    """Haelt den aktuellen Modus und meldet, wenn er sich aendert.

    Beobachtet wird das current-Verzeichnis, nicht colors.toml selbst:
    omarchy ersetzt beim Themewechsel den ganzen theme-Ordner (rm -rf + mv),
    ein Wachposten auf der Datei haenge danach an einer geloeschten Inode.
    Der Ordner selbst wird zusaetzlich beobachtet, weil `omarchy theme
    refresh` die colors.toml an Ort und Stelle neu schreibt.
    """

    def __init__(self, on_change) -> None:
        self.mode = current_mode()
        self._on_change = on_change
        self._settle_id = 0
        self._current_monitor = _monitor(OMARCHY_CURRENT, self._queue)
        self._theme_monitor = _monitor(THEME_DIR, self._queue)

    def stop(self) -> None:
        if self._settle_id:
            GLib.source_remove(self._settle_id)
            self._settle_id = 0
        for monitor in (self._current_monitor, self._theme_monitor):
            if monitor is not None:
                monitor.cancel()
        self._current_monitor = self._theme_monitor = None

    def _queue(self, *_args) -> None:
        if self._settle_id:
            GLib.source_remove(self._settle_id)
        self._settle_id = GLib.timeout_add(SETTLE_MS, self._settled)

    def _settled(self) -> bool:
        self._settle_id = 0
        # Der theme-Ordner von eben ist womoeglich schon Geschichte.
        if self._theme_monitor is not None:
            self._theme_monitor.cancel()
        self._theme_monitor = _monitor(THEME_DIR, self._queue)

        mode = current_mode()
        if mode != self.mode:
            self.mode = mode
            self._on_change(mode)
        return GLib.SOURCE_REMOVE


def _monitor(path: Path, callback):
    """Wachposten auf ein Verzeichnis; ohne Omarchy gibt es schlicht keinen."""
    try:
        monitor = Gio.File.new_for_path(str(path)).monitor_directory(
            Gio.FileMonitorFlags.WATCH_MOVES, None
        )
    except GLib.Error:
        return None
    monitor.connect("changed", callback)
    return monitor
