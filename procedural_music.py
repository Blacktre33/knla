"""
Procedural MIDI Music Generator

A comprehensive tool for generating procedural music with:
- Motif-based melody composition with variations
- Drum patterns with fills
- Chord pads and arpeggios
- Multiple scale support
- Humanization and dynamics
"""

import mido
import random
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from copy import deepcopy


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class TimingConfig:
    """Timing and tempo configuration."""
    ppq: int = 480                    # Pulses per quarter note
    bpm: int = 110                    # Beats per minute
    beats_per_bar: int = 4            # Time signature numerator
    steps_per_beat: int = 4           # Subdivision (16th notes)

    @property
    def ticks_per_step(self) -> int:
        return self.ppq // self.steps_per_beat

    @property
    def ticks_per_beat(self) -> int:
        return self.ppq

    @property
    def ticks_per_bar(self) -> int:
        return self.beats_per_bar * self.ppq

    @property
    def steps_per_bar(self) -> int:
        return self.beats_per_bar * self.steps_per_beat


# =============================================================================
# SCALES AND MUSIC THEORY
# =============================================================================

class Scale(Enum):
    """Available scales with their interval patterns."""
    MAJOR = [0, 2, 4, 5, 7, 9, 11]
    NATURAL_MINOR = [0, 2, 3, 5, 7, 8, 10]
    HARMONIC_MINOR = [0, 2, 3, 5, 7, 8, 11]
    DORIAN = [0, 2, 3, 5, 7, 9, 10]
    MIXOLYDIAN = [0, 2, 4, 5, 7, 9, 10]
    PENTATONIC_MAJOR = [0, 2, 4, 7, 9]
    PENTATONIC_MINOR = [0, 3, 5, 7, 10]
    BLUES = [0, 3, 5, 6, 7, 10]


@dataclass
class MusicConfig:
    """Musical configuration."""
    root_note: int = 60               # C4
    scale: Scale = Scale.MAJOR

    def get_scale_note(self, degree_index: int) -> int:
        """Convert a scale degree to MIDI pitch."""
        intervals = self.scale.value
        scale_len = len(intervals)
        octave = degree_index // scale_len
        note_in_scale = degree_index % scale_len
        return self.root_note + (octave * 12) + intervals[note_in_scale]

    def get_chord_tones(self, root_degree: int, extensions: int = 3) -> List[int]:
        """Get chord tones (root, 3rd, 5th, optionally 7th)."""
        tones = []
        for i in range(extensions):
            tones.append(root_degree + (i * 2))
        return tones


# =============================================================================
# DRUM DEFINITIONS (General MIDI)
# =============================================================================

class DrumSound(Enum):
    """General MIDI drum map."""
    KICK = 36
    SNARE = 38
    RIMSHOT = 37
    CLAP = 39
    CLOSED_HAT = 42
    OPEN_HAT = 46
    PEDAL_HAT = 44
    LOW_TOM = 45
    MID_TOM = 47
    HIGH_TOM = 50
    CRASH = 49
    RIDE = 51
    RIDE_BELL = 53


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class NoteEvent:
    """A concrete MIDI note event."""
    start_tick: int
    duration_ticks: int
    pitch: int
    velocity: int
    channel: int = 0


@dataclass
class MotifEvent:
    """Abstract instruction for a note inside a motif."""
    step_in_bar: int
    duration_steps: int
    chord_degree_offset: int  # 0=Root, 2=3rd, 4=5th, etc.
    velocity_accent: float = 1.0  # Velocity multiplier


@dataclass
class DrumHit:
    """A single drum hit in a pattern."""
    step: int
    sound: DrumSound
    velocity: int = 100


@dataclass
class DrumPattern:
    """A drum pattern for one bar."""
    hits: List[DrumHit] = field(default_factory=list)


# =============================================================================
# CHANNEL ASSIGNMENTS
# =============================================================================

class Channel:
    """MIDI channel assignments."""
    MELODY = 0
    BASS = 1
    CHORDS = 2
    ARPEGGIO = 3
    DRUMS = 9  # GM drums


# =============================================================================
# MOTIF GENERATOR
# =============================================================================

