#!/usr/bin/env bash
# Merge a Freerouting session into a board, stitch what is left open, run DRC, print a summary.
# usage: finish.sh base.kicad_pcb session.ses out_prefix [free_nets_csv]
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"; . "$HERE/bin/kicad-env.sh"
BASE="$1"; SES="$2"; OUT="$3"; FREE="${4:-}"; PRJ="${BASE%.kicad_pcb}"
Q() { grep -v -e "create wxApp" -e "memory leak" -e "GetWidth" -e "operator<" -e "Debug:" || true; }
if [ -n "$FREE" ]; then "$KIPY" "$HERE/forge/ses_merge.py" "$BASE" "$SES" "$OUT.a.kicad_pcb" --replace "$FREE" 2>&1 | Q
else "$KIPY" "$HERE/forge/ses_merge.py" "$BASE" "$SES" "$OUT.a.kicad_pcb" 2>&1 | Q; fi
for s in a b; do
  [ -f "$PRJ.kicad_pro" ] && cp "$PRJ.kicad_pro" "$OUT.$s.kicad_pro"; [ -f "$PRJ.kicad_dru" ] && cp "$PRJ.kicad_dru" "$OUT.$s.kicad_dru"
  "$KICAD_CLI" pcb drc --severity-all -o "$OUT.$s.drc.json" --format json "$OUT.$s.kicad_pcb" >/dev/null 2>&1 || true
  [ "$s" = a ] && "$KIPY" "$HERE/forge/stitch.py" "$OUT.a.kicad_pcb" "$OUT.a.drc.json" "$OUT.b.kicad_pcb" 2>&1 | Q
done
python3 - "$OUT.b.drc.json" <<'PY'
import json, sys, collections
d = json.load(open(sys.argv[1]))
err = collections.Counter(v['type'] for v in d['violations'] if v['severity'] == 'error')
print(f"RESULT {sys.argv[1]}: errors={dict(err)} unconnected={len(d['unconnected_items'])}")
for u in d['unconnected_items']: print('   open:', [i['description'][:50] for i in u['items']])
for v in d['violations']:
    if v['severity'] == 'error': print('   ERR', v['type'], [(i['description'][:40], i['pos']) for i in v['items']])
PY
