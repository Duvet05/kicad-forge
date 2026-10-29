#!/usr/bin/env bash
# JLCPCB package: gerbers+drill zip, BOM, CPL, STEP. usage: fab.sh board.kicad_pcb out_dir
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"; . "$HERE/bin/kicad-env.sh"
PCB="$1"; OUT="$2"; PRJ="${PCB%.kicad_pcb}"; SCH="$PRJ.kicad_sch"; mkdir -p "$OUT/gerbers"
"$KICAD_CLI" pcb export gerbers --subtract-soldermask --no-protel-ext -o "$OUT/gerbers/" "$PCB" >/dev/null
"$KICAD_CLI" pcb export drill --format excellon --excellon-separate-th --generate-map --map-format gerberx2 -o "$OUT/gerbers/" "$PCB" >/dev/null
(cd "$OUT" && rm -f gerbers.zip && zip -qr gerbers.zip gerbers)
"$KICAD_CLI" pcb export pos --format csv --units mm --side both --smd-only --use-drill-file-origin -o "$OUT/CPL.csv" "$PCB" >/dev/null
# JLCPCB headers for CPL
python3 - "$OUT/CPL.csv" <<'PY'
import csv,sys
p=sys.argv[1]; rows=list(csv.reader(open(p)))
hdr=["Designator","Val","Package","Mid X","Mid Y","Rotation","Layer"]
with open(p,"w",newline="") as f:
    w=csv.writer(f); w.writerow(hdr)
    for r in rows[1:]:
        if len(r)>=7: w.writerow([r[0],r[1],r[2],r[3],r[4],r[5],"Top" if r[6].lower().startswith("top") else "Bottom"])
PY
[ -f "$SCH" ] && "$KICAD_CLI" sch export bom --fields "Reference,Value,Footprint,LCSC,MPN" --labels "Designator,Comment,Footprint,LCSC Part #,MPN" --group-by "Value,Footprint,LCSC" --exclude-dnp -o "$OUT/BOM.csv" "$SCH" >/dev/null || true
"$KICAD_CLI" pcb export step --subst-models --force -o "$OUT/board.step" "$PCB" >/dev/null 2>&1 || echo "STEP skipped (missing 3D models?)"
ls -la "$OUT"
