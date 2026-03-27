import * as Tone from 'tone';

let polySynth = null;

function getSynth() {
  if (!polySynth) {
    polySynth = new Tone.PolySynth(Tone.Synth, {
      oscillator: { type: 'triangle' },
      envelope: { attack: 0.02, decay: 0.1, sustain: 0.35, release: 0.4 },
    }).toDestination();
    polySynth.volume.value = -8;
  }
  return polySynth;
}

export async function ensureAudioContext() {
  if (Tone.context.state !== 'running') {
    await Tone.start();
  }
}

/**
 * @param {number} bpm
 * @param {Array<{ notes?: string[], note_names?: string[] }>} chords
 * @param {(index: number) => void} [onProgress]
 * @returns {Promise<number>} total duration in seconds
 */
export async function playProgression(bpm, chords, onProgress) {
  await ensureAudioContext();
  const synth = getSynth();

  const list = (chords || []).map((c) => {
    const raw = c.notes || c.note_names || [];
    return raw.map((n) => String(n).trim()).filter(Boolean);
  });

  const barSec = (60 / bpm) * 4;
  const now = Tone.now();

  list.forEach((noteNames, i) => {
    const start = now + i * barSec;
    Tone.Draw.schedule(() => {
      if (onProgress) onProgress(i);
    }, start);
    const freq = noteNames.map((n) => Tone.Frequency(n).toFrequency());
    synth.triggerAttackRelease(freq, barSec * 0.95, start);
  });

  return list.length * barSec;
}

export function stopTransport() {
  Tone.Transport.cancel();
}

export function stopPlayback() {
  if (polySynth) {
    polySynth.releaseAll();
  }
}
