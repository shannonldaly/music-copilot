# Recording kickoff — the Ableton arrangement clip (written 2026-09-02)

**Job:** record the Send-to-Ableton demo clip and land it on the portfolio's /rubato/ page, replacing the placeholder. The arrangement send was E2E-proven 2026-09-02 (Shannon: "wooo it works") — this doc is everything a fresh session needs to get from zero to the published clip.

## What the clip shows (the arc)

The money shot is the full import: **prompt → Keep through stages → one click → three playable tracks land in Ableton, in key, in both views.** The /rubato/ page currently promises "Send to Ableton pushes the chords over MCP into a live set… That clip lands when Rubato comes off pause" — this clip over-delivers on that promise (whole arrangement, not just chords).

Suggested take structure (~30–45s final, can be two takes stitched):

0. **Audio:** confirm QuickTime's mic is BlackHole 2ch and Ableton outputs to the Multi-Output Device (see capture pipeline below) — the arrangement should be HEARD playing in takes 3-4.
1. **In Rubato (browser):** the finished session visible — chords + melody panel + bass panel + drums locked. Cursor hits **Send to Ableton**. (~5s)
2. **In Ableton Session View:** the three tracks appear at the right — "Rubato Chords" (piano, clip named with the actual chords e.g. "Am Dm Am Dm · A minor"), "Rubato Bass", "Rubato Drums" — each with EQ Eight. Linger on the chord-named clip. (~10s)
3. **Tab to Arrangement View:** same clips sitting on the timeline at bar 1. Key & Scale display shows the progression key. Press play; playhead moves. (~10s)
4. Optional close: open the piano roll on Rubato Chords — the actual chord notes. (~5s)

**This clip keeps its audio** (Shannon's ruling: hearing the arrangement land is the payoff — the other site clips stay muted). The capture pipeline is ALREADY SET UP AND PROVEN (2026-09-02, tested end to end):

- **BlackHole 2ch** is installed (brew) and a **Multi-Output Device** exists in Audio MIDI Setup: MacBook Pro Speakers (primary/clock) + BlackHole 2ch (drift correction on).
- **Ableton's Audio Output Device = Multi-Output Device** — she hears the set while BlackHole gets a copy. Live only scans devices at launch, so if the device is missing from Live's list, restart Live.
- **QuickTime screen recording with Microphone = BlackHole 2ch** captures clean direct Ableton audio (no room noise).
- While on the Multi-Output Device the Mac volume keys are dead — set level with Ableton's master fader (healthy level = recording level).
- After the shoot, switch Ableton's output back to MacBook Pro Speakers.

## Preflight checklist (walk Shannon through ONE STEP AT A TIME, numbered)

1. **Ableton script check** (Live auto-updates silently revert the patched remote script — it bit twice on 09-01; stock script = clips arrive empty while reporting success):
   ```
   grep -c set_song_key "/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/MIDI Remote Scripts/AbletonMCP/__init__.py"
   ```
   Non-zero → good. Zero → reinstall per `ableton_remote/README.md` (cp + Live restart).
2. **Ableton open**, MCP listening: `lsof -nP -iTCP:9877 -sTCP:LISTEN` shows Live.
3. **Clean set for camera:** a fresh or tidied Live set — delete leftover empty "Rubato …"/"N-MIDI" debris tracks from the 09-01 debugging era. The send creates its own tracks.
4. **Backend:** `cd ~/Documents/"Ableton Copilot" && ./venv/bin/uvicorn api.main:app --port 8000` (health: `curl localhost:8000/api/health` — "degraded" is fine, it only means no API key; check `ableton_connected: true`).
5. **Frontend:** `python3 -m http.server 5173` from `frontend/dist` (the vite dev server wedges; CORS allows only 3000/5173 and 3000 is her Langfuse). If frontend code changed since last build: `npm run build` first. Browser: hard refresh.
6. **Dry run before recording:** run a session (e.g. "melancholic lo-fi in A minor" → Keep → drums stage), hit Send, and VERIFY notes landed by reading them back (never trust command success alone):
   ```python
   # from repo root, venv python
   from services.mcp_client import AbletonMCPClient
   c = AbletonMCPClient()
   c._send_command("get_clip_notes", {"track_index": <idx>, "clip_index": 0})
   ```
7. Then delete the dry-run tracks, hit record, do it for real.

## Camera + cut + encode (the ruled settings)

- Shannon records with QuickTime (screen recording, Ableton window; browser take separately if doing the two-window arc). Files usually land on ~/Desktop.
- Cut/retime with ffmpeg; encode THIS clip WITH audio: `-c:v libx264 -crf 24 -preset slow -c:a aac -b:a 128k -movflags +faststart`, scale ~1600w, fps 30, **≤5MB** (the `-an` in the ruled settings applies to the muted clips only). The page video uses `controls preload="none"`, so sound only plays when the viewer clicks — no autoplay-with-audio problem.
- Poster frame: ffmpeg frame → `cwebp -q 80` (sips can't write webp).

## Landing it on the site

- Repo: `~/daly-ai/knowledge-layer-showcase` (= shannonldaly.github.io). Branch + PR; **declare "PR complete, nothing further coming"** (she merges fast and has caught branches mid-push).
- Page: `rubato/index.html`. Replace the paragraph "The full loop goes one step further… That clip lands when Rubato comes off pause." with a second `demo-block` (copy the existing figure markup: `.demo-block > figure > .frame > video` + `figcaption`). Media to `docs/media/` (e.g. `rubato-arrangement.mp4` + `-poster.webp`).
- Caption in her voice (load `~/daly-ai/ops-system/solto-standards/shannon_voice.md` before drafting; no em dashes; lead with viewer value, not system internals). The true facts to work with: one click lands chords, bass, and drums as three named tracks with instruments and EQ Eights, tempo and Live's Key & Scale set to match, clips named with the actual chords, visible in both Session and Arrangement view. Melody is deliberately left to the musician.

## Fences

- Nothing sensitive is on screen in Ableton/Rubato, but keep her browser bookmarks/tabs out of frame.
- music-copilot repo is public: run the full test suite (127) before any commit; all LLM calls stay on `claude -p` (subscription), never the API.
- Don't run the vite dev server; don't touch CLAUDE.md; frontend changes need `npm run build` to reach the served dist.