def create_motif(
    timing: TimingConfig,
    density: float = 0.6,
    seed: Optional[int] = None
) -> List[MotifEvent]:
    """
    Generates a 1-bar pattern of RELATIVE pitch instructions.

    Args:
        timing: Timing configuration
        density: Probability of notes on strong beats (0.0-1.0)
        seed: Random seed for reproducibility (None for random)
    """
    if seed is not None:  # Fixed: seed=0 now works correctly
        random.seed(seed)

    motif = []
    current_offset = 0

    for i in range(timing.steps_per_bar):
        # Rhythm Logic - strong beats get higher probability
        beat_position = i % timing.steps_per_beat
        is_downbeat = (i == 0)
        is_strong = (beat_position == 0)
        is_offbeat = (beat_position == 2)

        if is_downbeat:
            chance = density * 1.2
        elif is_strong:
            chance = density
        elif is_offbeat:
            chance = density * 0.5
        else:
            chance = density * 0.15

        if random.random() > chance:
            continue

        # Pitch Logic: Walk relative to the Chord Root
        move = random.choice([-1, 0, 1, 2, -2])
        current_offset += move
        current_offset = max(-4, min(7, current_offset))

        # Duration varies by position
        if is_downbeat:
            duration = random.choice([4, 6, 8])  # Quarter to half note
        elif is_strong:
            duration = random.choice([2, 4])
        else:
            duration = random.choice([1, 2])

        # Velocity accent
        accent = 1.2 if is_downbeat else (1.0 if is_strong else 0.85)

        motif.append(MotifEvent(i, duration, current_offset, accent))

    return motif


# =============================================================================
# MOTIF VARIATIONS
# =============================================================================

def invert_motif(motif: List[MotifEvent], pivot: int = 0) -> List[MotifEvent]:
    """Invert a motif around a pivot point (mirror pitch movement)."""
    inverted = []
    for event in motif:
        new_offset = pivot - (event.chord_degree_offset - pivot)
        inverted.append(MotifEvent(
            event.step_in_bar,
            event.duration_steps,
            new_offset,
            event.velocity_accent
        ))
    return inverted


def retrograde_motif(motif: List[MotifEvent], steps_per_bar: int) -> List[MotifEvent]:
    """Reverse a motif in time (play backwards)."""
    if not motif:
        return []

    retro = []
    for event in reversed(motif):
        # Mirror the step position
        new_step = steps_per_bar - 1 - event.step_in_bar
        retro.append(MotifEvent(
            max(0, new_step),
            event.duration_steps,
            event.chord_degree_offset,
            event.velocity_accent
        ))
    return sorted(retro, key=lambda e: e.step_in_bar)


def augment_motif(motif: List[MotifEvent], factor: float = 1.5) -> List[MotifEvent]:
    """Stretch note durations by a factor."""
    return [
        MotifEvent(
            event.step_in_bar,
            int(event.duration_steps * factor),
            event.chord_degree_offset,
            event.velocity_accent
        )
        for event in motif
    ]


def diminish_motif(motif: List[MotifEvent], factor: float = 0.5) -> List[MotifEvent]:
    """Shorten note durations by a factor."""
    return [
        MotifEvent(
            event.step_in_bar,
            max(1, int(event.duration_steps * factor)),
            event.chord_degree_offset,
            event.velocity_accent
        )
        for event in motif
    ]


def transpose_motif(motif: List[MotifEvent], semitones: int) -> List[MotifEvent]:
    """Transpose a motif by scale degrees."""
    return [
        MotifEvent(
            event.step_in_bar,
            event.duration_steps,
            event.chord_degree_offset + semitones,
            event.velocity_accent
        )
        for event in motif
    ]


def apply_variation(
    motif: List[MotifEvent],
    variation_type: str,
    timing: TimingConfig
) -> List[MotifEvent]:
    """Apply a named variation to a motif."""
    variations = {
        'original': lambda m: deepcopy(m),
        'invert': lambda m: invert_motif(m),
        'retrograde': lambda m: retrograde_motif(m, timing.steps_per_bar),
        'augment': lambda m: augment_motif(m),
        'diminish': lambda m: diminish_motif(m),
        'octave_up': lambda m: transpose_motif(m, 7),
        'octave_down': lambda m: transpose_motif(m, -7),
    }
    return variations.get(variation_type, variations['original'])(motif)


# =============================================================================
# MOTIF APPLIER
# =============================================================================

