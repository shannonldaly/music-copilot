/** Phase 2 — progress sidebar stage definitions per session mode */

export const SESSION_MODES = {
  CHORDS: 'chords',
  DRUMS: 'drums',
  MIXING: 'mixing',
  FULL: 'full',
};

export const MODE_BADGE_LABEL = {
  chords: 'CHORDS + MELODY',
  drums: 'DRUM PATTERN',
  mixing: 'SOUND MIXING',
  full: 'FULL SESSION',
};

export const STAGE_SEQUENCES = {
  chords: ['keyMode', 'bpm', 'progression', 'vibe', 'melodyDir', 'bass', 'drums', 'mix'],
  drums: ['genreFeel', 'bpm', 'pattern', 'splice', 'mix'],
  mixing: ['section', 'targetVibe', 'eq', 'automation'],
  full: ['keyMode', 'bpm', 'progression', 'vibe', 'melodyDir', 'bass', 'drums', 'mix'],
};

export const STAGE_LABELS = {
  keyMode: 'Key + Mode',
  bpm: 'BPM',
  progression: 'Progression',
  vibe: 'Vibe',
  melodyDir: 'Melody Direction',
  bass: 'Bass Line',
  drums: 'Drums',
  mix: 'Mix + Automation',
  genreFeel: 'Genre / Feel',
  pattern: 'Pattern',
  splice: 'Splice Search Terms',
  section: 'Section',
  targetVibe: 'Target vibe',
  eq: 'EQ priorities',
  automation: 'Automation plan',
};

export const SUGGESTIONS = {
  chords: {
    keyMode: {
      text: 'Lock in a key and mode — try naming a key (e.g. A minor) and a vibe.',
      prefill: 'Give me a lo-fi progression in A minor',
    },
    bpm: {
      text: 'Set a tempo — try mentioning BPM or “slow / fast”.',
      prefill: 'Around 85 BPM for this vibe',
    },
    progression: {
      text: 'Want a melodic direction over {key} {progression}?',
      prefill: 'Suggest a melodic direction over this progression',
    },
    vibe: {
      text: 'Narrow the genre or mood for tighter suggestions.',
      prefill: 'More melancholic and sparse',
    },
    melodyDir: {
      text: 'Now add a bass line — match the harmony you have.',
      prefill: 'Give me a lo-fi bass line to match this progression',
    },
    bass: {
      text: 'Ready for drums? Match the groove to your chords.',
      prefill: 'Give me a drum pattern that matches this vibe',
    },
    drums: {
      text: 'Shape the mix — EQ, space, and movement.',
      prefill: 'How should I EQ and space these chords in Ableton?',
    },
    mix: {
      text: 'Refine automation or final balance when you are ready.',
      prefill: 'Sidechain and mix bus tips for this track',
    },
  },
  drums: {
    genreFeel: {
      text: 'Name a genre or feel for the groove.',
      prefill: 'Trap drum pattern, dark feel',
    },
    bpm: { text: 'Dial in tempo for the pattern.', prefill: '140 BPM trap beat' },
    pattern: { text: 'Iterate on the pattern or layering.', prefill: 'Busier hi-hats for this pattern' },
    splice: { text: 'Note Splice search terms for one-shots.', prefill: 'Splice search terms for trap kicks' },
    mix: { text: 'Move to mix and automation.', prefill: 'Mix tips for punchy trap drums' },
  },
  mixing: {
    section: { text: 'Which section are you treating?', prefill: 'EQ plan for my drop section' },
    targetVibe: { text: 'Describe the target vibe for this section.', prefill: 'Warmer, wider drop' },
    eq: { text: 'Prioritize frequency roles.', prefill: 'EQ priorities for bass vs chords' },
    automation: { text: 'Plan filter and level rides.', prefill: 'Automation plan for build into drop' },
  },
  full: {}, // same keys as chords — reuse chords map
};

