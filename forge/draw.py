#!/usr/bin/env python3
"""Hand edits on a board from a JSON spec (mm, KiCad coordinates, y down):
  {"clear_nets": ["NET", ...],                      # delete every track and via on these nets
   "moves": {"C44": [61.9, 6.2], "C43": [63.3, 5.1, 90]},   # x, y [, rotation deg]
   "tracks": [{"net": "MIC2N", "layer": "F.Cu", "width": 0.127, "pts": [[61.02, 5.1], [60.9, 5.3]]}],
   "vias": [{"net": "I2S_DIN", "x": 63.3, "y": 10.6}]}
   "clear_new_nets": {"base": "orig.kicad_pcb", "nets": ["MIC2P"]},   # delete copper of these nets that the base board does not have
   "pad1_down": ["C44"]}                                                # rotate so pad 1 is the lower pad (+y)
  draw.py board.kicad_pcb spec.json out.kicad_pcb
"""
import json, sys
import pcbnew
src, spec, dst = sys.argv[1], sys.argv[2], sys.argv[3]
b = pcbnew.LoadBoard(src); s = json.load(open(spec))
def nm(mm): return int(round(mm * 1e6))
def V(x, y): return pcbnew.VECTOR2I(nm(x), nm(y))
cleared = 0
def key(t):
    if t.GetClass() == 'PCB_VIA': return ('V', t.GetPosition().x, t.GetPosition().y, t.GetNetname())
    return ('T', t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y, t.GetLayer(), t.GetNetname())
cn = s.get('clear_new_nets')
if cn:
    base = pcbnew.LoadBoard(cn['base']); have = {key(t) for t in base.Tracks()}
    for t in list(b.Tracks()):
        if t.GetNetname() in cn['nets'] and key(t) not in have: b.Delete(t); cleared += 1
for t in list(b.Tracks()):
    if t.GetNetname() in s.get('clear_nets', []): b.Delete(t); cleared += 1
for ref, p in s.get('moves', {}).items():
    fp = b.FindFootprintByReference(ref); fp.SetPosition(V(p[0], p[1]))
    if len(p) > 2: fp.SetOrientationDegrees(p[2])
for ref in s.get('pad1_down', []):
    fp = b.FindFootprintByReference(ref); pads = {p.GetNumber(): p for p in fp.Pads()}
    for rot in (90, 270, 0, 180):
        fp.SetOrientationDegrees(rot)
        if pads['1'].GetPosition().y > pads['2'].GetPosition().y and abs(pads['1'].GetPosition().x - pads['2'].GetPosition().x) < 1000: break
for tr in s.get('tracks', []):
    pts = [V(*p) for p in tr['pts']]
    for p, q in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b); t.SetStart(p); t.SetEnd(q); t.SetWidth(nm(tr.get('width', 0.127))); t.SetLayer(b.GetLayerID(tr['layer'])); t.SetNet(b.FindNet(tr['net'])); b.Add(t)
for v in s.get('vias', []):
    via = pcbnew.PCB_VIA(b); via.SetPosition(V(v['x'], v['y'])); via.SetWidth(nm(v.get('d', 0.45))); via.SetDrill(nm(v.get('drill', 0.3))); via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); via.SetNet(b.FindNet(v['net'])); b.Add(via)
for mv in s.get('move_vias', []):
    src_p, dst_p = V(*mv['from']), V(*mv['to'])
    for t in b.Tracks():
        if t.GetNetname() != mv['net']: continue
        if t.GetClass() == 'PCB_VIA' and abs(t.GetPosition().x - src_p.x) < 20000 and abs(t.GetPosition().y - src_p.y) < 20000: t.SetPosition(dst_p)
        elif t.GetClass() == 'PCB_TRACK':
            if abs(t.GetStart().x - src_p.x) < 20000 and abs(t.GetStart().y - src_p.y) < 20000: t.SetStart(dst_p)
            if abs(t.GetEnd().x - src_p.x) < 20000 and abs(t.GetEnd().y - src_p.y) < 20000: t.SetEnd(dst_p)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(dst, b)
print(f"draw: cleared {cleared} items, moved {len(s.get('moves',{}))}, tracks {sum(len(t['pts'])-1 for t in s.get('tracks',[]))}, vias {len(s.get('vias',[]))} -> {dst}")
