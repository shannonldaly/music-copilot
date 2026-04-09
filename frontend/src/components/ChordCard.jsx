import { useMemo } from 'react';
import styles from './ChordCard.module.css';

const PC_MAP = {
  C: 0,
  'C#': 1,
  Db: 1,
  D: 2,
  'D#': 3,
  Eb: 3,
  E: 4,
  F: 5,
  'F#': 6,
  Gb: 6,
  G: 7,
  'G#': 8,
  Ab: 8,
  A: 9,
  'A#': 10,
  Bb: 10,
  B: 11,
};

function parsePitchClass(noteStr) {
  if (!noteStr || typeof noteStr !== 'string') return null;
  const s = noteStr.trim();
  const m = s.match(/^([A-Ga-g])([#b]?)/);
  if (!m) return null;
  const letter = m[1].toUpperCase();
  const acc = m[2] === 'b' ? 'b' : m[2] === '#' ? '#' : '';
  const key = acc ? `${letter}${acc}` : letter;
  return PC_MAP[key] ?? PC_MAP[letter] ?? null;
}

/** One octave on piano: C..B as white keys 0..6; black keys at semitone positions. */
const WHITE_PCS = [0, 2, 4, 5, 7, 9, 11];
const BLACK_PCS = [1, 3, 6, 8, 10];

function chordPitchClasses(notes) {
  const set = new Set();
  for (const n of notes || []) {
    const pc = parsePitchClass(n);
    if (pc != null) set.add(pc);
  }
  return set;
}

export function chordQualityLabel(name) {
  const n = (name || '').trim();
  if (!n) return '—';
  if (/dim|°|ø/i.test(n)) return 'dim';
  if (/aug|\+/i.test(n)) return 'aug';
  if (/maj7|M7|Δ7/i.test(n)) return 'maj7';
  if (/m(?!aj)|min/i.test(n)) return 'minor';
  if (/sus|add|[79]|11|13/i.test(n)) return 'ext';
  return 'major';
}

const W = 120;
const H = 60;
const NW = 7;
const whiteW = W / NW;
const blackW = whiteW * 0.55;
const blackH = H * 0.58;

function MiniPiano({ highlightedPCs }) {
  const whiteKeys = useMemo(() => {
    return WHITE_PCS.map((pc, i) => {
      const x = i * whiteW;
      const fill = highlightedPCs.has(pc) ? 'var(--color-accent-primary)' : 'var(--color-bg-hover)';
      return (
        <rect
          key={`w-${pc}`}
          x={x + 0.5}
          y={0.5}
          width={whiteW - 1}
          height={H - 1}
          rx={3}
          ry={3}
          fill={fill}
          stroke="var(--color-border-medium)"
          strokeWidth={1}
        />
      );
    });
  }, [highlightedPCs]);

  const blackKeys = useMemo(() => {
    const positions = [
      { pc: 1, cx: whiteW - blackW * 0.45 },
      { pc: 3, cx: 2 * whiteW - blackW * 0.45 },
      { pc: 6, cx: 4 * whiteW - blackW * 0.45 },
      { pc: 8, cx: 5 * whiteW - blackW * 0.45 },
      { pc: 10, cx: 6 * whiteW - blackW * 0.45 },
    ];
    return positions.map(({ pc, cx }) => {
      const fill = highlightedPCs.has(pc) ? 'var(--color-accent-primary)' : '#0d0f0e';
      return (
        <rect
          key={`b-${pc}`}
          x={cx}
          y={0.5}
          width={blackW}
          height={blackH}
          rx={2}
          ry={2}
          fill={fill}
          stroke="rgba(0,0,0,0.4)"
          strokeWidth={0.5}
        />
      );
    });
  }, [highlightedPCs]);

  return (
    <svg
      className={styles.piano}
      viewBox={`0 0 ${W} ${H}`}
      width={W}
      height={H}
      aria-hidden
    >
      <g>{whiteKeys}</g>
      <g>{blackKeys}</g>
    </svg>
  );
}

export default function ChordCard({ name, numeral, notes, keepFlash }) {
  const quality = chordQualityLabel(name);
  const pcs = useMemo(() => chordPitchClasses(notes), [notes]);

  return (
    <div className={`${styles.card} ${keepFlash ? styles.keepFlash : ''}`}>
      <div className={styles.cardInner}>
        <div className={styles.chordName}>{name || '—'}</div>
        <div className={styles.numeral}>{numeral || '—'}</div>
        <span className={styles.badge}>{quality}</span>
        <div className={styles.keyboardHint} aria-hidden>
          <span className={styles.hoverPlayLabel}>hover to play</span>
          <svg width={16} height={16} viewBox="0 0 16 16" fill="none">
            <path
              d="M2 12V4h2v8H2zm3 0V7h2v5H5zm3 0V4h2v8H8zm3 0V7h2v5h-2zm3 0V4h2v8h-2z"
              fill="currentColor"
            />
          </svg>
        </div>
        {keepFlash ? (
          <div className={styles.keepCheck} aria-hidden>
            <svg width={22} height={22} viewBox="0 0 24 24" fill="none">
              <path
                d="M20 6L9 17l-5-5"
                stroke="var(--color-accent-primary)"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
        ) : null}
      </div>
      <div className={styles.hoverLayer}>
        <MiniPiano highlightedPCs={pcs} />
      </div>
    </div>
  );
}
