/** Phase 2 — progress sidebar stage definitions per session mode */

/** Shown in Suggested next before the first successful generation (chords + full session modes). */
export const CHORDS_SESSION_START_SUGGESTED_TEXT =
  'Describe what you want — a mood, genre, artist reference, or specific key. Try: melancholic lo-fi in A minor, or something like Massive Attack.';

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

/** Chords + full: user-facing stages only (key / BPM / vibe are Session Info metadata). */
export const STAGE_SEQUENCES = {
  chords: ['progression', 'melodyDir', 'bass', 'drums', 'mix'],
  drums: ['genreFeel', 'bpm', 'pattern', 'splice', 'mix'],
  mixing: ['section', 'targetVibe', 'eq', 'automation'],
  full: ['progression', 'melodyDir', 'bass', 'drums', 'mix'],
};

export const STAGE_LABELS = {
  progression: 'Progression',
  melodyDir: 'Melody Direction',
  bass: 'Bass Line',
  drums: 'Drums',
  mix: 'Mix + Automation',
  genreFeel: 'Genre / Feel',
  bpm: 'BPM',
  pattern: 'Pattern',
  splice: 'Splice Search Terms',
  section: 'Section',
  targetVibe: 'Target vibe',
  eq: 'EQ priorities',
  automation: 'Automation plan',
};

/** Suggested next while output exists but user has not clicked Keep yet (first unconfirmed stage in order). */
export const CONFIRM_SUGGESTIONS = {
  chords: {
    progression:
      'Happy with this progression? Hit Keep to lock it in, or try an alternative below.',
    melodyDir: 'Happy with this melody direction? Hit Keep to lock it in, or ask for changes in the input.',
    bass: 'Happy with this bass guidance? Hit Keep to lock it in, or try Regen.',
    drums: 'Happy with this drums guidance? Hit Keep to lock it in, or try Regen.',
    mix: 'Happy with this mix guidance? Hit Keep to lock it in, or try Regen.',
  },
  drums: {
    genreFeel: 'Happy with this genre / feel? Hit Keep to lock it in.',
    bpm: 'Happy with this tempo? Hit Keep to lock it in.',
    pattern: 'Happy with this pattern? Hit Keep to lock it in.',
    splice: 'Happy with these Splice notes? Hit Keep to lock it in.',
    mix: 'Happy with this mix guidance? Hit Keep to lock it in.',
  },
  mixing: {
    section: 'Happy with this section focus? Hit Keep to lock it in.',
    targetVibe: 'Happy with this vibe read? Hit Keep to lock it in.',
    eq: 'Happy with these EQ priorities? Hit Keep to lock it in.',
    automation: 'Happy with this automation plan? Hit Keep to lock it in.',
  },
  full: {},
};

export function getConfirmSuggestion(mode, stageId) {
  const m = mode === SESSION_MODES.FULL ? SESSION_MODES.CHORDS : mode;
  const table =
    m === SESSION_MODES.CHORDS || m === SESSION_MODES.FULL ? CONFIRM_SUGGESTIONS.chords : CONFIRM_SUGGESTIONS[m];
  return (
    table?.[stageId] ||
    'Happy with this step? Hit Keep to lock it in, or use Regen / Vary to try again.'
  );
}

