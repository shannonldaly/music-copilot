export function parseBpmFromText(text) {
  if (text == null) return null;
  if (typeof text === 'number' && !Number.isNaN(text)) return text;
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

  const prog = data.progressions?.[0];
  if (!prog) {
    return {
      empty: true,
      teaching_note: data.teaching_note,
      production_steps: data.production_steps,
      tokens_used: data.tokens_used,
      cost_usd: data.cost_usd,
    };
  }

  const chords = (prog.chords || []).map((c) => ({
    numeral: c.numeral,
    name: c.name,
    notes: c.note_names || c.notes || [],
  }));

  const bpm =
    parseBpmFromText(prog.tempo_suggestion) ??
    parseBpmFromText(prog.tempo_range) ??
    85;

  const warnings = data.validation?.warnings?.length
    ? data.validation.warnings.join(' ')
    : null;

  return {
    key: prog.key,
    scale: prog.scale || '',
    progression_name: prog.name || prog.numerals?.join('–') || '',
    chords,
    tempo_suggestion: `${bpm} BPM`,
    bpm,
    genre_context: Array.isArray(prog.genres) ? prog.genres.join(', ') : prog.genres || '',
    theory_explanation: prog.description || '',
    voice_leading_notes: warnings || '—',
    validation: data.validation,
    production_steps: data.production_steps || '',
    teaching_note: data.teaching_note || '',
    tokens_used: data.tokens_used,
    cost_usd: data.cost_usd,
    intent: data.intent,
  };
}

export function extractNumberedSteps(markdown) {
  if (!markdown) return [];
  const lines = markdown.split('\n');
  const steps = [];
  const re = /^(\d+)\.\s+(.+)$/;
  for (const line of lines) {
    const m = line.trim().match(re);
    if (m) steps.push({ n: parseInt(m[1], 10), text: m[2] });
  }
  if (steps.length) return steps;
  const loose = markdown.split(/\n(?=\d+\.\s)/);
  for (const chunk of loose) {
    const m = chunk.trim().match(/^(\d+)\.\s+([\s\S]+)/);
    if (m) steps.push({ n: parseInt(m[1], 10), text: m[2].trim() });
  }
  return steps;
}
