import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AGENTS } from './constants';
import {
  createSession,
  expandProgression,
  generatePrompt,
  generatePromptStreaming,
  postFeedback,
} from './utils/api';
import { normalizeGenerateResponse } from './utils/normalize';
import { playProgression, playDrumPattern, stopPlayback } from './utils/playback';
import {
  CHORDS_SESSION_START_SUGGESTED_TEXT,
  MODE_BADGE_LABEL,
  STAGE_LABELS,
  STAGE_SEQUENCES,
  allStagesComplete,
  applyApiToStages,
  buildContextPrefix,
  confirmFirstAwaitingStage,
  createInitialStages,
  firstAwaitingConfirmStage,
  getConfirmSuggestion,
  getPostKeepWorkOnHeadline,
  getSuggestionForStage,
  reopenStageForRevision,
  nextSuggestedStage,
  recomputeActive,
  regenResetFromFirstAwaiting,
  skipStage,
} from './sessionStages';
import TopBar from './components/TopBar';
import AgentBar from './components/AgentBar';
import MainWorkspace from './components/MainWorkspace';
import SoundEngineeringPanel from './components/SoundEngineeringPanel';
import ArtistBlendPanel from './components/ArtistBlendPanel';
import InputBar from './components/InputBar';
import SessionStartModal from './components/SessionStartModal';
import ProgressSidebar from './components/ProgressSidebar';
import WelcomeScreen from './components/WelcomeScreen';
import styles from './App.module.css';

function initialAgentStates() {
  return Object.fromEntries(AGENTS.map((a) => [a.id, 'idle']));
}

function mapStreamAgent(name) {
  if (!name) return null;
  const n = String(name).toLowerCase();
  if (n.includes('orchestr')) return 'orchestrator';
  if (n.includes('theory') && !n.includes('valid')) return 'theory';
  if (n.includes('valid')) return 'validator';
  if (n.includes('production')) return 'production';
  if (n.includes('teach')) return 'teaching';
  if (n.includes('sound') || n.includes('eng')) return 'sound_eng';
  const aliases = { 'sound-engineering': 'sound_eng', sound_engineering: 'sound_eng' };
  return aliases[n] || name;
}

function slimPrimaryFromModel(m) {
  return {
    label: 'previous',
    progression_name: m?.progression_name || '',
    chords: (m?.chords || []).map((c) => ({
      name: c.name,
      numeral: c.numeral || '',
    })),
    character: '',
  };
}

function chordNamesFromAlt(alt) {
  return (alt.chords || []).map((c) => (typeof c === 'string' ? c : c.name)).filter(Boolean);
}

function personalizeSuggestion(text, model) {
  if (!text) return text;
  return text
    .replace(/\{key\}/g, model?.key || 'your key')
    .replace(/\{progression\}/g, model?.progression_name || 'this progression');
}

