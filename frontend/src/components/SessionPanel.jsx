import { CHORD_BORDER_COLORS } from '../constants';
import { buildDrumRows } from '../utils/drums';
import { parseNoteToMidi, midiToRollRow } from '../utils/notes';
import styles from './SessionPanel.module.css';

function buildRollLayout(chords) {
  const list = chords || [];
  const midiVals = [];
  for (const c of list) {
    const notes = c.notes || c.note_names || [];
    for (const n of notes) {
      const m = parseNoteToMidi(n);
      if (m != null) midiVals.push(m);
    }
  }
  if (!midiVals.length) return { minMidi: 60, maxMidi: 72, rows: [] };

  const minMidi = Math.min(...midiVals) - 2;
  const maxMidi = Math.max(...midiVals) + 2;

  const rows = list.map((c, chordIdx) => {
    const notes = c.notes || c.note_names || [];
    const color = CHORD_BORDER_COLORS[chordIdx % CHORD_BORDER_COLORS.length];
    return {
      chordIdx,
      color,
      blocks: notes
        .map((n) => {
          const midi = parseNoteToMidi(n);
          if (midi == null) return null;
          const y = 1 - midiToRollRow(midi, minMidi, maxMidi);
          return { midi, label: n, y };
        })
        .filter(Boolean),
    };
  });

  return { minMidi, maxMidi, rows };
}

export default function SessionPanel({
  mode,
  chords,
  drumGrid,
  bpm,
  progressionName,
  keyName,
  genreContext,
  rollLoading,
}) {
  const { rows } = buildRollLayout(chords);
  const isDrums = mode === 'drums';
  const { rows: drumRows, stepIndices } = isDrums ? buildDrumRows(drumGrid) : { rows: [], stepIndices: [] };

  return (
    <section className={styles.panel}>
      <header className={styles.header}>
        <h2 className={styles.title}>Session View</h2>
        <span className={styles.meta}>
          {isDrums ? (
            <>
              <span className={styles.mono}>{progressionName || 'Drum pattern'}</span>
              {genreContext ? <span className={styles.dim}> · {genreContext}</span> : null}
            </>
          ) : (
            <>
              {keyName || '—'} {progressionName ? `· ${progressionName}` : ''}
            </>
          )}
        </span>
      </header>

      {isDrums ? (
        <div className={styles.drumSection}>
          <div className={styles.rollLabel}>16-step grid</div>
          <div className={styles.stepHeader}>
            <span className={styles.stepCorner} aria-hidden />
            {stepIndices.map((s) => (
              <span key={s} className={styles.stepIdx}>
                {s + 1}
              </span>
            ))}
          </div>
          {drumRows.map((row) => (
            <div key={row.id} className={styles.drumRow}>
              <span className={styles.drumLabel}>{row.label}</span>
              <div className={styles.drumSteps}>
                {stepIndices.map((step) => (
                  <div
                    key={step}
                    className={styles.drumCell}
                    style={{
                      background: row.steps.has(step) ? row.color : '#1a1a1a',
                      borderColor: row.steps.has(step) ? row.color : '#222',
                    }}
                    title={`${row.label} step ${step + 1}`}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <>
          <div className={styles.clipRow}>
            {(chords || []).slice(0, 8).map((c, i) => (
              <div
                key={`${c.name}-${i}`}
                className={styles.clip}
                style={{ borderTopColor: CHORD_BORDER_COLORS[i % CHORD_BORDER_COLORS.length] }}
              >
                <span className={styles.clipName}>{c.name}</span>
                <span className={styles.clipSub}>{c.numeral}</span>
              </div>
            ))}
          </div>

          <div className={styles.rollWrap}>
            <div className={styles.rollLabel}>Piano roll</div>
            <div className={styles.rollHost}>
              <div className={styles.roll}>
                {rows.map((row) => (
                  <div key={row.chordIdx} className={styles.chordColumn}>
                    {row.blocks.map((b) => (
                      <div
                        key={`${b.midi}-${b.label}`}
                        className={styles.noteBlock}
                        style={{
                          background: row.color,
                          top: `${b.y * 100}%`,
                        }}
                        title={b.label}
                      />
                    ))}
                  </div>
                ))}
              </div>
              {rollLoading ? (
                <div className={styles.rollOverlay}>
                  <span className={styles.rollOverlayText}>Loading notes…</span>
                </div>
              ) : null}
            </div>
          </div>
        </>
      )}

      <div className={styles.footer}>
        <span className={styles.mono}>{bpm} BPM</span>
      </div>
    </section>
  );
}
