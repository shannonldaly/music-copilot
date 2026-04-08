import styles from './SoundEngineeringPanel.module.css';

export default function SoundEngineeringPanel({ data }) {
  if (!data || typeof data !== 'object') return null;

  const summary = data.summary ?? '';
  const steps = Array.isArray(data.steps) ? data.steps : [];
  const path = data.ableton_path ?? data.abletonPath ?? '';
  const principle = data.principle ?? '';
  const artistRef = data.artist_reference ?? data.artistReference ?? '';

  if (!summary && steps.length === 0 && !path && !principle && !artistRef) return null;

  return (
    <section className={styles.panel}>
      <header className={styles.header}>
        <h2 className={styles.title}>Sound engineering</h2>
      </header>

      {summary ? <p className={styles.summary}>{summary}</p> : null}

      {steps.length > 0 ? (
        <div className={styles.section}>
          <div className={styles.sectionLabel}>Steps</div>
          <ol className={styles.steps}>
            {steps.map((text, i) => (
              <li key={i} className={styles.step}>
                <span className={styles.stepNum}>{i + 1}</span>
                <span className={styles.stepText}>{text}</span>
              </li>
            ))}
          </ol>
        </div>
      ) : null}

      {path ? (
        <div className={styles.section}>
          <div className={styles.sectionLabel}>Ableton path</div>
          <code className={styles.path}>{path}</code>
        </div>
      ) : null}

      {principle ? (
        <div className={styles.section}>
          <div className={styles.sectionLabel}>Principle</div>
          <div className={styles.principle}>{principle}</div>
        </div>
      ) : null}

      {artistRef ? (
        <footer className={styles.footer}>
          <div className={styles.sectionLabel}>Artist reference</div>
          <p className={styles.artistLine}>{artistRef}</p>
        </footer>
      ) : null}
    </section>
  );
}
