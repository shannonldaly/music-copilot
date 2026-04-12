import { useEffect, useRef, useState } from 'react';
import { patchSession } from '../utils/api';
import {
  MODE_BADGE_LABEL,
  STAGE_LABELS,
  STAGE_SEQUENCES,
} from '../sessionStages';
import styles from './ProgressSidebar.module.css';

const DEFAULT_SONG = 'Untitled Session';

function SessionInfoBlock({ infoKey, infoBpm, infoVibe, keyWasSpecified }) {
  const bpmText = infoBpm != null && infoBpm !== '' ? `${infoBpm} BPM` : '—';
  const vibeText = infoVibe != null && String(infoVibe).trim() !== '' ? String(infoVibe) : '—';

  return (
    <div className={styles.sessionInfo}>
      <div className={styles.sessionRow}>
        <div className={styles.sessionMetaLabel}>Key</div>
        {infoKey != null && String(infoKey).trim() !== '' ? (
          <div className={keyWasSpecified ? styles.sessionMetaValue : styles.sessionMetaValueMuted}>
            {keyWasSpecified ? infoKey : `${infoKey} (suggested)`}
          </div>
        ) : (
          <div className={styles.sessionMetaValue}>—</div>
        )}
      </div>
      <div className={styles.sessionRow}>
        <div className={styles.sessionMetaLabel}>BPM</div>
        <div className={styles.sessionMetaValue}>{bpmText}</div>
      </div>
      <div className={styles.sessionRow}>
        <div className={styles.sessionMetaLabel}>Vibe</div>
        <div className={styles.sessionMetaValue}>{vibeText}</div>
      </div>
    </div>
  );
}

function StageRow({
  id,
  label,
  data,
  onSkipClick,
  isActive,
  confirmFlash,
  historyClickable,
  onConfirmedStageClick,
}) {
  const { status, value } = data || { status: 'pending', value: '' };
  const showSkip = status === 'active' || status === 'pending';
  const doneConfirmed = status === 'done' && data?.confirmed;
  const doneReview = status === 'done' && !data?.confirmed;
  const rowNavigable = !!(doneConfirmed && historyClickable && onConfirmedStageClick);

  const rowClass = [
    styles.stageRow,
    isActive ? styles.stageRowActive : '',
    confirmFlash ? styles.stageRowConfirmFlash : '',
    rowNavigable ? styles.stageRowNavigable : '',
  ]
    .filter(Boolean)
    .join(' ');

  const handleRowKeyDown = (e) => {
    if (!rowNavigable) return;
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onConfirmedStageClick(id);
    }
  };

  return (
    <div
      className={rowClass}
      role={rowNavigable ? 'button' : undefined}
      tabIndex={rowNavigable ? 0 : undefined}
      onClick={rowNavigable ? () => onConfirmedStageClick(id) : undefined}
      onKeyDown={rowNavigable ? handleRowKeyDown : undefined}
      data-testid={`stage-row-${id}`}
    >
      <div className={styles.stageHead}>
        {doneConfirmed ? (
          <span className={styles.ledDone} aria-hidden>
            <svg width={12} height={12} viewBox="0 0 24 24" fill="none">
              <path
                d="M20 6L9 17l-5-5"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </span>
        ) : doneReview ? (
          <span className={styles.ledReview} aria-hidden />
        ) : status === 'skipped' ? (
          <span className={styles.ledSkip} aria-hidden />
        ) : isActive ? (
          <span className={styles.ledActive} aria-hidden />
        ) : (
          <span className={styles.ledPending} aria-hidden />
        )}
        <span
          className={
            doneConfirmed
              ? styles.textDone
              : isActive
                ? styles.textActive
                : status === 'skipped'
                  ? styles.textSkip
                  : styles.textPending
          }
        >
          {label}
        </span>
        {showSkip ? (
          <button
            type="button"
            className={styles.skipBtn}
            onClick={(e) => {
              e.stopPropagation();
              onSkipClick(id);
            }}
          >
            Skip
          </button>
        ) : (
          <span className={styles.skipSpacer} />
        )}
      </div>
      {status === 'done' && value ? <div className={styles.stageVal}>{value}</div> : null}
      {status === 'active' && !value ? (
        <div className={styles.stageValMuted}>Not started</div>
      ) : null}
      {status === 'skipped' ? (
        <div className={styles.stageValSkip}>{value}</div>
      ) : null}
    </div>
  );
}

