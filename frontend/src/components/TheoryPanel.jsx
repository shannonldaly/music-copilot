import { CHORD_BORDER_COLORS } from '../constants';
import styles from './TheoryPanel.module.css';

export default function TheoryPanel({
  chords,
  keyName,
  scale,
  progressionName,
  theoryExplanation,
  voiceLeadingNotes,
  validation,
}) {
  const list = (chords || []).slice(0, 8);

  return (
    <section className={styles.panel}>
      <header className={styles.header}>
        <h2 className={styles.title}>Theory + Validator</h2>
        <div className={styles.keyRow}>
          <span className={styles.mono}>{keyName || '—'}</span>
          {scale ? <span className={styles.dim}>{scale}</span> : null}
          {progressionName ? <span className={styles.dim}>· {progressionName}</span> : null}
        </div>
      </header>

      <div className={styles.cards}>
        {list.map((c, i) => (
          <div
            key={`${c.name}-${i}`}
            className={styles.card}
            style={{ borderTopColor: CHORD_BORDER_COLORS[i % CHORD_BORDER_COLORS.length] }}
          >
            <div className={styles.chordName}>{c.name}</div>
            <div className={styles.numeral}>{c.numeral}</div>
            <div className={styles.notes}>
              {(c.notes || []).map((n) => (
                <span key={n} className={styles.note}>
                  {n}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className={styles.block}>
        <div className={styles.blockTitle}>Theory</div>
        <p className={styles.body}>{theoryExplanation || '—'}</p>
      </div>

      <div className={styles.block}>
        <div className={styles.blockTitle}>Voice leading</div>
        <p className={styles.body}>{voiceLeadingNotes || '—'}</p>
      </div>

      <div className={styles.badgeRow}>
        <span className={styles.badge}>music21</span>
        {validation ? (
          <span className={validation.passed ? styles.ok : styles.fail}>
            {validation.passed ? 'passed' : 'failed'}
          </span>
        ) : (
          <span className={styles.dim}>—</span>
        )}
      </div>
    </section>
  );
}
