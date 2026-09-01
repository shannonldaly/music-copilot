# AbletonMCP remote script (repo copy)

This is the canonical copy of the AbletonMCP MIDI Remote Script Rubato talks to
on localhost:9877, including our `set_song_key` command (sets Live's Key & Scale
to the imported progression's key — Live 12+).

Ableton updates replace the app bundle, which wipes the installed script.
After a Live update, reinstall with:

    cp ableton_remote/AbletonMCP/__init__.py \
      "/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/MIDI Remote Scripts/AbletonMCP/__init__.py"

Then restart Live. The Control Surface stays selected in Preferences
(Link/Tempo/MIDI → AbletonMCP) across updates; only the script file is lost.

**Watch out: Live auto-updates on launch** (12.4.2 → 12.4.5 did this on
2026-09-01) and silently reverts the script to stock — sends then "succeed"
but clips arrive empty (stock uses the legacy set_notes API, a silent no-op
in Live 12). Quick check that the patched script is live:

    grep -c set_song_key \
      "/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/MIDI Remote Scripts/AbletonMCP/__init__.py"

0 means stock → reinstall with the cp above and restart Live.
