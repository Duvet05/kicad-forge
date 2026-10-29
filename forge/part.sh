#!/usr/bin/env bash
# Fetch symbol, footprint and 3D model for an LCSC part into lib/. usage: part.sh C365743 [lib_dir]
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"; LIB="${2:-$HERE/lib/forge}"; mkdir -p "$(dirname "$LIB")"
uvx easyeda2kicad --full --lcsc_id="$1" --output "$LIB" --overwrite
echo "-> $LIB.kicad_sym / $LIB.pretty / $LIB.3dshapes  (verify the footprint against the datasheet once)"
