import styles from './AlsoTryList.module.css';

const DOT_COLORS = ['#4a9eff', '#22c55e', '#a855f7'];

function chordLine(chords) {
  if (!chords?.length) return '—';
  return chords.map((c) => (typeof c === 'string' ? c : c.name || '?')).join(' – ');
}

export default function AlsoTryList({ alternatives, onPick, disabled }) {
  if (!alternatives?.length) return null;

  return (
    <div className={styles.wrap}>
      <div className={styles.sectionHead}>
        <span className={styles.sectionHeadAccent} aria-hidden />
        <div className={styles.sectionHeadText}>
          <div className={styles.title}>Also try</div>
          <p className={styles.subtitle}>Tap a row to swap it into your main progression — notes load next.</p>
        </div>
      </div>
      <ul className={styles.list}>
        {alternatives.map((alt, i) => (
          <li key={`${alt.label}-${i}`}>
            <button
              type="button"
              className={styles.row}
              disabled={disabled}
              onClick={() => onPick(alt, i)}
            >
              <span
                className={styles.dot}
                style={{ background: DOT_COLORS[i % DOT_COLORS.length] }}
                aria-hidden
              />
              <span className={styles.chords}>{chordLine(alt.chords)}</span>
              <span className={styles.tag}>[{alt.label}]</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
