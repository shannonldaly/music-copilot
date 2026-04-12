import { useState } from 'react';
import styles from './SessionStartModal.module.css';

function IconPiano() {
  return (
    <svg
      className={styles.modeIcon}
      width={20}
      height={20}
      viewBox="0 0 20 20"
      aria-hidden
      focusable="false"
    >
      <g fill="currentColor">
        <rect x="1" y="7" width="5" height="11" rx="0.8" opacity={0.35} />
        <rect x="7.5" y="7" width="5" height="11" rx="0.8" opacity={0.35} />
        <rect x="14" y="7" width="5" height="11" rx="0.8" opacity={0.35} />
        <rect x="4.25" y="7" width="2.75" height="6.5" rx="0.4" />
        <rect x="10.25" y="7" width="2.75" height="6.5" rx="0.4" />
      </g>
    </svg>
  );
}

function IconDrum() {
  return (
    <svg
      width={20}
      height={20}
      viewBox="0 0 20 20"
      aria-hidden
      focusable="false"
    >
      <circle cx="10" cy="10" r="7.5" fill="var(--color-accent-primary)" />
      <circle
        cx="10"
        cy="10"
        r="4.75"
        fill="none"
        stroke="var(--color-accent-primary)"
        strokeWidth="1.35"
        strokeOpacity={0.5}
      />
    </svg>
  );
}

function IconMix() {
  return (
    <svg
      className={styles.modeIcon}
      width={20}
      height={20}
      viewBox="0 0 20 20"
      aria-hidden
      focusable="false"
    >
      <g fill="currentColor">
        <rect x="3.5" y="11" width="3.2" height="6" rx="0.5" />
        <rect x="8.4" y="4" width="3.2" height="13" rx="0.5" />
        <rect x="13.3" y="7.5" width="3.2" height="9.5" rx="0.5" />
      </g>
    </svg>
  );
}

function IconFullSession() {
  return (
    <svg
      className={styles.modeIcon}
      width={20}
      height={20}
      viewBox="0 0 20 20"
      aria-hidden
      focusable="false"
    >
      <path
        fill="currentColor"
        d="M10 1.5L12 7.5L18.5 10L12 12.5L10 18.5L8 12.5L1.5 10L8 7.5L10 1.5z"
      />
    </svg>
  );
}

const OPTIONS = [
  {
    id: 'chords',
    title: 'Chords + Melody',
    description: 'Generate a progression and melodic direction',
    icon: IconPiano,
  },
  {
    id: 'drums',
    title: 'Drum Pattern',
    description: 'Build a rhythm pattern for your track',
    icon: IconDrum,
  },
  {
    id: 'mixing',
    title: 'Sound Mixing',
    description: 'Get mixing and sound engineering guidance',
    icon: IconMix,
  },
  {
    id: 'full',
    title: 'Full Session',
    description: 'Work through all elements from scratch',
    icon: IconFullSession,
  },
];

export default function SessionStartModal({ open, selected, onSelect, onContinue, animateIn }) {
  const [tab, setTab] = useState('new');

  if (!open) return null;

  return (
    <div
      className={styles.overlay}
      role="dialog"
      aria-modal="true"
      aria-labelledby="session-modal-title"
      data-testid="session-modal"
    >
      <div className={`${styles.card} ${animateIn ? styles.cardEnter : ''}`}>
        <div className={styles.tabs}>
          <button
            type="button"
            className={`${styles.tab} ${tab === 'new' ? styles.tabActive : ''}`}
            onClick={() => setTab('new')}
          >
            New Session
          </button>
          <button
            type="button"
            className={`${styles.tab} ${tab === 'recent' ? styles.tabActive : ''}`}
            onClick={() => setTab('recent')}
          >
            Recent Sessions
          </button>
        </div>

        {tab === 'new' ? (
          <>
            <h1 id="session-modal-title" className={styles.title}>
              Start session
            </h1>
            <p className={styles.hint}>Choose how you want to work</p>
            <div className={styles.grid}>
              {OPTIONS.map((o) => {
                const Icon = o.icon;
                return (
                  <button
                    key={o.id}
                    type="button"
                    className={`${styles.option} ${selected === o.id ? styles.optionSelected : ''}`}
                    onClick={() => onSelect(o.id)}
                    data-testid={`session-mode-${o.id}`}
                  >
                    {selected === o.id ? (
                      <span className={styles.checkMark} aria-hidden>
                        <svg width={18} height={18} viewBox="0 0 24 24" fill="none">
                          <path
                            d="M20 6L9 17l-5-5"
                            stroke="currentColor"
                            strokeWidth="2.2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        </svg>
                      </span>
                    ) : null}
                    <div className={styles.titleRow}>
                      <Icon />
                      <span className={styles.optTitle}>{o.title}</span>
                    </div>
                    <span className={styles.optSub}>{o.description}</span>
                  </button>
                );
              })}
            </div>
            <button
              type="button"
              className={styles.continue}
              disabled={!selected}
              onClick={onContinue}
              data-testid="session-modal-continue"
            >
              Continue
            </button>
          </>
        ) : (
          <div className={styles.recentPane}>
            <div className={styles.emptyIcon} aria-hidden>
              <svg width={40} height={40} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2">
                <circle cx="12" cy="12" r="9" opacity={0.35} />
                <path d="M12 7v6l4 2" strokeLinecap="round" />
              </svg>
            </div>
            <p className={styles.emptyTitle}>Your recent sessions will appear here</p>
            <p className={styles.emptySub}>Sessions are saved automatically as you work</p>
          </div>
        )}
      </div>
    </div>
  );
}
