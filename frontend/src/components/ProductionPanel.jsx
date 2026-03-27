import { extractNumberedSteps } from '../utils/normalize';
import styles from './ProductionPanel.module.css';

function fallbackLines(text) {
  if (!text) return [];
  return text
    .split('\n')
    .map((l) => l.trim())
    .filter((l) => l && !l.startsWith('#') && !l.startsWith('**'));
}

export default function ProductionPanel({ productionMarkdown, teachingNote }) {
  const numbered = extractNumberedSteps(productionMarkdown || '');
  const lines = numbered.length ? numbered : fallbackLines(productionMarkdown).map((t, i) => ({ n: i + 1, text: t }));

  return (
    <section className={styles.panel}>
      <header className={styles.header}>
        <h2 className={styles.title}>Production + Teaching</h2>
      </header>

      <div className={styles.section}>
        <div className={styles.sectionLabel}>Ableton</div>
        <ol className={styles.steps}>
          {lines.map((step) => (
            <li key={step.n} className={styles.step}>
              <span className={styles.stepNum}>{step.n}</span>
              <span className={styles.stepText}>{step.text}</span>
            </li>
          ))}
        </ol>
        {lines.length === 0 ? <p className={styles.empty}>No steps yet.</p> : null}
      </div>

      <div className={styles.teach}>
        <div className={styles.sectionLabel}>Teaching</div>
        <div className={styles.teachBody}>{teachingNote || '—'}</div>
      </div>
    </section>
  );
}
