#!/usr/bin/env python3
"""Close what an autorouter leaves open, from a kicad-cli DRC json:
 - two track ends of the same net closer than GAP mm -> a joining segment
 - a GND pad (or any pad on a plane net) left unconnected -> a via just outside the pad, joined by a short track
  stitch.py board.kicad_pcb drc.json out.kicad_pcb [plane_nets=GND]
"""
import json, math, sys, re
import pcbnew
GAP = 0.6
src, drc, dst = sys.argv[1], sys.argv[2], sys.argv[3]
planes = (sys.argv[4] if len(sys.argv) > 4 else 'GND').split(',')
b = pcbnew.LoadBoard(src)
d = json.load(open(drc))
def nm(mm): return int(round(mm * 1e6))
def pos_of(item):  # drc json gives pos in mm
    return pcbnew.VECTOR2I(nm(item['pos']['x']), nm(item['pos']['y']))
def nearest_track_end(net, pt, layer_name):
    best = None
    for t in b.Tracks():
        if t.GetClass() != 'PCB_TRACK' or t.GetNetname() != net or b.GetLayerName(t.GetLayer()) != layer_name: continue
        for e in (t.GetStart(), t.GetEnd()):
            dd = math.hypot(e.x - pt.x, e.y - pt.y)
            if best is None or dd < best[0]: best = (dd, e, t)
    return best
joined = vias = 0
for u in d['unconnected_items']:
    items = u['items']
    descs = [i['description'] for i in items]
    net = re.search(r'\[([^\]]+)\]', descs[0]).group(1)
    # case 1: track <-> track
    if all(dsc.startswith('Pista') or dsc.startswith('Track') for dsc in descs) and len(items) == 2:
        la = [re.search(r'\(([^)]+)\)', dsc).group(1) for dsc in descs]
        a = nearest_track_end(net, pos_of(items[0]), la[0]); c = nearest_track_end(net, pos_of(items[1]), la[1])
        if a and c and la[0] == la[1] and math.hypot(a[1].x - c[1].x, a[1].y - c[1].y) <= nm(GAP):
            t = pcbnew.PCB_TRACK(b); t.SetStart(a[1]); t.SetEnd(c[1]); t.SetWidth(a[2].GetWidth()); t.SetLayer(a[2].GetLayer()); t.SetNet(b.FindNet(net)); b.Add(t); joined += 1
        elif a and c and la[0] != la[1] and math.hypot(a[1].x - c[1].x, a[1].y - c[1].y) <= nm(0.3):
            v = pcbnew.PCB_VIA(b); v.SetPosition(a[1]); v.SetWidth(nm(0.45)); v.SetDrill(nm(0.3)); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(b.FindNet(net)); b.Add(v); vias += 1
    # case 2: pad on a plane net <-> zone
    elif net in planes and any(dsc.startswith('Pad') for dsc in descs):
        pd = next(i for i in items if i['description'].startswith('Pad'))
        m = re.match(r'Pad (\S+) \[[^\]]+\] de (\S+)', pd['description']) or re.match(r'Pad (\S+) \[[^\]]+\] of (\S+)', pd['description'])
        padnum, ref = m.group(1), m.group(2)
        fp = b.FindFootprintByReference(ref); pad = next(p for p in fp.Pads() if p.GetNumber() == padnum)
        if any(v.GetClass() == 'PCB_VIA' and math.hypot(v.GetPosition().x - pad.GetPosition().x, v.GetPosition().y - pad.GetPosition().y) < nm(1.0) and v.GetNetname() == net for v in b.Tracks()): continue
        c = fp.GetPosition(); p = pad.GetPosition(); dx, dy = p.x - c.x, p.y - c.y; L = math.hypot(dx, dy) or 1
        vpos = pcbnew.VECTOR2I(int(p.x + dx / L * nm(0.75)), int(p.y + dy / L * nm(0.75)))
        v = pcbnew.PCB_VIA(b); v.SetPosition(vpos); v.SetWidth(nm(0.45)); v.SetDrill(nm(0.3)); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(b.FindNet(net)); b.Add(v)
        t = pcbnew.PCB_TRACK(b); t.SetStart(p); t.SetEnd(vpos); t.SetWidth(nm(0.127)); t.SetLayer(pad.GetLayer() if pad.IsOnLayer(pcbnew.F_Cu) else pcbnew.F_Cu); t.SetNet(b.FindNet(net)); b.Add(t); vias += 1
for z in b.Zones(): z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(dst, b)
print(f"stitch: {joined} gaps joined, {vias} vias added -> {dst}")
