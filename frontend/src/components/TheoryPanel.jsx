import { CHORD_BORDER_COLORS } from '../constants';
import { FormattedTeaching } from '../utils/markdownLite';
import AlsoTryList from './AlsoTryList';
import MelodyDirectionPanel from './MelodyDirectionPanel';
import styles from './TheoryPanel.module.css';

export default function TheoryPanel({
  sessionId,
  mode,
  chords,
  keyName,
  scale,
  progressionName,
  theoryExplanation,
  voiceLeadingNotes,
  validation,
  validationBadge,
  drumPattern,
  genreContext,
  alsoTryAlternatives,
  onAlsoTryPick,
  expandLoading,
  expandError,
  melodyDirection,
  melodyIntroActive = false,
  onMelodyIntroComplete = () => {},
}) {
  const list = (chords || []).slice(0, 8);
  const isDrums = mode === 'drums';

  return (
    <section className={styles.panel}>
      <header className={styles.header}>
        <h2 className={styles.title}>Theory + Validator</h2>
        <div className={styles.keyRow}>
          {isDrums ? (
            <>
              <span className={styles.mono}>{drumPattern?.name || progressionName || '—'}</span>
              {genreContext ? <span className={styles.dim}>· {genreContext}</span> : null}
            </>
          ) : (
            <>
              <span className={styles.mono}>{keyName || '—'}</span>
              {scale ? <span className={styles.dim}>{scale}</span> : null}
              {progressionName ? <span className={styles.dim}>· {progressionName}</span> : null}
            </>
          )}
        </div>
      </header>

      {expandError ? <div className={styles.expandErr}>{expandError}</div> : null}

      {!isDrums ? (
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
      ) : null}

      {!isDrums && (alsoTryAlternatives?.length ?? 0) > 0 ? (
        <div className={styles.alsoTryShell}>
          <AlsoTryList
            alternatives={alsoTryAlternatives}
            onPick={onAlsoTryPick}
            disabled={expandLoading}
          />
        </div>
      ) : null}

      {!isDrums && melodyDirection ? (
        <MelodyDirectionPanel
          key={sessionId ? `${sessionId}-melody` : 'melody'}
          data={melodyDirection}
          animateIntro={melodyIntroActive}
          onIntroComplete={onMelodyIntroComplete}
        />
      ) : null}

      <div className={styles.block}>
        <div className={styles.blockTitle}>{isDrums ? 'Pattern notes' : 'Theory'}</div>
        <FormattedTeaching className={styles.prose}>{theoryExplanation || '—'}</FormattedTeaching>
      </div>

      {!isDrums ? (
        <div className={styles.block}>
          <div className={styles.blockTitle}>Voice leading</div>
          <p className={styles.body}>{voiceLeadingNotes || '—'}</p>
        </div>
      ) : null}

      <div className={styles.badgeRow}>
        <span className={styles.badge}>music21</span>
        {validationBadge === 'na_drums' ? (
          <span className={styles.neutral}>N/A — drum pattern</span>
        ) : validation ? (
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
