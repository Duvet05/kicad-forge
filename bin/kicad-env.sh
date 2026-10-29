# Locates KiCad's own tools. Source it: . bin/kicad-env.sh
KICAD_APP="${KICAD_APP:-/Applications/KiCad/KiCad.app/Contents}"
if command -v kicad-cli >/dev/null 2>&1; then KICAD_CLI="$(command -v kicad-cli)"; else KICAD_CLI="$KICAD_APP/MacOS/kicad-cli"; fi
KIPY="${KIPY:-$KICAD_APP/Frameworks/Python.framework/Versions/Current/bin/python3}"
[ -x "$KIPY" ] || KIPY="$(command -v python3)"
export KICAD_CLI KIPY
