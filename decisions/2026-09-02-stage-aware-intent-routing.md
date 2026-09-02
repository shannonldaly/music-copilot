# Stage-aware intent routing + follow-up stage marking

**Date:** 2026-09-02
**Trigger:** During recording preflight, a prompt at the Melody Direction stage kicked the
session back to "Keep this progression". Shannon: "why do I have to type melody if you are
on the melody direction prompt?"

## The two stacked bugs

1. **Routing was keyword-or-luck.** The sidebar stage lives only in the frontend; the
   backend re-detected intent from raw text every prompt. A keyword-free prompt got
   rescued by the headless-Claude classifier (commit 8512941), which is why stage prompts
   "just worked" without the word melody — but any mood/genre/key keyword ("dreamier",
   "lo-fi") skipped enrichment and landed on `mood_vibe`, regenerating a progression.
2. **Follow-up echoes clobbered the Progression stage.** Since commit abcc34b, follow-up
   intents echo the current progression back so the UI keeps showing it. April-era
   `applyApiToStages` treated any `progression_name` in a response as a new progression
   and reset the stage to unconfirmed — bouncing the user back even on correctly-routed
   follow-ups.

## Decision

Thread the active sidebar stage through the request and use it on both sides:

- **Frontend → API:** `App.jsx` sends `stage` (first awaiting-confirm stage, else next
  suggested) with every generate call; `GenerateRequest` gains an optional `stage` field.
- **Backend bias (`apply_stage_bias`, intent_detection.py):** a `mood_vibe` verdict at a
  biased stage re-routes to that stage's intent (melodyDir→melody_direction, bass→bass_line,
  drums/pattern/genreFeel/bpm/splice→drum_pattern, mix/eq/automation/targetVibe/section→
  sound_engineering). Specific keyword verdicts always stand, as does mood_vibe when the
  prompt names harmony (progression/chord/reharm/harmony/voicing/key change). Biased
  requests skip headless enrichment (deterministic + saves a call).
- **Frontend stage marking (`applyApiToStages`):** follow-up intents mark **their own**
  stage done (melodyDir/bass/drums/mix) and leave the confirmed progression alone.

## The four agent questions (orchestrator.execute)

1. **Expects:** prompt, use_api, optional session_context, optional `active_stage` (sidebar
   stage id or None).
2. **Guarantees:** same response contract as before; at a biased stage a mood_vibe prompt
   returns the stage's intent answered over the session progression.
3. **If missing:** `active_stage` None/unknown → behavior identical to pre-change.
4. **Downstream:** frontend `applyApiToStages` keys off `response.intent` to mark the
   follow-up's stage; older clients that don't send `stage` are unaffected.

## Verification

- 136 pytest green (127 existing + 9 new unit/integration for the bias).
- Live curl E2E: melody/bass/drums follow-ups with mood-only wording route to their stage's
  intent over the same progression; "give me a darker progression instead" at the melody
  stage still regenerates harmony.

## Deferred

- API mode (`use_api: true`, Haiku intent) does not use the stage hint — local mode only.
- `mix`-stage bias relies on `generate_sound_engineering_local` recognizing the topic; an
  unrecognized mix prompt with no API key returns an empty SE payload (pre-existing SE
  behavior).