def apply_motif(
    motif: List[MotifEvent],
    bar_start_tick: int,
    chord_root_degree: int,
    music: MusicConfig,
    timing: TimingConfig,
    base_velocity: int = 90,
    octave_offset: int = 0,
    channel: int = Channel.MELODY
) -> List[NoteEvent]:
    """
    Takes an abstract motif and stamps it onto a specific Bar and Chord.
    """
    events = []
    for m in motif:
        abs_start = bar_start_tick + (m.step_in_bar * timing.ticks_per_step)
        abs_dur = m.duration_steps * timing.ticks_per_step

        final_degree = chord_root_degree + m.chord_degree_offset + (octave_offset * 7)
        midi_pitch = music.get_scale_note(final_degree)

        # Velocity with accent and humanization
        vel = int(base_velocity * m.velocity_accent)
        vel = max(1, min(127, vel + random.randint(-8, 8)))

        events.append(NoteEvent(abs_start, abs_dur, midi_pitch, vel, channel))

    return events


# =============================================================================
# DRUM PATTERN GENERATOR
# =============================================================================

def create_basic_drum_pattern(style: str = 'rock') -> DrumPattern:
    """Create a basic drum pattern for one bar."""
    patterns = {
        'rock': DrumPattern(hits=[
            # Kick on 1 and 3
            DrumHit(0, DrumSound.KICK, 110),
            DrumHit(8, DrumSound.KICK, 100),
            # Snare on 2 and 4
            DrumHit(4, DrumSound.SNARE, 105),
            DrumHit(12, DrumSound.SNARE, 105),
            # Hi-hats on every 8th
            *[DrumHit(i * 2, DrumSound.CLOSED_HAT, 70 if i % 2 == 0 else 55)
              for i in range(8)],
        ]),
        'pop': DrumPattern(hits=[
            DrumHit(0, DrumSound.KICK, 110),
            DrumHit(6, DrumSound.KICK, 90),
            DrumHit(10, DrumSound.KICK, 85),
            DrumHit(4, DrumSound.SNARE, 100),
            DrumHit(12, DrumSound.SNARE, 100),
            *[DrumHit(i * 2, DrumSound.CLOSED_HAT, 65) for i in range(8)],
        ]),
        'electronic': DrumPattern(hits=[
            DrumHit(0, DrumSound.KICK, 120),
            DrumHit(4, DrumSound.KICK, 110),
            DrumHit(8, DrumSound.KICK, 110),
            DrumHit(12, DrumSound.KICK, 110),
            DrumHit(4, DrumSound.CLAP, 100),
            DrumHit(12, DrumSound.CLAP, 100),
            *[DrumHit(i, DrumSound.CLOSED_HAT, 50 + (i % 2) * 20) for i in range(16)],
        ]),
        'jazz': DrumPattern(hits=[
            DrumHit(0, DrumSound.KICK, 75),
            DrumHit(10, DrumSound.KICK, 65),
            DrumHit(4, DrumSound.SNARE, 50),  # Ghost note
            DrumHit(7, DrumSound.SNARE, 85),
            DrumHit(14, DrumSound.SNARE, 50),
            *[DrumHit(i * 2, DrumSound.RIDE, 70 if i % 2 == 0 else 55) for i in range(8)],
            DrumHit(3, DrumSound.RIDE, 60),
            DrumHit(9, DrumSound.RIDE, 60),
        ]),
        'halftime': DrumPattern(hits=[
            DrumHit(0, DrumSound.KICK, 110),
            DrumHit(8, DrumSound.SNARE, 105),
            *[DrumHit(i * 2, DrumSound.CLOSED_HAT, 60) for i in range(8)],
            DrumHit(6, DrumSound.OPEN_HAT, 75),
            DrumHit(14, DrumSound.OPEN_HAT, 75),
        ]),
    }
    return deepcopy(patterns.get(style, patterns['rock']))


