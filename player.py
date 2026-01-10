"""
Real-time MIDI Playback Module

Provides real-time playback of generated music using system MIDI output.
Supports both hardware MIDI devices and virtual MIDI ports.
"""

import time
import threading
from typing import List, Optional, Callable
from dataclasses import dataclass

try:
    import mido
    from mido import Message
    MIDO_AVAILABLE = True
except ImportError:
    MIDO_AVAILABLE = False
    print("Warning: mido not installed. Install with: pip install mido python-rtmidi")


@dataclass
class PlaybackState:
    """Tracks the current playback state."""
    is_playing: bool = False
    is_paused: bool = False
    current_tick: int = 0
    should_stop: bool = False


class MIDIPlayer:
    """
    Real-time MIDI player that sends events to a MIDI output port.
    """

    def __init__(self):
        self.output_port: Optional[mido.ports.BaseOutput] = None
        self.state = PlaybackState()
        self._playback_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def get_available_ports(self) -> List[str]:
        """Returns list of available MIDI output ports."""
        if not MIDO_AVAILABLE:
            return []
        try:
            return mido.get_output_names()
        except Exception as e:
            print(f"Error getting MIDI ports: {e}")
            return []

    def open_port(self, port_name: Optional[str] = None) -> bool:
        """
        Opens a MIDI output port.

        Args:
            port_name: Name of port to open. If None, opens default/first available.

        Returns:
            True if port opened successfully.
        """
        if not MIDO_AVAILABLE:
            print("mido not available")
            return False

        try:
            self.close_port()

            available = self.get_available_ports()

            if port_name and port_name in available:
                self.output_port = mido.open_output(port_name)
            elif available:
                # Try to find a suitable port
                # Prefer virtual ports or common DAW ports
                preferred = ['IAC', 'loopMIDI', 'Bus', 'Virtual', 'Microsoft GS']
                selected = available[0]

                for port in available:
                    for pref in preferred:
                        if pref.lower() in port.lower():
                            selected = port
                            break

                self.output_port = mido.open_output(selected)
                print(f"Opened MIDI port: {selected}")
            else:
                # Try to open a virtual port (works on macOS/Linux with rtmidi)
                try:
                    self.output_port = mido.open_output('Algorythm', virtual=True)
                    print("Created virtual MIDI port: Algorythm")
                except Exception:
                    print("No MIDI output ports available and couldn't create virtual port")
                    return False

            return True

        except Exception as e:
            print(f"Error opening MIDI port: {e}")
            return False

    def close_port(self):
        """Closes the current MIDI output port."""
        if self.output_port:
            try:
                # Send all notes off
                for channel in range(16):
                    self.output_port.send(Message('control_change',
                                                   channel=channel,
                                                   control=123,  # All Notes Off
                                                   value=0))
                self.output_port.close()
            except Exception:
                pass
            self.output_port = None

    def play(
        self,
        events: List,
        timing,
        on_progress: Optional[Callable[[int, int], None]] = None
    ) -> bool:
        """
        Plays a list of NoteEvents in real-time.

        Args:
            events: List of NoteEvent objects to play
            timing: TimingConfig with BPM and timing info
            on_progress: Optional callback(current_tick, total_ticks)

        Returns:
            True if playback completed successfully.
        """
        if not self.output_port:
            if not self.open_port():
                return False

        if not events:
            return True

        # Reset state
        with self._lock:
            self.state.is_playing = True
            self.state.is_paused = False
            self.state.should_stop = False
            self.state.current_tick = 0

        # Build timeline of MIDI messages
        timeline = []
        for event in events:
            timeline.append({
                'tick': event.start_tick,
                'type': 'note_on',
                'note': event.pitch,
                'velocity': event.velocity,
                'channel': event.channel
            })
            timeline.append({
                'tick': event.start_tick + event.duration_ticks,
                'type': 'note_off',
                'note': event.pitch,
                'velocity': 0,
                'channel': event.channel
            })

        # Sort by tick, note_off before note_on at same tick
        timeline.sort(key=lambda x: (x['tick'], 0 if x['type'] == 'note_off' else 1))

        if not timeline:
            return True

        # Calculate timing
        ticks_per_beat = timing.ppq
        microseconds_per_beat = mido.bpm2tempo(timing.bpm)
        seconds_per_tick = microseconds_per_beat / 1_000_000 / ticks_per_beat

        total_ticks = max(e['tick'] for e in timeline)

        # Send program changes for each channel used
        channels_used = set(e['channel'] for e in timeline)
        programs = {
            0: 80,   # Melody: Square Lead
            1: 33,   # Bass: Finger Bass
            2: 4,    # Chords: Electric Piano
            3: 88,   # Arpeggio: Synth Lead
            # Channel 9 (drums) doesn't need program change
        }
        for ch in channels_used:
            if ch != 9 and ch in programs:
                self.output_port.send(Message('program_change',
                                               channel=ch,
                                               program=programs[ch]))

        # Playback loop
        start_time = time.perf_counter()
        event_index = 0

        try:
            while event_index < len(timeline):
                with self._lock:
                    if self.state.should_stop:
                        break
                    if self.state.is_paused:
                        time.sleep(0.01)
                        continue

                current_event = timeline[event_index]
                target_tick = current_event['tick']

                # Calculate when this event should play
                target_time = start_time + (target_tick * seconds_per_tick)
                current_time = time.perf_counter()

                # Wait until it's time
                wait_time = target_time - current_time
                if wait_time > 0:
                    time.sleep(wait_time)

                # Send the MIDI message
                msg = Message(
                    current_event['type'],
                    note=current_event['note'],
                    velocity=current_event['velocity'],
                    channel=current_event['channel']
                )
                self.output_port.send(msg)

                # Update state
                with self._lock:
                    self.state.current_tick = target_tick

                # Progress callback
                if on_progress:
                    on_progress(target_tick, total_ticks)

                event_index += 1

        except Exception as e:
            print(f"Playback error: {e}")
            return False

        finally:
            with self._lock:
                self.state.is_playing = False

            # All notes off
            if self.output_port:
                for channel in channels_used:
                    self.output_port.send(Message('control_change',
                                                   channel=channel,
                                                   control=123,
                                                   value=0))

        return not self.state.should_stop

    def stop(self):
        """Stops playback immediately."""
        with self._lock:
            self.state.should_stop = True
            self.state.is_playing = False

    def pause(self):
        """Pauses playback."""
        with self._lock:
            self.state.is_paused = True

    def resume(self):
        """Resumes paused playback."""
        with self._lock:
            self.state.is_paused = False

    @property
    def is_playing(self) -> bool:
        with self._lock:
            return self.state.is_playing


