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