function SongNameField({ sessionId, songName, onSaved }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(songName);
  const [saving, setSaving] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => {
    if (!editing) setDraft(songName);
  }, [songName, editing]);

  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editing]);

  const commit = async () => {
    const next = draft.trim() || DEFAULT_SONG;
    setEditing(false);
    if (next === songName) return;
    setSaving(true);
    try {
      await patchSession(sessionId, { song_name: next });
      onSaved(next);
    } catch {
      setDraft(songName);
    } finally {
      setSaving(false);
    }
  };

  const cancel = () => {
    setDraft(songName);
    setEditing(false);
  };

  return (
    <div className={styles.songBlock}>
      {editing ? (
        <input
          ref={inputRef}
          className={styles.songInput}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={() => commit()}
          onKeyDown={(e) => {
            if (e.key === 'Enter') commit();
            if (e.key === 'Escape') cancel();
          }}
          disabled={saving}
          aria-label="Session name"
        />
      ) : (
        <button
          type="button"
          className={styles.songDisplay}
          onClick={() => setEditing(true)}
          title="Click to rename"
        >
          {songName || DEFAULT_SONG}
        </button>
      )}
    </div>
  );
}

export default function ProgressSidebar({
  sessionId,
  songName,
  onSongNameSaved,
  sessionMode,
  infoKey,
  infoBpm,
  infoVibe,
  keyWasSpecified,
  stages,
  suggestedText,
  suggestedPrefill,
  awaitingConfirmation,
  onSuggestedTry,
  onSkipConfirm,
  justConfirmedStageId,
  hasStageSnapshot,
  onConfirmedStageClick,
}) {
  const [skipFor, setSkipFor] = useState(null);
  const [skipNote, setSkipNote] = useState('');

  const seq = STAGE_SEQUENCES[sessionMode] || STAGE_SEQUENCES.chords;

  const handleSkipSubmit = (e) => {
    e.preventDefault();
    if (!skipFor) return;
    onSkipConfirm(skipFor, skipNote);
    setSkipFor(null);
    setSkipNote('');
  };

  const inProgress = seq.find((id) => stages[id]?.status === 'active');

  return (
    <aside className={styles.sidebar} data-testid="progress-sidebar">
      <SongNameField sessionId={sessionId} songName={songName} onSaved={onSongNameSaved} />

      <div className={styles.modePill}>{MODE_BADGE_LABEL[sessionMode] || sessionMode}</div>

      <SessionInfoBlock
        infoKey={infoKey}
        infoBpm={infoBpm}
        infoVibe={infoVibe}
        keyWasSpecified={keyWasSpecified}
      />

      <div className={styles.sectionLabel}>Stages</div>

      <div className={styles.block}>
        {seq.every((id) => {
          const s = stages[id];
          return !s || (s.status === 'pending' && !s.value);
        }) ? (
          <div className={styles.empty}>No steps yet</div>
        ) : null}
        {seq.map((id) => {
          const s = stages[id];
          if (!s) return null;
          const showSkip = s.status === 'active' || s.status === 'pending';
          return (
            <StageRow
              key={id}
              id={id}
              label={STAGE_LABELS[id] || id}
              data={s}
              onSkipClick={showSkip ? setSkipFor : () => {}}
              isActive={id === inProgress}
              confirmFlash={justConfirmedStageId === id}
              historyClickable={hasStageSnapshot?.(id)}
              onConfirmedStageClick={onConfirmedStageClick}
            />
          );
        })}
      </div>

      {skipFor ? (
        <form className={styles.skipForm} onSubmit={handleSkipSubmit}>
          <div className={styles.skipFormLabel}>Already have this?</div>
          <input
            className={styles.skipInput}
            placeholder="Describe it or leave blank"
            value={skipNote}
            onChange={(e) => setSkipNote(e.target.value)}
          />
          <div className={styles.skipActions}>
            <button type="submit" className={styles.skipOk}>
              Confirm
            </button>
            <button type="button" className={styles.skipCancel} onClick={() => setSkipFor(null)}>
              Cancel
            </button>
          </div>
        </form>
      ) : null}

      <div className={styles.rule} />

      <div className={styles.suggested}>
        <div
          className={`${styles.suggestedInner} ${awaitingConfirmation ? styles.suggestedInnerConfirm : ''}`}
        >
          <div className={styles.suggestedLabel}>Suggested next</div>
          {awaitingConfirmation ? (
            <div className={styles.keepHint}>Keep →</div>
          ) : null}
          <div className={styles.suggestedText}>{suggestedText || 'Generate to see the next step.'}</div>
          {suggestedText && suggestedPrefill?.trim() ? (
            <button type="button" className={styles.suggestedBtn} onClick={onSuggestedTry}>
              Try it
            </button>
          ) : null}
        </div>
      </div>
    </aside>
  );
}