export function getSuggestionForStage(mode, stageId) {
  const m = mode === SESSION_MODES.FULL ? SESSION_MODES.CHORDS : mode;
  const table = m === SESSION_MODES.CHORDS || m === SESSION_MODES.FULL ? SUGGESTIONS.chords : SUGGESTIONS[m];
  return table?.[stageId] || { text: 'Try a follow-up in the input bar.', prefill: '' };
}

export function createInitialStages(mode) {
  const seq = STAGE_SEQUENCES[mode] || STAGE_SEQUENCES.chords;
  const o = {};
  seq.forEach((id, i) => {
    o[id] = { status: i === 0 ? 'active' : 'pending', value: '' };
  });
  return o;
}

/**
 * Apply /api/generate fields to stage state (done + values).
 */
export function applyApiToStages(prev, mode, apiPayload, normalized) {
  const seq = STAGE_SEQUENCES[mode] || STAGE_SEQUENCES.chords;
  const next = { ...prev };
  const setDone = (id, value) => {
    if (!seq.includes(id)) return;
    if (next[id]?.status === 'skipped') return;
    next[id] = { ...next[id], status: 'done', value: value != null ? String(value) : '' };
  };

  if (mode === SESSION_MODES.DRUMS) {
    if (normalized?.genre_context || apiPayload?.genre_context) {
      setDone('genreFeel', normalized?.genre_context || apiPayload?.genre_context);
    }
    if (normalized?.bpm != null || apiPayload?.bpm != null) {
      setDone('bpm', normalized?.bpm ?? apiPayload?.bpm);
    }
    if (normalized?.progression_name || apiPayload?.progression_name) {
      setDone('pattern', normalized?.progression_name || apiPayload?.progression_name);
    }
  } else if (mode === SESSION_MODES.MIXING) {
    if (apiPayload?.intent) setDone('section', apiPayload.intent);
  } else {
    if (normalized?.key || apiPayload?.key) setDone('keyMode', normalized?.key || apiPayload?.key);
    if (normalized?.bpm != null || apiPayload?.bpm != null) {
      setDone('bpm', normalized?.bpm ?? apiPayload?.bpm);
    }
    if (normalized?.progression_name || apiPayload?.progression_name) {
      setDone('progression', normalized?.progression_name || apiPayload?.progression_name);
    }
    if (normalized?.genre_context || apiPayload?.genre_context) {
      setDone('vibe', normalized?.genre_context || apiPayload?.genre_context);
    }
    const md = apiPayload?.melody_direction || normalized?.melody_direction;
    if (md && (typeof md === 'object' ? Object.keys(md).length : String(md).length)) {
      setDone('melodyDir', 'Defined');
    }
  }

  recomputeActive(next, seq);
  return next;
}

export function recomputeActive(stages, seq) {
  let found = false;
  for (const id of seq) {
    const s = stages[id];
    if (!s) continue;
    if (s.status === 'skipped' || s.status === 'done') continue;
    if (!found) {
      s.status = 'active';
      found = true;
    } else {
      s.status = 'pending';
    }
  }
}

export function skipStage(stages, seq, stageId, note) {
  const next = { ...stages };
  if (!next[stageId]) return next;
  next[stageId] = {
    status: 'skipped',
    value: note != null && String(note).trim() ? String(note).trim() : 'Skipped',
  };
  recomputeActive(next, seq);
  return next;
}

export function buildContextPrefix(stages, seq) {
  const parts = [];
  for (const id of seq) {
    const s = stages[id];
    if (!s || s.status !== 'skipped' || !s.value || s.value === 'Skipped') continue;
    parts.push(`${STAGE_LABELS[id] || id}: ${s.value}`);
  }
  if (!parts.length) return '';
  return `[Session context]\n${parts.join('\n')}\n\n`;
}

export function nextSuggestedStage(stages, mode) {
  const seq = STAGE_SEQUENCES[mode] || STAGE_SEQUENCES.chords;
  for (const id of seq) {
    const s = stages[id];
    if (!s || s.status === 'skipped') continue;
    if (s.status === 'done') continue;
    return id;
  }
  return null;
}
