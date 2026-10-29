# Locates KiCad's own tools. Source it: . bin/kicad-env.sh
for app in "${KICAD_APP:-}" "$HOME/Applications/KiCad/KiCad.app/Contents" "/Applications/KiCad/KiCad.app/Contents"; do
  [ -n "$app" ] && [ -x "$app/MacOS/kicad-cli" ] && { KICAD_APP="$app"; break; }
done
if [ -n "${KICAD_APP:-}" ]; then
  KICAD_CLI="$KICAD_APP/MacOS/kicad-cli"
  KIPY="$(ls -d "$KICAD_APP"/Frameworks/Python.framework/Versions/[0-9]* 2>/dev/null | tail -1)/bin/python3"
else
  KICAD_CLI="$(command -v kicad-cli)"; KIPY="$(command -v python3)"
fi
export KICAD_APP KICAD_CLI KIPY
