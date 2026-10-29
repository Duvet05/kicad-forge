#!/usr/bin/env bash
# DRC (with schematic parity) and ERC via kicad-cli. usage: check.sh board.kicad_pcb [rules.kicad_dru]
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"; . "$HERE/bin/kicad-env.sh"
PCB="$1"; PRJ="${PCB%.kicad_pcb}"; SCH="$PRJ.kicad_sch"; RULES="${2:-}"
if [ -n "$RULES" ]; then cp "$RULES" "$PRJ.kicad_dru"; echo "rules: $RULES -> $PRJ.kicad_dru"; fi
"$KICAD_CLI" pcb drc --schematic-parity --severity-all --exit-code-violations -o "$PRJ.drc.json" --format json "$PCB" && echo "DRC: clean" || echo "DRC: violations in $PRJ.drc.json"
python3 - "$PRJ.drc.json" <<'PY'
import json,sys,collections
d=json.load(open(sys.argv[1])); c=collections.Counter()
for v in d.get("violations",[]): c[(v["severity"],v["type"])]+=1
for (s,t),n in sorted(c.items()): print(f"  {s:8} {n:4}  {t}")
print(f"  unconnected: {len(d.get('unconnected_items',[]))}")
PY
[ -f "$SCH" ] && { "$KICAD_CLI" sch erc --severity-all --exit-code-violations -o "$PRJ.erc.json" --format json "$SCH" && echo "ERC: clean" || echo "ERC: see $PRJ.erc.json"; } || true
