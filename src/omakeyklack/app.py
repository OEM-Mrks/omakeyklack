"""Die Anwendung: haelt Konfiguration, Packs, Engine, Tray und Fenster zusammen."""

from __future__ import annotations

import signal
import sys

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gio, GLib, Gtk  # noqa: E402

from . import APP_ID, autostart, packs as packs_module, tray as tray_module  # noqa: E402
from .config import Config, clamp_volume  # noqa: E402
from .engine import Engine, EngineError  # noqa: E402
from .preview import Preview  # noqa: E402
from .tray import Tray  # noqa: E402
from .window import SettingsWindow  # noqa: E402


class Omakeyklack(Gtk.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
        )
        self.config = Config()
        self.packs: list = []
        self.engine = Engine(on_change=self._on_engine_change)
        self.preview = Preview()
        self.tray: Tray | None = None
        self.window: SettingsWindow | None = None
        self.last_error: str = ""

        self.add_main_option(
            "tray", ord("t"), GLib.OptionFlags.NONE, GLib.OptionArg.NONE,
            "Nur ins Tray starten, kein Fenster oeffnen", None,
        )

    # -- Lebenszyklus ---------------------------------------------------

    def do_startup(self) -> None:
        Gtk.Application.do_startup(self)
        self.hold()  # ohne offenes Fenster am Leben bleiben
        # SIGTERM/SIGINT sauber abfangen, damit do_shutdown laeuft und
        # wayvibes mitgenommen wird.
        for sig in (signal.SIGINT, signal.SIGTERM):
            GLib.unix_signal_add(GLib.PRIORITY_HIGH, sig, self._on_signal)
        self.reload_packs(refresh_ui=False)
        self._apply_autostart_default()
        self._build_tray()
        if self.config["enabled"]:
            self._start_engine()
        if self.tray is not None:
            self.tray.refresh()

    def _apply_autostart_default(self) -> None:
        """Beim allerersten Start den Autostart anlegen.

        Eine Tray-App, die nach dem naechsten Anmelden weg ist, wirkt wie
        eine, die nicht funktioniert - darum ist der Autostart die
        sinnvollere Vorbelegung. Genau einmal allerdings: wer ihn danach
        abschaltet, soll ihn nicht beim naechsten Start wiederfinden. Der
        Merker steht in der Konfiguration, ueberlebt also auch eine
        Neuinstallation.
        """
        if self.config["autostart_initialized"]:
            return
        self.config["autostart_initialized"] = True
        # Nur bei einer wirklich frischen Einrichtung eingreifen. Wer schon
        # eine Konfiguration hat, hat seine Wahl getroffen - auch die, den
        # Autostart nicht zu wollen.
        if self.config.first_run and not autostart.is_enabled():
            try:
                autostart.set_enabled(True)
            except OSError as exc:
                print(f"omakeyklack: Autostart nicht angelegt: {exc}", file=sys.stderr)
        self.config.save()

    def _build_tray(self) -> None:
        """Tray aufbauen - und ohne Tray weiterlaufen, statt zu sterben.

        Fehlt libayatana-appindicator, war das frueher ein Traceback beim
        Start. Das Fenster und wayvibes funktionieren aber auch ohne
        Tray-Symbol, darum wird der Ausfall nur gemeldet.
        """
        if tray_module.UNAVAILABLE:
            self.last_error = tray_module.UNAVAILABLE
            print(f"omakeyklack: {tray_module.UNAVAILABLE}", file=sys.stderr)
            return
        try:
            self.tray = Tray(self)
        except Exception as exc:  # noqa: BLE001 - Tray ist nie den Start wert
            self.last_error = f"Tray-Symbol liess sich nicht anlegen: {exc}"
            print(f"omakeyklack: {self.last_error}", file=sys.stderr)

    def do_command_line(self, command_line) -> int:
        options = command_line.get_options_dict().end().unpack()
        # Ohne Tray waere "--tray" eine App ganz ohne Bedienoberflaeche.
        if not options.get("tray") or self.tray is None:
            self.show_window()
        return 0

    def do_shutdown(self) -> None:
        self.preview.cancel()
        self.engine.stop()
        if self.tray is not None:
            self.tray.shutdown()
        Gtk.Application.do_shutdown(self)

    def _on_signal(self) -> bool:
        self.quit_app()
        return GLib.SOURCE_REMOVE

    def quit_app(self) -> None:
        self.release()
        self.quit()

    # -- Zustand --------------------------------------------------------

    @property
    def current_pack(self):
        pack = packs_module.find(self.packs, self.config["pack"])
        if pack is None and self.packs:
            pack = self.packs[0]
        return pack

    def reload_packs(self, refresh_ui: bool = True) -> None:
        self.packs = packs_module.discover(self.config.packs_dir)
        # Verschwundenes Pack durch das erste vorhandene ersetzen.
        if self.packs and not packs_module.find(self.packs, self.config["pack"]):
            self.config["pack"] = self.packs[0].key
            self.config.save()
        if refresh_ui:
            # Packliste hat sich geaendert -> Untermenues wirklich neu bauen.
            if self.tray is not None:
                self.tray.rebuild_menus()
            if self.window is not None and self.window.get_visible():
                self.window.refresh()

    # -- Aktionen -------------------------------------------------------

    def set_pack(self, key: str) -> None:
        if key == self.config["pack"]:
            return
        self.config["pack"] = key
        self.config.save()
        pack = self.current_pack
        if pack and self.config["preview_on_select"]:
            self.preview.play_pack(pack, self.config["volume"])
        if self.engine.running:
            self._start_engine()
        self._refresh_ui()

    def set_volume(self, volume: float) -> None:
        volume = clamp_volume(volume)
        if abs(volume - float(self.config["volume"])) < 1e-6:
            return
        self.config["volume"] = volume
        self.config.save()
        pack = self.current_pack
        if pack and self.config["preview_on_select"]:
            self.preview.play_single(pack, volume)
        if self.engine.running:
            self._start_engine()
        self._refresh_ui()

    def set_device(self, device: str) -> None:
        if device == self.config["device"]:
            return
        self.config["device"] = device
        self.config.save()
        if self.engine.running:
            self._start_engine()

    def set_enabled(self, enabled: bool) -> None:
        if enabled == self.engine.running:
            return
        self.config["enabled"] = enabled
        self.config.save()
        if enabled:
            self._start_engine()
        else:
            self.engine.stop()
        self._refresh_ui()

    def preview_pack(self, key: str, limit: int | None = None) -> None:
        """Ein Pack vorhoeren, ohne es zu aktivieren."""
        pack = packs_module.find(self.packs, key)
        if pack is not None:
            self.preview.play_pack(pack, float(self.config["volume"]), limit)

    def play_demo(self) -> None:
        pack = self.current_pack
        if pack:
            self.preview.play_pack(pack, self.config["volume"])

    def show_window(self) -> None:
        if self.window is None:
            self.window = SettingsWindow(self)
        self.window.refresh()
        self.window.show_all()
        self.window.present()

    # -- intern ---------------------------------------------------------

    def _start_engine(self) -> None:
        pack = self.current_pack
        if pack is None:
            self.last_error = "Kein Soundpack gefunden."
            return
        try:
            self.engine.start(pack, float(self.config["volume"]), self.config["device"])
            self.last_error = ""
        except EngineError as exc:
            self.last_error = str(exc)
            print(f"omakeyklack: {exc}", file=sys.stderr)

    def _on_engine_change(self, running: bool) -> None:
        if self.tray is not None:
            self.tray.update_icon()
        if self.window is not None:
            self.window.update_status()

    def _refresh_ui(self) -> None:
        if self.tray is not None:
            self.tray.refresh()
        if self.window is not None and self.window.get_visible():
            # Die Packliste selbst aendert sich hier nie - nur reload_packs()
            # baut sie neu. Nicht neu fuellen: set_pack() laeuft auch aus dem
            # "row-selected"-Signal heraus, siehe SettingsWindow.refresh().
            self.window.refresh(refill_packs=False)
