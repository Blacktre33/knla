"""
Algorythm: Procedural Music Engine

A Tkinter GUI for the procedural MIDI music generator.
Allows building songs from sections and playing/exporting them.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import random

from procedural_music import (
    TimingConfig, MusicConfig, Scale, SongSection,
    create_motif, build_song, apply_song_dynamics,
    write_midi_file
)
from player import play_events_realtime, stop_playback, list_midi_ports


class AlgorythmApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Algorythm: Procedural Music Engine")
        self.root.geometry("950x650")
        self.root.minsize(800, 500)

        # --- STATE ---
        self.sections_list = []
        self.is_playing = False
        self.motifs = {}
        self.last_events = None
        self.last_timing = None

        # --- UI LAYOUT ---
        self._init_global_controls()
        self._init_progression_controls()
        self._init_section_manager()
        self._init_transport_controls()

    def _init_global_controls(self):
        """Top bar for BPM, Key, Scale."""
        frame = ttk.LabelFrame(self.root, text="Global Settings", padding=10)
        frame.pack(fill="x", padx=10, pady=5)

        # BPM
        ttk.Label(frame, text="BPM:").pack(side="left")
        self.bpm_var = tk.IntVar(value=120)
        bpm_spin = ttk.Spinbox(frame, from_=40, to=240, textvariable=self.bpm_var, width=5)
        bpm_spin.pack(side="left", padx=5)

        # Root Note
        ttk.Label(frame, text="Key:").pack(side="left", padx=(15, 0))
        self.root_note_combo = ttk.Combobox(
            frame,
            values=["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"],
            width=5,
            state="readonly"
        )
        self.root_note_combo.set("C")
        self.root_note_combo.pack(side="left", padx=5)

        # Scale
        ttk.Label(frame, text="Scale:").pack(side="left", padx=(15, 0))
        scale_names = [s.name.replace("_", " ").title() for s in Scale]
        self.scale_combo = ttk.Combobox(frame, values=scale_names, state="readonly", width=15)
        self.scale_combo.set("Major")
        self.scale_combo.pack(side="left", padx=5)

        # MIDI Port selector
        ttk.Label(frame, text="MIDI Out:").pack(side="left", padx=(15, 0))
        ports = list_midi_ports()
        port_values = ports if ports else ["(No ports found)"]
        self.midi_port_combo = ttk.Combobox(frame, values=port_values, state="readonly", width=25)
        if ports:
            self.midi_port_combo.set(ports[0])
        else:
            self.midi_port_combo.set("(No ports found)")
        self.midi_port_combo.pack(side="left", padx=5)

        ttk.Button(frame, text="Refresh", command=self._refresh_ports, width=8).pack(side="left", padx=2)

    def _init_progression_controls(self):
        """Chord progression configuration."""
        frame = ttk.LabelFrame(self.root, text="Chord Progression", padding=10)
        frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(frame, text="Progression (scale degrees, comma-separated):").pack(side="left")

        self.progression_var = tk.StringVar(value="1, 5, 6, 4")
        prog_entry = ttk.Entry(frame, textvariable=self.progression_var, width=30)
        prog_entry.pack(side="left", padx=5)

        # Preset progressions
        ttk.Label(frame, text="Presets:").pack(side="left", padx=(15, 0))

        presets = {
            "Pop (I-V-vi-IV)": "1, 5, 6, 4",
            "Jazz (ii-V-I)": "2, 5, 1",
            "Blues (I-IV-I-V)": "1, 4, 1, 5",
            "Canon": "1, 5, 6, 3, 4, 1, 4, 5",
            "Andalusian": "6, 5, 4, 3",
        }

        self.preset_combo = ttk.Combobox(frame, values=list(presets.keys()), state="readonly", width=18)
        self.preset_combo.set("Pop (I-V-vi-IV)")
        self.preset_combo.pack(side="left", padx=5)

        def apply_preset(*args):
            name = self.preset_combo.get()
            if name in presets:
                self.progression_var.set(presets[name])

        self.preset_combo.bind("<<ComboboxSelected>>", apply_preset)
        ttk.Button(frame, text="Apply", command=apply_preset, width=6).pack(side="left", padx=2)

    def _init_section_manager(self):
        """Middle area: List of song sections."""
        frame = ttk.LabelFrame(self.root, text="Song Structure", padding=10)
        frame.pack(fill="both", expand=True, padx=10, pady=5)

        # The Treeview (List)
        cols = ("Name", "Bars", "Motif", "Variation", "Drums", "Bass", "Arp", "Dyn")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings", height=10)

        col_widths = {"Name": 120, "Bars": 50, "Motif": 60, "Variation": 80,
                      "Drums": 80, "Bass": 80, "Arp": 50, "Dyn": 50}
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=col_widths.get(col, 80), anchor="center")

        self.tree.pack(side="left", fill="both", expand=True)

        # Scrollbar
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # Buttons Frame
        btn_frame = ttk.Frame(self.root, padding=10)
        btn_frame.pack(fill="x")

        ttk.Label(btn_frame, text="Add Section:").pack(side="left")

        # Quick Presets
        section_presets = [
            ("+ Intro", "Intro"),
            ("+ Verse", "Verse"),
            ("+ Chorus", "Chorus"),
            ("+ Bridge", "Bridge"),
            ("+ Outro", "Outro"),
            ("+ Drop", "Drop"),
        ]

        for text, preset in section_presets:
            ttk.Button(btn_frame, text=text, command=lambda p=preset: self.add_preset(p)).pack(side="left", padx=2)

        # Right-side controls
        ttk.Button(btn_frame, text="Remove Selected", command=self.remove_selected).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Clear All", command=self.clear_sections).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Move Down", command=lambda: self.move_section(1)).pack(side="right", padx=2)
        ttk.Button(btn_frame, text="Move Up", command=lambda: self.move_section(-1)).pack(side="right", padx=2)

    def _init_transport_controls(self):
        """Bottom bar: Play and Export."""
        frame = ttk.Frame(self.root, padding=15)
        frame.pack(fill="x", side="bottom")

        # Status bar
        self.status_var = tk.StringVar(value="Ready - Add sections to build your song")
        status_label = ttk.Label(frame, textvariable=self.status_var, relief="sunken", padding=5)
        status_label.pack(side="left", fill="x", expand=True, padx=(0, 10))

        # Transport buttons
        self.stop_btn = ttk.Button(frame, text="Stop", command=self.stop_playback, state="disabled")
        self.stop_btn.pack(side="right", padx=5)

        self.play_btn = ttk.Button(frame, text="Generate & Play", command=self.start_playback)
        self.play_btn.pack(side="right", padx=5)

        ttk.Button(frame, text="Export MIDI", command=self.export_midi).pack(side="right", padx=5)

        # New seed button
        ttk.Button(frame, text="New Seed", command=self._regenerate_motifs).pack(side="right", padx=5)

    # --- HELPER METHODS ---

    def _refresh_ports(self):
        """Refresh MIDI port list."""
        ports = list_midi_ports()
        self.midi_port_combo['values'] = ports if ports else ["(No ports found)"]
        if ports:
            self.midi_port_combo.set(ports[0])
            self.status_var.set(f"Found {len(ports)} MIDI port(s)")
        else:
            self.midi_port_combo.set("(No ports found)")
            self.status_var.set("No MIDI ports found")

    def _regenerate_motifs(self):
        """Generate new random motifs."""
        seed = random.randint(0, 9999)
        timing = TimingConfig(bpm=self.bpm_var.get())
        self.motifs = {
            'A': create_motif(timing, seed=seed, density=0.5),
            'B': create_motif(timing, seed=seed + 1, density=0.75),
            'C': create_motif(timing, seed=seed + 2, density=0.3),
        }
        self.status_var.set(f"Generated new motifs (seed: {seed})")

    def _parse_progression(self) -> list:
        """Parse the progression string into scale degrees (0-indexed)."""
        try:
            text = self.progression_var.get()
            # Parse comma-separated numbers, convert 1-indexed to 0-indexed
            degrees = []
            for part in text.split(","):
                part = part.strip()
                if part:
                    deg = int(part) - 1  # Convert to 0-indexed
                    degrees.append(deg)
            return degrees if degrees else [0, 4, 5, 3]  # Default fallback
        except ValueError:
            return [0, 4, 5, 3]

    def _update_tree(self):
        """Refresh the treeview from sections_list."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        for section in self.sections_list:
            arp = "Yes" if section.include_arpeggio else "No"
            self.tree.insert("", "end", values=(
                section.name,
                section.bars,
                section.motif_key,
                section.variation,
                section.drum_style,
                section.bass_style,
                arp,
                f"{section.dynamics:.0%}"
            ))

    # --- SECTION MANAGEMENT ---

    def add_preset(self, preset_type: str):
        """Adds a pre-configured SongSection based on type."""
        count = sum(1 for s in self.sections_list if preset_type in s.name) + 1

        presets = {
            "Intro": SongSection(
                f"Intro {count}", 4, 'A', 'original', 'halftime', 'simple',
                include_chords=True, include_arpeggio=False, dynamics=0.7
            ),
            "Verse": SongSection(
                f"Verse {count}", 8, 'A', 'original', 'rock', 'root_fifth',
                include_chords=True, include_arpeggio=False, dynamics=0.85
            ),
            "Chorus": SongSection(
                f"Chorus {count}", 8, 'B', 'augment', 'pop', 'driving',
                include_chords=True, include_arpeggio=True, dynamics=1.0
            ),
            "Bridge": SongSection(
                f"Bridge {count}", 4, 'C', 'invert', 'jazz', 'walking',
                include_chords=True, include_arpeggio=False, dynamics=0.8
            ),
            "Outro": SongSection(
                f"Outro {count}", 4, 'C', 'diminish', 'halftime', 'simple',
                include_chords=True, include_arpeggio=False, dynamics=0.6
            ),
            "Drop": SongSection(
                f"Drop {count}", 8, 'B', 'octave_up', 'electronic', 'driving',
                include_chords=True, include_arpeggio=True, dynamics=1.0
            ),
        }

        section = presets.get(preset_type, presets["Verse"])
        self.sections_list.append(section)
        self._update_tree()
        self.status_var.set(f"Added {section.name}")

    def remove_selected(self):
        """Remove the selected section."""
        selected = self.tree.selection()
        if not selected:
            return

        idx = self.tree.index(selected[0])
        if 0 <= idx < len(self.sections_list):
            removed = self.sections_list.pop(idx)
            self._update_tree()
            self.status_var.set(f"Removed {removed.name}")

    def clear_sections(self):
        """Clear all sections."""
        self.sections_list = []
        self._update_tree()
        self.status_var.set("Cleared all sections")

    def move_section(self, direction: int):
        """Move selected section up (-1) or down (+1)."""
        selected = self.tree.selection()
        if not selected:
            return

        idx = self.tree.index(selected[0])
        new_idx = idx + direction

        if 0 <= new_idx < len(self.sections_list):
            self.sections_list[idx], self.sections_list[new_idx] = \
                self.sections_list[new_idx], self.sections_list[idx]
            self._update_tree()
            # Re-select the moved item
            children = self.tree.get_children()
            if children:
                self.tree.selection_set(children[new_idx])

    # --- GENERATION & PLAYBACK ---

    def _generate_events(self):
        """Compiles the song based on GUI settings."""
        # Config
        bpm = self.bpm_var.get()
        timing = TimingConfig(bpm=bpm)

        # Convert key name to MIDI note
        notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        root_str = self.root_note_combo.get()
        root_val = 60 + notes.index(root_str)

        # Get scale
        scale_name = self.scale_combo.get().upper().replace(" ", "_")
        try:
            scale_enum = Scale[scale_name]
        except KeyError:
            scale_enum = Scale.MAJOR

        music = MusicConfig(root_note=root_val, scale=scale_enum)

        # Ensure motifs exist
        if not self.motifs:
            self._regenerate_motifs()

        # Parse progression
        progression = self._parse_progression()

        # Build song
        events = build_song(
            progression=progression,
            sections=self.sections_list,
            motifs=self.motifs,
            timing=timing,
            music=music
        )

        # Apply dynamics
        total_bars = sum(s.bars for s in self.sections_list)
        events = apply_song_dynamics(events, total_bars, timing, 'verse_chorus')

        return events, timing

    def start_playback(self):
        """Start generating and playing the song."""
        if not self.sections_list:
            messagebox.showwarning("Empty Song", "Add some sections first!")
            return

        self.play_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.is_playing = True
        self.root.update()

        threading.Thread(target=self._playback_thread, daemon=True).start()

    def _playback_thread(self):
        """Background thread for generation and playback."""
        try:
            self.status_var.set("Generating song...")
            events, timing = self._generate_events()
            self.last_events = events
            self.last_timing = timing

            self.status_var.set(f"Playing {len(events)} events at {timing.bpm} BPM...")

            # Get selected port
            port_name = self.midi_port_combo.get()
            if port_name == "(No ports found)":
                port_name = None

            success = play_events_realtime(events, timing, port_name=port_name)

            if not success:
                self.status_var.set("Playback stopped or no MIDI output available")
            else:
                self.status_var.set("Playback finished")

        except Exception as e:
            self.status_var.set(f"Error: {str(e)}")
            print(f"Playback error: {e}")

        finally:
            self.is_playing = False
            self.root.after(0, self._reset_transport)

    def _reset_transport(self):
        """Reset transport buttons (called from main thread)."""
        self.play_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

    def stop_playback(self):
        """Stop current playback."""
        stop_playback()
        self.is_playing = False
        self.status_var.set("Stopped")
        self._reset_transport()

    def export_midi(self):
        """Export the current song to a MIDI file."""
        if not self.sections_list:
            messagebox.showwarning("Empty Song", "Add some sections first!")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".mid",
            filetypes=[("MIDI files", "*.mid"), ("All files", "*.*")],
            title="Export MIDI File"
        )

        if filename:
            self.status_var.set("Generating...")
            events, timing = self._generate_events()
            write_midi_file(events, filename, timing)
            self.status_var.set(f"Exported to {filename}")


def main():
    root = tk.Tk()

    # Style configuration
    style = ttk.Style()
    try:
        style.theme_use('clam')  # Clean cross-platform look
    except tk.TclError:
        pass  # Use default if clam not available

    # Configure some styles
    style.configure('TButton', padding=5)
    style.configure('TLabel', padding=2)

    app = AlgorythmApp(root)

    # Handle window close
    def on_close():
        if app.is_playing:
            stop_playback()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