def create_drum_fill(intensity: str = 'medium') -> DrumPattern:
    """Create a drum fill pattern for transitions."""
    fills = {
        'light': DrumPattern(hits=[
            DrumHit(12, DrumSound.SNARE, 90),
            DrumHit(13, DrumSound.SNARE, 85),
            DrumHit(14, DrumSound.SNARE, 95),
            DrumHit(15, DrumSound.SNARE, 100),
        ]),
        'medium': DrumPattern(hits=[
            DrumHit(8, DrumSound.SNARE, 85),
            DrumHit(10, DrumSound.HIGH_TOM, 90),
            DrumHit(11, DrumSound.HIGH_TOM, 85),
            DrumHit(12, DrumSound.MID_TOM, 95),
            DrumHit(13, DrumSound.MID_TOM, 90),
            DrumHit(14, DrumSound.LOW_TOM, 100),
            DrumHit(15, DrumSound.KICK, 110),
        ]),
        'heavy': DrumPattern(hits=[
            *[DrumHit(i, DrumSound.SNARE, 80 + i * 3) for i in range(4, 16)],
            DrumHit(15, DrumSound.CRASH, 110),
        ]),
        'crash': DrumPattern(hits=[
            DrumHit(0, DrumSound.CRASH, 110),
            DrumHit(0, DrumSound.KICK, 110),
        ]),
    }
    return deepcopy(fills.get(intensity, fills['medium']))


def generate_drums(
    num_bars: int,
    timing: TimingConfig,
    style: str = 'rock',
    fill_every: int = 4,
    humanize: bool = True
) -> List[NoteEvent]:
    """Generate a complete drum track."""
    events = []
    base_pattern = create_basic_drum_pattern(style)

    for bar in range(num_bars):
        bar_start = bar * timing.ticks_per_bar

        # Determine if this is a fill bar
        is_fill_bar = (bar + 1) % fill_every == 0 and bar < num_bars - 1
        is_first_of_section = bar % fill_every == 0

        if is_fill_bar:
            # Use fill for last part of bar
            pattern = create_basic_drum_pattern(style)
            fill = create_drum_fill('medium')
            # Remove hits from step 8 onwards in base pattern
            pattern.hits = [h for h in pattern.hits if h.step < 8]
            pattern.hits.extend(fill.hits)
        else:
            pattern = deepcopy(base_pattern)

        # Add crash on first beat of sections
        if is_first_of_section and bar > 0:
            pattern.hits.append(DrumHit(0, DrumSound.CRASH, 100))

        for hit in pattern.hits:
            tick = bar_start + (hit.step * timing.ticks_per_step)
            vel = hit.velocity

            if humanize:
                vel = max(1, min(127, vel + random.randint(-5, 5)))
                # Slight timing humanization (kept subtle)
                tick += random.randint(-5, 5)

            events.append(NoteEvent(
                max(0, tick),
                timing.ticks_per_step // 2,  # Short drum hits
                hit.sound.value,
                vel,
                Channel.DRUMS
            ))

    return events


# =============================================================================
# BASS GENERATOR
# =============================================================================

