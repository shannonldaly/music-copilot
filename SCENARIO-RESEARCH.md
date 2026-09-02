# Music Copilot Backend: Merged Research Report

Five research lanes (vocabulary, theory-data, scenario-matrix, references, ops-readiness). Theory-bearing lanes were adversarially verified by re-execution against live code. All findings below are what the lanes measured. Nothing here is invented.

**Repo note:** the engine the lanes examined lives at `/Users/shannondaly/Documents/Ableton Copilot`. All file paths in this report are relative to that project. `/Users/shannondaly/daly-ai/knowledge-layer-showcase` contains only the showcase write-up (`rubato/index.html`), not the code.

---

## 1. Executive summary

1. The data the engine owns is far wider than the vocabulary that can reach it: 11 mood keywords against 31 mood tags in the progression corpus, 13 genre keywords against 22 progression keys and 21 drum-pattern keys.
2. Two silent collapses make a miss look like a hit. `search_progressions` normalizes the query to underscores but compares against dashed tags, so `lo-fi`, the flagship genre, has a completely dead lookup. And `get_artist_reference` returns entry 0 on a zero score, so every unrecognized prompt is confidently told "Massive Attack".
3. The mix stage is the deepest hole: 30 of 40 stage-by-prompt cells return `{success, intent, confidence}` with no payload, and the frontend then blanks the workspace including the chord row the user just confirmed.
4. Two of the three session modes cannot be completed. Mixing can never advance past its first stage; drums can only be finished with the Skip button.
5. Adversarial review of the 15 proposed progressions and 18 drum patterns found six musical defects and fixed them in place: the "Gospel 6-2-5-1" never reached the 1, the "punk d-beat" was not a d-beat, plus a stray blues kick, a false tresillo claim, and three mispaired genre tags.
6. The proposal's claim that the new data spells correctly in all six test keys is false: Eb minor emits Cb7 (with Bbb) and F# major emits D#7 (with F##).
7. The references lane produced nothing usable. Its input payload was a schema probe with no musical content, so this report contains no new artist-reference data.
8. "Prod" can only mean a packaged local Mac app. The MCP socket is hardcoded to localhost:9877 and headless Claude is an absolute path into Shannon's home directory on her personal subscription. Neither survives hosting.
9. The real prod blockers are not deploy plumbing: a reverted Ableton remote script returns a silent false success, `/api/health` is structurally incapable of returning "ok", every endpoint blocks the event loop for up to 90 seconds, and `python api/main.py` binds 0.0.0.0 with no auth on an endpoint that spends her subscription.
10. Almost every vocabulary gap closes by adding rows to tables that already exist. Only two need new mechanisms: boundary matching, and enharmonic respelling.

---

## 2. Prioritized action list

Ordered by leverage: how much of the field-observed failure each item removes per unit of work.

### Tier 1: the app currently lies or goes blank

| # | What | Where | Effort | Lane |
|---|---|---|---|---|
| 1 | Make the sound-engineering branch never return empty. Add a `DEFAULT_BY_STAGE` map over existing `LOCAL_RESPONSES` (mix→eq, targetVibe→reverb, automation→automate, eq→eq, section→eq) plus a final fallback in `generate_sound_engineering_local` that returns the eq response with a "closest match" line instead of None. Closes 30 of 40 dead cells and the blank-workspace path. | `agents/orchestrator_pipeline.py:100-107`, `agents/se_local_data.py:171-177` | S | vocabulary, scenario-matrix, ops |
| 2 | Fix the `lo-fi` genre lookup. Normalize both sides in `search_progressions` (use the same `_normalize_key` variation list `drum_patterns.py:585` already uses) and add `lofi`/`lo_fi` aliases to `GENRE_PROGRESSIONS`. | `theory/genre_progressions.py:462-465, 326` | S | vocabulary, theory-data |
| 3 | Stop the artist-reference impersonation. Change `if score > best_score` to `if score > best_score and score > 0` so zero-overlap falls through to the real pentatonic fallback instead of always saying Massive Attack. | `agents/theory_local.py:381-387` | S | vocabulary |
| 4 | Surface the reverted-Ableton-script warning. The `set_song_key` probe already detects a stock script, but the result is dropped and the send still reports success with a note count of what it sent, not what Live accepted. Carry the probe result into the return payload as a `warning`, and add it to `/api/health` as `ableton_script_patched`. | `services/mcp_client.py:109-112, 215-219` | S | ops |
| 5 | Guard `setDone` so it does not clear `confirmed` on an already-confirmed stage (`if (next[id]?.confirmed) return;`). Without this, every second generation rewinds the sidebar to stage 1 in both drums and mixing mode. | `frontend/src/sessionStages.js:157-161` | S | scenario-matrix |
| 6 | Map the mixing-mode payload to the stage the prompt actually addressed (the frontend already computes `activeStage`) instead of only ever setting `section` to the raw intent string. Unblocks the mixing mode's three unreachable stages and stops `sound_engineering` rendering as the user's chosen section. | `frontend/src/sessionStages.js:173-174`, `App.jsx:269-272` | M | scenario-matrix |
| 7 | Fall back when a recognized genre has zero drum patterns (jazz, classical, ambient all return `[]` today, which blanks the screen). In `_lookup_drums`, when the genre loop yields nothing, fall through to session genres then `['trap']`, and attach the substitution as a note. | `agents/orchestrator_pipeline.py:187` | S | scenario-matrix |
| 8 | Drop `async` on the four blocking endpoints so FastAPI runs them in a threadpool, and lower the headless timeout from 90s to about 20s. One prompt currently stalls the whole server, health included. | `api/main.py:190, 249, 294, 313`, `utils/headless_claude.py:38-45` | S | ops |
| 9 | Bind `127.0.0.1` in the `__main__` block and pass an empty `--allowedTools` to the headless subprocess. Today anyone on the same wifi can POST to an unauthenticated endpoint that spends her Claude subscription, with the raw prompt piped into an agent running in the repo directory. | `api/main.py:525`, `utils/headless_claude.py:43` | S | ops |

### Tier 2: make it answer instead of guessing

| # | What | Where | Effort | Lane |
|---|---|---|---|---|
| 10 | Pass unmatched user adjectives through to `search_progressions(tags=[...])`. The scoring already exists and the corpus already carries `jazzy`, `dusty`, `sad`, `noir`, `spanish`, `anthemic`. Cheapest fix in the whole set, no new data. | `agents/orchestrator_pipeline.py:171, 173, 237, 418` | S | theory-data |
| 11 | Inherit session context in the mood_vibe / theory_request branch (`extracted.setdefault('key', ctx['key'])`, same for genres). Today the app's own "alternative progression in the same key" prefill returns C major from an A-minor session and overwrites the sidebar key. | `agents/orchestrator_pipeline.py:68-69` | S | scenario-matrix |
| 12 | Add a mood path into drum selection: a `MOOD_DRUM_PATTERNS` table plus three lines in `_lookup_drums` after the genre loop. Full proposed table in Appendix A6. | `theory/drum_patterns.py:578`, `orchestrator_pipeline.py:187` | S | vocabulary |
| 13 | Expand `MOOD_KEYWORDS` with the 17 free-win words that already rank in the corpus, and `GENRE_KEYWORDS` with the 13 progression-reachable and 9 drum-reachable genres. Full lists in Appendix A2 and A3. | `agents/intent_detection.py:47-50` | M | vocabulary |
| 14 | Extend `KEYWORD_TO_TOPIC` with vibe adjectives (warm, punchy, muddy, wide, loud, glue, pump, gritty, dusty) plus two new topics, `saturation` and `loudness`, and one `lofi_texture`. Full mapping in Appendix A4. | `agents/se_local_data.py:144-155` | M | vocabulary |
| 15 | Replace substring matching with a shared boundary matcher: `re.search(rf'(?<![a-z]){re.escape(w)}(?![a-z])', ...)`. Fixes six live misroutes at once (mixolydian and sequence going to sound_engineering, afrobeats and upbeat going to drums, subtle going to bass, hyperpop going to pop). | `agents/intent_detection.py:250-285`, `agents/se_local_data.py:171` | M | vocabulary |
| 16 | Add rows to the key-inference tables for every word added above, or new words silently land in C major. Today `chill`, `dreamy`, `jazz`, `rock`, `hip hop`, `r&b`, `classical` are all unclassified. Also normalize `'hip hop'` to `hip_hop` at line 256. | `agents/intent_detection.py:103-106, 256` | S | vocabulary |
| 17 | Alias `production_question` to the sound-engineering branch and remove it from the headless classifier's allowed outputs. It is a routable intent with no handler. | `agents/orchestrator_pipeline.py:100`, `utils/headless_claude.py:20-26` | S | scenario-matrix |
| 18 | Extract BPM from the prompt (`\b(\d{2,3})\s*(?:bpm)\b`) and prefer it over the pattern midpoint. The drums mode has a dedicated bpm stage whose own prefill "140 BPM trap beat" returns 150. | `agents/intent_detection.py:172-185`, `orchestrator_pipeline.py:355-357` | S | scenario-matrix |
| 19 | Echo the session progression into the drum and SE responses the way melody and bass already do, so the chord row survives a follow-up answer. | `agents/orchestrator_pipeline.py:92-107` | S | scenario-matrix |

### Tier 3: new theory data and the parser work it needs

