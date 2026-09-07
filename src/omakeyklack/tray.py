"""Tray-Symbol (StatusNotifierItem) mit Schnellzugriff auf Pack und Lautstaerke."""

from __future__ import annotations

from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("AyatanaAppIndicator3", "0.1")
from gi.repository import AyatanaAppIndicator3 as AppIndicator  # noqa: E402
from gi.repository import Gtk  # noqa: E402

from . import theme  # noqa: E402

INDICATOR_ID = "omakeyklack"

VOLUME_PRESETS = (0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 8.0)


class Tray:
    """Das Menue wird einmal aufgebaut und danach nur noch aktualisiert.

    Das Top-Level-Menue eines AppIndicators komplett neu zu bestuecken
    bringt libdbusmenu zum Absturz; deshalb werden ausschliesslich die
    Untermenues neu befuellt, und auch nur wenn sich die Packliste aendert.
    """

    def __init__(self, app) -> None:
        self.app = app
        self._updating = False
        self._pack_items: list[Gtk.CheckMenuItem] = []
        self._volume_items: list[tuple[Gtk.CheckMenuItem, float]] = []
        # Helle Leiste, helles Symbol - das waere unsichtbar. Der Waechter
        # meldet jeden Themewechsel, damit das Symbol mitgeht.
        self.theme_mode = theme.ModeWatcher(self._on_mode_changed)

        self.indicator = AppIndicator.Indicator.new(
            INDICATOR_ID,
            theme.icon_name(False, self.theme_mode.mode),
            AppIndicator.IndicatorCategory.HARDWARE,
        )
        icon_dir = _icon_dir()
        if icon_dir is not None:
            self.indicator.set_icon_theme_path(str(icon_dir))
        self.indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
        self.indicator.set_title("omakeyklack")

        self.menu = Gtk.Menu()
        self.pack_menu = Gtk.Menu()
        self.volume_menu = Gtk.Menu()
        self._build_menu()
        self.indicator.set_menu(self.menu)
        self.rebuild_menus()

    # -- Aufbau (genau einmal) ------------------------------------------

    def _build_menu(self) -> None:
        self.toggle_item = Gtk.CheckMenuItem(label="Tastatur-Sounds")
        self.toggle_item.connect("toggled", self._on_toggle)
        self.menu.append(self.toggle_item)
        self.menu.append(Gtk.SeparatorMenuItem())

        pack_item = Gtk.MenuItem(label="Soundpack")
        pack_item.set_submenu(self.pack_menu)
        self.menu.append(pack_item)

        volume_item = Gtk.MenuItem(label="Lautstärke")
        volume_item.set_submenu(self.volume_menu)
        self.menu.append(volume_item)

        demo_item = Gtk.MenuItem(label="Demo abspielen")
        demo_item.connect("activate", lambda *_: self.app.play_demo())
        self.menu.append(demo_item)

        self.menu.append(Gtk.SeparatorMenuItem())

        settings_item = Gtk.MenuItem(label="Einstellungen…")
        settings_item.connect("activate", lambda *_: self.app.show_window())
        self.menu.append(settings_item)

        quit_item = Gtk.MenuItem(label="Beenden")
        quit_item.connect("activate", lambda *_: self.app.quit_app())
        self.menu.append(quit_item)

        self.menu.show_all()

    # -- Untermenues neu befuellen (nur wenn sich die Packs aendern) -----

    def rebuild_menus(self) -> None:
        self._updating = True
        try:
            self._fill_pack_menu()
            self._fill_volume_menu()
        finally:
            self._updating = False
        self.refresh()

    def _fill_pack_menu(self) -> None:
        for child in self.pack_menu.get_children():
            self.pack_menu.remove(child)
            child.destroy()
        self._pack_items.clear()

        if not self.app.packs:
            empty = Gtk.MenuItem(label="Keine Soundpacks gefunden")
            empty.set_sensitive(False)
            self.pack_menu.append(empty)
            self.pack_menu.show_all()
            return

        for pack in self.app.packs:
            item = Gtk.CheckMenuItem(label=pack.name)
            item.set_draw_as_radio(True)
            item.pack_key = pack.key
            item.connect("toggled", self._on_pack_chosen, pack.key)
            self.pack_menu.append(item)
            self._pack_items.append(item)
        self.pack_menu.show_all()

    def _fill_volume_menu(self) -> None:
        for child in self.volume_menu.get_children():
            self.volume_menu.remove(child)
            child.destroy()
        self._volume_items.clear()

        for value in VOLUME_PRESETS:
            item = Gtk.CheckMenuItem(label=f"×{value:g}")
            item.set_draw_as_radio(True)
            item.connect("toggled", self._on_volume_chosen, value)
            self.volume_menu.append(item)
            self._volume_items.append((item, value))
        self.volume_menu.show_all()

    # -- Aktualisierung (haeufig, ohne Neuaufbau) ------------------------

    def refresh(self) -> None:
        self._updating = True
        try:
            current_pack = self.app.config["pack"]
            for item in self._pack_items:
                item.set_active(item.pack_key == current_pack)

            current_volume = float(self.app.config["volume"])
            for item, value in self._volume_items:
                # Ein per Schieberegler gesetzter Zwischenwert laesst
                # bewusst alle Haekchen leer.
                item.set_active(abs(value - current_volume) < 1e-6)

            self.toggle_item.set_active(self.app.engine.running)
        finally:
            self._updating = False
        self.update_icon()

    def update_icon(self) -> None:
        running = self.app.engine.running
        self.indicator.set_icon_full(
            theme.icon_name(running, self.theme_mode.mode),
            "Tastatur-Sounds an" if running else "Tastatur-Sounds aus",
        )
        self._updating = True
        self.toggle_item.set_active(running)
        self._updating = False

    def shutdown(self) -> None:
        self.theme_mode.stop()

    # -- Ereignisse -----------------------------------------------------

    def _on_mode_changed(self, _mode: str) -> None:
        self.update_icon()

    def _on_toggle(self, item) -> None:
        if self._updating:
            return
        self.app.set_enabled(item.get_active())

    def _on_pack_chosen(self, item, key: str) -> None:
        if self._updating:
            return
        if not item.get_active():
            # Abwaehlen des aktiven Packs ergibt keinen Sinn - Haekchen zurueck.
            if key == self.app.config["pack"]:
                self._updating = True
                item.set_active(True)
                self._updating = False
            return
        self.app.set_pack(key)

    def _on_volume_chosen(self, item, value: float) -> None:
        if self._updating or not item.get_active():
            return
        self.app.set_volume(value)


def _icon_dir() -> Path | None:
    """Verzeichnis, in dem die Tray-Symbole tatsaechlich liegen.

    set_icon_theme_path haelt genau einen Pfad - ein zweiter Aufruf
    ueberschreibt den ersten. Darum wird das erste Verzeichnis genommen, das
    die Datei wirklich enthaelt; ein Pfad ohne Symbol wuerde die Leiste auf
    ein Ersatzsymbol zurueckfallen lassen. Uebergeben wird der apps-Ordner,
    weil die gaengigen Leisten dort direkt nach <name>.svg suchen.
    """
    candidates = [
        Path.home() / ".local/share/icons/hicolor/scalable/apps",
        Path("/usr/share/icons/hicolor/scalable/apps"),
        # Start aus dem Quellbaum, ohne Installation
        Path(__file__).resolve().parents[2] / "data/icons/hicolor/scalable/apps",
    ]
    for path in candidates:
        if (path / f"{theme.icon_name(True, theme.DARK)}.svg").is_file():
            return path
    return None
