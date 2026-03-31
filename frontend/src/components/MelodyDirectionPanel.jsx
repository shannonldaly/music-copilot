import { useEffect, useRef } from 'react';
import styles from './MelodyDirectionPanel.module.css';

export default function MelodyDirectionPanel({ data, animateIntro, onIntroComplete }) {
  const introCallbackFiredRef = useRef(false);

  useEffect(() => {
    if (!animateIntro) {
      introCallbackFiredRef.current = false;
      return undefined;
    }
    if (introCallbackFiredRef.current) return undefined;
    introCallbackFiredRef.current = true;
    const t = window.setTimeout(() => {
      onIntroComplete?.();
    }, 650);
    return () => clearTimeout(t);
  }, [animateIntro, onIntroComplete]);

  if (!data || typeof data !== 'object') return null;

  const start = data.start_note ?? data.start_note_context;
  const startCtx = data.start_note && data.start_note_context ? data.start_note_context : null;

  const rootClass = [styles.panel, animateIntro ? styles.panelIntro : ''].filter(Boolean).join(' ');

  return (
    <div className={rootClass}>
      <div className={styles.head}>
        <span className={styles.accentBar} aria-hidden />
        <div className={styles.headText}>
          <div className={styles.kicker}>Melodic guidance</div>
          <h3 className={styles.title}>Melody direction</h3>
        </div>
      </div>

      <div className={styles.body}>
        {data.start_note ? (
          <div className={styles.row}>
            <span className={styles.k}>Start note</span>
            <span className={styles.v}>{data.start_note}</span>
            {startCtx ? <span className={styles.sub}>{startCtx}</span> : null}
          </div>
        ) : start ? (
          <div className={styles.row}>
            <span className={styles.k}>Start</span>
            <span className={styles.v}>{start}</span>
          </div>
        ) : null}
        {data.contour ? (
          <div className={styles.row}>
            <span className={styles.k}>Contour</span>
            <span className={styles.v}>{data.contour}</span>
          </div>
        ) : null}
        {data.rhythm_feel ? (
          <div className={styles.row}>
            <span className={styles.k}>Rhythm feel</span>
            <span className={styles.v}>{data.rhythm_feel}</span>
          </div>
        ) : null}
        {data.avoid_on_strong_beats != null ? (
          <div className={styles.row}>
            <span className={styles.k}>Avoid on strong beats</span>
            <span className={styles.v}>
              {Array.isArray(data.avoid_on_strong_beats)
                ? data.avoid_on_strong_beats.join(', ')
                : String(data.avoid_on_strong_beats)}
              {data.avoid_context ? ` — ${data.avoid_context}` : ''}
            </span>
          </div>
        ) : data.avoid_strong ? (
          <div className={styles.row}>
            <span className={styles.k}>Avoid on strong beats</span>
            <span className={styles.v}>{data.avoid_strong}</span>
          </div>
        ) : null}
        {data.suggested_range ? (
          <div className={styles.row}>
            <span className={styles.k}>Range</span>
            <span className={styles.v}>{data.suggested_range}</span>
          </div>
        ) : data.range ? (
          <div className={styles.row}>
            <span className={styles.k}>Range</span>
            <span className={styles.v}>{data.range}</span>
          </div>
        ) : null}
        {data.artist_reference ? (
          <div className={styles.row}>
            <span className={styles.k}>Reference</span>
            <span className={styles.v}>{data.artist_reference}</span>
          </div>
        ) : data.reference ? (
          <div className={styles.row}>
            <span className={styles.k}>Reference</span>
            <span className={styles.v}>{data.reference}</span>
          </div>
        ) : null}
      </div>
    </div>
  );
}
