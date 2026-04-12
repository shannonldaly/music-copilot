import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import AlsoTryList from './AlsoTryList';
import ChordCard from './ChordCard';
import MelodyDirectionPanel from './MelodyDirectionPanel';
import { FormattedTeaching } from '../utils/markdownLite';
import { extractNumberedSteps } from '../utils/normalize';
import { buildDrumRows } from '../utils/drums';
import { sendProgressionToAbleton } from '../utils/api';
import styles from './MainWorkspace.module.css';

const EXAMPLE_PROMPTS = ['melancholic lo-fi', 'something like Massive Attack', 'uplifting in D major'];

function fallbackLines(text) {
  if (!text) return [];
  return text
    .split('\n')
    .map((l) => l.trim())
    .filter((l) => l && !l.startsWith('#') && !l.startsWith('**'));
}

/** Split validator-style voice leading copy on "between chords" into display bullets. */
function voiceLeadingBulletLines(text) {
  const s = String(text || '').trim();
  if (!s || s === '—') return [];
  const parts = s.split(/between chords/gi);
  const lines = [];
  if (parts[0]?.trim()) {
    lines.push(`• ${parts[0].trim()}`);
  }
  for (let i = 1; i < parts.length; i++) {
    const seg = parts[i].trim();
    if (seg) lines.push(`• between chords ${seg}`);
  }
  return lines.length ? lines : [`• ${s}`];
}

function buildProgressionPayload(chordList, m) {
  return {
    key: m?.key,
    progression_name: m?.progression_name,
    chords: chordList.map((c) => ({
      name: c.name,
      numeral: c.numeral,
      note_names: c.notes || c.note_names || [],
    })),
  };
}

function parseSendToAbletonError(e) {
  const d = e?.response?.data?.detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d)) return d.map((x) => (typeof x === 'object' && x?.msg ? x.msg : String(x))).join(', ');
  if (d && typeof d === 'object') return JSON.stringify(d);
  return e?.message || 'Request failed';
}

function AbletonMarkIcon() {
  return (
    <svg className={styles.sendAbletonIcon} width={14} height={14} viewBox="0 0 14 14" aria-hidden>
      <circle cx="5.25" cy="7" r="3.25" fill="currentColor" />
      <circle cx="8.75" cy="7" r="3.25" fill="currentColor" />
    </svg>
  );
}

