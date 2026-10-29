#!/usr/bin/env bash
# Route the open connections of a .kicad_pcb with Freerouting, keeping existing copper.
# usage: route.sh board.kicad_pcb [out.kicad_pcb] [max_passes]
# Existing tracks, vias and pours are marked (type protect) in the DSN so Freerouting only lays
# the open connections; set KEEP_COPPER=0 to let it rip up and re-route everything.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"; . "$HERE/bin/kicad-env.sh"
PCB="$1"; OUT="${2:-$1}"; PASSES="${3:-20}"
FR_VER="${FR_VER:-2.5.0}"; CACHE="$HOME/.cache/kicad-forge"; JAR="$CACHE/freerouting-$FR_VER.jar"
mkdir -p "$CACHE"
# Freerouting 2.5 needs Java 25+: prefer Homebrew's current openjdk over whatever is on PATH
JAVA="${JAVA:-}"; for j in /opt/homebrew/opt/openjdk/libexec/openjdk.jdk/Contents/Home/bin/java /usr/local/opt/openjdk/libexec/openjdk.jdk/Contents/Home/bin/java; do [ -z "$JAVA" ] && [ -x "$j" ] && JAVA="$j"; done; JAVA="${JAVA:-java}"
[ -f "$JAR" ] || curl -sSL -o "$JAR" "https://github.com/freerouting/freerouting/releases/download/v$FR_VER/freerouting-$FR_VER.jar"
W="$(mktemp -d)"; DSN="$W/board.dsn"; SES="$W/board.ses"
"$KIPY" "$HERE/forge/dsn.py" export "$PCB" "$DSN" 2>&1 | grep -v "create wxApp"
# KiCad writes the netclass clearance; the board-level clearance (default 0.2 mm) is what DRC enforces
CLEAR_UM="${CLEAR_UM:-200}"; sed -i.bak "s/(clearance 127)/(clearance $CLEAR_UM)/g" "$DSN"
[ "${KEEP_COPPER:-1}" = "1" ] && sed -i.bak 's/(type route)/(type protect)/g' "$DSN" && echo "protected $(grep -c "(type protect)" "$DSN") existing copper items"
# -de design in, -do session out, -mp max passes, -oit stop optimizing when <0.1 % better, -mt threads
"$JAVA" -Djava.awt.headless=true -jar "$JAR" -de "$DSN" -do "$SES" -mp "$PASSES" -oit 0.1 -mt 4 2>&1 | grep -vE '^\s*$' | tail -20
# merge only the new copper (protected items are skipped), drop stubs on NC pads, refill zones
"$KIPY" "$HERE/forge/ses_merge.py" "$PCB" "$SES" "$OUT" 2>&1 | grep -v -e "create wxApp" -e "memory leak"
echo "routed -> $OUT (work dir $W)"
