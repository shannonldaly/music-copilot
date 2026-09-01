import styles from './MelodyDirectionPanel.module.css';

/**
 * Bass line guidance panel.
 *
 * Expects: model.bass_line — {root_notes, pattern, rhythm_feel, register, tip,
 * artist_reference}, produced by generate_bass_line_local over the session's
 * current progression.
 * Guarantees: renders only the fields present; returns null for a missing or
 * non-object payload, so the workspace can render it unconditionally.
 * Shares MelodyDirectionPanel's styles so the two guidance panels read as one
 * family; the stage flow's Keep button treats this output like any other stage.
 */
export default function BassLinePanel({ data }) {
  if (!data || typeof data !== 'object') return null;

  return (
    <div className={styles.panel}>
      <div className={styles.head}>
        <span className={styles.accentBar} aria-hidden />
        <div className={styles.headText}>
          <div className={styles.kicker}>Low end</div>
          <h3 className={styles.title}>Bass line</h3>
        </div>
      </div>

      <div className={styles.body}>
        {Array.isArray(data.root_notes) && data.root_notes.length ? (
          <div className={styles.row}>
            <span className={styles.k}>Root notes</span>
            <span className={styles.v}>{data.root_notes.join(' · ')}</span>
          </div>
        ) : null}
        {data.pattern ? (
          <div className={styles.row}>
            <span className={styles.k}>Pattern</span>
            <span className={styles.v}>{data.pattern}</span>
          </div>
        ) : null}
        {data.rhythm_feel ? (
          <div className={styles.row}>
            <span className={styles.k}>Rhythm feel</span>
            <span className={styles.v}>{data.rhythm_feel}</span>
          </div>
        ) : null}
        {data.register ? (
          <div className={styles.row}>
            <span className={styles.k}>Register</span>
            <span className={styles.v}>{data.register}</span>
          </div>
        ) : null}
        {data.tip ? (
          <div className={styles.row}>
            <span className={styles.k}>Tip</span>
            <span className={styles.v}>{data.tip}</span>
          </div>
        ) : null}
        {data.artist_reference ? (
          <div className={styles.row}>
            <span className={styles.k}>Reference</span>
            <span className={styles.v}>{data.artist_reference}</span>
          </div>
        ) : null}
      </div>
    </div>
  );
}
