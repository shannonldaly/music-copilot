export function parseBpmFromText(text) {
  if (text == null) return null;
  if (typeof text === 'number' && !Number.isNaN(text)) return text;
  if (Array.isArray(text) && text.length >= 2) {
    const a = Number(text[0]);
    const b = Number(text[1]);
    if (!Number.isNaN(a) && !Number.isNaN(b)) return Math.round((a + b) / 2);
  }
  const s = String(text);
  const m = s.match(/(\d+)\s*[-–]\s*(\d+)/);
  if (m) return Math.round((parseInt(m[1], 10) + parseInt(m[2], 10)) / 2);
  const n = s.match(/(\d+)/);
  return n ? parseInt(n[1], 10) : null;
}

/**
 * Map API /api/generate response to UI model (aligned with CLAUDE.md theory shape where possible).
 */
export function normalizeGenerateResponse(data) {
  if (!data) return null;

  if (data.clarification_needed) {
    return {
      clarification_only: true,
      clarification_question: data.clarification_question,
      tokens_used: data.tokens_used,
      cost_usd: data.cost_usd,
    };
  }

  if (!data.success) return null;

  const prog = data.progression || data.progressions?.[0];
  const drum = data.drum_patterns?.[0];

  if (drum && !prog) {
    const bpm =
      (typeof data.bpm === 'number' ? data.bpm : null) ??
      parseBpmFromText(drum.tempo_suggestion) ??
      parseBpmFromText(drum.tempo_range) ??
      110;

    const genres = Array.isArray(drum.genres) ? drum.genres.join(', ') : drum.genres || '';

    return {
      mode: 'drums',
      drumPattern: {
        name: drum.name,
        description: drum.description || '',
        tempo_range: drum.tempo_range,
        swing: drum.swing,
        grid: drum.grid || {},
        genres,
        genresList: drum.genres || [],
      },
      bpm,
      tempo_suggestion: `${bpm} BPM`,
      genre_context: data.genre_context ?? genres,
      theory_explanation: drum.description || '',
      chords: [],
      key: data.key ?? null,
      scale: '',
      progression_name: data.progression_name ?? drum.name,
      voice_leading_notes: '—',
      validation: null,
      validationBadge: 'na_drums',
      production_steps: data.production_steps || '',
      teaching_note: data.teaching_note || '',
      tokens_used: data.tokens_used,
      cost_usd: data.cost_usd,
      intent: data.intent,
      alternatives: data.alternatives ?? [],
      melody_direction: data.melody_direction ?? null,
    };
  }

  if (!prog) {
    return {
      empty: true,
      mode: 'empty',
      teaching_note: data.teaching_note,
      production_steps: data.production_steps,
      tokens_used: data.tokens_used,
      cost_usd: data.cost_usd,
      alternatives: data.alternatives ?? [],
      melody_direction: data.melody_direction ?? null,
    };
  }

  const chords = (prog.chords || []).map((c) => ({
    numeral: c.numeral,
    name: c.name,
    notes: c.note_names || c.notes || [],
  }));

  const bpm =
    (typeof data.bpm === 'number' ? data.bpm : null) ??
    parseBpmFromText(prog.tempo_suggestion) ??
    parseBpmFromText(prog.tempo_range) ??
    85;

  const warnings = data.validation?.warnings?.length
    ? data.validation.warnings.join(' ')
    : null;

  const genre_context =
    data.genre_context ??
    (Array.isArray(prog.genres) ? prog.genres.join(', ') : prog.genres || '');

  return {
    mode: 'chords',
    drumPattern: null,
    key: data.key ?? prog.key,
    scale: prog.scale || '',
    progression_name:
      data.progression_name ?? prog.name ?? prog.numerals?.join('–') ?? '',
    chords,
    tempo_suggestion: `${bpm} BPM`,
    bpm,
    genre_context,
    theory_explanation: prog.description || '',
    voice_leading_notes: warnings || '—',
    validation: data.validation,
    validationBadge: null,
    production_steps: data.production_steps || '',
    teaching_note: data.teaching_note || '',
    tokens_used: data.tokens_used,
    cost_usd: data.cost_usd,
    intent: data.intent,
    alternatives: data.alternatives ?? [],
    melody_direction: data.melody_direction ?? null,
  };
}

/**
 * Collect ordered step lines from markdown; renumber 1..N so section restarts don't break the list.
 */
export function extractNumberedSteps(markdown) {
  if (!markdown) return [];
  const lines = markdown.split('\n');
  const raw = [];
  const re = /^(\d+)\.\s+(.+)$/;
  for (const line of lines) {
    const m = line.trim().match(re);
    if (m) raw.push(m[2]);
  }
  if (raw.length) {
    return raw.map((text, i) => ({ n: i + 1, text }));
  }
  const loose = markdown.split(/\n(?=\d+\.\s)/);
  for (const chunk of loose) {
    const m = chunk.trim().match(/^(\d+)\.\s+([\s\S]+)/);
    if (m) raw.push(m[2].trim());
  }
  return raw.map((text, i) => ({ n: i + 1, text }));
}
