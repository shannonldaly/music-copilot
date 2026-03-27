import { useCallback, useEffect, useRef, useState } from 'react';
import { AGENTS } from './constants';
import { createSession, generatePrompt, generatePromptStreaming, postFeedback } from './utils/api';
import { normalizeGenerateResponse } from './utils/normalize';
import { playProgression, playDrumPattern, stopPlayback } from './utils/playback';
import TopBar from './components/TopBar';
import AgentBar from './components/AgentBar';
import SessionPanel from './components/SessionPanel';
import TheoryPanel from './components/TheoryPanel';
import ProductionPanel from './components/ProductionPanel';
import InputBar from './components/InputBar';
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

export default function App() {
  const [sessionId, setSessionId] = useState(null);
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [model, setModel] = useState(null);
  const [bpm, setBpm] = useState(85);
  const [tokenCostUsd, setTokenCostUsd] = useState(0);
  const [cpuPercent, setCpuPercent] = useState(14);

  const [agentStates, setAgentStates] = useState(initialAgentStates);
  const streamSimOffRef = useRef(false);
  const playTimerRef = useRef(null);

  const [isPlaying, setIsPlaying] = useState(false);

  useEffect(() => {
    createSession()
      .then(setSessionId)
      .catch(() => setError('Could not create session'));
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

  const handleGenerate = async () => {
    const text = prompt.trim();
    if (!text || loading) return;

    setLoading(true);
    setError(null);
    setAgentStates(initialAgentStates());

    try {
      let data;
      try {
        const out = await generatePromptStreaming(text, sessionId, {
          onAgentEvent: applyStreamAgent,
        });
        data = out.data;
      } catch {
        data = null;
      }
      if (!data) {
        data = await generatePrompt(text, sessionId);
      }

      if (!data) {
        throw new Error('Empty response from server');
      }

      finalizeAgentsDone();

      const normalized = normalizeGenerateResponse(data);
      setModel(normalized);

      if (normalized && !normalized.clarification_only && normalized.bpm != null) {
        const next = Number(normalized.bpm);
        if (!Number.isNaN(next)) setBpm(next);
      }
      if (data.cost_usd != null) setTokenCostUsd(data.cost_usd);
      else if (normalized?.cost_usd != null) setTokenCostUsd(normalized.cost_usd);
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

  const handlePlayToggle = async () => {
    if (loading) return;
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

  const sendFeedback = async (feedback) => {
    if (!sessionId) {
      setError('No session');
      return;
    }
    try {
      await postFeedback(sessionId, feedback);
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Feedback failed');
    }
  };

  return (
    <div className={styles.root}>
      <TopBar
        bpm={bpm}
        cpuPercent={cpuPercent}
        tokenCostUsd={tokenCostUsd}
        isPlaying={isPlaying}
        onPlayToggle={handlePlayToggle}
        onStop={handleStop}
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
          />
          <TheoryPanel
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
          />
          <ProductionPanel productionMarkdown={model?.production_steps} teachingNote={model?.teaching_note} />
        </div>
      </main>

      <InputBar
        value={prompt}
        onChange={setPrompt}
        onGenerate={handleGenerate}
        onKeep={() => sendFeedback('thumbs_up')}
        onRegen={() => sendFeedback('regenerate')}
        onVary={() => sendFeedback('regenerate')}
        disabled={!sessionId}
        loading={loading}
      />
    </div>
  );
}
