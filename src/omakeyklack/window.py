"""Einstellungsfenster: Soundpack waehlen, Lautstaerke regeln, Geraet setzen."""

from __future__ import annotations

import grp
import os
from contextlib import contextmanager

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk, Pango  # noqa: E402

from . import autostart  # noqa: E402
from .config import VOLUME_MAX, VOLUME_MIN  # noqa: E402
from .engine import keyboards  # noqa: E402

AUTO_DEVICE = "(automatisch waehlen)"
# Wartezeit, bevor eine Schiebereglerbewegung wirklich angewendet wird.
VOLUME_DEBOUNCE_MS = 350
# Wartezeit, bis die Maus ueber einem Eintrag als "gemeint" gilt. Ohne die
# feuert jedes Ueberstreichen der Liste eine Vorschau ab.
HOVER_DELAY_MS = 220
# Beim Ueberfahren nur ein paar Anschlaege, nicht die volle Tippsequenz.
HOVER_PREVIEW_KEYS = 3


def _may_read_input() -> bool:
    """Darf der Benutzer die Eingabegeraete lesen?

    wayvibes horcht per evdev an /dev/input; ohne die Gruppe 'input'
    startet es zwar, hoert aber nie eine Taste. Das ist die Huerde, die
    beim Einrichten am haeufigsten uebersehen wird - und von aussen sieht
    sie aus, als taete die App einfach nichts.
    """
    try:
        gid = grp.getgrnam("input").gr_gid
    except KeyError:
        return True  # keine Gruppe 'input' -> hier nichts zu melden
    # Bewusst die Gruppen der laufenden Sitzung, nicht /etc/group: nach
    # 'usermod -aG' steht der Benutzer zwar drin, darf aber erst nach dem
    # naechsten Anmelden wirklich lesen.
    return gid in os.getgroups() or os.geteuid() == 0


class SettingsWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="omakeyklack")
        self.app = app
        self._volume_timer: int | None = None
        self._hover_timer: int | None = None
        self._hovered_key: str | None = None
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
        # ListBoxRow hat kein eigenes Ereignisfenster, darum lauscht die
        # Liste selbst und ordnet die Position ueber get_row_at_y zu.
        self.pack_list.add_events(
            Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK
        )
        self.pack_list.connect("motion-notify-event", self._on_pack_motion)
        self.pack_list.connect("leave-notify-event", self._on_pack_leave)
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

        self.hover_check = Gtk.CheckButton(label="Beim Darüberfahren vorhören")
        self.hover_check.connect("toggled", self._on_hover_toggled)
        grid.attach(self.hover_check, 0, 1, 2, 1)

        self.preview_check = Gtk.CheckButton(label="Beim Auswählen vorhören")
        self.preview_check.connect("toggled", self._on_preview_toggled)
        grid.attach(self.preview_check, 0, 2, 2, 1)

        self.autostart_check = Gtk.CheckButton(label="Beim Anmelden starten")
        self.autostart_check.connect("toggled", self._on_autostart_toggled)
        grid.attach(self.autostart_check, 0, 3, 2, 1)
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

    def refresh(self, refill_packs: bool = True) -> None:
        """Widgets an den aktuellen Zustand angleichen.

        refill_packs=False laesst die vorhandenen Zeilen stehen und gleicht
        nur die Auswahl ab. Das ist Pflicht, wenn der Aufruf (ueber
        app.set_pack) aus "row-selected" kommt: GTK arbeitet nach dem Signal
        mit der angeklickten Zeile weiter und haelt darauf nur einen
        geliehenen Zeiger. Ein Neuaufbau gibt sie unter GTK weg - der Zugriff
        in gtk_list_box_update_cursor traf dann freigegebenen Speicher.
        """
        with self._frozen():
            if refill_packs:
                self._fill_packs()
            else:
                self._select_current_pack()
            self._fill_devices()
            self.volume_scale.set_value(self.app.config["volume"])
            self.enabled_switch.set_active(self.app.engine.running)
            self.preview_check.set_active(self.app.config["preview_on_select"])
            self.hover_check.set_active(self.app.config["preview_on_hover"])
            self.autostart_check.set_active(autostart.is_enabled())
        self.update_status()

    def update_status(self) -> None:
        """Statuszeile setzen - fehlende Voraussetzungen zuerst.

        Wer die App zum ersten Mal oeffnet, soll hier lesen koennen, was
        noch fehlt, statt vor einer leeren Liste zu sitzen. Deshalb nennt
        jede Meldung auch gleich den Befehl, der weiterhilft.
        """
        pack = self.app.current_pack
        if not self.app.engine.available:
            text = ("wayvibes ist nicht installiert - ohne das bleibt die Tastatur "
                    "stumm. Abhilfe im Terminal: omakeyklack --check --fix")
        elif not self.app.packs:
            text = (f"Keine Soundpacks in {self.app.config.packs_dir}. "
                    "Abhilfe im Terminal: omakeyklack --check --fix")
        elif not _may_read_input():
            text = ("Der Benutzer darf die Tastatur nicht lesen (Gruppe 'input'). "
                    "Abhilfe im Terminal: omakeyklack --check --fix")
        elif self.app.engine.running and pack:
            text = f"Aktiv: {pack.name}"
        else:
            text = "Sounds sind aus."
        self.status.set_text(text)
        with self._frozen():
            self.enabled_switch.set_active(self.app.engine.running)

    def _fill_packs(self) -> None:
        with self._frozen():
            for child in self.pack_list.get_children():
                self.pack_list.remove(child)

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

            self.pack_list.show_all()
            self._select_current_pack()

    def _select_current_pack(self) -> None:
        """Auswahl an die Konfiguration angleichen, ohne Zeilen anzufassen."""
        with self._frozen():
            current = self.app.config["pack"]
            for row in self.pack_list.get_children():
                if getattr(row, "pack_key", None) == current:
                    self.pack_list.select_row(row)
                    return

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
        # Ein Klick beendet die Hover-Vorschau; gleich folgt die volle Sequenz.
        self._cancel_hover()
        self.app.set_pack(row.pack_key)

    def _on_pack_motion(self, listbox, event) -> bool:
        row = listbox.get_row_at_y(int(event.y))
        key = getattr(row, "pack_key", None)
        if key == self._hovered_key:
            return False
        self._hovered_key = key
        self._cancel_hover()
        if key and self.app.config["preview_on_hover"]:
            self._hover_timer = GLib.timeout_add(HOVER_DELAY_MS, self._fire_hover, key)
        return False

    def _on_pack_leave(self, listbox, event) -> bool:
        # INFERIOR heisst: der Zeiger ist nur in ein Kind gewandert, die Liste
        # wurde gar nicht verlassen.
        if event.detail == Gdk.NotifyType.INFERIOR:
            return False
        # Beim Wechsel zwischen Zeilen kommen ebenfalls Verlassen-Ereignisse,
        # obwohl der Zeiger noch ueber der Liste steht. Wuerde hier trotzdem
        # zurueckgesetzt, spielte dieselbe Zeile gleich noch einmal vor.
        allocation = listbox.get_allocation()
        if 0 <= event.x < allocation.width and 0 <= event.y < allocation.height:
            return False
        self._hovered_key = None
        self._cancel_hover()
        return False

    def _fire_hover(self, key: str) -> bool:
        self._hover_timer = None
        self.app.preview_pack(key, limit=HOVER_PREVIEW_KEYS)
        return GLib.SOURCE_REMOVE

    def _cancel_hover(self) -> None:
        if self._hover_timer is not None:
            GLib.source_remove(self._hover_timer)
            self._hover_timer = None

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

    def _on_hover_toggled(self, check) -> None:
        if self._updating:
            return
        self.app.config["preview_on_hover"] = check.get_active()
        self.app.config.save()
        if not check.get_active():
            self._cancel_hover()

    def _on_autostart_toggled(self, check) -> None:
        if self._updating:
            return
        autostart.set_enabled(check.get_active())

    def _on_delete(self, *_args) -> bool:
        self._cancel_hover()
        self.app.preview.cancel()
        self.hide()
        return True  # Fenster nicht zerstoeren
