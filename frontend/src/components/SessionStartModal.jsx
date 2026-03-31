import styles from './SessionStartModal.module.css';

const OPTIONS = [
  {
    id: 'chords',
    title: 'Chords + Melody',
    subtitle: 'Progressions · Voice leading · Theory',
  },
  {
    id: 'drums',
    title: 'Drum Pattern',
    subtitle: 'Groove · Genre · Splice search',
  },
  {
    id: 'mixing',
    title: 'Sound Mixing',
    subtitle: 'EQ · Automation · Effects chain',
  },
  {
    id: 'full',
    title: 'Full Session',
    subtitle: 'Guided start-to-finish workflow',
  },
];

export default function SessionStartModal({ open, selected, onSelect, onContinue }) {
  if (!open) return null;

  return (
    <div className={styles.overlay} role="dialog" aria-modal="true" aria-labelledby="session-modal-title">
      <div className={styles.card}>
        <h1 id="session-modal-title" className={styles.title}>
          Start session
        </h1>
        <p className={styles.hint}>Choose how you want to work</p>
        <div className={styles.grid}>
          {OPTIONS.map((o) => (
            <button
              key={o.id}
              type="button"
              className={`${styles.option} ${selected === o.id ? styles.optionSelected : ''}`}
              onClick={() => onSelect(o.id)}
            >
              <span className={styles.optTitle}>{o.title}</span>
              <span className={styles.optSub}>{o.subtitle}</span>
            </button>
          ))}
        </div>
        <button
          type="button"
          className={styles.continue}
          disabled={!selected}
          onClick={onContinue}
        >
          Continue →
        </button>
      </div>
    </div>
  );
}