# Global player instance for convenience
_player: Optional[MIDIPlayer] = None


def get_player() -> MIDIPlayer:
    """Gets or creates the global MIDIPlayer instance."""
    global _player
    if _player is None:
        _player = MIDIPlayer()
    return _player


def play_events_realtime(
    events: List,
    timing,
    port_name: Optional[str] = None,
    on_progress: Optional[Callable[[int, int], None]] = None
) -> bool:
    """
    Convenience function to play events in real-time.

    Args:
        events: List of NoteEvent objects
        timing: TimingConfig with BPM info
        port_name: Optional MIDI port name
        on_progress: Optional progress callback

    Returns:
        True if playback successful.
    """
    player = get_player()

    if port_name:
        player.open_port(port_name)
    elif not player.output_port:
        if not player.open_port():
            return False

    return player.play(events, timing, on_progress)


def stop_playback():
    """Stops any current playback."""
    player = get_player()
    player.stop()


def list_midi_ports() -> List[str]:
    """Returns list of available MIDI output ports."""
    return get_player().get_available_ports()


# Simple test
if __name__ == "__main__":
    print("Available MIDI ports:")
    ports = list_midi_ports()
    for i, port in enumerate(ports):
        print(f"  {i}: {port}")

    if not ports:
        print("  (none found - you may need to install python-rtmidi)")
        print("  Install with: pip install python-rtmidi")
