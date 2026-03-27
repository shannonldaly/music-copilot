import { CHORD_BORDER_COLORS } from '../constants';
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

export default function SessionPanel({ chords, bpm, progressionName, keyName }) {
  const { rows } = buildRollLayout(chords);

  return (
    <section className={styles.panel}>
      <header className={styles.header}>
        <h2 className={styles.title}>Session View</h2>
        <span className={styles.meta}>
          {keyName || '—'} {progressionName ? `· ${progressionName}` : ''}
        </span>
      </header>

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
      </div>
      <div className={styles.footer}>
        <span className={styles.mono}>{bpm} BPM</span>
      </div>
    </section>
  );
}
