import axios from 'axios';

const BASE = import.meta.env.DEV ? '' : 'http://localhost:8000';

export const api = axios.create({
  baseURL: BASE,
  headers: { 'Content-Type': 'application/json' },
  timeout: 120000,
});

export async function generatePrompt(prompt, sessionId) {
  const { data } = await api.post('/api/generate', {
    prompt,
    session_id: sessionId || undefined,
    use_api: false,
  });
  return data;
}

export async function generatePromptStreaming(prompt, sessionId, { onAgentEvent } = {}) {
  const res = await fetch(`${BASE}/api/generate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json, application/x-ndjson, text/event-stream',
    },
    body: JSON.stringify({ prompt, session_id: sessionId || undefined, use_api: false }),
  });

  if (!res.ok) {
    const errText = await res.text().catch(() => '');
    throw new Error(errText || `HTTP ${res.status}`);
  }

  const ct = res.headers.get('content-type') || '';

  if (ct.includes('application/json')) {
    const data = await res.json();
    return { data, streamed: false };
  }

  if (!res.body) {
    const data = await res.json();
    return { data, streamed: false };
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let finalData = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      const l = line.trim();
      if (!l) continue;
      if (l.startsWith('data:')) {
        const payload = l.slice(5).trim();
        if (payload === '[DONE]') continue;
        try {
          const obj = JSON.parse(payload);
          dispatchStreamObj(obj, onAgentEvent, (d) => {
            finalData = d;
          });
        } catch {
          /* ignore */
        }
        continue;
      }
      try {
        const obj = JSON.parse(l);
        dispatchStreamObj(obj, onAgentEvent, (d) => {
          finalData = d;
        });
      } catch {
        /* ignore */
      }
    }
  }

  if (buffer.trim()) {
    try {
      const obj = JSON.parse(buffer.trim());
      dispatchStreamObj(obj, onAgentEvent, (d) => {
        finalData = d;
      });
    } catch {
      /* ignore */
    }
  }

  return { data: finalData, streamed: true };
}

function dispatchStreamObj(obj, onAgentEvent, setFinal) {
  if (obj.type === 'agent' && onAgentEvent) onAgentEvent(obj);
  if (obj.type === 'result') setFinal(obj.payload ?? obj.data);
  if (obj.success !== undefined && obj.session_id) setFinal(obj);
}

export function postFeedback(sessionId, feedback, { entryIndex = -1, swapLabel } = {}) {
  return api.post('/api/feedback', {
    session_id: sessionId,
    entry_index: entryIndex,
    feedback,
    swap_label: swapLabel,
  });
}

export async function createSession(body = {}) {
  const { data } = await api.post('/api/session', body);
  return data;
}

export async function patchSession(sessionId, body) {
  const { data } = await api.patch(`/api/session/${sessionId}`, body);
  return data;
}

export async function expandProgression({ chords, key, progression_name, sessionId }) {
  const { data } = await api.post('/api/progression/expand', {
    chords,
    key,
    progression_name,
    session_id: sessionId || undefined,
  });
  return data;
}
