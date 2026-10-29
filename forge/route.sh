#!/usr/bin/env bash
# Route the open connections of a .kicad_pcb with Freerouting, keeping existing copper.
# usage: route.sh board.kicad_pcb [out.kicad_pcb] [max_passes]
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"; . "$HERE/bin/kicad-env.sh"
PCB="$1"; OUT="${2:-$1}"; PASSES="${3:-20}"
FR_VER="${FR_VER:-2.5.0}"; CACHE="$HOME/.cache/kicad-forge"; JAR="$CACHE/freerouting-$FR_VER.jar"
mkdir -p "$CACHE"
[ -f "$JAR" ] || curl -sSL -o "$JAR" "https://github.com/freerouting/freerouting/releases/download/v$FR_VER/freerouting-$FR_VER.jar"
W="$(mktemp -d)"; DSN="$W/board.dsn"; SES="$W/board.ses"
"$KIPY" "$HERE/forge/dsn.py" export "$PCB" "$DSN"
# -de design in, -do session out, -mp max passes, -oit stop optimizing when <0.1 % better, -mt threads
java -Djava.awt.headless=true -jar "$JAR" -de "$DSN" -do "$SES" -mp "$PASSES" -oit 0.1 -mt 4 -dct 60 2>&1 | grep -vE '^\s*$' | tail -20
"$KIPY" "$HERE/forge/dsn.py" import "$PCB" "$SES" "$OUT"
echo "routed -> $OUT (work dir $W)"
