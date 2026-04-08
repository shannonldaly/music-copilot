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
      <h2 className={styles.sessionInfoTitle}>Session info</h2>
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

function StageRow({ id, label, data, onSkipClick }) {
  const { status, value } = data || { status: 'pending', value: '' };
  const showSkip = status === 'active' || status === 'pending';
  const ledClass =
    status === 'done'
      ? styles.ledDone
      : status === 'active'
        ? styles.ledActive
        : status === 'skipped'
          ? styles.ledSkip
          : styles.ledPending;
  const textClass =
    status === 'done'
      ? styles.textDone
      : status === 'active'
        ? styles.textActive
        : status === 'skipped'
          ? styles.textSkip
          : styles.textPending;

  return (
    <div className={styles.stageRow}>
      <div className={styles.stageHead}>
        <span className={ledClass} aria-hidden />
        <span className={textClass}>{label}</span>
        {showSkip ? (
          <button type="button" className={styles.skipBtn} onClick={() => onSkipClick(id)}>
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
      <div className={styles.songLabel}>Song</div>
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
          aria-label="Song name"
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

  const decided = seq.filter((id) => stages[id]?.status === 'done' && stages[id]?.confirmed);
  const review = seq.filter((id) => stages[id]?.status === 'done' && !stages[id]?.confirmed);
  const skipped = seq.filter((id) => stages[id]?.status === 'skipped');
  const inProgress = seq.find((id) => stages[id]?.status === 'active');
  const upNext = seq.filter((id) => stages[id]?.status === 'pending');

  return (
    <aside className={styles.sidebar}>
      <SongNameField sessionId={sessionId} songName={songName} onSaved={onSongNameSaved} />

      <SessionInfoBlock
        infoKey={infoKey}
        infoBpm={infoBpm}
        infoVibe={infoVibe}
        keyWasSpecified={keyWasSpecified}
      />

      <div className={styles.badge}>{MODE_BADGE_LABEL[sessionMode] || sessionMode}</div>

      <div className={styles.topBlock}>
        <div className={styles.header}>Session tracker</div>
        <p className={styles.purpose}>
          Live map of this session — see what is locked in, what you are on now, and what is next.
        </p>
      </div>

      <div className={styles.rule} />

      <div className={styles.sectionLabel}>Decided</div>
      <div className={styles.block}>
        {decided.length === 0 && skipped.length === 0 ? <div className={styles.empty}>—</div> : null}
        {decided.map((id) => (
          <StageRow
            key={id}
            id={id}
            label={STAGE_LABELS[id] || id}
            data={stages[id]}
            onSkipClick={() => {}}
          />
        ))}
        {skipped.map((id) => (
          <StageRow
            key={`sk-${id}`}
            id={id}
            label={STAGE_LABELS[id] || id}
            data={stages[id]}
            onSkipClick={() => {}}
          />
        ))}
      </div>

      <div className={styles.sectionLabel}>Review</div>
      <div className={styles.block}>
        {review.length === 0 ? <div className={styles.empty}>—</div> : null}
        {review.map((id) => (
          <StageRow
            key={`rv-${id}`}
            id={id}
            label={STAGE_LABELS[id] || id}
            data={stages[id]}
            onSkipClick={() => {}}
          />
        ))}
      </div>

      <div className={styles.sectionLabel}>In Progress</div>
      <div className={styles.block}>
        {inProgress ? (
          <StageRow
            key={inProgress}
            id={inProgress}
            label={STAGE_LABELS[inProgress] || inProgress}
            data={stages[inProgress]}
            onSkipClick={setSkipFor}
          />
        ) : (
          <div className={styles.empty}>—</div>
        )}
      </div>

      <div className={styles.sectionLabel}>Up Next</div>
      <div className={styles.block}>
        {upNext.length === 0 ? <div className={styles.empty}>—</div> : null}
        {upNext.map((id) => (
          <StageRow
            key={id}
            id={id}
            label={STAGE_LABELS[id] || id}
            data={stages[id]}
            onSkipClick={setSkipFor}
          />
        ))}
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
              Try it →
            </button>
          ) : null}
        </div>
      </div>
    </aside>
  );
}