| # | What | Where | Effort | Lane |
|---|---|---|---|---|
| 20 | Add the corrected `ROMAN_NUMERALS` entries (`Idom7`, `VI7`, `IVdom7`, plus the 9th/maj9 keys). Today `VI7` silently becomes a major 7 and `I9` silently drops the 9. Make the parser raise on an unrecognized digit rather than guess, and `logger.warning` on the swallowed ValueError in `_convert_progressions`. | `theory/progressions.py:126-146`, `orchestrator_pipeline.py:272-273` | M | theory-data |
| 21 | Merge the 15 corrected progressions and 18 corrected drum patterns. Corrected file: `/private/tmp/claude-501/-Users-shannondaly/b24b53af-f2ec-40b5-a5d8-a6987fe33f77/scratchpad/proposed_reviewed.py` (15/15 and 18/18 re-validated, 0 failures). Full listings in Appendix B6 and B7. | `theory/genre_progressions.py:317, 324`, `theory/drum_patterns.py:549, 556` | M | theory-data |
| 22 | Derive the three genre/mood lookup maps from each entry's own `genres`/`moods` at import time, keeping the hand-written maps as ordering overrides only, plus a one-line pytest asserting `declared <= lookup_keys`. Closes all 34 unreachable genres and 16 unreachable moods at once and keeps new data honest. | `theory/genre_progressions.py:324`, `theory/drum_patterns.py:556` | S | theory-data |
| 23 | Add the theory_local rule-branch rows so new genres change the actual musical advice instead of falling to the generic branch. Full proposed branches in Appendix A10. | `agents/theory_local.py:236-241, 247-253, 317-328` | M | vocabulary |
| 24 | Add the eight new `ARTIST_REFERENCES` rows for techno, dnb, garage, blues/soul, disco/funk, drill/phonk, reggaeton/afrobeats, synthwave. Key them off the same normalized vocabulary so one keyword addition lights up melody, bass, drums and mix. | `agents/theory_local.py:348-373` | M | vocabulary |
| 25 | Enharmonic respell at the chord layer: if a built chord carries a double accidental, respell from the enharmonic root (Cb7 to B7, D#7 to Eb7). Until this lands, do not repeat the six-key validation claim. | `Chord.get_notes()` / `theory/progressions.py:154-156` | M | theory-data |

### Tier 4: correctness, persistence, packaging

| # | What | Where | Effort | Lane |
|---|---|---|---|---|
| 26 | Atomic session writes (dump to `.tmp`, `os.replace`) and a try/except around `load_session`'s parse. One corrupt file currently 500s that session permanently on six endpoints. | `memory/session.py:153-169` | S | ops |
| 27 | Cap session growth: sort `list_sessions` by mtime and parse only the newest 25; truncate `add_to_history` to the last 50 entries. Currently 756 files, 4.9MB, all parsed on every `/api/sessions` call. | `memory/session.py:179-212` | S | ops |
| 28 | Persist `bass_line`, `melody_direction` and `sound_engineering_response` in the session `output` dict. Free, the schema is JSON. | `api/main.py:277-280` | S | scenario-matrix |
| 29 | Serve the built frontend from FastAPI (`StaticFiles(directory="frontend/dist", html=True)`) and set the frontend base URL to `''`. One process, one port, same origin. Closes the CORS brittleness and the port-5173 coincidence, and lets a startup line log the bundle mtime so the stale-dist trap is visible. | `api/main.py:50`, `frontend/src/utils/api.js:3` | S | ops |
| 30 | Rebase `/api/health` on required deps only (music21) and move the rest into a `capabilities` block (ableton, ableton_script_patched, headless_claude, api_key). Today it reports "degraded" in the healthy state, so it is unusable as a signal. | `api/main.py:207-212` | S | ops |
| 31 | Surface `data.message` on the Blueprint-complete send instead of one hardcoded "is Live open?" string covering three different failures, and make the error persist until the next attempt rather than self-clearing after 3s. | `frontend/src/App.jsx:552-565, 790-792`, `MainWorkspace.jsx:167-172` | S | ops |
| 32 | Fix the headless classifier: run it via `asyncio.to_thread`, drop `not stage_biased` from the gate (it currently never fires at 12 of 14 stages, which is exactly where the dead ends are), and normalize its returned genres through the same `replace('-','_')` the keyword path uses. Measured 9.2s blocking today. | `agents/orchestrator.py:128-136`, `utils/headless_claude.py:38-49, 88-91` | M | scenario-matrix |
| 33 | Handle artist names at follow-up stages: extend `apply_stage_bias` so an `artist_reference` verdict at a biased stage keeps the stage's intent and passes artists through as flavor. Today "make the bass more like Massive Attack" throws away the confirmed progression and rewinds the sidebar. | `agents/intent_detection.py:221-222`, `sessionStages.js:130-135` | M | scenario-matrix |
| 34 | Fix `to_ascii` to iterate `sound_order + sorted(remaining)`. RIDE, CONGA, BONGO, COWBELL and SNAP can never print, which hides the defining voice of eight of the new patterns. Debug surface only, the API path is fine. | `theory/drum_patterns.py:144-152` | S | theory-data |
| 35 | Fix `DrumHit.beat_str` for multi-bar (`beat = (self.step % 16) // 4 + 1` plus a bar number) before any `bars=2` entry lands. Today step 28 reports "beat 8". | `theory/drum_patterns.py:84-95, 74` | S | theory-data |
| 36 | Decide what `swing` means. It is metadata only, never applied to the emitted grid, so blues_shuffle and jazz_swing_ride export straight. Either implement it in `to_grid`/MIDI export, or reword the descriptions to say plainly that it is an instruction for the DAW groove pool. | `theory/drum_patterns.py:648`, `agents/teaching_agent.py:198, 366, 389-390` | M (reword) / L (implement) | theory-data |
| 37 | Add one parametrized integration test that walks every stage id in `STAGE_INTENT_BIAS` with a no-keyword prompt and asserts a renderable payload. That single test would have caught actions 1, 7 and 17 before the field session. Plus three ops tests: arrangement send with a refused connection, `load_session` on truncated JSON, `execute()` with `headless_available` False. | `tests/integration/` | M | scenario-matrix, ops |
| 38 | Delete the `.env` setup step from the README and retire `.env.example`. Nothing calls `load_dotenv`, `python-dotenv` is not installed, so following the README exactly produces no effect and no error. Replace with an honest line about the `claude` binary path. | `README.md:22-25`, `.env.example:12` | S | ops |
| 39 | Add `requirements-dev.txt` with pytest and playwright (the README's step 6 currently fails on a clean clone) and correct or drop the "92 tests" count (it is 145 non-e2e plus 8 e2e). | `requirements.txt`, `README.md:46-50` | S | ops |
| 40 | Add a LICENSE and a four-line `docs/README.md` stating the /docs corpus is compiled research grounding with inline sources retained, not an authoritative reference. Credibility item for a public portfolio repo aimed at music companies. | repo root, `docs/` | S | ops |

---

## 3. Prod-readiness verdict

**Prod can only mean a packaged local Mac app.** Two dependencies are hard-pinned to Shannon's machine: the MCP socket at `localhost:9877` (`services/mcp_client.py:35-36`) and headless Claude at `/Users/shannondaly/.local/bin/claude` running on her personal subscription (`utils/headless_claude.py:15`). Neither survives a hosted deploy, and a hosted UI with a local bridge would still need the bridge installed per user. Framed as "one process, one port, one command on the producer's Mac", the gap list gets smaller, not bigger.

**What actually stands between this and that target, in order:**

1. **The Ableton send can lie.** Live auto-updates and silently restores the stock remote script (it did this on 2026-09-01, 12.4.2 to 12.4.5). The client detects it, logs it, then returns `success: True` counting notes it sent rather than notes Live accepted. The UI shows "Sent ✓" over an empty clip. On camera you find out by looking at the piano roll. Action 4.
2. **There is no working health signal.** `/api/health` ANDs in `api_key_configured` and `ableton_connected`, both normally false by design, so it reports "degraded" when everything is fine and has no distinguishable unhealthy state. It also does not check the `claude` binary, which is the actual LLM dependency. Action 30.
3. **One prompt stalls the server.** Every endpoint is `async def` doing blocking I/O. The keyword-blank path (the exact path "blues", "jazzy", "dusty", "moody" hit in the field) shells out to `claude -p` with a 90s timeout on the event loop. Measured 9.2s for one classification. Health queues behind it. Action 8.
4. **The direct-run command is an open door.** `python api/main.py` binds 0.0.0.0 with no auth and no rate limit on an endpoint that spends her subscription, and the raw prompt is piped into an agent with no tool restriction, running in the repo's working directory. Action 9.
5. **The product still goes blank on ordinary use.** 30 of 40 mix-stage cells and three recognized genres return no payload, and the frontend response to no payload is to erase the workspace including work the user confirmed. Two of three session modes cannot be completed without the Skip button. This is not a deploy problem but it is a "would not ship" problem. Actions 1, 5, 6, 7.

**What does not stand in the way, despite looking like it might:** JSON files as the session store are correct for a single-user local app (they just need atomic writes and a cap). No CI, containers, observability stack or multi-user anything is warranted. The 5-package `requirements.txt` is fine for runtime.

**Honest sequence:** actions 1, 4, 5, 7, 8, 9, 30 make it demo-safe. Add 2, 3, 6, 10, 11, 26, 27, 29 and it is a defensible v1 local app. Everything else is quality of answer, not readiness.

---

## Appendix A: Vocabulary lane, full findings

Method: audited every keyword list in `agents/intent_detection.py` and every mood/genre-keyed selection rule downstream, then probed each against live code in the project venv.

Headline numbers: `MOOD_KEYWORDS` holds 11 words against 31 mood tags in the progression corpus. `GENRE_KEYWORDS` holds 13 against 22 `GENRE_PROGRESSIONS` keys and 21 `GENRE_DRUM_PATTERNS` keys.

### A1. lo-fi / j-pop / k-pop genre lookup is silently dead (HIGH)

`theory/genre_progressions.py:462` normalizes the *query* (`genre.lower().replace(' ','_').replace('-','_')`) but compares it against `prog.genres` (line 463) and `GENRE_PROGRESSIONS` keys (line 465), both of which store the literal dashed tags `'lo-fi'`, `'j-pop'`, `'k-pop'`. Neither tier can ever match.

Verified: `search_progressions(genre='lo-fi', key_type='minor')` returns byte-identical results to `search_progressions(genre='zzzz', key_type='minor')`: 10 progressions topped by Andalusian Cadence, scored purely on key_type. Same for `'lo_fi'` (which is what `agents/intent_detection.py:256` actually emits), `'j-pop'`, `'k-pop'`. Every other genre works: trap, jazz, house, pop, r&b, chillhop all differ from the unknown baseline.

This is the project's flagship genre and one of the hardcoded `preferred_genres` in CLAUDE.md.

Fix inside the existing tables: normalize both sides at 463/465 (`if genre_key in [g.lower().replace('-','_') for g in prog.genres]`) and add underscore aliases `'lo_fi'`, `'j_pop'`, `'k_pop'` to `GENRE_PROGRESSIONS` (lines 326, 358, 359). Drums are unaffected: `theory/drum_patterns.py:585` `_normalize_key` tries dash and underscore variants, which is the pattern `genre_progressions.py` should copy.

### A2. MOOD_KEYWORDS carries 11 words; the corpus already ranks on 31 (HIGH)

Current (`agents/intent_detection.py:47-48`): melancholic, happy, sad, dark, chill, uplifting, epic, dreamy, nostalgic, aggressive, romantic.

Mood tags carried by the 21 progressions in `theory/genre_progressions.py`: anthemic, bittersweet, chill, classic, dark, dramatic, dreamy, emotional, energetic, epic, ethereal, euphoric, groovy, happy, head-nodding, hopeful, introspective, melancholic, mysterious, noir, nostalgic, raw, resolved, romantic, smooth, sophisticated, soulful, tense, tragic, uplifting, youthful. `MOOD_PROGRESSIONS` (lines 367-384) additionally keys on ethereal, groovy, hopeful, bittersweet, tense, mysterious. All are already selectable via `search_progressions(mood=...)` and score +3. They are simply never extracted.

**Free wins, add to MOOD_KEYWORDS, zero other changes** (each verified to return a distinct non-baseline ranking):

| Word | Where it already lands |
|---|---|
| ethereal | Classic Trance / Minor Line Cliché; also feeds the contour branch at `theory_local.py:240` and the Ben Böhmer ARTIST_REFERENCES row |
| groovy | Boom Bap / Jazz Turnaround / 12-Bar Blues; feeds the GRiZ row at `theory_local.py:365` |
| soulful | Minor Plagal / 12-Bar Blues |
| anthemic | Epic Minor / Axis / EDM Anthem |
| introspective | Minor Plagal / Emotional Trap |
| smooth | Jazz Turnaround / ii-V-I Major |
| sophisticated | Minor Line Cliché / ii-V-i Minor |
| euphoric | EDM Anthem |
| energetic | Pop Punk |
| tense, mysterious, hopeful, bittersweet, dramatic, tragic, noir, emotional, youthful | existing tags, all reachable |

**Needs a keyword AND a MOOD_PROGRESSIONS row** (field-observed blanks with no tag anywhere; each currently returns the identical unknown-word baseline):

| Word | Proposed MOOD_PROGRESSIONS row |
|---|---|
| moody | `['lofi_sad','epic_minor','minor_line_cliche','trap_emotional']` |
| dusty | `['lofi_sad','lofi_chill','boom_bap']` |
| gritty | `['blues','boom_bap','andalusian']` |
| mellow | `['lofi_chill','jazz_turnaround','two_five_one_major']` |
| cinematic | `['epic_minor','minor_line_cliche','tragic','andalusian']` |
| bouncy | `['boom_bap','axis','blues']` |
| wavy | `['lofi_chill','trap_emotional','lofi_sad']` |
| hype | `['edm_anthem','pop_punk','trance']` |
| haunting / eerie | `['minor_line_cliche','andalusian','two_five_one_minor']` |
| warm | `['lofi_chill','50s','minor_plagal']` |
| angsty | `['pop_punk','trap_emotional','epic_minor']` |

### A3. GENRE_KEYWORDS carries 13 words; 20+ genres have rows they can never reach (HIGH)

Current (`intent_detection.py:49-50`): lo-fi, lofi, trap, jazz, rock, pop, edm, house, hip-hop, hip hop, r&b, classical, ambient.

**Selects a progression today, just add the keyword:** `blues` (a genre tag on the 12-Bar Blues progression, scores +3, and the exact word the user typed in the field session), `soul` (Minor Plagal / 50s / Jazz Turnaround), `neo soul` / `neo_soul` (ii-V-i Minor / Jazz Turnaround), `trance` (Classic Trance / Epic Minor), `indie`, `chillhop`, `emo rap`, `future bass`, `film score`, `pop punk`, `folk`, `country`, `metal`.

**Selects drums only today** (add to GENRE_KEYWORDS so `_lookup_drums` can key off them; every one currently falls through to the hardcoded trap default at `orchestrator_pipeline.py:187`):

| Keyword | Patterns it reaches |
|---|---|
| techno | techno_driving / house_basic |
| drill, uk drill | uk_drill / chicago_drill |
| dnb, drum and bass, drum n bass | halftime / breakbeat |
| breakbeat | breakbeat |
| reggaeton | dembow |
| latin | dembow |
| boom bap | boom_bap_basic / boom_bap_syncopated |
| deep house | house_groovy |
| halftime | halftime |

**Needs a keyword AND table rows** (no data anywhere today): funk, disco, garage / uk garage, dubstep, synthwave, phonk, jungle, afrobeats, amapiano, grime, reggae, shoegaze, trip-hop.

Proposed `GENRE_PROGRESSIONS` rows: `'funk': ['blues','jazz_turnaround','boom_bap']`, `'disco': ['edm_anthem','50s','axis']`, `'garage': ['edm_anthem','lofi_chill','axis']`, `'dubstep': ['epic_minor','andalusian','trap_emotional']`, `'synthwave': ['epic_minor','axis','trance']`, `'phonk': ['trap_emotional','epic_minor','andalusian']`, `'trip_hop': ['minor_line_cliche','lofi_sad','minor_plagal']`.

Proposed `GENRE_DRUM_PATTERNS` rows reusing existing patterns: `'garage': ['house_groovy','breakbeat']`, `'jungle': ['breakbeat','halftime']`, `'dubstep': ['halftime','trap_basic']`, `'phonk': ['trap_basic','trap_triplet_hats']`, `'afrobeats': ['dembow','house_groovy']`, `'disco': ['house_basic','rock_basic']`, `'funk': ['boom_bap_syncopated','rnb_groove']`.

Also: `ambient` is in GENRE_KEYWORDS but has no row in either table. It is extracted, then silently produces the unknown-word baseline (verified: "ambient pad" gives F# minor Andalusian Cadence). It functions only as a key-mode hint via MINOR_GENRES.

### A4. Mix-stage vibe words return an empty payload (HIGH)

`intent_detection.py:67-83` `STAGE_INTENT_BIAS` guarantees anything typed at `mix`/`eq`/`automation`/`targetVibe`/`section` becomes `sound_engineering`. `orchestrator_pipeline.py:100-107` then calls `generate_sound_engineering_local(prompt)`; if that returns None and there is no API key, `local_data` stays `{}` and `build_response` returns a bare skeleton with no `sound_engineering_response` key at all.

`agents/se_local_data.py:144-155` `KEYWORD_TO_TOPIC` is 25 keys over 9 topics, all nouns for tools (sidechain, eq, compress, reverb, automate, filter, bass, kick, synthesis). No adjective a producer would type at a mix stage is in it. Verified empty payloads: "make it warmer", "make it punchy", "wavy and dusty", "make it hit harder". ("give it more space" works only because "space" happens to be a reverb alias.)

Proposed additions:

| Words | Topic |
|---|---|
| warm, warmer, analog, saturate, saturation, tape, fat, thick | new `saturation` topic (Saturator, drive, harmonics) |
| punch, punchy, snappy, transient, hit harder, harder | compress |
| glue, gel, cohesive | compress |
| muddy, mud, boomy, harsh, boxy, thin, tinny, bright, brighter, dull, dark | eq |
| wide, wider, stereo, width, roomy, ambient, spacey, distant | reverb |
| loud, louder, quiet, headroom, lufs, master, export | new `loudness` topic |
| pump, pumping, breathing, duck | sidechain |
| gritty, dirty, crunchy, distort | saturation |
| dusty, vinyl, lofi, crackle, old | new `lofi_texture` topic |

Then add a final fallback in `generate_sound_engineering_local` (`se_local_data.py:171-177`): when nothing matches, return the eq response with a one-line "here is the general approach" summary rather than None. The empty-payload path should be unreachable in local mode.

### A5. Drum selection is genre-only, so every mood word and unknown genre gets trap (HIGH)

`orchestrator_pipeline.py:187`: `genres = extracted.get('genres') or ['trap']`. There is no mood path into drum selection at all.

Verified misfires: "give me a drum and bass beat" gives drum_pattern intent with empty genres, so **trap**. "afrobeats vibe please" gives drum_pattern (via the substring bug), empty genres, so **trap**. "something dusty" gives mood_vibe, and even at the drums stage there is no route to the existing `lofi_dusty` pattern (`drum_patterns.py:315`) even though it is literally named Dusty.

### A6. Proposed MOOD_DRUM_PATTERNS table

Add next to `GENRE_DRUM_PATTERNS` (`theory/drum_patterns.py:578`), same shape, then in `_lookup_drums` iterate `extracted.get('moods', [])` against it after the genre loop and before the trap fallback.

```
'dusty':      ['lofi_dusty','lofi_basic','boom_bap_basic']
'chill':      ['lofi_basic','lofi_dusty']
'groovy':     ['house_groovy','boom_bap_syncopated','rnb_groove']
'bouncy':     ['house_groovy','uk_drill','dembow']
'aggressive': ['techno_driving','rock_driving','trap_rolling_hats']
'hype':       ['house_basic','techno_driving','trap_rolling_hats']
'dark':       ['uk_drill','techno_driving','trap_basic']
'mellow':     ['lofi_basic','rnb_groove']
'energetic':  ['rock_driving','breakbeat','house_basic']
'moody':      ['lofi_dusty','uk_drill','halftime']
```

### A7. Every unrecognized word produces the identical output (MEDIUM)

Two collapses stack.

(1) `theory/genre_progressions.py:455-495`: an unmatched mood or genre contributes 0 to every progression, so the only surviving score is the +1 key_type match. "moody", "dusty", "gritty", "mellow", "cinematic", "techno", "funk", "ambient", "k-pop" and a nonsense string all return the same 10 progressions in the same order, topped by Andalusian Cadence.

(2) `agents/theory_local.py:381-387` `get_artist_reference` initializes `best_score = -1` and takes `score > best_score`, so a zero-overlap vibe always returns `ARTIST_REFERENCES[0]`. Every unrecognized prompt is told "Massive Attack, sparse, Phrygian-influenced melodies". Verified for blank, techno, dnb, garage, reggaeton, blues and moody inputs. The documented fallback string at lines 389-392 is dead code: `best_ref` is never None once the list is non-empty.

Minimum fix: line 384 becomes `if score > best_score and score > 0`. Optionally have `_lookup_progressions` record which extracted words scored 0 so the UI can say it does not know "dusty" yet rather than confidently serving Andalusian Cadence.

### A8. Substring matching already misfires on live vocabulary (MEDIUM)

Every list is checked with `kw in prompt_lower` (`intent_detection.py:250-256, 262-285`; `se_local_data.py:171`). Confirmed live misroutes:

| Token | List | Live misroute |
|---|---|---|
| `mix` | SOUND_ENGINEERING_KEYWORDS (`:56`) | "give me a mixolydian melody" routes to sound_engineering. Also catches "remix". Mixolydian is a mode this app actively references (`theory_local.py:366`) |
| `eq` | SOUND_ENGINEERING_KEYWORDS (`:56`) | "what order should the sequence go in" routes to sound_engineering. Also catches technique, equal, frequent |
| `beat` | DRUM_KEYWORDS (`:51`) | "afrobeats vibe please" and "something upbeat" both route to drum_pattern, which serves trap. Also breakbeat, offbeat, downbeat, heartbeat |
| `sub` | KEYWORD_TO_TOPIC (`:151`) | "add subtle saturation" resolves to the bass mixing answer. Also subtractive, substitute |
| `pop` | GENRE_KEYWORDS (`:49`) | "hyperpop energy" extracts genre `pop` |

Interim table fix: make `mix` and `eq` boundary-guarded (`' mix'`, `'mixing'`, `'mixdown'`, `'the mix'`; `'eq '`, `'eq.'`, `'eq the'`, keep `'equaliz'`), require `beat` not to be preceded by a letter, change `sub` to `'sub bass'` / `'sub-bass'` / `' sub '`. The shared `_matches` helper is the smallest mechanism change that removes the whole class.

### A9. Words that must NOT be added bare

| Word | Collides with | Safe form |
|---|---|---|
| trip (trip-hop) | **triplet**, which appears in the app's own rhythm_feel copy (`theory_local.py:249`) and in prompts ("triplet hats") | `trip-hop`, `trip hop`, `triphop` |
| arp | **sharp**, and "C sharp minor" is a supported key phrasing | `arpeggio`, `arpeggiate`, `arps` |
| emo | **demo**, emotional, memory | `emo rap`, `emo-rap` |
| techno | **technique**, technical | boundary match, or accept knowingly |
| metal | **metallic**, a common mix descriptor | boundary match |
| raw | **draw** / drawing; "Draw Mode" and "draw automation" are in the app's own Ableton instructions | boundary match |
| hype | hyperpop | boundary match |
| wave | synthwave, wavetable | boundary match |
| house | warehouse | boundary match |
| drill | drilling | boundary match |
| disco | disconnect | boundary match |
| lead | leading, leads | boundary match |

**Safe as-is, no collisions found:** blues, jazzy (already caught by jazz), dusty, moody, gritty, bouncy, ethereal, cinematic, groovy, mellow, wavy, soulful, anthemic, dnb, garage, ambient, funk (also catches the desirable "funky"), soul (also catches the desirable "soulful"), afrobeats, reggaeton, synthwave, phonk, jungle, grime, amapiano, shoegaze, dubstep, breakbeat, boom bap.

### A10. Key inference tables lag the keyword lists (MEDIUM)

`intent_detection.py:103-106`: MINOR_MOODS/MAJOR_MOODS cover 9 of the 11 existing mood keywords; MINOR_GENRES/MAJOR_GENRES cover 8 of the 13 genre keywords. Unclassified today: moods `chill`, `dreamy`; genres `jazz`, `rock`, `hip hop`, `r&b`, `classical`. Anything unclassified falls to `FALLBACK_KEY[1]` = major at `orchestrator_pipeline.py:163`.

Verified: "something dreamy" gives Bb **major**, "something chill" gives G **major**, "an r&b thing" gives A **major**, even though `MOOD_PROGRESSIONS['dreamy']` is dominated by minor progressions (lofi_chill, lofi_sad, trance).

Note MINOR_GENRES uses underscored forms (`lo_fi`, `hip_hop`, `emo_rap`) matching the `'-'` to `'_'` conversion at line 256, but `hip hop` (space form, line 50) converts to `hip hop` and misses `hip_hop`.

Proposed:
- MINOR_MOODS += dreamy, moody, gritty, ethereal, mysterious, tense, noir, haunting, eerie, introspective, bittersweet, tragic, dramatic, dusty, cinematic
- MAJOR_MOODS += hopeful, groovy, soulful, anthemic, euphoric, bouncy, hype, mellow, smooth, warm, energetic
- MINOR_GENRES += drill, phonk, dnb, techno, dubstep, industrial, trip_hop, shoegaze, jungle, grime, emo, metal
- MAJOR_GENRES += disco, funk, soul, neo_soul, r&b, garage, afrobeats, reggaeton, synthwave, amapiano, country, folk

### A11. theory_local rule branches recognize ~14 tokens (MEDIUM)

`agents/theory_local.py:236-241` (contour), `:247-253` (rhythm_feel) and `:317-328` (bass) are the only places genre and mood actually change the musical advice. Their whole vocabulary:

- contour: {melancholic, sad, dark} / {uplifting, epic, happy} / {dreamy, ethereal, chill}
- rhythm: {lo_fi, lofi, chillhop, jazz} / {trap, hip_hop} / {edm, house, trance}
- bass: {trap, hip_hop, drill, emo_rap} / {lo_fi, lofi, chillhop, jazz} / {house, edm, dance, techno, disco}

Verified: dnb, garage, reggaeton, blues, breakbeat and afrobeats all fall to the generic "roots on beats 1 and 3" bass and "relaxed, mostly on the beat" rhythm. `moody` and `groovy` fall to the generic arch contour. (techno and disco already hit the house bass branch at line 325, they just cannot be extracted.)

**Proposed rhythm_feel rows (lines 247-253):**

| Genres | Advice |
|---|---|
| techno, industrial | locked to a driving 16th grid, hypnotic and unvarying |
| dnb, drum_and_bass, jungle, breakbeat | half-time melodic phrasing over a double-time break, long notes, the drums carry the speed |
| garage, uk_garage, 2step | shuffled 16ths, notes landing off the grid on the swung offbeats |
| funk, disco, soul, neo_soul, r&b | syncopated 16ths with rests on the downbeat, phrasing pushes and pulls around beat 1 |
| blues | swung eighths with bends into the 3rd and 7th |
| reggaeton, latin, afrobeats | phrases sit across the dembow accent, never square on the beat |
| drill, phonk | sparse, sliding, half-time with long gaps |

**Proposed bass rows (lines 317-328):**

| Genres | Advice |
|---|---|
| dnb, jungle, breakbeat | one long reese/sub note per bar under the break, movement from the filter not the notes |
| garage, uk_garage, 2step | shuffled offbeat stabs, short and clipped, syncopated against the kick |
| funk, disco | sixteenth-note fingered line, ghost notes between roots, octave pops on the and-of-4 |
| blues | walking-adjacent shuffle outlining root-3rd-5th-6th over each chord |
| reggaeton, afrobeats, latin | root on the dembow accent, held through the pattern, no busy movement |

**Proposed contour rows (lines 236-241):**

| Moods | Advice |
|---|---|
| groovy, bouncy, funky | call-and-response, short rhythmic cell answered a step or third away |
| moody, mysterious, noir, haunting | narrow, circling the tonic with a chromatic neighbour, resolving late |
| anthemic, hype, euphoric | stepwise climb to a held peak note, then a wide drop back to the tonic |

### A12. ARTIST_REFERENCES coverage, and it is melody-only (MEDIUM)

`theory_local.py:348-373` scores on genres {trip_hop, lo_fi, ambient, edm, dubstep, house, dance, rock, metal, alternative, industrial, electronic, world_bass, funk, hip_hop, trap, emo_rap, chillhop, jazz, progressive} and moods {dark, melancholic, mysterious, nostalgic, aggressive, epic, uplifting, happy, dreamy, ethereal, tense, groovy, chill}.

Absent: techno, dnb, garage, disco, soul, neo_soul, blues, drill, phonk, reggaeton, afrobeats, synthwave, and the moods soulful, anthemic, bouncy, hype, moody, gritty, smooth, sophisticated. Because of first-entry-wins (A7), each silently yields the Massive Attack line.

Proposed new rows (genres / moods): `{techno, industrial} / {dark, hypnotic, aggressive}`; `{dnb, jungle, breakbeat} / {dark, energetic}`; `{garage, uk_garage, house} / {bouncy, groovy, uplifting}`; `{blues, rock, soul} / {raw, soulful, groovy}`; `{disco, funk, soul, neo_soul} / {groovy, smooth, happy}`; `{drill, phonk, trap} / {dark, gritty, aggressive}`; `{reggaeton, afrobeats, latin} / {bouncy, happy, groovy}`; `{synthwave, edm} / {nostalgic, cinematic, epic}`.

Scope note: this table is consumed only by `generate_melody_direction_local` (`theory_local.py:267`). `generate_bass_line_local` carries its own reference strings inline (`:311-332`). There is no equivalent for drums (`orchestrator_pipeline.py:350-372` emits drum_patterns with no reference field) or for mix (`se_local_data.py` responses have a fixed per-topic `artist_reference` that never varies with genre or mood). Any DRUM_REFERENCES / MIX_REFERENCES layer should key off the same normalized vocabulary so one keyword addition lights up all four instruments.

### A13. MELODY_KEYWORDS and BASS_KEYWORDS miss producer words (LOW)

`intent_detection.py:52` MELODY_KEYWORDS = melody, melodic, topline, top line, lead line, vocal line. Safe additions: `hook`, `riff`, `motif`, `arpeggio`, `arpeggiate`, `counter melody`, `countermelody`, `lead synth`, `pad line`, `main line`. (Not bare `arp`, not bare `lead`.)

`intent_detection.py:53-54` BASS_KEYWORDS = bass line, bassline, bass groove, walking bass, 808 line, sub line, low end, low-end, sub bass, 808. Missing: `reese`, `wobble bass`, `acid bass`, `303`, `bass part`, `bass sound`, `give me a bass`. Bare `bass` is deliberately excluded (it would swallow "drum and bass" and "bass eq"), which is correct, but it means "give me a bass" currently falls to mood_vibe.

The bass_style branch at `:274-279` recognizes only sub / trap(808) / walking. Extend with `'reese'` or `'wobble'` to `bass_style='reese'`, `'acid'` or `'303'` to `'acid'`, and add matching branches to `generate_bass_line_local` (`theory_local.py:308-332`).

### A14. Multi-word genre phrasing is inconsistent (LOW)

GENRE_KEYWORDS carries both `'hip-hop'` and `'hip hop'` but only `'lo-fi'`/`'lofi'` (no `'lo fi'`). Line 256 normalizes only `'-'` to `'_'`, not spaces, so `'hip hop'` is stored as `'hip hop'`, which matches nothing in MINOR_GENRES, GENRE_PROGRESSIONS or GENRE_DRUM_PATTERNS. The theory_local norm sets do normalize spaces (`:305`, `:378`), so the bass and artist-reference paths survive but progression, drum and key-inference do not.

Every multi-word genre added above (`drum and bass`, `boom bap`, `neo soul`, `deep house`, `uk garage`, `future bass`, `emo rap`, `film score`, `trip hop`) hits the same asymmetry. Fix once at line 256: `.replace('-', '_').replace(' ', '_')`, and add space-form spellings alongside the dashed ones.

---

## Appendix B: Theory-data lane, full corrected findings

Method: adversarial review of 15 proposed progressions and 18 drum patterns against the real engine. Every claim re-executed rather than trusted. All structural/code claims CONFIRMED verbatim, including the exact 34-genre and 16-mood unreachable lists. Six musical defects found and fixed. Corrected data at:

`/private/tmp/claude-501/-Users-shannondaly/b24b53af-f2ec-40b5-a5d8-a6987fe33f77/scratchpad/proposed_reviewed.py`

All 15 progressions and 18 patterns re-validated after correction: 0 failures on step range, velocity range, `to_grid()` and `to_ascii()`.

### B1. Six musical errors found and fixed (HIGH)

The proposal's own harness only checked that entries parse and render without exception. It never checked whether the rendered music matches what the entry claims to be.

1. **gospel_6251, name/content mismatch.** Named "Gospel 6-2-5-1", numerals `['vi7','II7','ii7','V7']` render Am7 D7 Dm7 G7 in C. There is no I chord anywhere; it is a 6-2-2-5 that never resolves. **Fixed** to `['vi7','II7','V7','Imaj7']` giving Am7 D7 G7 Cmaj7, the genuine gospel 6-2-5-1 with the secondary dominant. Bonus: all four numerals already exist in ROMAN_NUMERALS, so this entry no longer depends on the parser additions (dependent count drops from 4 to 3).
2. **punk_dbeat, not a d-beat and self-contradicting.** Hits were K 0,3,8,11 while the description said "kick on 1 and the and-of-1". The & of 1 is step 2; step 3 is the "a". Neither reading is a d-beat. **Fixed** to K 0,6,8 (1, the &-of-2, 3), the canonical Discharge pattern, snare unchanged on 4/12. Verified: `beat_str` now reports `['1','2 &','3']`.
3. **blues_slow_stomp, kick on step 9**, the second 16th of beat 3. Musically arbitrary for a slow stomp and not mentioned in its own description. **Fixed** to step 10 (the & of 3), the standard slow-blues kick.
4. **afrobeats_basic, false theory claim.** Description said the kick "follows the 3-3-2 tresillo" but the kicks are 0,6,10. Tresillo is 0,3,6 (and 8,11,14), which the proposal itself implements correctly in phonk_memphis's cowbell, proving it knew the figure. Kicks 0,6,10 (1, &-of-2, &-of-3) are a real and common afrobeats figure, so hits kept, **description fixed**, `tresillo` tag dropped. Tags are now `['afrobeats','percussion','syncopated','offbeat_kick']`.
5-6. **Genre mispairings dropped**, since they would misroute retrieval: `metal` off punk_dbeat (metal's fast analogue is the blast beat or double kick, not a d-beat), `dancehall` off afrobeats_basic (dancehall's identity is the dembow, which already exists as its own pattern at `drum_patterns.py:494`), `jazz_hop` off jazz_swing_ride (jazz_hop is straight-eighth boom-bap, not a 90-220 BPM swung bebop ride).

Knock-on to the alias rows: `metal` should no longer map to punk_dbeat (leave it on rock_driving only), and the proposed `metal` progression row should drop phonk_memphis. Andalusian and epic_minor are genuinely Phrygian and metal-adjacent; a Memphis phonk loop is not.

### B2. The "correctly spelled in all 6 keys" claim is false (HIGH)

Two of the six claimed keys fail. The proposal's spelling check evidently only hunted double sharps on the bVII path and missed the flat side entirely.

Measured, on the corrected data:

| Progression | Key | Output |
|---|---|---|
| blues_minor | Eb minor | VI7 renders Cbdominant7, notes `['Cb4','Eb4','Gb4','Bbb4']`. A real chart writes B7 |
| blues_turnaround | F# major | VI7 renders D#dominant7 containing F## |

Eb minor and F# major are both ordinary keys a producer will pick. A wider 12-key scan also flags blues_minor (Db, Ab), liquid_dnb (Db), synthwave_outrun (Db), phonk_memphis (Db).

Clean in all 12 keys: blues_12_bar, funk_dorian_vamp, funk_one_chord, gospel_6251, gospel_walkup, neo_soul_9ths, bossa_classic, ambient_suspended, techno_two_chord, country_three_chord.

This is a **different root cause** from the bVI/bVII finding (B8). That one is the flat-numeral `transpose()` path. This one is `Chord.get_notes()` spelling a 7th or 9th stacked on a diatonic degree that is already flat-side (VI in Eb minor is legitimately Cb, and a dominant 7th on Cb legitimately needs Bbb). The theory is correct; the output is unusable, and it would display as a double accidental in the UI and in Ableton instructions.

The numerals are musically right, so this is not fixable in the data. Fix is an enharmonic respell at the chord layer. Until then, the honest statement is "validated in C/A/Bb/D; Eb minor and F# major produce double accidentals".

### B3. Roman-numeral parser silently mis-qualifies dominant 7ths and strips 9ths (HIGH)

Confirmed by execution, every claim exact. The fallback parser at `theory/progressions.py:126-146` does not raise on unknown-but-parseable numerals, it guesses, and guesses wrong for precisely the chords this data needs.

| Call | Returns | Should be |
|---|---|---|
| `roman_to_chord('VI7','C','major')` | Amajor7 `['A3','C#4','E4','G#4']` | A7 |
| `roman_to_chord('I9','C','major')` | bare Cmajor `['C3','E3','G3']` | C9 |
| `roman_to_chord('IV7','A','minor')` | Dmajor7 `['D4','F#4','A4','C#5']`, C# outside both A minor and A dorian | D7 |
| `'Idom7'`, `'Imaj9'`, `'Isus2'`, `'#ivo'` | ValueError | (need keys) |

Cause: line 142, `quality = 'dominant7' if degree == 5 else 'major7'`, so any uppercase 7th that is not V becomes a major 7. The `'9'` matches no branch (only `'7'`, `'°'`, `'o'`, `'+'` are tested) so the extension is silently discarded. `'IV7'` is a hardcoded entry, `(4,'major7')` at line 53, not a parser guess, so the dorian funk IV7 is unreachable without a new key. `'I7'` is already taken as `(1,'major7')` at line 46, so the blues I7 genuinely needs its own `'Idom7'` key.

`_convert_progressions` swallows ValueError with a bare `pass` (`agents/orchestrator_pipeline.py:272-273`, confirmed), so a bad numeral makes the whole progression vanish with no log.

All 17 proposed qualities exist in CHORD_PATTERNS (verified: `9`, `m9`, `maj9`, `m11`, `sus2`, `dominant7`, `major7` all present). The ROMAN_NUMERALS additions are correct as proposed. `VI7=(6,'dominant7')` is right in both modes: in C major degree 6 is A giving A7 (V/ii); in A minor degree 6 is F giving F7 (bVI7). Same for IVdom7: F7 in C major (blues IV7), D7 in A minor (dorian IV7).

Authoring quirk confirmed: the diminished branch tests `'o' in suffix`, but `'o'` is alphabetic so it is stripped into base_numeral first. `'#ivo'` raises ValueError while `'#iv°'` correctly returns F#diminished. Use the ° character.

### B4. search_progressions never matches lo-fi (HIGH)

Confirmed independently of the vocabulary lane. `theory/genre_progressions.py:462` turns `'lo-fi'` into `'lo_fi'`, then compares against `prog.genres` (hyphenated) and `GENRE_PROGRESSIONS` (hyphenated key).

Measured: `search_progressions(genre='lo-fi')`, `(genre='lo_fi')` and `(genre='lofi')` all return `[]`.

`get_progressions_by_genre()` does this correctly via `_normalize_key()` (line 396), which tries five variations including both hyphen and underscore forms. The bug is confined to `search_progressions`, which is the function the orchestrator actually calls (`orchestrator_pipeline.py:171-173, 237, 418`).

Reconciliation with Appendix A1: the two lanes are consistent. With genre alone, the result is `[]`. With a `key_type` also passed (what the orchestrator does), key_type still scores 1 for every matching progression, so the genre contributes nothing and the user gets dict-order noise rather than an empty result. That is why this survived unnoticed: it only looks correct when a mood also matches.

Any new hyphenated genre key inherits the same silent failure, so this must land with the new data.

### B5. 34 genres and 16 moods are declared on entries but unreachable (MEDIUM)

Confirmed, and the exact lists match the proposal's claim precisely (14 + 20 = 34 genres, 16 moods). Both lookups only consult the hand-maintained genre-to-name maps. Each entry's own `genres` field is decorative for retrieval and read only by `search_progressions`, which has its own hyphen bug. Nothing keeps the two in sync.

**Declared on drum patterns, not a key in GENRE_DRUM_PATTERNS (14):** alt_rock, chicago_drill, dembow, disco, experimental, grime, indie, industrial, jazz_hop, jungle, old_school, punk, rap, soul.
So `get_patterns_by_genre('disco')` returns `[]` even though house_basic declares disco (line 346), and `'jungle'` returns `[]` even though breakbeat declares it (line 544).

**Declared on progressions, not a key in GENRE_PROGRESSIONS (20):** ballad, bebop, blues, boom_bap, country, doo_wop, emo, flamenco, folk, gospel, jazz_hop, metal, musical_theatre, old_school, oldies, pop_punk, sad_hop, singer_songwriter, uplifting_trance, wedding.

**Moods used on progressions, not keys in MOOD_PROGRESSIONS (16):** anthemic, classic, dramatic, emotional, energetic, euphoric, head-nodding, introspective, noir, raw, resolved, smooth, sophisticated, soulful, tragic, youthful.
`get_progressions_by_mood('soulful')` returns `[]` even though three progressions declare it, and several proposed entries use soulful, raw and sophisticated, so they would inherit the dead end.

**Coverage map, genres returning nothing:**
- Zero progressions AND zero drum patterns: blues, funk, gospel, disco, garage, ambient, synthwave, afrobeats, phonk, bossa, country, metal, punk.
- Zero drum patterns only: soul (3 progs), jazz (4 progs), trance, dubstep, downtempo/trip-hop, jungle, dancehall, amapiano.
- Zero progressions only: techno (2 patterns), dnb (2), drill (2), reggaeton (1).

The blues case is the sharpest illustration: a blues progression exists at `theory/genre_progressions.py:232` declaring `genres=['blues','rock','jazz']`, but `'blues'` is not a key in GENRE_PROGRESSIONS, so `get_progressions_by_genre('blues')` returns `[]`. The entry only surfaces incidentally through `search_progressions`' per-progression scan, with junk attached. Drill is the other notable hole: a first-class routed intent with two drum patterns (`drum_patterns.py:393, 411`) and no GENRE_PROGRESSIONS key at all.

Cheapest durable fix: derive the three maps from the entries' own genres/moods at import time, keeping the hand-written maps as curated ordering overrides. A one-line pytest asserting `declared_genres <= set(lookup_keys)` catches all 34 and keeps new data honest.

### B6. The 15 progressions, validated, with gospel_6251 corrected (HIGH)

All 15 render correct chords via `get_progression_chords`. Literal `Progression(...)` blocks in the corrected file; they slot into NAMED_PROGRESSIONS at `theory/genre_progressions.py:317`. Renders shown in C / A minor unless noted. Read alongside B2 for the Eb-minor and F#-major caveats.

**Blues**

| id | Tempo, key_type | Renders | Note |
|---|---|---|---|
| blues_12_bar | 70-140, major | C7 C7 C7 C7 / F7 F7 C7 C7 / G7 F7 C7 G7 | Standard 12-bar with turnaround, bar form correct. Supersedes the existing `blues` entry at line 232, which is 8 bars of plain triads |
| blues_minor | 60-120, minor | Am7 Dm7 Am7 Am7 / Dm7 Dm7 Am7 Am7 / F7 E7 Am7 E7 | Correct minor blues, the bVI7-V7 at bars 9-10 is right. Examples "The Thrill Is Gone" and "Equinox" are both genuine minor blues |
| blues_turnaround | 80-180, major | C7 A7 Dm7 G7 | Correct I7-VI7-ii7-V7 |

**Funk**

| id | Tempo | Renders | Note |
|---|---|---|---|
| funk_dorian_vamp | 95-125, minor | Am7 D7 Am7 D7 | The F# inside D7 is the raised 6th, so the "that's what makes it Dorian" note is accurate |
| funk_one_chord | 95-120, major | C9 C9 C9 F9 | |

**Gospel / soul / r&b**

| id | Tempo | Renders | Note |
|---|---|---|---|
| gospel_6251 | 60-120 | Am7 D7 G7 Cmaj7 | **CORRECTED** from Am7 D7 Dm7 G7, which never reached the 1 despite the name |
| gospel_walkup | 60-120 | C F F#diminished C | `['I','IV','#iv°','I']`. Correct chromatic passing diminished. The ° character is required |
| neo_soul_9ths | 65-100 | Dm9 G9 Cmaj9 Am9 | |

**Electronic**

| id | Tempo | Renders | Note |
|---|---|---|---|
| techno_two_chord | 120-145 | Am Am G G | |
| liquid_dnb | 165-178 | Am9 Fmaj7 Dm9 G | Tempo correct for dnb |
| ambient_suspended | 50-95 | Csus2 Fadd9 Am7 Fmaj9 | IV appears twice, fine for ambient |
| synthwave_outrun | 85-120 | Am G F G | |
| phonk_memphis | 130-165 | Am F G F | |

**Other**

| id | Tempo | Renders | Note |
|---|---|---|---|
| bossa_classic | 120-145 | Cmaj7 D7 Dm7 G7 | Correct Ipanema A-section motion |
| country_three_chord | 90-160 | C F C G | |

Every tempo range checked and sane for its genre.

**Deliberately not invented** (endorsed restraint): afrobeats, reggaeton, garage, drill and metal harmony. Those genres are defined rhythmically, not harmonically. Alias them to existing minor loops rather than fabricating entries.

### B7. The 18 drum patterns, validated, with three rhythmic fixes (HIGH)

Grid convention confirmed by reading `theory/drum_patterns.py:98-176`: a flat `hits` list of `_h(SOUND, step, velocity)` on a 16-step 16th grid, one bar. Step 0 = beat 1, 4 = beat 2, 8 = beat 3, 12 = beat 4. Shortcuts K S C CH OH R P at lines 180-186. RIDE, SHAKER, CONGA, COWBELL and TOM_LOW have no shortcut and are written inline, matching the existing precedent at line 381. All 18 pass step range, velocity range, `to_grid()` and `to_ascii()`.

`swing` is documented as "0-100, amount of swing" (line 106) and existing entries use 30/40/50/60/70, so the proposed 15, 55 and 66 are all in range. See B10 for what swing does not do.

**Corrected:** blues_slow_stomp kick 9 to 10; punk_dbeat K 0,3,8,11 to 0,6,8 with description and genres fixed; afrobeats_basic description and tags de-tresillo'd.

**Verified correct as proposed:**

| id | Tempo, swing | Grid and verdict |
|---|---|---|
| blues_shuffle | 70-130, sw66 | ride on 8ths plus swing = shuffle |
| blues_slow_stomp | sw66 | kick corrected to step 10 (& of 3) |
| gospel_praise_break | 150-210 | fast shout tempo is right |
| funk_sixteenth | 90-120, sw15 | K 0,6,10 with ghosted snares at 3,7,15 and 16th hats. Legitimate funk sixteenth; the low swing value is musically apt |
| motown_backbeat | 105-140 | snare on 2 and 4; tambourine honestly noted as occupying the shaker slot |
| disco_four_on_floor | 105-130 | open hat on every upbeat 8th (2,6,10,14), correct disco signature |
| techno_hypnotic | 125-145 | clap on step 12 only (beat 4), matching its "one landmark not two" claim |
| garage_2step | 128-140, sw55 | K 0,10 with no kick on 2 or 4, snare 4/12. Correct 2-step, tempo right for UKG. The highest-value missing pattern |
| dnb_two_step | 165-180 | K 0,10 / S 4,12, the canonical dnb two-step. Correct that neither existing `halftime` nor `breakbeat` is one |
| trip_hop_lean | 70-95, sw55 | snare on step 8 only = halftime backbeat on 3. Correct, tempo right |
| amapiano_log | 108-118 | four-on-floor with TOM_LOW log drum at 3,7,11,14. Tempo exactly right |
| phonk_memphis | 130-165 | cowbell at 0,3,6,8,11,14 is a genuine 3-3-2 tresillo across both halves. Correctly implemented, which is what exposed the afrobeats error |
| jazz_swing_ride | 90-220, sw66 | ride at 0,4,6,8,12,14 = ding, ding-a-ding; CH at 4,12 as the hi-hat foot on 2 and 4. Both correct conventions. The wide range is honest for swing |
| afrobeats_basic | | K 0,6,10, conga-led. Description corrected, tresillo tag dropped |
| punk_dbeat | | K 0,6,8 / S 4,12 corrected |
| ambient_pulse | | sane |
| synthwave_gated | | sane |
| jungle_amen | | sane |

Agreed on not proposing bossa or samba drums: their clave genuinely spans two bars (see B11).

### B8. bVI / bVII / bIII in a major key spell out with double sharps (MEDIUM)

Confirmed exactly. `roman_to_chord('bVII','C','major')` gives A#major `['A#3','C##4','E#4']`; `roman_to_chord('bVI','C','major')` gives G#major `['G#3','B#3','D#4']`. Pitch-wise enharmonically right, spelling wrong, and it would display as a double sharp in the UI and in Ableton instructions.

Cause: `theory/progressions.py:154-156` transposes the diatonic degree down a semitone via `transpose()`, which has no key context and defaults to sharps.

No existing NAMED_PROGRESSIONS entry uses bVI/bVII/bIII, so nothing is broken today. The numerals are defined at lines 33-35 and unused. The proposal correctly avoided them in all major-key entries, which is why mixolydian rock and major-key synthwave remain uncovered; those become writable once the flat path spells relative to the key.

The sharp direction is fine: `'#iv°'` correctly returns F#diminished in C, so gospel_walkup is safe now.

Pair with B2. Both are enharmonic spelling, but they are two distinct code paths (flat-numeral transpose versus extended-chord construction on a flat-side degree), and fixing one will not fix the other.

### B9. Progression tags are never searched (MEDIUM)

`search_progressions` accepts a `tags` argument and scores one point per matching tag (`theory/genre_progressions.py:489-491`), and the table carries a rich descriptive vocabulary there: `jazzy` on lofi_chill (line 291), `sad`/`nostalgic` on lofi_sad, `noir`/`chromatic` on minor_line_cliche, plus `spanish`, `viral`, `anthemic`, and `dusty` on the lofi_dusty drum pattern.

But every call site passes only mood, genre and key_type (`orchestrator_pipeline.py:171, 173, 237, 418`). `tags` is never populated from user input anywhere in the codebase, which is why "jazzy" and "dusty" draw blanks even though both words are literally present in the data.

Cheapest fix in the lane and it needs no new data: pass the user's unmatched adjectives through to `search_progressions(tags=[...])` and let the existing scoring work. It also gives the vocabulary lane somewhere to route words absent from MOOD_KEYWORDS instead of dropping them. Worth pairing with the new entries' tags, which already carry `dusty` (trip_hop_lean), `jazzy` (bossa_classic), `soulful`, `raw` and `hypnotic`.

### B10. swing is metadata only, never applied to the emitted grid (MEDIUM)

Not in the original proposal, found while checking its swing values. Grepped the whole project: `swing` is read only at `theory/drum_patterns.py:648` (formatted as a percentage string for `explain_pattern`) and in `agents/teaching_agent.py:198, 366, 389-390` (prose generation). Nothing applies it to hit timing, and `to_grid()` emits the raw straight-16th steps.

So for every pattern whose identity depends on swing, the exported grid is rhythmically wrong unless the producer manually sets groove in Ableton: blues_shuffle (sw66) exports as straight 8ths, not a shuffle; jazz_swing_ride (sw66) exports a straight-8th ride, which is the one thing a jazz ride must not be; gospel_praise_break (sw66), garage_2step (sw55), trip_hop_lean (sw55) and blues_slow_stomp (sw66) are all affected. The four existing swung patterns (lines 269, 287, 309, 327, 485) have the same issue today.

This does not block the data. The patterns are correctly authored on a straight grid with swing declared, which is the right representation. But blues_shuffle's description telling the user to "set swing to 66 so the offbeats land as triplets" assumes an MPC-style 50-75 percentage convention; this field is documented 0-100 and is not consumed by any timing code at all.

### B11. Bossa, samba and full dembow need bars=2, and the multi-bar path has a latent bug (LOW)

Confirmed. `DrumPattern` carries a `bars` field (`theory/drum_patterns.py:103`) and `to_ascii()` honours it (line 156), but all 18 existing patterns are 1 bar and nothing exercises bars > 1.

`DrumHit.beat_str` (lines 84-95) computes `beat = self.step // 4 + 1` with no modulo. Verified: `DrumHit(step=16).beat_str` returns "5" and `DrumHit(step=28).beat_str` returns "8". `explain_pattern()` (line 653) feeds those strings into its user-facing `beats` list, so a two-bar pattern would instruct the producer to play on beat 8 of a 4/4 bar. Fix is `beat = (self.step % 16) // 4 + 1` plus a bar number, and the DrumHit docstring at line 74 ("step: 0-15 for 16th notes in one bar") should describe the multi-bar convention.

Once the fix lands, the two worth adding are a bossa side-stick clave (rim over two bars against a surdo kick) and a full two-bar dembow alongside the existing one-bar `dembow` at line 494.

### B12. to_ascii() silently drops ride, conga, cowbell, bongo and snap rows (MEDIUM)

Confirmed by execution. `theory/drum_patterns.py:144-150` hardcodes `sound_order` as CLOSED_HAT, OPEN_HAT, SNARE, CLAP, RIM, KICK, TOM_HIGH, TOM_MID, TOM_LOW, PERC, SHAKER, and line 152 renders only sounds in that list. RIDE, CONGA, BONGO, COWBELL and SNAP are defined in DrumSound (lines 39-46) and mapped to MIDI notes (lines 60-67) but can never print.

Already live today: `get_drum_pattern('techno_driving').sounds_used` reports `['kick','ride','clap','closed_hat']`, but `to_ascii()` renders only closed_hat, clap and kick. The ride hits at line 381 are invisible.

This matters for the new data because blues_shuffle, blues_slow_stomp, gospel_praise_break, jazz_swing_ride and jungle_amen are ride-led, afrobeats_basic is conga-led, and phonk_memphis is cowbell-led. Their defining voice would be missing from any ASCII view.

The API path is unaffected: `to_grid()` iterates `sounds_used` and is complete (verified its keys include ride), and `orchestrator_pipeline.py:201` serialises `to_grid()`. So this is a dev/debug and teaching-note surface, not user-facing data loss.

### B13. Where the new entries slot in, and the alias rows they need (MEDIUM)

**Progressions:** 15 objects into NAMED_PROGRESSIONS before the closing brace at `theory/genre_progressions.py:317`, then new rows in GENRE_PROGRESSIONS (line 324) for blues, funk, gospel, disco, techno, dnb, jungle, ambient, synthwave, phonk, bossa_nova, country, punk, drill, reggaeton, afrobeats, garage, reusing existing entries wherever the genre is rhythmically rather than harmonically defined. Extend existing rows for neo_soul, r&b, soul, jazz, and lo-fi (adding the lofi/lo_fi aliases B4 needs).

**Correction to the proposed map:** `'metal'` should be `['andalusian','epic_minor']`, dropping phonk_memphis.

**Drum patterns:** 18 objects before the closing brace at `theory/drum_patterns.py:549`, then rows in GENRE_DRUM_PATTERNS (line 556) for blues, funk, soul, motown, gospel, disco, garage/uk_garage/2step, dnb (replacing line 575), jungle, trip_hop, downtempo, ambient, synthwave, retrowave, afrobeats, amapiano, phonk, jazz, swing, punk; extend techno at line 565.

**Correction:** `'metal'` should map to `['rock_driving']` only, since punk_dbeat is removed from it. That leaves metal thin on the drum side, which is an honest gap rather than a wrong answer.

Fold in the unreachable-alias rows from B5 at the same time, or better, replace the whole hand-maintained approach with import-time derivation.

---

## Appendix C: Scenario-matrix lane, full findings

Method: executed the full grid, 14 stage ids by 8 prompt shapes, against the real pipeline with the headless classifier stubbed off, then re-checked the live headless path once for latency.

**Grid verdict by stage:**

| Stage | Verdict |
|---|---|
| `progression` (no bias) | OK for in-vocabulary mood/genre/artist prompts. DEGRADED for out-of-vocabulary words and free-form (all collapse to the identical three C-major progressions). DEGRADED for explicit-harmony prompts, since the session key is never inherited |
| `melodyDir`, `bass` | OK on every prompt shape except artist names (which regenerate the harmony and rewind the sidebar). Out-of-vocabulary mood/genre words route correctly but have zero effect on the output |
| `drums`, `genreFeel`, `bpm`, `pattern`, `splice` | DEAD-END for jazz / classical / ambient (recognized genres with zero drum patterns, so empty list, so blank workspace). DEGRADED for tempo prompts (no BPM is ever extracted). `splice` can never be marked done |
| `mix`, `section`, `targetVibe`, `eq`, `automation` | DEAD-END on 6 of 8 prompt shapes, 30 cells returning `{success, intent, confidence}` with no body |

Routing itself is healthy: `apply_stage_bias` sends prompts to the right intent at every stage. Three of the five destinations have nothing to serve, and the frontend's stage bookkeeping cannot mark most non-chords stages at all.

### C1. Every mix/SE stage dead-ends on any prompt the 9-topic keyword table misses, 30 of 40 cells (HIGH)

Verified by execution: every one returns exactly `{success, intent:'sound_engineering', confidence:0.75, key_was_specified, tokens_used, cost_usd}` with no payload.

Trace: `apply_stage_bias` re-routes mood_vibe to sound_engineering for all five stages (`intent_detection.py:67-83, 220-230`), then `lookup_local` calls `generate_sound_engineering_local(prompt)` (`orchestrator_pipeline.py:100-107`), the keyword loop returns None when no key of the 40-entry `KEYWORD_TO_TOPIC` appears (`se_local_data.py:171-177`), the API fallback is gated on `has_api_key` which is False in zero-cost local mode (`orchestrator.py:59`, `orchestrator_pipeline.py:104`), so `local_data = {}` and `build_response` short-circuits at `if not local_data: return response` (`orchestrator_pipeline.py:297-298`).

Frontend consequence is worse than "nothing new": `normalizeGenerateResponse` has no progression and no drum so it returns `{empty:true, mode:'empty'}` (`normalize.js:86-88`), `setModel(normalized)` replaces the whole model (`App.jsx:296`), and `hasContentGeneration` is already true, so MainWorkspace renders `contentRoot` with no chord row, no SE panel, no teaching note and no error. The user's progression disappears and nothing replaces it.

The app's own suggested prefills land here: drums-mode mix prefill "Mix tips for punchy trap drums" (`sessionStages.js:112`) and mixing-mode targetVibe prefill "Warmer, wider drop" (`:116`) both return an empty payload, confirmed by running them.

### C2. The mixing session mode can never advance past its first stage (HIGH)

`applyApiToStages` for MIXING mode contains one line: `if (apiPayload?.intent) setDone('section', apiPayload.intent)` (`sessionStages.js:173-174`). Two defects fall out.

1. `targetVibe`, `eq`, `automation` are in `STAGE_SEQUENCES.mixing` (`:25`) but nothing ever marks them done. `handleKeep` only confirms a stage whose status is already `done` (`App.jsx:493-504` via `firstAwaitingConfirmStage`, `sessionStages.js:259-266`), so Keep is inert on them and `allStagesComplete` (`:380-389`) can never be true. The Blueprint-complete screen is unreachable in mixing mode.
2. `setDone` unconditionally rewrites `confirmed: false` (`:157-161`). So the second generation in a mixing session re-marks `section` done-unconfirmed, `recomputeActive` (`:217-244`) sets `blocked = true`, and the sidebar rewinds to stage 1. The user Keeps section, types the next prompt, and lands back on section.

Also visible: the value written into the section stage is the raw intent string, so the sidebar displays `sound_engineering` as the user's chosen section.

### C3. Drums mode: splice and mix are never markable, and every generation rewinds the other three (HIGH)

`STAGE_SEQUENCES.drums = ['genreFeel','bpm','pattern','splice','mix']` (`sessionStages.js:24`), but the DRUMS branch of `applyApiToStages` only ever sets genreFeel, bpm, pattern (`:163-172`).

Nothing in the codebase produces a Splice-search-terms payload at all. `apply_stage_bias` maps `splice` to `drum_pattern`, so the stage's own prefill "Splice search terms for trap kicks" returns three trap drum patterns (verified), never search terms. `mix` in drums mode routes to sound_engineering, whose payload the DRUMS branch ignores entirely.

Compounded by the same `confirmed:false` reset. Once the user Keeps through genreFeel/bpm/pattern and reaches splice, their next prompt re-marks all three unconfirmed and rewinds the sidebar to genreFeel. The drums session can only be completed using the Skip button (`ProgressSidebar.jsx:51, 117-126`).

Fix: the `confirmed` guard, plus map the drums-mode `mix` stage to `sound_engineering_response` the way chords mode does (`sessionStages.js:189-191`), and either drop `splice` from the sequence or mark it done off the drum result using the pattern's genre tags as the search terms.

### C4. A recognized genre with no drum patterns returns an empty list and blanks the screen (HIGH)

Verified: `execute('jazz', active_stage='drums')` returns `{'drum_patterns': []}` and nothing else.

`_lookup_drums` applies the `['trap']` fallback only when `extracted['genres']` is empty (`orchestrator_pipeline.py:187`). jazz, classical and ambient ARE in GENRE_KEYWORDS so genres is non-empty, but `get_drum_patterns_by_genre` returns 0 patterns for each. Checked all 13 genre keywords: jazz 0, classical 0, ambient 0, the rest 2-3.

`build_response` then guards on `if local_data["drum_patterns"]:` (`:353`) so bpm, genre_context, production_steps and teaching_note are all omitted, and the frontend's normalize sees `drum_patterns[0] === undefined` (`normalize.js:42`) and falls to the `{empty:true}` branch. Blank workspace, no error.

### C5. mood_vibe and theory_request ignore session_context (HIGH)

`lookup_local` threads `session_context` into melody_direction, bass_line and drum_pattern (`orchestrator_pipeline.py:71-98`) but the mood_vibe/theory_request branch calls `_lookup_progressions(extracted)` with no context at all (`:68-69`). With no mood/genre/key words in the prompt, `_lookup_progressions` resolves `key_mode` to `FALLBACK_KEY[1]` = major and `_vibe_key_root` returns the pool head 'C' (`:158-164, 138-141`).

Verified against the app's own sidebar prefill: in an A-minor lo-fi session, "Give me an alternative progression in the same key" (`sessionStages.js:84-85`) returns **C major**, Axis of Awesome / Pop Punk / 50s Doo-Wop. The frontend then writes that key into project state and the sidebar Key field (`App.jsx:303-308`). The same path fires for every `HARMONY_OVERRIDE_KEYWORDS` prompt at a follow-up stage (`intent_detection.py:87-88, 224-226`).

### C6. Naming an artist at any follow-up stage regenerates the harmony and rewinds the sidebar (MEDIUM)

`apply_stage_bias` re-routes only a `mood_vibe` verdict (`intent_detection.py:221-222`), and `detect_intent_local` returns `artist_reference` at 0.9 for a single known artist (`:287-288`) before mood_vibe is ever considered. Verified: "something like Massive Attack" at the `bass` stage returns a full new progression set with progressions/validation/production_steps/melody_direction and no bass_line.

Frontend: `artist_reference` is not in `FOLLOWUP_INTENT_STAGE` (`sessionStages.js:130-135`), so `applyApiToStages` takes the else branch and calls `setDone('progression', ...)` (`:193-195`), which resets `confirmed:false` and blocks every later stage. "Make the bass more like Massive Attack" throws away the confirmed progression and sends the user back to stage 1.

Fix: extend `apply_stage_bias` so an `artist_reference` verdict at a biased stage keeps the stage's intent and passes the artists through as flavor (`extracted['artists']`). The bass and melody generators already accept `intent_data`, and `get_artist_reference` (`theory_local.py:376`) can key off it.

### C7. production_question is a routable intent with no handler (MEDIUM)

Verified: `execute('how do i lay out my arrangement')` returns `{'success': True, 'intent': 'production_question', 'confidence': 0.8}` and nothing else.

`detect_intent_local` returns `production_question` at 0.8 (`intent_detection.py:61, 266-267`), but `lookup_local` has no `production_question` branch (`orchestrator_pipeline.py:68-121`), the same for `feedback_loop` and `unknown`. The headless classifier can also emit it: its system prompt lists `production_question` as a valid output (`utils/headless_claude.py:20-26`), so even the LLM safety net routes into the hole. Result is the C1 blank-workspace path.

### C8. The headless classifier blocks for ~9s and never runs at a biased stage (MEDIUM)

Three defects in the one path meant to catch "blues / jazzy / dusty / moody".

1. **Never fires where it is most needed.** The gate is `if not stage_biased and confidence <= 0.5 and not (moods|genres|key|artists)` (`agents/orchestrator.py:128-136`). Every prompt at melodyDir, bass, drums, mix, genreFeel, bpm, pattern, splice, section, targetVibe, eq, automation sets `stage_biased = True` (`intent_detection.py:230`), so the classifier is skipped at 12 of the 14 stages, exactly the cells that dead-end in C1 and C4.
2. **Blocking subprocess inside an async endpoint.** `call_headless` is a synchronous `subprocess.run` with a 90s timeout (`headless_claude.py:38-49`) called from `Orchestrator.execute`, awaited from `async def generate` (`api/main.py:248-264`). Measured live: **9.2s** for one classification, with no streaming or progress signal to the UI.
3. **Output is not normalized to the internal vocabulary.** `classify_intent_headless` returns genres verbatim (`headless_claude.py:88-91`); the live call returned `['lo-fi']`, while `detect_intent_local` stores the underscore form and `MINOR_GENRES` only contains `'lo_fi'`. Verified impact: the same vibe resolves to C minor via the headless path versus G minor via the keyword path, because `_vibe_key_root` hashes the raw strings (`orchestrator_pipeline.py:138-143`).

### C9. The drums-mode bpm stage cannot honor a tempo (MEDIUM)

Verified: the stage's own prefill "140 BPM trap beat" (`sessionStages.js:109`) returns **bpm 150**, the midpoint of Trap Basic's `tempo_range`.

`detect_intent_local` extracts key, artists, moods and genres but never a tempo (`intent_detection.py:239-256`). `tempo` appears only in the API-mode Haiku prompt (`:312`) and the headless prompt (`headless_claude.py:23`), and neither `lookup_local` nor `build_response` reads it. `build_response` always derives bpm from `parse_bpm_from_tempo(pattern['tempo_range'])` (`orchestrator_pipeline.py:355-357`). A dedicated sidebar stage exists for a value the backend cannot receive.

### C10. Every successful follow-up answer clears the chord row it is meant to annotate (LOW)

The melody and bass branches deliberately echo the session progression back so the UI keeps showing it (`orchestrator_pipeline.py:71-90`), and those two render fine. But `drum_pattern` returns only `drum_patterns` (`:92-98`) and `sound_engineering` returns only `sound_engineering_response` (`:100-107`).

`normalizeGenerateResponse` keys entirely off the presence of a progression: the drums payload takes the `mode:'drums'` branch with `chords: []` (`normalize.js:41-56`), the SE payload takes the `{empty:true}` branch, and `setModel` replaces the previous model wholesale (`App.jsx:295-296`). So the moment the user asks for drums or a mix note, the progression they just confirmed vanishes from the workspace. The SE panel at least still renders below (`App.jsx:836-843`); the drum case shows only the grid.

### C11. Session history persists only progressions and drum patterns (LOW)

`/api/generate` writes `output={"progressions":…, "drum_patterns":…}` and nothing else (`api/main.py:273-281`). `bass_line`, `melody_direction` and `sound_engineering_response` are dropped. So `_session_context` (`:235-245`) can never see a mix or bass answer; in mixing mode every history entry is `{progressions:None, drum_patterns:None}` so the context builder always returns None; and a reloaded session cannot restore the mix/bass panels (the frontend's `stageSnapshots` at `App.jsx:496-500` are in-memory only).

### C12. Stage-bias tests assert the verdict but never that the destination returns a payload (LOW)

`tests/unit/test_intent_detection.py:184-214` covers `apply_stage_bias` in isolation: that `mix` yields `sound_engineering`, that specific verdicts stand, that unknown stages no-op. Every one passes while the mix stage returns an empty body, because none of them run `lookup_local`/`build_response` behind the verdict. The integration suite tests sound_engineering only through a prompt that hits the keyword table (`tests/integration/test_generate.py:59-65`).

Dead code found while tracing: `apply_stage_bias` sets `extracted['question'] = prompt` (`intent_detection.py:228-229`) and a test asserts it (`test_intent_detection.py:191-195`), but `lookup_local` passes the raw `prompt` to the SE agent and never reads `extracted['question']` (`orchestrator_pipeline.py:101`).

One parametrized integration test walking each stage id in `STAGE_INTENT_BIAS` with a no-keyword prompt, asserting a renderable payload, would have caught C1, C4 and C7 before the field session.

---

## Appendix D: References lane

**This lane produced no usable output, and no new artist/reference data exists in this report.**

The payload the lane received contained exactly one row (title "probe", detail "probe", priority low) with no music-theory content: no progression names, no roman numerals, no key_type, no tempo ranges, no drum grids, and no artist/genre/mood rows. There was therefore nothing to check for numeral-versus-progression agreement, major/minor key_type consistency, genre-appropriate BPM, rhythmic sensibility, or artist-pairing accuracy.

The lane deleted the "probe" row as unsalvageable: it is a schema shape test, not a proposed engine addition, and merging it would inject a content-free row into the progressions, patterns and reference tables. Nothing was rewritten in place, since a row with no musical assertion cannot be corrected into a valid one, only removed.

What the lane did confirm:
- Schema round-trip works (summary plus `findings[]` with title/detail/priority).
- Checking the working tree at `/Users/shannondaly/daly-ai/knowledge-layer-showcase` for the engine's theory tables, the only music-related file is `rubato/index.html`, a showcase write-up describing the music21-backed deterministic validator, not the data tables.

Lane's own note for a re-run: route real rows with actual numerals, key_type, BPM and grid fields so the correctness checks have something to bite on. Per that showcase page, the deterministic music21 gate is the intended final authority, so this lane's review is a pre-filter ahead of it, not a replacement.

**Consequence for the action list:** the ARTIST_REFERENCES expansion (action 24) rests on the vocabulary lane's row proposals alone and has not been adversarially verified.

---

## Appendix E: Ops-readiness lane, full findings

Files read: `api/main.py`, `services/mcp_client.py`, `memory/session.py`, `utils/` (logging, headless_claude), `agents/orchestrator.py` and `orchestrator_pipeline.py`, the frontend serving path (`vite.config.js`, `src/utils/api.js`, `App.jsx`, `MainWorkspace.jsx`), `.env.example`, `.gitignore`, README/CLAUDE/BACKLOG, `ableton_remote/README.md`, and the test suite.

Nothing below proposes CI, containers, observability stacks, or multi-user anything. Those all failed the "one user today" test.

### E1. "Prod" is undefined; the only coherent target is a local packaged app (HIGH)

Two dependencies pin this to one machine: the MCP socket hardcoded to localhost:9877 (`services/mcp_client.py:35-36`) and `claude -p` invoked at `CLAUDE_BIN = "/Users/shannondaly/.local/bin/claude"` (`utils/headless_claude.py:15`), billing her subscription login. Neither can be hosted.

The built frontend hardcodes the backend to `http://localhost:8000` (`frontend/src/utils/api.js:3`: `import.meta.env.DEV ? '' : 'http://localhost:8000'`), and CORS allows exactly two origins (`api/main.py:50`). The current serving story from `RECORDING-KICKOFF.md:35` (`python3 -m http.server 5173` over `frontend/dist`) works only because 5173 happens to be on that allowlist. Serving on any other port, or opening `dist/index.html` over `file://`, is blocked by CORS with no useful error.

Smallest step: `app.mount("/", StaticFiles(directory="frontend/dist", html=True))` and change `api.js:3` to `const BASE = '';` unconditionally. One process on port 8000, same origin, CORS middleware becomes unnecessary rather than needing more entries, and the port coincidence disappears. Closes the CORS brittleness and the stale-dist trap.

### E2. A reverted Ableton remote script returns a silent false success (HIGH)

`ableton_remote/README.md` documents that Live auto-updates on launch (12.4.2 to 12.4.5 did this on 2026-09-01) and silently restores the stock script, whose legacy `set_notes` call is a no-op in Live 12.

The client already detects this: when `set_song_key` fails it logs "remote script may predate set_song_key" and continues (`services/mcp_client.py:109-112`). But that signal dies in the log. The function goes on to return `{"success": True, "message": f"Created {len(chords)} chords ({total_notes} notes)..."}` (`:215-219`) counting notes it *sent*, not notes Live *accepted*. The frontend renders "Sent to Ableton ✓". A silent success is worse than a failure: on camera you find out by looking at an empty piano roll.

Smallest step: the `set_song_key` probe is already the version check. Carry its result into the return payload instead of dropping it. Add `"warning": "Remote script looks stock, clips may land empty. Reinstall from ableton_remote/ and restart Live."` to the success dict when that call failed, and render it. Second half: add the same probe to `/api/health` as `ableton_script_patched`, so it is visible before a send rather than after.

### E3. /api/health can never return "ok" (HIGH)

`api/main.py:212` computes `all_ok = all(checks.values())` over three checks including `api_key_configured` (`:207`) and `ableton_connected` (`:210`). But the architecture's hard constraint is no Anthropic API key (there is no `.env` on this machine and nothing loads one), and Live being closed is the normal resting state. So status is "degraded" whenever everything is fine, and there is no distinguishable unhealthy state. The README (line 35) documents the output as "ok or degraded" without noticing it is pinned.

Also missing: nothing checks the headless `claude` binary, which is the actual LLM dependency. `utils/headless_claude.py:34-35` exposes `headless_available()` and nothing calls it from health.

Smallest step: base `status` on required deps only (music21) and move the rest into a `capabilities` block: `{"ableton": bool, "ableton_script_patched": bool, "headless_claude": headless_available(), "api_key": bool}`. Then "degraded" means something and the capability row tells you which optional path is dark.

### E4. Every endpoint is async def doing blocking I/O (HIGH)

`generate` is `async def` (`api/main.py:249`) and calls `orchestrator.execute()` synchronously. On the keyword-blank path (`agents/orchestrator.py:128-136`, exactly the path the field session hit with blues, jazzy, dusty, moody) that shells out to `claude -p` via `subprocess.run` with `timeout_seconds=90` (`utils/headless_claude.py:38-45`). That blocks the event loop, so for up to 90 seconds every other request queues behind it, including `/api/health`.

The same pattern applies to `health_check` (`main.py:190`, socket call with `SOCKET_TIMEOUT=5.0` at `mcp_client.py:45`), `send_to_ableton` (`main.py:294`) and `send_arrangement_to_ableton` (`main.py:313`), which opens a fresh TCP connection per MCP command, dozens for a full arrangement. The frontend's axios timeout is 120s (`api.js:8`), so the user just watches a spinner.

Smallest step: drop the `async` keyword on those four endpoints. FastAPI runs plain `def` path operations in a threadpool, so the blocking work moves off the loop with a one-word edit each. Then lower the headless timeout from 90s to about 20s, longer than a classification needs and shorter than anyone will wait.

### E5. python api/main.py binds 0.0.0.0 on an unauthenticated endpoint that spends her subscription (HIGH)

`api/main.py:525` runs `uvicorn.run(app, host="0.0.0.0", port=8000)`, all interfaces. The README's documented command (`uvicorn api.main:app --reload --port 8000`) defaults to 127.0.0.1, so this only bites when the module is run directly, but that is the more natural invocation for a packaged app.

There is no auth and no rate limit on any endpoint, and CORS is irrelevant to non-browser callers. Anyone on the same wifi (studio, coworking, conference, and this is a portfolio product she demos) can POST `/api/generate`, and each keyword-blank prompt fans out to `claude -p` on her personal subscription.

Separately, the raw user prompt is interpolated straight into the CLI's stdin (`utils/headless_claude.py:59`) with no tool restriction on the invocation (`:43` passes only `-p --output-format text`), so injected instructions reach an agent running in the repo's working directory.

Smallest step, two lines: change the `__main__` host to `"127.0.0.1"`, and add an explicit empty tool allowlist to the subprocess argv (`"--allowedTools", ""`) so the classifier can only classify. A per-process counter capping headless calls per minute is the next-smallest addition.

### E6. The README's .env setup step does nothing (MEDIUM)

`README.md:22-25` tells a new user `cp .env.example .env` and add ANTHROPIC_API_KEY, and `.env.example:12` repeats it. But nothing in the repo calls `load_dotenv`: grep for dotenv across all Python returns zero hits, and `python-dotenv` is not in `requirements.txt`. The key is only ever read from the live environment (`api/main.py:207`, `agents/orchestrator.py:59`), so following the README exactly produces no effect and no error. The user silently gets local templates and a health check reporting `api_key_configured: false`. This is also part of why health is pinned to "degraded". It directly fails the Phase 3c bar "a new person can clone and run the project from these instructions alone."

Smallest step: do not add dotenv, delete the step. The architecture's hard constraint is zero API cost, so remove the `.env` instructions from README and retire `.env.example`, replacing them with one honest line: the LLM path runs through the Claude Code CLI on a subscription, requires the `claude` binary, and the path is set in `utils/headless_claude.py`.

### E7. Session writes are not atomic, and one corrupt file 500s that session permanently (MEDIUM)

`save_session` (`memory/session.py:163-169`) opens the file in `"w"` (truncating it) then `json.dumps` into it. A crash, kill, or full disk mid-write leaves invalid JSON on disk.

`list_sessions` anticipates exactly this and guards with try/except (`:192-193`, "Skipped corrupt session file"), but `load_session` (`:153-161`) does not: `json.load` raises straight out. Since `load_session` backs `/api/generate` (`main.py:256`), `/api/session/{id}` (`:399`), PATCH, `/api/feedback` (`:459`), `/api/project` and the arrangement send (`:321`), a single bad file turns into a 500 on every subsequent request for that session, with no recovery path in the UI. The asymmetry (one caller defends, the other does not) suggests this was already seen once from the list side.

Smallest step: dump to `path.with_suffix('.tmp')` then `os.replace(tmp, path)`, atomic on POSIX. And wrap `load_session`'s parse in try/except JSONDecodeError, logging and returning None. The main caller already handles None gracefully by minting a fresh session (`get_or_create_session`, `:299-309`).

### E8. 756 session files, 4.9MB, no cap or cleanup (MEDIUM)

`memory/sessions/` currently holds 756 JSON files totalling 4.9MB, largest 101KB. `list_sessions` (`memory/session.py:179-194`) globs the directory and `json.loads` every file just to read four fields (session_id, created_at, updated_at, history_count), and it runs on the event loop via GET `/api/sessions` (`main.py:512-516`), so it compounds E4.

The growth driver: `add_to_history` (`:196-212`) appends the full progression and drum_pattern output for every request and rewrites the whole file (`main.py:273-281`), so a long session's file balloons and every subsequent request re-reads and re-writes the lot. This is `BACKLOG.md` row #8, filed 2026-04-08 and still open. It is now measurably real rather than theoretical.

Smallest step, two edits, no schema change and no DB: in `list_sessions`, sort by `path.stat().st_mtime` and only json-parse the newest 25 (the UI never shows more). In `add_to_history`, truncate to the last 50 entries before saving.

### E9. The Blueprint-complete send discards the server's error message (MEDIUM)

`handleCompletionSend` (`frontend/src/App.jsx:552-565`) collapses the response to `setCompletionSendUi(data?.success ? 'sent' : 'error')` at line 561, throwing away `data.message`. The UI then prints one hardcoded string for every failure: "Could not reach Ableton, is Live open with the Rubato remote script?" (`:790-792`).

But `/api/send-arrangement-to-ableton` returns three quite different failures through that same branch: "Session not found" (`main.py:323`), "No progression in this session yet" (`:341`), and per-chord failures like "Failed to add chord 3 (Dm)" (`mcp_client.py:204-207`). The user is told to check Ableton when Ableton is fine.

This is the newest send path (commit 8320b6f, "Blueprint-complete screen sends the arrangement for real") and it regressed against the older one: `MainWorkspace.jsx:167-168` already surfaces `data?.message` correctly.

Smallest step: mirror MainWorkspace, holding `data.message` in state alongside the error flag. While in there: MainWorkspace's error toast self-clears after 3000ms (`:170-172, 186`), which is easy to miss mid-take. Make the error state persist until the next send attempt.

### E10. An unrecognized mix-stage prompt returns HTTP 200 with an entirely empty body (MEDIUM)

Same defect as C1, seen from the ops side. `agents/orchestrator_pipeline.py:100-107`: for `sound_engineering` intent, if `generate_sound_engineering_local` misses and there is no API key (the standing configuration), nothing is written to `local_data`. `build_response` then skips the SE block (`:375-376`) and returns `{success: true, intent: "sound_engineering", confidence: ...}` with every payload field None. The frontend's normalize (`normalize.js:39` onward) passes `success:true` straight through, finds no progression and no drum pattern, and renders a model with no content: no error, no explanation, no recovery.

The API-fallback branch at line 104 is gated on `has_api_key`, permanently false by design, so the fallback built for this case can never fire. `BACKLOG.md` files this as Low; the field session shows it is the actual dead end a user hits.

Smallest step: when the local SE lookup misses and no fallback is available, return a `sound_engineering_response` in the existing shape whose `summary` says what was not recognized and whose `steps` list the 9 topics that do work (`agents/se_local_data.py`). Same contract, same panel, zero frontend change. The dead end becomes a menu.

### E11. Test coverage is strong on the content engine and thin exactly on the prod paths (MEDIUM)

145 non-e2e tests, and the local music engine is well covered (27 intent-detection, 16 session-context, 13 mcp_client). The holes line up with the findings above:

- Nothing covers the stock-remote-script case. `tests/integration/test_mcp_client.py:90` asserts the happy command sequence and `:262` asserts a hard server error, but not the case that actually happens: every command returns success while zero notes land.
- Nothing covers `/api/send-arrangement-to-ableton` at all. `tests/integration/test_send_to_ableton.py`'s 7 tests are all `/api/send-to-ableton` plus two health assertions, even though the arrangement send is what the completion screen uses and the one with three distinct failure returns.
- Nothing covers a corrupt or missing session file (E7).
- `utils/headless_claude.py` has no test file at all, including the case that decides portability: `headless_available()` returning False on a machine that is not hers (`agents/orchestrator.py:133` guards it, but nothing proves the guard holds).

Smallest step: three tests, all with existing fixtures. (1) arrangement send with `AbletonMCPClient` patched to connection-refused, asserting the message reaches the response body. (2) `load_session` against a deliberately truncated JSON file, asserting None rather than a raised JSONDecodeError. (3) `execute()` with `headless_available` monkeypatched False on a blank prompt like "dusty", asserting a well-formed response still returns.

### E12. No LICENSE, and the /docs grounding corpus is an unattributed research compilation (LOW)

There is no LICENSE file. `/docs` is 243KB across 9 files, and several are clearly LLM-generated research reports that retain their inline citation markers and numbered source lists pointing at third-party sites: `docs/electronic_music_production.md:444, 472, 542` list imusician.pro and theghostproduction.com URLs; `docs/music_theory.md:406-410` carries `[^9]`, `[^53]`, `[^57]` markers whose footnote definitions were dropped. They are presented under the header "Music Co-Pilot Knowledge Base" with no provenance note, in a public repo aimed at LANDR, Output and Splice.

This is a credibility question more than a legal one, but it is the kind of thing a hiring engineer at a music company notices, and the fix is cheap.

Smallest step: add a LICENSE (MIT for the code) and a four-line `docs/README.md` stating these are research summaries compiled as agent grounding context, that source lists are retained inline, and that they are not authoritative music-theory references. That turns an unlabeled liability into a documented method.

### E13. requirements.txt cannot reproduce the test setup the README tells you to run (LOW)

`requirements.txt` has exactly 5 runtime packages (anthropic, music21, fastapi, uvicorn, httpx). `pytest` is absent, yet `README.md:46-50` instructs `pytest tests/` as step 6 of Quick Start. `playwright` is absent too, and `tests/e2e/conftest.py:11` tells you to `pip install playwright && python -m playwright install chromium` in a docstring rather than in the dependency file. A clean clone following the README fails at step 6 with a command-not-found.

The README also claims "92 tests across contract, integration, unit, and regression suites" (`:49`). The suite is now 145 non-e2e plus 8 e2e.

Smallest step: add `requirements-dev.txt` with pytest and playwright, reference it from the README's test step, and either correct the count or drop the number so it cannot go stale again.

### E14. Stale-dist trap (LOW)

`frontend/dist` is gitignored (`.gitignore:12`) and served as static files, so the served app and the source can silently diverge. `RECORDING-KICKOFF.md:61` already carries this as a manual reminder ("frontend changes need `npm run build` to reach the served dist"), which means it has bitten at least once. Currently clean: no file under `frontend/src` is newer than the built bundle (`dist/assets/index-BbmZwg-R.js`, 14:42), though the last four commits landed after that, so the margin is thin. A hand-maintained reminder in a kickoff doc is not a mechanism.

Smallest step: if E1 lands and FastAPI serves the dist, log the bundle's mtime at startup, one line in a startup event, so the age of the build you are actually serving prints in the same terminal you start the server from. No build tooling, no watcher.
