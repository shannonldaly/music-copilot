/**
 * Parse "A3", "Bb4" style strings to MIDI note numbers (C4 = 60).
 */
const NOTE_TO_SEMITONE = {
  C: 0,
  'C#': 1,
  Db: 1,
  D: 2,
  'D#': 3,
  Eb: 3,
  E: 4,
  F: 5,
  'F#': 6,
  Gb: 6,
  G: 7,
  'G#': 8,
  Ab: 8,
  A: 9,
  'A#': 10,
  Bb: 10,
  B: 11,
};

export function parseNoteToMidi(noteStr) {
  if (!noteStr || typeof noteStr !== 'string') return null;
  const s = noteStr.trim();
  const match = s.match(/^([A-Ga-g])([#b]?)(\d+)$/);
  if (!match) return null;
  const letter = match[1].toUpperCase() + (match[2] || '');
  const octave = parseInt(match[3], 10);
  const base = NOTE_TO_SEMITONE[letter];
  if (base === undefined) return null;
  return (octave + 1) * 12 + base;
}

export function midiToRollRow(midi, minMidi, maxMidi) {
  if (maxMidi <= minMidi) return 0.5;
  return (midi - minMidi) / (maxMidi - minMidi);
}
