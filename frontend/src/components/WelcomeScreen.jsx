import styles from './WelcomeScreen.module.css';

export default function WelcomeScreen({ visible, exiting, onStart }) {
  if (!visible && !exiting) return null;

  return (
    <div
      className={`${styles.root} ${exiting ? styles.exiting : ''}`}
      role="dialog"
      aria-modal="true"
      aria-labelledby="welcome-title"
    >
      <div className={styles.inner}>
        <svg
          className={styles.noteIcon}
          width={32}
          height={32}
          viewBox="0 0 32 32"
          aria-hidden="true"
          focusable="false"
        >
          <g fill="currentColor">
            <path d="M9 4.5H24.5V9H9V4.5z" />
            <path d="M11.2 9h2.6v14.5h-2.6V9z" />
            <path d="M22.2 9h2.6v14.5h-2.6V9z" />
            <path
              transform="rotate(-22 8 25)"
              d="M13.2 25A5.2 3.6 0 1 1 2.8 25A5.2 3.6 0 1 1 13.2 25z"
            />
            <path
              transform="rotate(-22 19.5 25)"
              d="M24.7 25A5.2 3.6 0 1 1 14.3 25A5.2 3.6 0 1 1 24.7 25z"
            />
          </g>
        </svg>
        <h1 id="welcome-title" className={styles.wordmark}>
          Rubato
        </h1>
        <p className={styles.tagline}>Builds the blueprint. You build the track.</p>
        <button type="button" className={styles.startBtn} onClick={onStart}>
          Start a session
        </button>
      </div>
    </div>
  );
}