export const SUGGESTIONS = {
  chords: {
    progression: {
      text: 'Refine this harmony — ask for a different progression, reharmonization, or voicing.',
      prefill: 'Give me an alternative progression in the same key',
    },
    melodyDir: {
      text: 'Want a melodic direction over {key} {progression}?',
      prefill: 'Suggest a melodic direction over this progression',
    },
    bass: {
      text: 'Now add a bass line — match the harmony you have.',
      prefill: 'Give me a lo-fi bass line to match this progression',
    },
    drums: {
      text: 'Ready for drums? Match the groove to your chords.',
      prefill: 'Give me a drum pattern that matches this vibe',
    },
    mix: {
      text: 'Shape the mix — EQ, space, and movement.',
      prefill: 'How should I EQ and space these chords in Ableton?',
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
  full: {},
};

export function getSuggestionForStage(mode, stageId) {
  const m = mode === SESSION_MODES.FULL ? SESSION_MODES.CHORDS : mode;
  const table = m === SESSION_MODES.CHORDS || m === SESSION_MODES.FULL ? SUGGESTIONS.chords : SUGGESTIONS[m];
  return table?.[stageId] || { text: 'Try a follow-up in the input bar.', prefill: '' };
}

function emptyStage(status, value = '') {
  return { status, value, confirmed: false };
}

export function createInitialStages(mode) {
  const seq = STAGE_SEQUENCES[mode] || STAGE_SEQUENCES.chords;
  const o = {};
  seq.forEach((id, i) => {
    o[id] = emptyStage(i === 0 ? 'active' : 'pending', '');
  });
  return o;
}

/**
 * Apply /api/generate fields to stage state.
 * Each filled stage is `done` with confirmed: false until the user clicks Keep.
 */
export function applyApiToStages(prev, mode, apiPayload, normalized) {
  const seq = STAGE_SEQUENCES[mode] || STAGE_SEQUENCES.chords;
  const next = { ...prev };
  const setDone = (id, value) => {
    if (!seq.includes(id)) return;
    if (next[id]?.status === 'skipped') return;
    next[id] = { ...next[id], status: 'done', value: value != null ? String(value) : '', confirmed: false };
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
    if (normalized?.progression_name || apiPayload?.progression_name) {
      setDone('progression', normalized?.progression_name || apiPayload?.progression_name);
    }
    const md = apiPayload?.melody_direction || normalized?.melody_direction;
    if (md && (typeof md === 'object' ? Object.keys(md).length : String(md).length)) {
      setDone('melodyDir', 'Defined');
    }
  }

  recomputeActive(next, seq);
  return next;
}

/**
 * Recalculate active/pending: any `done` with confirmed false blocks later non-done stages from becoming active.
 */
export function recomputeActive(stages, seq) {
  let blocked = false;
  let assignedActive = false;

  for (const id of seq) {
    const s = stages[id];
    if (!s) continue;

    if (s.status === 'skipped') continue;

    if (s.status === 'done') {
      if (!s.confirmed) blocked = true;
      continue;
    }

    if (blocked) {
      s.status = 'pending';
      continue;
    }

    if (!assignedActive) {
      s.status = 'active';
      assignedActive = true;
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
    confirmed: true,
  };
  recomputeActive(next, seq);
  return next;
}

/** First stage in order that is done but not yet confirmed (user must Keep). */
export function firstAwaitingConfirmStage(stages, mode) {
  const seq = STAGE_SEQUENCES[mode] || STAGE_SEQUENCES.chords;
  for (const id of seq) {
    const s = stages[id];
    if (s?.status === 'done' && !s.confirmed) return id;
  }
  return null;
}

/** Mark the first unconfirmed done stage as confirmed and recompute active. */
export function confirmFirstAwaitingStage(stages, mode) {
  const seq = STAGE_SEQUENCES[mode] || STAGE_SEQUENCES.chords;
  const next = { ...stages };
  const target = firstAwaitingConfirmStage(next, mode);
  if (!target) return next;
  next[target] = { ...next[target], confirmed: true };
  recomputeActive(next, seq);
  return next;
}

/**
 * Regen/Vary: reset first awaiting stage to active (cleared) and clear later non-skipped stages.
 */
export function regenResetFromFirstAwaiting(stages, mode) {
  const seq = STAGE_SEQUENCES[mode] || STAGE_SEQUENCES.chords;
  const first = firstAwaitingConfirmStage(stages, mode);
  if (!first) return stages;
  const idx = seq.indexOf(first);
  if (idx < 0) return stages;
  const next = { ...stages };
  for (let i = idx; i < seq.length; i++) {
    const id = seq[i];
    if (next[id]?.status === 'skipped') continue;
    if (i === idx) {
      next[id] = emptyStage('active', '');
    } else {
      next[id] = emptyStage('pending', '');
    }
  }
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

/** Next stage for normal suggestions (after all outputs are confirmed or skipped). */
export function nextSuggestedStage(stages, mode) {
  if (firstAwaitingConfirmStage(stages, mode)) return null;
  const seq = STAGE_SEQUENCES[mode] || STAGE_SEQUENCES.chords;
  for (const id of seq) {
    const s = stages[id];
    if (!s || s.status === 'skipped') continue;
    if (s.status === 'done') continue;
    return id;
  }
  return null;
}