export default function App() {
  const [showWelcome, setShowWelcome] = useState(true);
  const [welcomeExiting, setWelcomeExiting] = useState(false);
  const [showSessionModal, setShowSessionModal] = useState(false);
  const [modalEnterAnim, setModalEnterAnim] = useState(false);
  const [pendingMode, setPendingMode] = useState(null);
  const [sessionMode, setSessionMode] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [songName, setSongName] = useState('Untitled Session');
  const [stages, setStages] = useState(null);
  const [melodyIntroActive, setMelodyIntroActive] = useState(false);
  const sessionMelodyIntroUsedRef = useRef(false);
  const [hasContentGeneration, setHasContentGeneration] = useState(false);

  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [model, setModel] = useState(null);
  const [alternatives, setAlternatives] = useState([]);
  const [bpm, setBpm] = useState(85);
  const [tokenCostUsd, setTokenCostUsd] = useState(0);
  const [cpuPercent, setCpuPercent] = useState(14);

  const [expandLoading, setExpandLoading] = useState(false);
  const [expandError, setExpandError] = useState(null);

  const [agentStates, setAgentStates] = useState(initialAgentStates);
  const streamSimOffRef = useRef(false);
  const playTimerRef = useRef(null);

  const [isPlaying, setIsPlaying] = useState(false);

  const [postKeepFocus, setPostKeepFocus] = useState(null);
  const [workspaceFadeKeep, setWorkspaceFadeKeep] = useState(false);
  const [keepChordFlash, setKeepChordFlash] = useState(false);
  const [justConfirmedStageId, setJustConfirmedStageId] = useState(null);
  const [historyStageId, setHistoryStageId] = useState(null);
  const [stageSnapshots, setStageSnapshots] = useState({});

  const seq = STAGE_SEQUENCES[sessionMode] || STAGE_SEQUENCES.chords;

  useEffect(() => {
    if (!showSessionModal) return undefined;
    setModalEnterAnim(true);
    const id = setTimeout(() => setModalEnterAnim(false), 450);
    return () => clearTimeout(id);
  }, [showSessionModal]);

  useEffect(() => {
    sessionMelodyIntroUsedRef.current = false;
    setMelodyIntroActive(false);
  }, [sessionId]);

  useEffect(() => {
    if (!model?.melody_direction || sessionMelodyIntroUsedRef.current) return;
    sessionMelodyIntroUsedRef.current = true;
    setMelodyIntroActive(true);
  }, [model?.melody_direction]);

  const handleMelodyIntroComplete = useCallback(() => {
    setMelodyIntroActive(false);
  }, []);

  useEffect(() => {
    const id = setInterval(() => {
      setCpuPercent(10 + Math.floor(Math.random() * 22));
    }, 1800);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    if (!loading) return undefined;
    streamSimOffRef.current = false;
    const order = AGENTS.map((a) => a.id);
    let step = 0;
    const tick = () => {
      if (streamSimOffRef.current) return;
      setAgentStates(() => {
        const next = {};
        order.forEach((id, i) => {
          if (i < step) next[id] = 'done';
          else if (i === step) next[id] = 'firing';
          else next[id] = 'idle';
        });
        return next;
      });
      step += 1;
      if (step >= order.length) step = order.length - 1;
    };
    tick();
    const interval = setInterval(tick, 220);
    return () => clearInterval(interval);
  }, [loading]);

  const finalizeAgentsDone = useCallback(() => {
    setAgentStates(Object.fromEntries(AGENTS.map((a) => [a.id, 'done'])));
  }, []);

  const applyStreamAgent = useCallback((obj) => {
    streamSimOffRef.current = true;
    const raw = obj.agent ?? obj.name ?? obj.id;
    const id = mapStreamAgent(raw) || raw;
    const st = (obj.state || obj.status || '').toLowerCase();
    if (!id || !AGENTS.some((a) => a.id === id)) return;
    setAgentStates((prev) => {
      const next = { ...prev };
      if (st === 'firing' || st === 'active' || st === 'running') next[id] = 'firing';
      else if (st === 'done' || st === 'complete' || st === 'finished') next[id] = 'done';
      else if (st === 'idle') next[id] = 'idle';
      return next;
    });
  }, []);

  const handleWelcomeStart = () => {
    setWelcomeExiting(true);
    setTimeout(() => {
      setShowWelcome(false);
      setWelcomeExiting(false);
      setShowSessionModal(true);
    }, 400);
  };

  const handleModalContinue = async () => {
    if (!pendingMode) return;
    try {
      const data = await createSession({ session_mode: pendingMode });
      setSessionId(data.session_id);
      setSessionMode(data.session_mode || pendingMode);
      const nm = data.current_project?.name?.trim();
      setSongName(nm || 'Untitled Session');
      setStages(createInitialStages(data.session_mode || pendingMode));
      setHasContentGeneration(false);
      setHistoryStageId(null);
      setStageSnapshots({});
      setShowSessionModal(false);
      setError(null);
    } catch {
      setError('Could not create session');
    }
  };

  const handleNewSession = () => {
    setShowWelcome(false);
    setWelcomeExiting(false);
    setShowSessionModal(true);
    setPendingMode(null);
    setSessionId(null);
    setSessionMode(null);
    setSongName('Untitled Session');
    setStages(null);
    setModel(null);
    setAlternatives([]);
    setPrompt('');
    setExpandError(null);
    setHasContentGeneration(false);
    setPostKeepFocus(null);
    setWorkspaceFadeKeep(false);
    setKeepChordFlash(false);
    setJustConfirmedStageId(null);
    setHistoryStageId(null);
    setStageSnapshots({});
  };

  const handleGenerate = async () => {
    const text = prompt.trim();
    if (!text || loading || !sessionId) return;

    setLoading(true);
    setError(null);
    setExpandError(null);
    setAgentStates(initialAgentStates());

    const prefix = stages && sessionMode ? buildContextPrefix(stages, seq) : '';
    const fullPrompt = prefix + text;

    try {
      let data;
      try {
        const out = await generatePromptStreaming(fullPrompt, sessionId, {
          onAgentEvent: applyStreamAgent,
        });
        data = out.data;
      } catch {
        data = null;
      }
      if (!data) {
        data = await generatePrompt(fullPrompt, sessionId);
      }

      if (!data) {
        throw new Error('Empty response from server');
      }

      finalizeAgentsDone();

      const normalized = normalizeGenerateResponse(data);
      setModel(normalized);
      setAlternatives(normalized?.alternatives || data.alternatives || []);

      if (normalized && !normalized.clarification_only && normalized.bpm != null) {
        const next = Number(normalized.bpm);
        if (!Number.isNaN(next)) setBpm(next);
      }
      if (data.cost_usd != null) setTokenCostUsd(data.cost_usd);
      else if (normalized?.cost_usd != null) setTokenCostUsd(normalized.cost_usd);

      if (stages && sessionMode && normalized && !normalized.clarification_only) {
        setStages((prev) => applyApiToStages(prev, sessionMode, data, normalized));
      }

      if (normalized && !normalized.clarification_only) {
        const progressed =
          (normalized.mode === 'chords' && (normalized.chords?.length ?? 0) > 0) ||
          (normalized.mode === 'drums' && normalized.drumPattern?.grid) ||
          (normalized.sound_engineering_response != null &&
            typeof normalized.sound_engineering_response === 'object') ||
          (normalized.artist_blend != null && typeof normalized.artist_blend === 'object');
        if (progressed) setHasContentGeneration(true);
      }

      setPostKeepFocus(null);
      setWorkspaceFadeKeep(false);
      setHistoryStageId(null);
    } catch (e) {
      setError(e.message || 'Request failed');
      setAgentStates(initialAgentStates());
    } finally {
      setLoading(false);
    }
  };

  const displayModel =
    historyStageId && stageSnapshots[historyStageId]?.model
      ? stageSnapshots[historyStageId].model
      : model;
  const displayAlternatives =
    historyStageId && stageSnapshots[historyStageId]
      ? stageSnapshots[historyStageId].alternatives ?? []
      : alternatives;

  const chords = displayModel?.chords || [];
  const isDrumSession = displayModel?.mode === 'drums';
  const drumGrid = displayModel?.drumPattern?.grid;

  const soundEngPayload = model?.sound_engineering_response;
  const artistBlendPayload = model?.artist_blend;
  const showSoundEngPanel =
    !model?.clarification_only &&
    soundEngPayload != null &&
    typeof soundEngPayload === 'object';
  const showArtistBlendPanel =
    !model?.clarification_only &&
    artistBlendPayload != null &&
    typeof artistBlendPayload === 'object';

  const suggestedStageId = useMemo(() => {
    if (!stages || !sessionMode) return null;
    return nextSuggestedStage(stages, sessionMode);
  }, [stages, sessionMode]);

  const sessionComplete =
    !!sessionId &&
    !!sessionMode &&
    !!stages &&
    allStagesComplete(stages, sessionMode);

  const completionProgression =
    stages?.progression?.value || model?.progression_name || '—';
  const completionDrum =
    sessionMode === 'drums'
      ? stages?.pattern?.value || model?.progression_name || '—'
      : '—';

  const suggestedCopy = useMemo(() => {
    const empty = { text: '', prefill: '', awaitingConfirmation: false };
    if (!sessionMode) return empty;
    const chordLike = sessionMode === 'chords' || sessionMode === 'full';
    if (chordLike && !hasContentGeneration) {
      return { text: CHORDS_SESSION_START_SUGGESTED_TEXT, prefill: '', awaitingConfirmation: false };
    }
    if (!stages) return empty;
    const awaiting = firstAwaitingConfirmStage(stages, sessionMode);
    if (awaiting) {
      return {
        text: getConfirmSuggestion(sessionMode, awaiting),
        prefill: '',
        awaitingConfirmation: true,
      };
    }
    if (!suggestedStageId) return empty;
    const { text, prefill } = getSuggestionForStage(sessionMode, suggestedStageId);
    return {
      text: personalizeSuggestion(text, model),
      prefill,
      awaitingConfirmation: false,
    };
  }, [hasContentGeneration, suggestedStageId, sessionMode, model, stages]);

  const handleSuggestedTry = () => {
    if (suggestedCopy.prefill) setPrompt(suggestedCopy.prefill);
  };

  const handleSkipConfirm = (stageId, note) => {
    if (!stages || !sessionMode) return;
    setStages((prev) => skipStage(prev, seq, stageId, note));
  };

  const handlePlayToggle = async () => {
    if (loading || expandLoading) return;
    if (isDrumSession) {
      if (!drumGrid || typeof drumGrid !== 'object') return;
    } else if (!chords.length) {
      return;
    }

    if (isPlaying) {
      stopPlayback();
      setIsPlaying(false);
      if (playTimerRef.current) {
        clearTimeout(playTimerRef.current);
        playTimerRef.current = null;
      }
      return;
    }
    setIsPlaying(true);
    const dur = isDrumSession
      ? await playDrumPattern(bpm, drumGrid)
      : await playProgression(bpm, chords, () => {});
    playTimerRef.current = setTimeout(() => {
      setIsPlaying(false);
      playTimerRef.current = null;
    }, Math.max(dur * 1000, 400));
  };

  const handleStop = () => {
    stopPlayback();
    setIsPlaying(false);
    if (playTimerRef.current) {
      clearTimeout(playTimerRef.current);
      playTimerRef.current = null;
    }
  };

  const sendFeedback = async (feedback, opts = {}) => {
    if (!sessionId) {
      setError('No session');
      return;
    }
    try {
      await postFeedback(sessionId, feedback, opts);
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Feedback failed');
    }
  };

  const handleKeep = async () => {
    if (historyStageId) {
      setHistoryStageId(null);
      return;
    }

    const awaiting = stages && sessionMode ? firstAwaitingConfirmStage(stages, sessionMode) : null;

    if (awaiting && model) {
      setStageSnapshots((prev) => ({
        ...prev,
        [awaiting]: { model: JSON.parse(JSON.stringify(model)), alternatives: [...alternatives] },
      }));
    }

    let nextStagesSnapshot = stages;
    if (stages && sessionMode) {
      nextStagesSnapshot = confirmFirstAwaitingStage(stages, sessionMode);
      if (
        awaiting === 'progression' &&
        model?.melody_direction &&
        nextStagesSnapshot.melodyDir?.status === 'pending'
      ) {
        nextStagesSnapshot = {
          ...nextStagesSnapshot,
          melodyDir: { status: 'done', value: 'Defined', confirmed: false },
        };
        recomputeActive(nextStagesSnapshot, seq);
      }
      setStages(nextStagesSnapshot);
    }

    setPrompt('');

    await sendFeedback('thumbs_up');

    if (!sessionMode || !nextStagesSnapshot) return;

    if (allStagesComplete(nextStagesSnapshot, sessionMode)) {
      setKeepChordFlash(true);
      if (awaiting) setJustConfirmedStageId(awaiting);
      setTimeout(() => setKeepChordFlash(false), 350);
      setTimeout(() => setJustConfirmedStageId(null), 500);
      return;
    }

    const nextId = nextSuggestedStage(nextStagesSnapshot, sessionMode);
    const { text } = getSuggestionForStage(sessionMode, nextId);
    const guidance = personalizeSuggestion(text, model);
    const headline = getPostKeepWorkOnHeadline(nextId);

    setKeepChordFlash(true);
    if (awaiting) setJustConfirmedStageId(awaiting);

    setTimeout(() => setKeepChordFlash(false), 350);
    setTimeout(() => setWorkspaceFadeKeep(true), 300);
    setTimeout(() => {
      setPostKeepFocus({ headline, guidance });
      setWorkspaceFadeKeep(false);
      setJustConfirmedStageId(null);
    }, 600);
  };

  const handleRegen = async () => {
    setPostKeepFocus(null);
    setWorkspaceFadeKeep(false);
    if (historyStageId && stages && sessionMode) {
      const snap = stageSnapshots[historyStageId];
      setStages((prev) => reopenStageForRevision(prev, sessionMode, historyStageId));
      if (snap?.model) setModel(snap.model);
      if (snap?.alternatives) setAlternatives(snap.alternatives);
      setHistoryStageId(null);
    } else if (stages && sessionMode) {
      setStages((prev) => regenResetFromFirstAwaiting(prev, sessionMode));
    }
    await sendFeedback('regenerate');
  };

  const handleVary = async () => {
    setPostKeepFocus(null);
    setWorkspaceFadeKeep(false);
    if (historyStageId && stages && sessionMode) {
      const snap = stageSnapshots[historyStageId];
      setStages((prev) => reopenStageForRevision(prev, sessionMode, historyStageId));
      if (snap?.model) setModel(snap.model);
      if (snap?.alternatives) setAlternatives(snap.alternatives);
      setHistoryStageId(null);
    } else if (stages && sessionMode) {
      setStages((prev) => regenResetFromFirstAwaiting(prev, sessionMode));
    }
    await sendFeedback('regenerate');
  };

  const handleAlsoTryPick = async (alt) => {
    setHistoryStageId(null);
    if (!model || !sessionId || expandLoading || model.mode !== 'chords') return;

    const names = chordNamesFromAlt(alt);
    if (!names.length || !model.key) return;

    const snapshot = JSON.parse(JSON.stringify(model));
    const prevAlts = [...alternatives];

    const optimisticChords = names.map((name, i) => ({
      numeral: alt.chords?.[i]?.numeral || '',
      name,
      notes: [],
    }));

    setModel((m) =>
      m
        ? {
            ...m,
            chords: optimisticChords,
            progression_name: alt.progression_name || m.progression_name,
          }
        : m
    );
    setAlternatives((alts) =>
      alts.filter((a) => a.label !== alt.label).concat([slimPrimaryFromModel(snapshot)])
    );
    setExpandLoading(true);
    setExpandError(null);

    if (isPlaying) {
      handleStop();
    }

    try {
      const out = await expandProgression({
        chords: names,
        key: model.key,
        progression_name: alt.progression_name || snapshot.progression_name,
        sessionId,
      });

      const nextChords = (out.chords || []).map((c) => ({
        numeral: c.numeral,
        name: c.name,
        notes: c.note_names || c.notes || [],
      }));

      setModel((m) =>
        m
          ? {
              ...m,
              chords: nextChords,
              progression_name: out.progression_name || alt.progression_name,
              validation: out.validation,
            }
          : m
      );

      await sendFeedback('progression_swap', { swapLabel: alt.label });

      if (stages && sessionMode) {
        setStages((prev) => {
          const next = { ...prev };
          if (next.progression) {
            next.progression = {
              ...next.progression,
              status: 'done',
              value: alt.progression_name || next.progression.value,
              confirmed: false,
            };
          }
          recomputeActive(next, seq);
          return next;
        });
      }

      setExpandLoading(false);
    } catch (e) {
      setModel(snapshot);
      setAlternatives(prevAlts);
      setExpandError(e.response?.data?.detail || e.message || 'Expand failed');
      setExpandLoading(false);
    }
  };

  const shell = (
    <div className={styles.root}>
      <div className={styles.bodyRow}>
        {sessionId && sessionMode && stages ? (
          <ProgressSidebar
            sessionId={sessionId}
            songName={songName}
            onSongNameSaved={setSongName}
            sessionMode={sessionMode}
            infoKey={model?.key ?? null}
            infoBpm={model?.bpm}
            infoVibe={model?.genre_context ?? null}
            keyWasSpecified={model?.key_was_specified === true}
            stages={stages}
            suggestedText={suggestedCopy.text}
            suggestedPrefill={suggestedCopy.prefill}
            awaitingConfirmation={suggestedCopy.awaitingConfirmation}
            onSuggestedTry={handleSuggestedTry}
            onSkipConfirm={handleSkipConfirm}
            justConfirmedStageId={justConfirmedStageId}
            hasStageSnapshot={(id) => !!stageSnapshots[id]?.model}
            onConfirmedStageClick={(id) => {
              if (!stageSnapshots[id]?.model) return;
              setHistoryStageId(id);
              setPostKeepFocus(null);
            }}
          />
        ) : null}

        <div className={styles.mainColumn}>
          <TopBar
            songName={sessionId ? songName : null}
            bpm={bpm}
            cpuPercent={cpuPercent}
            tokenCostUsd={tokenCostUsd}
            isPlaying={isPlaying}
            onPlayToggle={handlePlayToggle}
            onStop={handleStop}
            onNewSession={handleNewSession}
            audioLoading={expandLoading}
          />
          {!showSessionModal ? <AgentBar states={agentStates} /> : null}

          <main
            className={`${styles.workspace} ${workspaceFadeKeep ? styles.workspaceFade : ''}`}
          >
            {error ? <div className={styles.error}>{error}</div> : null}

            {model?.clarification_only ? (
              <div className={styles.clarify}>{model.clarification_question}</div>
            ) : null}

            {sessionComplete ? (
              <div className={styles.completionWrap}>
                <div className={styles.completionWordmark}>Rubato</div>
                <h2 className={styles.completionTitle}>Blueprint complete</h2>
                <ul className={styles.completionList}>
                  <li>
                    <span className={styles.completionLabel}>Key</span>
                    <span className={styles.completionValue}>{model?.key || '—'}</span>
                  </li>
                  <li>
                    <span className={styles.completionLabel}>BPM</span>
                    <span className={styles.completionValue}>
                      {model?.bpm != null ? `${model.bpm}` : `${bpm}`}
                    </span>
                  </li>
                  <li>
                    <span className={styles.completionLabel}>Progression</span>
                    <span className={styles.completionValue}>{completionProgression}</span>
                  </li>
                  <li>
                    <span className={styles.completionLabel}>Drum pattern</span>
                    <span className={styles.completionValue}>{completionDrum}</span>
                  </li>
                </ul>
                <button
                  type="button"
                  className={styles.openAbleton}
                  onClick={() => console.log('MCP not connected yet')}
                >
                  Open in Ableton
                </button>
                <p className={styles.completionHint}>Ableton integration coming soon</p>
              </div>
            ) : null}

            {!model?.clarification_only && !sessionComplete && postKeepFocus ? (
              <div className={styles.nextStageOverlay}>
                <div className={styles.wordmarkSm}>Rubato</div>
                <h2 className={styles.nextHeadline}>{postKeepFocus.headline}</h2>
                <p className={styles.nextGuidance}>{postKeepFocus.guidance}</p>
              </div>
            ) : null}

            {!model?.clarification_only && !sessionComplete && !postKeepFocus ? (
              <>
                <div className={styles.workspaceMainScroll}>
                  <MainWorkspace
                    sessionId={sessionId}
                    sessionMode={sessionMode}
                    modeLabel={sessionMode ? MODE_BADGE_LABEL[sessionMode] || sessionMode : ''}
                    suggestedText={
                      suggestedCopy.text?.trim() || 'Describe what you want in the input below.'
                    }
                    onExamplePrompt={setPrompt}
                    hasContentGeneration={hasContentGeneration}
                    chords={chords}
                    model={displayModel}
                    alternatives={displayAlternatives}
                    onAlsoTryPick={handleAlsoTryPick}
                    expandLoading={expandLoading}
                    expandError={expandError}
                    melodyIntroActive={melodyIntroActive}
                    onMelodyIntroComplete={handleMelodyIntroComplete}
                    keepChordFlash={keepChordFlash}
                    historyStageId={historyStageId}
                    historyStageLabel={
                      historyStageId ? STAGE_LABELS[historyStageId] || historyStageId : ''
                    }
                    onExitHistory={() => setHistoryStageId(null)}
                  />
                </div>

                {showSoundEngPanel || showArtistBlendPanel ? (
                  <div className={styles.panelsSecondary}>
                    {showSoundEngPanel ? (
                      <div data-testid="sound-engineering-panel">
                        <SoundEngineeringPanel data={soundEngPayload} />
                      </div>
                    ) : null}
                    {showArtistBlendPanel ? (
                      <div data-testid="artist-blend-panel">
                        <ArtistBlendPanel data={artistBlendPayload} />
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </>
            ) : null}
          </main>

          {!showSessionModal && !showWelcome ? (
            <InputBar
              value={prompt}
              onChange={setPrompt}
              onGenerate={handleGenerate}
              onKeep={handleKeep}
              onRegen={handleRegen}
              onVary={handleVary}
              disabled={!sessionId}
              loading={loading}
              awaitingConfirmation={suggestedCopy.awaitingConfirmation || !!historyStageId}
              prominent={!!postKeepFocus}
              onDismissPostKeepOverlay={
                postKeepFocus ? () => setPostKeepFocus(null) : undefined
              }
            />
          ) : null}
        </div>
      </div>

      <SessionStartModal
        open={showSessionModal}
        selected={pendingMode}
        onSelect={setPendingMode}
        onContinue={handleModalContinue}
        animateIn={modalEnterAnim}
      />

      <WelcomeScreen
        visible={showWelcome}
        exiting={welcomeExiting}
        onStart={handleWelcomeStart}
      />
    </div>
  );

  return shell;
}
