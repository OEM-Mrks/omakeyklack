"""Einstellungsfenster: Soundpack waehlen, Lautstaerke regeln, Geraet setzen."""

from __future__ import annotations

from contextlib import contextmanager

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, Pango  # noqa: E402

from . import autostart  # noqa: E402
from .config import VOLUME_MAX, VOLUME_MIN  # noqa: E402
from .engine import keyboards  # noqa: E402

AUTO_DEVICE = "(automatisch waehlen)"
# Wartezeit, bevor eine Schiebereglerbewegung wirklich angewendet wird.
VOLUME_DEBOUNCE_MS = 350


class SettingsWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="omakeyklack")
        self.app = app
        self._volume_timer: int | None = None
        # Zaehler statt Flag: refresh() ruft Helfer, die selbst wieder
        # Widgets setzen - ein Bool wuerde die Sperre zu frueh loesen.
        self._updating = 0

        self.set_default_size(520, 640)
        self.set_icon_name("omakeyklack")

        header = Gtk.HeaderBar(title="Tastatur-Sounds", show_close_button=True)
        self.enabled_switch = Gtk.Switch(valign=Gtk.Align.CENTER)
        self.enabled_switch.connect("notify::active", self._on_enabled_toggled)
        header.pack_end(self.enabled_switch)
        self.set_titlebar(header)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_border_width(16)
        self.add(box)

        box.pack_start(self._build_pack_list(), True, True, 0)
        box.pack_start(self._build_volume(), False, False, 0)
        box.pack_start(self._build_options(), False, False, 0)
        box.pack_start(self._build_actions(), False, False, 0)

        self.status = Gtk.Label(xalign=0.0)
        self.status.get_style_context().add_class("dim-label")
        box.pack_start(self.status, False, False, 0)

        # Schliessen versteckt nur - die App lebt im Tray weiter.
        self.connect("delete-event", self._on_delete)

    @contextmanager
    def _frozen(self):
        """Solange aktiv, loesen Widget-Aenderungen keine Aktionen aus."""
        self._updating += 1
        try:
            yield
        finally:
            self._updating -= 1

    # -- Aufbau ---------------------------------------------------------

    def _build_pack_list(self) -> Gtk.Widget:
        frame = Gtk.Frame(label="Soundpack")
        frame.set_label_align(0.02, 0.5)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_min_content_height(260)

        self.pack_list = Gtk.ListBox()
        self.pack_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.pack_list.connect("row-selected", self._on_pack_selected)
        scroller.add(self.pack_list)
        frame.add(scroller)
        return frame

    def _build_volume(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.pack_start(Gtk.Label(label="Lautstärke", xalign=0.0), False, False, 0)

        self.volume_scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, VOLUME_MIN, VOLUME_MAX, 0.1
        )
        self.volume_scale.set_digits(1)
        self.volume_scale.set_value_pos(Gtk.PositionType.RIGHT)
        for mark in (0, 1, 2, 5, 10):
            self.volume_scale.add_mark(mark, Gtk.PositionType.BOTTOM, str(mark))
        self.volume_scale.connect("value-changed", self._on_volume_changed)
        box.pack_start(self.volume_scale, False, False, 0)
        return box

    def _build_options(self) -> Gtk.Widget:
        grid = Gtk.Grid(column_spacing=12, row_spacing=8)

        grid.attach(Gtk.Label(label="Tastatur", xalign=0.0), 0, 0, 1, 1)
        self.device_combo = Gtk.ComboBoxText()
        self.device_combo.set_hexpand(True)
        self.device_combo.connect("changed", self._on_device_changed)
        grid.attach(self.device_combo, 1, 0, 1, 1)

        self.preview_check = Gtk.CheckButton(label="Beim Auswählen vorhören")
        self.preview_check.connect("toggled", self._on_preview_toggled)
        grid.attach(self.preview_check, 0, 1, 2, 1)

        self.autostart_check = Gtk.CheckButton(label="Beim Anmelden starten")
        self.autostart_check.connect("toggled", self._on_autostart_toggled)
        grid.attach(self.autostart_check, 0, 2, 2, 1)
        return grid

    def _build_actions(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        demo = Gtk.Button(label="Demo abspielen")
        demo.connect("clicked", lambda *_: self.app.play_demo())
        box.pack_start(demo, False, False, 0)

        refresh = Gtk.Button(label="Packs neu einlesen")
        refresh.connect("clicked", lambda *_: self.app.reload_packs())
        box.pack_start(refresh, False, False, 0)
        return box

    # -- Anzeige aktualisieren ------------------------------------------

    def refresh(self) -> None:
        """Widgets an den aktuellen Zustand angleichen."""
        with self._frozen():
            self._fill_packs()
            self._fill_devices()
            self.volume_scale.set_value(self.app.config["volume"])
            self.enabled_switch.set_active(self.app.engine.running)
            self.preview_check.set_active(self.app.config["preview_on_select"])
            self.autostart_check.set_active(autostart.is_enabled())
        self.update_status()

    def update_status(self) -> None:
        pack = self.app.current_pack
        if not self.app.engine.available:
            text = "wayvibes ist nicht installiert - Sounds können nicht abgespielt werden."
        elif self.app.engine.running and pack:
            text = f"Aktiv: {pack.name}"
        elif pack:
            text = "Sounds sind aus."
        else:
            text = f"Keine Soundpacks in {self.app.config.packs_dir} gefunden."
        self.status.set_text(text)
        with self._frozen():
            self.enabled_switch.set_active(self.app.engine.running)

    def _fill_packs(self) -> None:
        with self._frozen():
            for child in self.pack_list.get_children():
                self.pack_list.remove(child)

            current = self.app.config["pack"]
            selected_row = None
            for pack in self.app.packs:
                row = Gtk.ListBoxRow()
                row.pack_key = pack.key
                inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                inner.set_border_width(8)
                title = Gtk.Label(label=pack.name, xalign=0.0)
                title.set_ellipsize(Pango.EllipsizeMode.END)
                subtitle = Gtk.Label(label=pack.key, xalign=0.0)
                subtitle.get_style_context().add_class("dim-label")
                inner.pack_start(title, False, False, 0)
                inner.pack_start(subtitle, False, False, 0)
                row.add(inner)
                self.pack_list.add(row)
                if pack.key == current:
                    selected_row = row

            self.pack_list.show_all()
            if selected_row is not None:
                self.pack_list.select_row(selected_row)

    def _fill_devices(self) -> None:
        with self._frozen():
            self.device_combo.remove_all()
            self.device_combo.append_text(AUTO_DEVICE)
            names = keyboards()
            current = self.app.config["device"]
            if current and current not in names:
                names.append(current)
            for name in names:
                self.device_combo.append_text(name)
            self.device_combo.set_active(names.index(current) + 1 if current in names else 0)

    # -- Ereignisse -----------------------------------------------------

    def _on_pack_selected(self, _list, row) -> None:
        if self._updating or row is None:
            return
        self.app.set_pack(row.pack_key)

    def _on_volume_changed(self, scale) -> None:
        if self._updating:
            return
        if self._volume_timer is not None:
            GLib.source_remove(self._volume_timer)

        def apply() -> bool:
            self._volume_timer = None
            self.app.set_volume(scale.get_value())
            return GLib.SOURCE_REMOVE

        self._volume_timer = GLib.timeout_add(VOLUME_DEBOUNCE_MS, apply)

    def _on_device_changed(self, combo) -> None:
        if self._updating:
            return
        text = combo.get_active_text() or AUTO_DEVICE
        self.app.set_device("" if text == AUTO_DEVICE else text)

    def _on_enabled_toggled(self, switch, _param) -> None:
        if self._updating:
            return
        self.app.set_enabled(switch.get_active())

    def _on_preview_toggled(self, check) -> None:
        if self._updating:
            return
        self.app.config["preview_on_select"] = check.get_active()
        self.app.config.save()

    def _on_autostart_toggled(self, check) -> None:
        if self._updating:
            return
        autostart.set_enabled(check.get_active())

    def _on_delete(self, *_args) -> bool:
        self.hide()
        return True  # Fenster nicht zerstoeren
