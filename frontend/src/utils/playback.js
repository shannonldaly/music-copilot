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

let drumMasterGain = null;
let kickSynth = null;
let snareSynth = null;
let hatSynth = null;

function getDrumMasterGain() {
  if (!drumMasterGain) {
    drumMasterGain = new Tone.Gain(1).toDestination();
  }
  return drumMasterGain;
}

function getKick() {
  if (!kickSynth) {
    kickSynth = new Tone.MembraneSynth({
      pitchDecay: 0.02,
      octaves: 6,
      oscillator: { type: 'sine' },
      envelope: { attack: 0.001, decay: 0.25, sustain: 0.01, release: 0.2 },
    }).connect(getDrumMasterGain());
    kickSynth.volume.value = -2;
  }
  return kickSynth;
}

function getSnare() {
  if (!snareSynth) {
    snareSynth = new Tone.NoiseSynth({
      noise: { type: 'white' },
      envelope: { attack: 0.001, decay: 0.15, sustain: 0, release: 0.08 },
    }).connect(getDrumMasterGain());
    snareSynth.volume.value = -6;
  }
  return snareSynth;
}

function getHat() {
  if (!hatSynth) {
    hatSynth = new Tone.MetalSynth({
      envelope: { attack: 0.001, decay: 0.05, release: 0.01 },
      harmonicity: 5.1,
      modulationIndex: 32,
      resonance: 4000,
      octaves: 1.5,
    }).connect(getDrumMasterGain());
    hatSynth.volume.value = -14;
  }
  return hatSynth;
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
  getDrumMasterGain().gain.value = 0;
  const synth = getSynth();
  synth.releaseAll();

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
    if (!noteNames.length) return;
    const freq = noteNames.map((n) => Tone.Frequency(n).toFrequency());
    synth.triggerAttackRelease(freq, barSec * 0.95, start);
  });

  return list.length * barSec;
}

/**
 * @param {number} bpm
 * @param {Record<string, number[]>} grid - kick, snare, closed_hat, open_hat, …
 * @returns {Promise<number>} duration in seconds (one bar)
 */
export async function playDrumPattern(bpm, grid) {
  await ensureAudioContext();
  if (polySynth) {
    polySynth.releaseAll();
  }
  getDrumMasterGain().gain.value = 1;

  const kick = getKick();
  const snare = getSnare();
  const hat = getHat();

  const sixteenthSec = (60 / bpm) / 4;
  const now = Tone.now();
  const g = grid || {};

  const kicks = new Set((g.kick || []).map(Number));
  const snares = new Set((g.snare || []).map(Number));
  const hats = new Set([...(g.closed_hat || []), ...(g.open_hat || [])].map(Number));

  for (let step = 0; step < 16; step += 1) {
    const t = now + step * sixteenthSec;
    if (kicks.has(step)) {
      kick.triggerAttackRelease('C1', 0.12, t);
    }
    if (snares.has(step)) {
      snare.triggerAttackRelease(0.08, t, 0.85);
    }
    if (hats.has(step)) {
      hat.triggerAttackRelease(280, 0.05, t, 0.45);
    }
  }

  return 16 * sixteenthSec;
}

export function stopTransport() {
  Tone.Transport.cancel();
}

export function stopPlayback() {
  if (polySynth) {
    polySynth.releaseAll();
  }
  if (drumMasterGain) {
    drumMasterGain.gain.value = 0;
  }
}
