"""XDG-Autostart-Eintrag an- und abschalten."""

from __future__ import annotations

import os
from pathlib import Path

AUTOSTART_DIR = Path(
    os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
) / "autostart"
AUTOSTART_FILE = AUTOSTART_DIR / "omakeyklack.desktop"

TEMPLATE = """[Desktop Entry]
Type=Application
Version=1.0
Name=omakeyklack
Comment=Tastatur-Sounds beim Anmelden starten
Exec={exec_path} --tray
Icon=omakeyklack
Terminal=false
StartupNotify=false
X-GNOME-Autostart-enabled=true
"""


def launcher_command() -> str:
    """Pfad, mit dem sich die App wieder starten laesst."""
    installed = Path.home() / ".local" / "bin" / "omakeyklack"
    if installed.is_file():
        return str(installed)
    return "omakeyklack"


def is_enabled() -> bool:
    if not AUTOSTART_FILE.is_file():
        return False
    try:
        text = AUTOSTART_FILE.read_text(encoding="utf-8")
    except OSError:
        return False
    # Hidden=true ist die uebliche Art, einen Eintrag stillzulegen.
    return "Hidden=true" not in text


def set_enabled(enabled: bool) -> None:
    if enabled:
        AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
        AUTOSTART_FILE.write_text(
            TEMPLATE.format(exec_path=launcher_command()), encoding="utf-8"
        )
    else:
        AUTOSTART_FILE.unlink(missing_ok=True)
