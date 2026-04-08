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
  STAGE_SEQUENCES,
  applyApiToStages,
  buildContextPrefix,
  confirmFirstAwaitingStage,
  createInitialStages,
  firstAwaitingConfirmStage,
  getConfirmSuggestion,
  getSuggestionForStage,
  nextSuggestedStage,
  recomputeActive,
  regenResetFromFirstAwaiting,
  skipStage,
} from './sessionStages';
import TopBar from './components/TopBar';
import AgentBar from './components/AgentBar';
import SessionPanel from './components/SessionPanel';
import TheoryPanel from './components/TheoryPanel';
import ProductionPanel from './components/ProductionPanel';
import SoundEngineeringPanel from './components/SoundEngineeringPanel';
import ArtistBlendPanel from './components/ArtistBlendPanel';
import InputBar from './components/InputBar';
import SessionStartModal from './components/SessionStartModal';
import ProgressSidebar from './components/ProgressSidebar';
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
  const [showSessionModal, setShowSessionModal] = useState(true);
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

  const seq = STAGE_SEQUENCES[sessionMode] || STAGE_SEQUENCES.chords;

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
      setShowSessionModal(false);
      setError(null);
    } catch {
      setError('Could not create session');
    }
  };

  const handleNewSession = () => {
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
    } catch (e) {
      setError(e.message || 'Request failed');
      setAgentStates(initialAgentStates());
    } finally {
      setLoading(false);
    }
  };

  const chords = model?.chords || [];
  const isDrumSession = model?.mode === 'drums';
  const drumGrid = model?.drumPattern?.grid;

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
    if (stages && sessionMode) {
      setStages((prev) => confirmFirstAwaitingStage(prev, sessionMode));
    }
    await sendFeedback('thumbs_up');
  };

  const handleRegen = async () => {
    if (stages && sessionMode) {
      setStages((prev) => regenResetFromFirstAwaiting(prev, sessionMode));
    }
    await sendFeedback('regenerate');
  };

  const handleVary = async () => {
    if (stages && sessionMode) {
      setStages((prev) => regenResetFromFirstAwaiting(prev, sessionMode));
    }
    await sendFeedback('regenerate');
  };

  const handleAlsoTryPick = async (alt) => {
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
      <SessionStartModal
        open={showSessionModal}
        selected={pendingMode}
        onSelect={setPendingMode}
        onContinue={handleModalContinue}
      />

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
          <AgentBar states={agentStates} />

          <main className={styles.workspace}>
            {error ? <div className={styles.error}>{error}</div> : null}

            {model?.clarification_only ? (
              <div className={styles.clarify}>{model.clarification_question}</div>
            ) : null}

            <div className={styles.panels}>
              <SessionPanel
                mode={model?.mode}
                chords={chords}
                drumGrid={drumGrid}
                bpm={bpm}
                progressionName={model?.progression_name}
                keyName={model?.key}
                genreContext={model?.genre_context}
                rollLoading={expandLoading && !isDrumSession}
              />
              <TheoryPanel
                sessionId={sessionId}
                mode={model?.mode}
                chords={chords}
                drumPattern={model?.drumPattern}
                keyName={model?.key}
                scale={model?.scale}
                progressionName={model?.progression_name}
                theoryExplanation={model?.theory_explanation}
                voiceLeadingNotes={model?.voice_leading_notes}
                validation={model?.validation}
                validationBadge={model?.validationBadge}
                genreContext={model?.genre_context}
                alsoTryAlternatives={alternatives}
                onAlsoTryPick={handleAlsoTryPick}
                expandLoading={expandLoading}
                expandError={expandError}
                melodyDirection={model?.melody_direction}
                melodyIntroActive={melodyIntroActive}
                onMelodyIntroComplete={handleMelodyIntroComplete}
              />
              <ProductionPanel productionMarkdown={model?.production_steps} teachingNote={model?.teaching_note} />
            </div>

            {showSoundEngPanel || showArtistBlendPanel ? (
              <div className={styles.panelsSecondary}>
                {showSoundEngPanel ? (
                  <SoundEngineeringPanel data={soundEngPayload} />
                ) : null}
                {showArtistBlendPanel ? <ArtistBlendPanel data={artistBlendPayload} /> : null}
              </div>
            ) : null}
          </main>

          {!showSessionModal ? (
            <InputBar
              value={prompt}
              onChange={setPrompt}
              onGenerate={handleGenerate}
              onKeep={handleKeep}
              onRegen={handleRegen}
              onVary={handleVary}
              disabled={!sessionId}
              loading={loading}
              awaitingConfirmation={suggestedCopy.awaitingConfirmation}
            />
          ) : null}
        </div>
      </div>
    </div>
  );

  return shell;
}
