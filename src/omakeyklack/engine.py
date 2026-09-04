"""Steuerung des wayvibes-Prozesses.

omakeyklack spielt die Tastentoene nicht selbst - das erledigt wayvibes,
das per evdev an der Tastatur lauscht. Hier wird der Prozess nur mit den
richtigen Parametern gestartet, gestoppt und ueberwacht.
"""

from __future__ import annotations

import ctypes
import os
import shutil
import signal
import subprocess
from pathlib import Path

from gi.repository import GLib

from .packs import Pack

BINARY = "wayvibes"
PR_SET_PDEATHSIG = 1


def _die_with_parent() -> None:
    """Im Kindprozess: SIGTERM anfordern, sobald der Elternprozess stirbt.

    Ohne das laeuft wayvibes weiter, wenn omakeyklack hart abgeschossen
    wird - und die Tastatur klackt dann ohne Bedienoberflaeche weiter.
    """
    try:
        libc = ctypes.CDLL("libc.so.6", use_errno=True)
        libc.prctl(PR_SET_PDEATHSIG, signal.SIGTERM, 0, 0, 0)
    except OSError:
        pass


class EngineError(RuntimeError):
    pass


class Engine:
    """Haelt genau eine wayvibes-Instanz als Kindprozess."""

    def __init__(self, on_change=None) -> None:
        self._process: subprocess.Popen | None = None
        self._watch: int | None = None
        self._on_change = on_change

    # -- Status ---------------------------------------------------------

    @property
    def available(self) -> bool:
        return shutil.which(BINARY) is not None

    @property
    def running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    # -- Steuerung ------------------------------------------------------

    def start(self, pack: Pack, volume: float, device: str = "") -> None:
        if not self.available:
            raise EngineError(
                f"{BINARY} wurde nicht gefunden. Installiere es, z. B. mit "
                f"'yay -S wayvibes-git'."
            )
        self.stop()
        kill_strays()

        command = [BINARY, str(pack.directory), "-v", f"{volume:g}"]
        if device:
            command += ["--device-name", device]

        try:
            self._process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=_die_with_parent,
            )
        except OSError as exc:
            raise EngineError(f"{BINARY} liess sich nicht starten: {exc}") from exc

        self._watch = GLib.child_watch_add(
            GLib.PRIORITY_DEFAULT, self._process.pid, self._on_exit
        )
        self._notify()

    def stop(self) -> None:
        process, self._process = self._process, None
        if self._watch is not None:
            GLib.source_remove(self._watch)
            self._watch = None
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
        self._notify()

    def restart(self, pack: Pack, volume: float, device: str = "") -> None:
        """Neu starten - noetig, weil wayvibes Pack und Lautstaerke nur
        beim Start liest."""
        self.start(pack, volume, device)

    # -- intern ---------------------------------------------------------

    def _on_exit(self, pid: int, status: int) -> None:
        GLib.spawn_close_pid(pid)
        self._watch = None
        self._process = None
        self._notify()

    def _notify(self) -> None:
        if self._on_change is not None:
            self._on_change(self.running)


def kill_strays() -> None:
    """Fremde wayvibes-Instanzen beenden (z. B. aus einem alten Autostart),
    damit die Toene nicht doppelt kommen."""
    own = os.getpid()
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if pid == own:
            continue
        try:
            if (entry / "comm").read_text().strip() != BINARY:
                continue
            os.kill(pid, signal.SIGTERM)
        except (OSError, ValueError):
            continue


def keyboards() -> list[str]:
    """Namen der Eingabegeraete, die wie eine echte Tastatur aussehen.

    /proc/bus/input/devices listet auch Power-Buttons als 'kbd'; die haben
    aber nur eine Handvoll Tasten. Darum wird die KEY-Bitmaske gezaehlt.
    """
    try:
        blocks = Path("/proc/bus/input/devices").read_text().split("\n\n")
    except OSError:
        return []

    found: list[str] = []
    for block in blocks:
        name = ""
        is_kbd = False
        key_bits = 0
        for line in block.splitlines():
            if line.startswith('N: Name="'):
                name = line[9:].rstrip('"')
            elif line.startswith("H: Handlers=") and "kbd" in line:
                is_kbd = True
            elif line.startswith("B: KEY="):
                key_bits = sum(
                    bin(int(chunk, 16)).count("1")
                    for chunk in line[7:].split()
                    if chunk
                )
        if name and is_kbd and key_bits >= 60:
            found.append(name)
    return found
