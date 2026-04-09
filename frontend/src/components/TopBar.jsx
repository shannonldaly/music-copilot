import styles from './TopBar.module.css';

export default function TopBar({
  songName,
  bpm,
  cpuPercent,
  tokenCostUsd,
  isPlaying,
  onPlayToggle,
  onStop,
  onNewSession,
  audioLoading,
}) {
  return (
    <header className={styles.menubar}>
      <div className={styles.left}>
        <span className={styles.appName}>Rubato</span>
        {songName ? <span className={styles.songName}>{songName}</span> : null}
        {onNewSession ? (
          <button type="button" className={styles.newSess} onClick={onNewSession}>
            New Session
          </button>
        ) : null}
      </div>
      <div className={styles.right}>
        <div className={styles.transport}>
          <button
            type="button"
            className={styles.transportBtn}
            onClick={onPlayToggle}
            disabled={audioLoading}
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
