"""Demo-Wiedergabe der Soundpacks ueber GStreamer.

Bewusst getrennt von der Engine: wayvibes spielt Toene bei echten
Tastendruecken, hier geht es nur um das Vorhoeren beim Auswaehlen.
"""

from __future__ import annotations

import gi

gi.require_version("Gst", "1.0")
from gi.repository import GLib, Gst  # noqa: E402

from .packs import Pack, Sound  # noqa: E402

# Abstaende der Demo-Anschlaege in ms - leicht ungleichmaessig, damit es
# nach Tippen klingt und nicht nach Metronom.
DEMO_TIMING = (0, 95, 185, 300, 390, 520, 665)


class Preview:
    """Spielt einzelne Sounds oder eine kurze Tippsequenz ab."""

    def __init__(self) -> None:
        if not Gst.is_initialized():
            Gst.init(None)
        self._pending: set[int] = set()
        self._active: list[Gst.Element] = []

    # -- oeffentlich ----------------------------------------------------

    def play_pack(self, pack: Pack, volume: float) -> None:
        """Kurze Tippsequenz aus dem Pack abspielen."""
        self.cancel()
        sounds = pack.demo_sounds()
        for index, sound in enumerate(sounds):
            delay = DEMO_TIMING[index] if index < len(DEMO_TIMING) else index * 95
            self._schedule(delay, sound, volume)

    def play_single(self, pack: Pack, volume: float) -> None:
        """Nur einen Anschlag - fuer schnelles Nachregeln der Lautstaerke."""
        self.cancel()
        sounds = pack.demo_sounds()
        if sounds:
            self._play(sounds[0], volume)

    def cancel(self) -> None:
        """Laufende und geplante Wiedergabe stoppen."""
        for source in self._pending:
            GLib.source_remove(source)
        self._pending = set()
        for player in list(self._active):
            self._teardown(player)

    # -- intern ---------------------------------------------------------

    def _schedule(self, delay_ms: int, sound: Sound, volume: float) -> None:
        """Einen Anschlag verzoegert abspielen. Der Timer traegt sich beim
        Ausloesen selbst aus, damit cancel() keine toten IDs anfasst."""
        if delay_ms <= 0:
            self._play(sound, volume)
            return

        holder: dict[str, int] = {}

        def fire() -> bool:
            self._pending.discard(holder["id"])
            self._play(sound, volume)
            return GLib.SOURCE_REMOVE

        holder["id"] = GLib.timeout_add(delay_ms, fire)
        self._pending.add(holder["id"])

    def _play(self, sound: Sound, volume: float) -> None:
        player = Gst.ElementFactory.make("playbin", None)
        if player is None:
            return
        player.set_property("uri", Gst.filename_to_uri(str(sound.path)))
        # playbin-volume ist wie wayvibes -v ein linearer Faktor.
        player.set_property("volume", max(0.0, min(10.0, float(volume))))

        bus = player.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._on_message, sound)

        self._active.append(player)
        player.set_state(Gst.State.PAUSED if sound.is_slice else Gst.State.PLAYING)

    def _on_message(self, bus: Gst.Bus, message: Gst.Message, sound: Sound) -> None:
        player = message.src
        while player is not None and not isinstance(player, Gst.Pipeline):
            player = player.get_parent()
        if player is None:
            return

        if message.type in (Gst.MessageType.EOS, Gst.MessageType.ERROR):
            self._teardown(player)
        elif message.type == Gst.MessageType.ASYNC_DONE and sound.is_slice:
            self._seek_slice(player, sound)

    def _seek_slice(self, player: Gst.Element, sound: Sound) -> None:
        """Sprite-Packs: nur den definierten Ausschnitt spielen."""
        start = sound.offset_ms * Gst.MSECOND
        stop = (sound.offset_ms + sound.duration_ms) * Gst.MSECOND
        player.seek(
            1.0,
            Gst.Format.TIME,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE,
            Gst.SeekType.SET,
            start,
            Gst.SeekType.SET,
            stop,
        )
        player.set_state(Gst.State.PLAYING)

    def _teardown(self, player: Gst.Element) -> None:
        bus = player.get_bus()
        if bus is not None:
            bus.remove_signal_watch()
        player.set_state(Gst.State.NULL)
        if player in self._active:
            self._active.remove(player)