def generate_bass(
    progression: List[int],
    timing: TimingConfig,
    music: MusicConfig,
    style: str = 'simple',
    octave_offset: int = -2
) -> List[NoteEvent]:
    """Generate bass line following the chord progression."""
    events = []

    for bar_idx, chord_root in enumerate(progression):
        bar_start = bar_idx * timing.ticks_per_bar
        root_pitch = music.get_scale_note(chord_root + (octave_offset * 7))
        fifth_pitch = music.get_scale_note(chord_root + 4 + (octave_offset * 7))

        if style == 'simple':
            # Whole note on root
            events.append(NoteEvent(
                bar_start,
                timing.ticks_per_bar - timing.ticks_per_step,
                root_pitch,
                85,
                Channel.BASS
            ))

        elif style == 'root_fifth':
            # Root on 1, fifth on 3
            events.append(NoteEvent(
                bar_start,
                timing.ticks_per_bar // 2 - timing.ticks_per_step,
                root_pitch,
                90,
                Channel.BASS
            ))
            events.append(NoteEvent(
                bar_start + timing.ticks_per_bar // 2,
                timing.ticks_per_bar // 2 - timing.ticks_per_step,
                fifth_pitch,
                80,
                Channel.BASS
            ))

        elif style == 'driving':
            # Eighth notes alternating root and octave
            for i in range(8):
                step_start = bar_start + (i * timing.ticks_per_beat // 2)
                pitch = root_pitch if i % 2 == 0 else root_pitch + 12
                vel = 90 if i % 2 == 0 else 75
                events.append(NoteEvent(
                    step_start,
                    timing.ticks_per_beat // 2 - 20,
                    pitch,
                    vel + random.randint(-5, 5),
                    Channel.BASS
                ))

        elif style == 'walking':
            # Walking bass - chromatic approaches
            notes_per_bar = 4
            for i in range(notes_per_bar):
                step_start = bar_start + (i * timing.ticks_per_beat)
                if i == 0:
                    pitch = root_pitch
                elif i == 3:
                    # Approach next chord
                    next_chord = progression[(bar_idx + 1) % len(progression)]
                    next_root = music.get_scale_note(next_chord + (octave_offset * 7))
                    # Chromatic approach from above or below
                    pitch = next_root + random.choice([-1, 1])
                else:
                    # Chord tones or passing tones
                    pitch = music.get_scale_note(
                        chord_root + random.choice([0, 2, 4]) + (octave_offset * 7)
                    )

                events.append(NoteEvent(
                    step_start,
                    timing.ticks_per_beat - 20,
                    pitch,
                    85 + random.randint(-8, 8),
                    Channel.BASS
                ))

    return events


# =============================================================================
# CHORD PAD GENERATOR
# =============================================================================

def generate_chord_pads(
    progression: List[int],
    timing: TimingConfig,
    music: MusicConfig,
    voicing: str = 'triad',
    octave_offset: int = 0
) -> List[NoteEvent]:
    """Generate sustained chord pads."""
    events = []

    for bar_idx, chord_root in enumerate(progression):
        bar_start = bar_idx * timing.ticks_per_bar

        # Get chord tones
        if voicing == 'triad':
            degrees = [0, 2, 4]  # Root, 3rd, 5th
        elif voicing == 'seventh':
            degrees = [0, 2, 4, 6]  # Root, 3rd, 5th, 7th
        elif voicing == 'add9':
            degrees = [0, 2, 4, 8]  # Root, 3rd, 5th, 9th
        elif voicing == 'sus4':
            degrees = [0, 3, 4]  # Root, 4th, 5th
        else:
            degrees = [0, 2, 4]

        for degree_offset in degrees:
            final_degree = chord_root + degree_offset + (octave_offset * 7)
            pitch = music.get_scale_note(final_degree)

            # Slight velocity variation per note
            vel = 60 + random.randint(-5, 10)

            # Slight strum effect - offset start times
            strum_offset = degrees.index(degree_offset) * 10

            events.append(NoteEvent(
                bar_start + strum_offset,
                timing.ticks_per_bar - timing.ticks_per_step - strum_offset,
                pitch,
                vel,
                Channel.CHORDS
            ))

    return events


# =============================================================================
# ARPEGGIATOR
# =============================================================================

def generate_arpeggio(
    progression: List[int],
    timing: TimingConfig,
    music: MusicConfig,
    pattern: str = 'up',
    rate: int = 4,  # Notes per beat
    octave_offset: int = 1
) -> List[NoteEvent]:
    """Generate arpeggiated patterns over the chord progression."""
    events = []

    # Define arpeggio patterns (indices into chord tones)
    patterns = {
        'up': [0, 1, 2, 3],
        'down': [3, 2, 1, 0],
        'updown': [0, 1, 2, 3, 2, 1],
        'random': None,  # Handled specially
        'alberti': [0, 2, 1, 2],  # Classical pattern
    }

    ticks_per_note = timing.ticks_per_beat // rate
    notes_per_bar = timing.beats_per_bar * rate

    for bar_idx, chord_root in enumerate(progression):
        bar_start = bar_idx * timing.ticks_per_bar

        # Get extended chord tones for arpeggio
        chord_tones = [
            music.get_scale_note(chord_root + d + (octave_offset * 7))
            for d in [0, 2, 4, 7]  # Root, 3rd, 5th, Octave
        ]

        arp_pattern = patterns.get(pattern, patterns['up'])

        for i in range(notes_per_bar):
            note_start = bar_start + (i * ticks_per_note)

            if pattern == 'random':
                idx = random.randint(0, len(chord_tones) - 1)
            else:
                idx = arp_pattern[i % len(arp_pattern)]

            pitch = chord_tones[idx % len(chord_tones)]

            # Accent pattern - emphasize downbeats
            vel = 80 if i % rate == 0 else 60
            vel += random.randint(-5, 5)

            events.append(NoteEvent(
                note_start,
                ticks_per_note - 10,
                pitch,
                vel,
                Channel.ARPEGGIO
            ))

    return events


# =============================================================================
# DYNAMICS ENGINE
# =============================================================================

def apply_song_dynamics(
    events: List[NoteEvent],
    num_bars: int,
    timing: TimingConfig,
    curve: str = 'verse_chorus'
) -> List[NoteEvent]:
    """Apply overall song dynamics (volume envelope over time)."""

    curves = {
        'flat': lambda pos: 1.0,
        'crescendo': lambda pos: 0.7 + (0.3 * pos),
        'decrescendo': lambda pos: 1.0 - (0.3 * pos),
        'verse_chorus': lambda pos: 0.85 if (int(pos * 8) % 8) < 4 else 1.0,
        'wave': lambda pos: 0.8 + 0.2 * abs((pos * 4) % 2 - 1),
    }

    curve_fn = curves.get(curve, curves['flat'])
    total_ticks = num_bars * timing.ticks_per_bar

    for event in events:
        if event.channel == Channel.DRUMS:
            continue  # Don't affect drums as much

        position = event.start_tick / total_ticks if total_ticks > 0 else 0
        multiplier = curve_fn(position)
        event.velocity = max(1, min(127, int(event.velocity * multiplier)))

    return events


# =============================================================================
# MIDI WRITER
# =============================================================================

def write_midi_file(
    events: List[NoteEvent],
    filename: str,
    timing: TimingConfig
) -> None:
    """Write note events to a MIDI file."""
    mid = mido.MidiFile(ticks_per_beat=timing.ppq)

    # Sort events into channels
    channels: Dict[int, List[NoteEvent]] = {}
    for e in events:
        channels.setdefault(e.channel, []).append(e)

    # Track names for each channel
    track_names = {
        Channel.MELODY: 'Melody',
        Channel.BASS: 'Bass',
        Channel.CHORDS: 'Chords',
        Channel.ARPEGGIO: 'Arpeggio',
        Channel.DRUMS: 'Drums',
    }

    # Program changes (GM instruments)
    programs = {
        Channel.MELODY: 80,   # Square Lead
        Channel.BASS: 33,     # Finger Bass
        Channel.CHORDS: 4,    # Electric Piano
        Channel.ARPEGGIO: 88, # Synth Lead
        # Drums don't need program change
    }

    for ch, evs in sorted(channels.items()):
        track = mido.MidiTrack()
        mid.tracks.append(track)

        # Track name
        track.append(mido.MetaMessage(
            'track_name',
            name=track_names.get(ch, f'Track {ch}')
        ))

        # Tempo on first track only
        if ch == min(channels.keys()):
            track.append(mido.MetaMessage(
                'set_tempo',
                tempo=mido.bpm2tempo(timing.bpm)
            ))

        # Program change (not for drums)
        if ch != Channel.DRUMS and ch in programs:
            track.append(mido.Message(
                'program_change',
                program=programs[ch],
                channel=ch,
                time=0
            ))

        # Build timeline
        timeline = []
        for e in evs:
            timeline.append({
                "time": e.start_tick,
                "type": "note_on",
                "note": e.pitch,
                "vel": e.velocity
            })
            timeline.append({
                "time": e.start_tick + e.duration_ticks,
                "type": "note_off",
                "note": e.pitch,
                "vel": 0
            })

        # Sort by time, then note_off before note_on at same time
        timeline.sort(key=lambda x: (x["time"], 0 if x["type"] == "note_off" else 1))

        # Convert to delta time
        last_time = 0
        for t in timeline:
            delta = t["time"] - last_time
            track.append(mido.Message(
                t["type"],
                note=t["note"],
                velocity=t["vel"],
                time=delta,
                channel=ch
            ))
            last_time = t["time"]

    mid.save(filename)
    print(f"Saved: {filename}")


# =============================================================================
# SONG BUILDER
# =============================================================================

@dataclass
class SongSection:
    """Defines a section of the song."""
    name: str
    bars: int
    motif_key: str
    variation: str = 'original'
    drum_style: str = 'rock'
    bass_style: str = 'root_fifth'
    include_arpeggio: bool = False
    include_chords: bool = True
    dynamics: float = 1.0


def build_song(
    progression: List[int],
    sections: List[SongSection],
    motifs: Dict[str, List[MotifEvent]],
    timing: TimingConfig,
    music: MusicConfig
) -> List[NoteEvent]:
    """Build a complete song from sections."""
    all_events = []
    current_bar = 0

    for section in sections:
        section_progression = []
        prog_idx = 0

        # Build progression for this section
        for _ in range(section.bars):
            section_progression.append(progression[prog_idx % len(progression)])
            prog_idx += 1

        section_start = current_bar * timing.ticks_per_bar

        # Get motif with variation
        base_motif = motifs.get(section.motif_key, motifs.get('A', []))
        motif = apply_variation(base_motif, section.variation, timing)

        # Generate melody
        for bar_idx, chord_root in enumerate(section_progression):
            bar_start = section_start + (bar_idx * timing.ticks_per_bar)
            melody_events = apply_motif(
                motif, bar_start, chord_root, music, timing,
                base_velocity=int(90 * section.dynamics)
            )
            all_events.extend(melody_events)

        # Generate accompaniment
        all_events.extend(generate_bass(
            section_progression, timing, music,
            style=section.bass_style
        ))

        if section.include_chords:
            all_events.extend(generate_chord_pads(
                section_progression, timing, music
            ))

        if section.include_arpeggio:
            all_events.extend(generate_arpeggio(
                section_progression, timing, music,
                pattern='updown'
            ))

        all_events.extend(generate_drums(
            section.bars, timing,
            style=section.drum_style,
            fill_every=4
        ))

        # Offset all events by current position
        for event in all_events:
            if event.start_tick < section_start:
                continue  # Already positioned

        current_bar += section.bars

    return all_events


# =============================================================================
# MAIN - DEMO
# =============================================================================

if __name__ == "__main__":
    # Configuration
    timing = TimingConfig(bpm=120)
    music = MusicConfig(root_note=60, scale=Scale.MAJOR)  # C Major

    # Chord Progression (I - V - vi - IV in C Major)
    progression = [0, 4, 5, 3]

    # Create Motifs
    motifs = {
        'A': create_motif(timing, seed=42, density=0.5),   # Main theme
        'B': create_motif(timing, seed=99, density=0.7),   # Bridge (busier)
        'C': create_motif(timing, seed=10, density=0.3),   # Outro (sparse)
    }

    # Define Song Structure
    sections = [
        SongSection('Intro', 4, 'A', 'original', 'halftime', 'simple',
                    include_chords=True, include_arpeggio=False, dynamics=0.8),
        SongSection('Verse 1', 4, 'A', 'original', 'rock', 'root_fifth',
                    include_chords=True, include_arpeggio=False, dynamics=0.9),
        SongSection('Chorus', 4, 'B', 'original', 'rock', 'driving',
                    include_chords=True, include_arpeggio=True, dynamics=1.0),
        SongSection('Verse 2', 4, 'A', 'invert', 'rock', 'root_fifth',
                    include_chords=True, include_arpeggio=False, dynamics=0.9),
        SongSection('Chorus 2', 4, 'B', 'augment', 'rock', 'driving',
                    include_chords=True, include_arpeggio=True, dynamics=1.0),
        SongSection('Bridge', 4, 'C', 'retrograde', 'jazz', 'walking',
                    include_chords=True, include_arpeggio=False, dynamics=0.85),
        SongSection('Final Chorus', 4, 'B', 'octave_up', 'rock', 'driving',
                    include_chords=True, include_arpeggio=True, dynamics=1.0),
        SongSection('Outro', 4, 'C', 'diminish', 'halftime', 'simple',
                    include_chords=True, include_arpeggio=False, dynamics=0.7),
    ]

    # Build the song
    print("Generating song...")
    all_events = build_song(progression, sections, motifs, timing, music)

    # Apply overall dynamics
    total_bars = sum(s.bars for s in sections)
    all_events = apply_song_dynamics(all_events, total_bars, timing, 'verse_chorus')

    # Write output
    write_midi_file(all_events, "procedural_song.mid", timing)

    print(f"\nGenerated {len(all_events)} note events across {total_bars} bars")
    print("Sections:", [s.name for s in sections])

    # Also generate a simpler version for quick testing
    print("\nGenerating simple demo...")
    simple_events = []

    for bar_idx, chord_root in enumerate(progression * 2):  # 8 bars
        bar_start = bar_idx * timing.ticks_per_bar
        simple_events.extend(apply_motif(
            motifs['A'], bar_start, chord_root, music, timing
        ))

    simple_events.extend(generate_bass(progression * 2, timing, music, 'root_fifth'))
    simple_events.extend(generate_chord_pads(progression * 2, timing, music))
    simple_events.extend(generate_drums(8, timing, 'pop'))

    write_midi_file(simple_events, "procedural_simple.mid", timing)