function SendOkCheckIcon() {
  return (
    <svg className={styles.sendAbletonCheck} width={14} height={14} viewBox="0 0 14 14" aria-hidden>
      <path
        d="M3 7.2 L6.2 10.2 L11.2 4.2"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function MainWorkspace({
  sessionId,
  sessionMode,
  modeLabel,
  suggestedText,
  onExamplePrompt,
  hasContentGeneration,
  chords,
  model,
  alternatives,
  onAlsoTryPick,
  expandLoading,
  expandError,
  melodyIntroActive,
  onMelodyIntroComplete,
  keepChordFlash,
  historyStageId,
  historyStageLabel,
  onExitHistory,
}) {
  const [abletonOpen, setAbletonOpen] = useState(false);
  const [abletonSendUi, setAbletonSendUi] = useState('idle');
  const [abletonSendErr, setAbletonSendErr] = useState(null);
  const abletonTimersRef = useRef([]);

  const clearAbletonTimers = () => {
    abletonTimersRef.current.forEach(clearTimeout);
    abletonTimersRef.current = [];
  };

  useEffect(() => () => clearAbletonTimers(), []);

  const isDrums = model?.mode === 'drums';
  const drumGrid = model?.drumPattern?.grid;
  const { rows: drumRows, stepIndices } = useMemo(
    () => (isDrums && drumGrid ? buildDrumRows(drumGrid) : { rows: [], stepIndices: [] }),
    [isDrums, drumGrid]
  );

  const productionMarkdown = model?.production_steps;
  const numberedSteps = useMemo(() => {
    const numbered = extractNumberedSteps(productionMarkdown || '');
    if (numbered.length) return numbered;
    return fallbackLines(productionMarkdown).map((t, i) => ({ n: i + 1, text: t }));
  }, [productionMarkdown]);

  const teachingNote = model?.teaching_note;
  const theoryExplanation = model?.theory_explanation;
  const voiceLeadingNotes = model?.voice_leading_notes;
  const melodyDirection = model?.melody_direction;
  const validation = model?.validation;
  const validationBadge = model?.validationBadge;

  const list = (chords || []).slice(0, 8);
  const showChordRow = !isDrums && list.length > 0;
  const showDrumGrid = isDrums && drumRows.length > 0;
  const showAlsoTry = !isDrums && (alternatives?.length ?? 0) > 0;
  const showMelody = !isDrums && melodyDirection && typeof melodyDirection === 'object';
  const hasTheoryText = theoryExplanation && String(theoryExplanation).trim() && String(theoryExplanation).trim() !== '—';
  const hasVoiceText =
    !isDrums && voiceLeadingNotes && String(voiceLeadingNotes).trim() && String(voiceLeadingNotes).trim() !== '—';
  const voiceBullets = useMemo(
    () => (hasVoiceText ? voiceLeadingBulletLines(voiceLeadingNotes) : []),
    [hasVoiceText, voiceLeadingNotes]
  );
  const hasTeachingText = teachingNote && String(teachingNote).trim() && String(teachingNote).trim() !== '—';
  const hasAbletonSteps = numberedSteps.length > 0;
  const hasProductionMarkdown = !!(productionMarkdown && String(productionMarkdown).trim());

  const handleSendToAbleton = useCallback(async () => {
    clearAbletonTimers();
    setAbletonSendErr(null);
    setAbletonSendUi('sending');
    const bpmRaw = Number(model?.bpm);
    const bpm = Number.isFinite(bpmRaw) && bpmRaw > 0 ? Math.round(bpmRaw) : 120;
    const progression = buildProgressionPayload(list, model);
    try {
      const data = await sendProgressionToAbleton({ progression, bpm });
      if (!data?.success) {
        const msg = data?.message || 'Could not send to Ableton';
        setAbletonSendErr(msg);
        abletonTimersRef.current.push(
          window.setTimeout(() => setAbletonSendErr(null), 3000)
        );
        setAbletonSendUi('idle');
        return;
      }
      setAbletonSendUi('flash');
      abletonTimersRef.current.push(
        window.setTimeout(() => {
          setAbletonSendUi('sent');
          abletonTimersRef.current.push(
            window.setTimeout(() => setAbletonSendUi('idle'), 2000)
          );
        }, 350)
      );
    } catch (e) {
      setAbletonSendErr(parseSendToAbletonError(e));
      abletonTimersRef.current.push(window.setTimeout(() => setAbletonSendErr(null), 3000));
      setAbletonSendUi('idle');
    }
  }, [list, model]);

  if (!hasContentGeneration) {
    return (
      <div className={styles.emptyRoot}>
        <p className={styles.modeTag}>{modeLabel || sessionMode || 'SESSION'}</p>
        <p className={styles.guidance}>{suggestedText}</p>
        <div className={styles.pills}>
          {EXAMPLE_PROMPTS.map((p) => (
            <button key={p} type="button" className={styles.pill} onClick={() => onExamplePrompt(p)}>
              {p}
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className={styles.contentRoot}>
      {historyStageId && historyStageLabel ? (
        <div className={styles.historyBanner}>
          <p className={styles.historyBannerText}>
            Viewing saved <strong>{historyStageLabel}</strong> — Keep to return to the current step, or Try Again /
            Vary to revise.
          </p>
          <button type="button" className={styles.historyExit} onClick={onExitHistory}>
            Back to current
          </button>
        </div>
      ) : null}
      {expandError ? <div className={styles.expandErr}>{expandError}</div> : null}

      {showChordRow ? (
        <>
          <div className={styles.chordRow} data-testid="chord-row">
            {list.map((c, i) => (
              <ChordCard
                key={`${c.name}-${i}`}
                name={c.name}
                numeral={c.numeral}
                notes={c.notes || c.note_names || []}
                keepFlash={keepChordFlash}
              />
            ))}
          </div>
          {expandLoading ? <p className={styles.expandLoading}>Updating notes…</p> : null}
          <div className={styles.validationRow}>
            <span className={styles.badge} data-testid="validation-badge">
              music21
            </span>
            {validationBadge === 'na_drums' ? (
              <span className={styles.neutral}>N/A — drum pattern</span>
            ) : validation ? (
              <span className={validation.passed ? styles.ok : styles.fail}>
                {validation.passed ? 'passed' : 'failed'}
              </span>
            ) : (
              <span className={styles.neutral}>—</span>
            )}
          </div>
          <div className={styles.sendAbletonWrap}>
            <button
              type="button"
              className={`${styles.sendAbletonBtn} ${abletonSendUi === 'flash' ? styles.sendAbletonBtnFlash : ''}`}
              disabled={abletonSendUi === 'sending' || abletonSendUi === 'flash' || abletonSendUi === 'sent'}
              onClick={handleSendToAbleton}
              aria-label={
                abletonSendUi === 'sending'
                  ? 'Sending to Ableton'
                  : abletonSendUi === 'flash'
                    ? 'Sent to Ableton'
                    : abletonSendUi === 'sent'
                      ? 'Sent to Ableton'
                      : 'Send progression to Ableton'
              }
            >
              {abletonSendUi === 'flash' ? (
                <SendOkCheckIcon />
              ) : abletonSendUi === 'sent' ? null : (
                <AbletonMarkIcon />
              )}
              {abletonSendUi === 'sending'
                ? 'Sending...'
                : abletonSendUi === 'flash'
                  ? ''
                  : abletonSendUi === 'sent'
                    ? 'Sent to Ableton ✓'
                    : 'Send to Ableton'}
            </button>
            {abletonSendErr ? <p className={styles.sendAbletonErr}>{abletonSendErr}</p> : null}
          </div>
        </>
      ) : null}

      {showDrumGrid ? (
        <>
          <div className={styles.drumBlock} data-testid="drum-grid-block">
            <div className={styles.drumSection}>
              <div className={styles.stepHeader}>
                <span className={styles.stepCorner} aria-hidden />
                {stepIndices.map((s) => (
                  <span key={s} className={styles.stepIdx}>
                    {s + 1}
                  </span>
                ))}
              </div>
              {drumRows.map((row) => (
                <div key={row.id} className={styles.drumRow}>
                  <span className={styles.drumLabel}>{row.label}</span>
                  <div className={styles.drumSteps}>
                    {stepIndices.map((step) => (
                      <div
                        key={step}
                        className={styles.drumCell}
                        style={{
                          background: row.steps.has(step) ? row.color : '#242820',
                          borderColor: row.steps.has(step) ? row.color : 'rgba(240, 237, 232, 0.08)',
                        }}
                        title={`${row.label} step ${step + 1}`}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className={styles.validationRow}>
            <span className={styles.badge}>music21</span>
            {validationBadge === 'na_drums' ? (
              <span className={styles.neutral}>N/A — drum pattern</span>
            ) : validation ? (
              <span className={validation.passed ? styles.ok : styles.fail}>
                {validation.passed ? 'passed' : 'failed'}
              </span>
            ) : (
              <span className={styles.neutral}>—</span>
            )}
          </div>
        </>
      ) : isDrums ? (
        <div className={styles.validationRow}>
          <span className={styles.badge}>music21</span>
          {validationBadge === 'na_drums' ? (
            <span className={styles.neutral}>N/A — drum pattern</span>
          ) : validation ? (
            <span className={validation.passed ? styles.ok : styles.fail}>
              {validation.passed ? 'passed' : 'failed'}
            </span>
          ) : (
            <span className={styles.neutral}>—</span>
          )}
        </div>
      ) : null}

      {showAlsoTry ? (
        <div className={styles.alsoTryWrap} data-testid="also-try-section">
          <AlsoTryList
            alternatives={alternatives}
            onPick={(alt) => onAlsoTryPick(alt)}
            disabled={expandLoading}
          />
        </div>
      ) : null}

      {showMelody ? (
        <div data-testid="melody-direction-panel">
          <MelodyDirectionPanel
            key={sessionId ? `${sessionId}-melody` : 'melody'}
            data={melodyDirection}
            animateIntro={melodyIntroActive}
            onIntroComplete={onMelodyIntroComplete}
          />
        </div>
      ) : null}

      {hasTheoryText ? (
        <div className={styles.proseBlock}>
          <div className={styles.proseLabel}>{isDrums ? 'Pattern notes' : 'Theory'}</div>
          <FormattedTeaching className={styles.prose}>{theoryExplanation}</FormattedTeaching>
        </div>
      ) : null}

      {hasVoiceText ? (
        <div className={styles.proseBlock}>
          <div className={styles.proseLabel}>Voice leading</div>
          <ul className={styles.voiceBulletList}>
            {voiceBullets.map((line, i) => (
              <li key={`vl-${i}`} className={styles.voiceBullet}>
                {line}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {hasTeachingText ? (
        <div className={styles.teachPanel} data-testid="teaching-note-section">
          <FormattedTeaching className={styles.teachBody}>{teachingNote}</FormattedTeaching>
        </div>
      ) : null}

      {hasAbletonSteps || hasProductionMarkdown ? (
        <div className={styles.abletonShell} data-testid="ableton-steps-section">
          <button
            type="button"
            className={styles.abletonToggle}
            onClick={() => setAbletonOpen((o) => !o)}
            aria-expanded={abletonOpen}
          >
            <span>{abletonOpen ? 'Hide Ableton steps' : 'Show Ableton steps'}</span>
            <span className={styles.abletonChevron} aria-hidden>
              {abletonOpen ? '▲' : '▼'}
            </span>
          </button>
          {abletonOpen ? (
            <div className={styles.abletonBody}>
              {hasAbletonSteps ? (
                <ol className={styles.steps}>
                  {numberedSteps.map((step) => (
                    <li key={step.n} className={styles.step}>
                      <span className={styles.stepNum}>{step.n}</span>
                      <span className={styles.stepText}>{step.text}</span>
                    </li>
                  ))}
                </ol>
              ) : (
                <p className={styles.stepsEmpty}>No steps yet.</p>
              )}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
