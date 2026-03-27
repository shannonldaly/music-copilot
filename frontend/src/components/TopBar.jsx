import styles from './TopBar.module.css';

export default function TopBar({
  bpm,
  cpuPercent,
  tokenCostUsd,
  isPlaying,
  onPlayToggle,
  onStop,
}) {
  return (
    <header className={styles.menubar}>
      <div className={styles.left}>
        <span className={styles.appName}>Co-Pilot</span>
      </div>
      <div className={styles.right}>
        <div className={styles.transport}>
          <button
            type="button"
            className={styles.transportBtn}
            onClick={onPlayToggle}
            aria-label={isPlaying ? 'Pause preview' : 'Play preview'}
          >
            {isPlaying ? '❚❚' : '▶'}
          </button>
          <button type="button" className={styles.transportBtn} onClick={onStop} aria-label="Stop">
            ⏹
          </button>
        </div>
        <span className={styles.mono}>{bpm} BPM</span>
        <span className={styles.mono}>CPU {cpuPercent}%</span>
        <span className={styles.mono}>
          ${typeof tokenCostUsd === 'number' ? tokenCostUsd.toFixed(4) : '0.0000'}
        </span>
      </div>
    </header>
  );
}
