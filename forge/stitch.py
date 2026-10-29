#!/usr/bin/env python3
"""Close what an autorouter leaves open, driven by a kicad-cli DRC json.
  stitch.py board.kicad_pcb drc.json out.kicad_pcb [plane_nets=GND]
Cases handled, each reported in the summary:
  gap     two track ends of the same net on one layer closer than GAP  -> joining segment
  via     two track ends of the same net on different layers within 0.3 mm -> via
  pad     a track end within GAP of an unconnected pad of its net          -> segment to the pad
  plane   a pad on a plane net left unconnected                            -> via beside it (first clean spot) + stub
  island  a filled piece of a plane-net zone with no via in it             -> via inside it
  short   a track the DRC says shorts a now-unconnected pad                -> deleted
"""
import json, math, sys, re
import pcbnew
GAP = 0.6
src, drc, dst = sys.argv[1], sys.argv[2], sys.argv[3]
planes = (sys.argv[4] if len(sys.argv) > 4 else 'GND').split(',')
b = pcbnew.LoadBoard(src)
d = json.load(open(drc))
def nm(mm): return int(round(mm * 1e6))
def V(x, y): return pcbnew.VECTOR2I(int(x), int(y))
def dist(p, q): return math.hypot(p.x - q.x, p.y - q.y)
def pos_of(item): return V(nm(item['pos']['x']), nm(item['pos']['y']))
def net_of(desc): return re.search(r'\[([^\]]+)\]', desc).group(1)
def layer_of(desc):
    m = re.search(r'\(([^)]+)\)', desc); return m.group(1) if m else None
def tracks(net=None, layer=None):
    for t in b.Tracks():
        if t.GetClass() != 'PCB_TRACK': continue
        if net and t.GetNetname() != net: continue
        if layer and b.GetLayerName(t.GetLayer()) != layer: continue
        yield t
def track_at(net, layer, pt):
    best = None
    for t in tracks(net, layer):
        dd = min(dist(t.GetStart(), pt), dist(t.GetEnd(), pt), seg_dist(t, pt))
        if best is None or dd < best[0]: best = (dd, t)
    return best[1] if best and best[0] < nm(0.05) else None
def seg_dist(t, q):
    a, c = t.GetStart(), t.GetEnd(); L2 = (c.x - a.x) ** 2 + (c.y - a.y) ** 2
    if L2 == 0: return dist(a, q)
    u = max(0, min(1, ((q.x - a.x) * (c.x - a.x) + (q.y - a.y) * (c.y - a.y)) / L2))
    return math.hypot(q.x - (a.x + u * (c.x - a.x)), q.y - (a.y + u * (c.y - a.y)))
def add_track(p, q, layer_id, net, w=nm(0.127)):
    t = pcbnew.PCB_TRACK(b); t.SetStart(p); t.SetEnd(q); t.SetWidth(w); t.SetLayer(layer_id); t.SetNet(b.FindNet(net)); b.Add(t)
def add_via(p, net):
    v = pcbnew.PCB_VIA(b); v.SetPosition(p); v.SetWidth(nm(0.45)); v.SetDrill(nm(0.3)); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(b.FindNet(net)); b.Add(v)
RULE_AREAS = [z for z in b.Zones() if z.GetIsRuleArea() and (z.GetDoNotAllowVias() or z.GetDoNotAllowTracks())]
def in_keepout(p):
    return any(z.Outline().Contains(p) for z in RULE_AREAS)
def clean_spot(p, net, radius=nm(0.45 / 2 + 0.16)):
    """True if no pad/track/via of another net lies within radius of p (any layer) and p is outside every via keep-out."""
    if in_keepout(p): return False
    for fp in b.GetFootprints():
        for pd in fp.Pads():
            if pd.GetNetname() != net and dist(pd.GetPosition(), p) < radius + max(pd.GetSize().x, pd.GetSize().y) / 2: return False
    for t in b.Tracks():
        if t.GetNetname() == net: continue
        if t.GetClass() == 'PCB_VIA' and dist(t.GetPosition(), p) < radius + t.GetWidth(pcbnew.F_Cu) / 2: return False
        if t.GetClass() == 'PCB_TRACK' and seg_dist(t, p) < radius + t.GetWidth() / 2: return False
    return True
def find_pad(desc):
    m = re.match(r'Pad (\S+) \[[^\]]+\] (?:de|of) (\S+)', desc); fp = b.FindFootprintByReference(m.group(2))
    return next(p for p in fp.Pads() if p.GetNumber() == m.group(1))
n = dict(gap=0, via=0, pad=0, plane=0, island=0, short=0)
# --- shorts on NC pads (delete the offending track)
for v in d.get('violations', []):
    if v['type'] != 'shorting_items' or not any('[unconnected-' in i['description'] for i in v['items']): continue
    for it in v['items']:
        if it['description'].startswith(('Pista', 'Track')):
            t = track_at(net_of(it['description']), layer_of(it['description']), pos_of(it))
            if t: b.Delete(t); n['short'] += 1
# --- opens
for u in d['unconnected_items']:
    items = u['items']; descs = [i['description'] for i in items]; net = net_of(descs[0])
    kinds = ['track' if x.startswith(('Pista', 'Track')) else 'pad' if x.startswith('Pad') else 'via' if x.startswith(('Vía', 'Via')) else 'zone' for x in descs]
    if kinds == ['track', 'track']:
        la, lb = layer_of(descs[0]), layer_of(descs[1])
        ta, tb = track_at(net, la, pos_of(items[0])), track_at(net, lb, pos_of(items[1]))
        if not (ta and tb): continue
        ends = [(dist(p, q), p, q) for p in (ta.GetStart(), ta.GetEnd()) for q in (tb.GetStart(), tb.GetEnd())]
        dd, p, q = min(ends)
        if la == lb and dd <= nm(GAP): add_track(p, q, ta.GetLayer(), net, ta.GetWidth()); n['gap'] += 1
        elif la != lb and dd <= nm(0.3): add_via(p, net); n['via'] += 1
        elif la != lb and dd <= nm(GAP): add_track(p, q, ta.GetLayer(), net, ta.GetWidth()); add_via(q, net); n['via'] += 1
    elif sorted(kinds) == ['pad', 'track'] or sorted(kinds) == ['pad', 'via']:
        pi = kinds.index('pad'); oi = 1 - pi; pad = find_pad(descs[pi])
        if kinds[oi] == 'via':
            vpos = pos_of(items[oi])
            if dist(vpos, pad.GetPosition()) <= nm(GAP): add_track(vpos, pad.GetPosition(), pcbnew.F_Cu if pad.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu, net); n['pad'] += 1
        else:
            t = track_at(net, layer_of(descs[oi]), pos_of(items[oi]))
            if t and pad.IsOnLayer(t.GetLayer()):
                p = min((t.GetStart(), t.GetEnd()), key=lambda e: dist(e, pad.GetPosition()))
                if dist(p, pad.GetPosition()) <= nm(GAP): add_track(p, pad.GetPosition(), t.GetLayer(), net, t.GetWidth()); n['pad'] += 1
    elif 'pad' in kinds and net in planes:
        pad = find_pad(descs[kinds.index('pad')]); fp = pad.GetParentFootprint() if hasattr(pad, 'GetParentFootprint') else pad.GetParent()
        p = pad.GetPosition(); c = fp.GetPosition(); ang0 = math.atan2(p.y - c.y, p.x - c.x)
        if any(t.GetClass() == 'PCB_VIA' and t.GetNetname() == net and dist(t.GetPosition(), p) < nm(1.0) for t in b.Tracks()): continue
        for r in (0.75, 0.9, 1.1):
            for da in (0, 30, -30, 60, -60, 90, -90):
                a = ang0 + math.radians(da); q = V(p.x + math.cos(a) * nm(r), p.y + math.sin(a) * nm(r))
                if clean_spot(q, net):
                    add_via(q, net); add_track(p, q, pcbnew.F_Cu if pad.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu, net); n['plane'] += 1; r = None; break
            if r is None: break
# --- missing vias: tracks of one net on different layers ending at the same point with no via there
ends = {}
for t in tracks():
    for e in (t.GetStart(), t.GetEnd()):
        ends.setdefault((t.GetNetname(), e.x // 1000, e.y // 1000), set()).add(t.GetLayer())
vias_at = {(v.GetNetname(), v.GetPosition().x // 1000, v.GetPosition().y // 1000) for v in b.Tracks() if v.GetClass() == 'PCB_VIA'}
n['missing_via'] = 0
for k, layers in ends.items():
    if len(layers) >= 2 and k not in vias_at:
        q = V(k[1] * 1000, k[2] * 1000)
        if clean_spot(q, k[0], radius=nm(0.45 / 2 + 0.127)): add_via(q, k[0]); n['missing_via'] += 1
# --- pad <-> track of the same net within GAP (nearest end of any track on the pad's layer)
for u in d['unconnected_items']:
    items = u['items']; descs = [i['description'] for i in items]; net = net_of(descs[0])
    kinds = ['track' if x.startswith(('Pista', 'Track')) else 'pad' if x.startswith('Pad') else 'other' for x in descs]
    if sorted(kinds) != ['pad', 'track']: continue
    pad = find_pad(descs[kinds.index('pad')]); pp = pad.GetPosition()
    cands = [(dist(e, pp), e, t) for t in tracks(net) if pad.IsOnLayer(t.GetLayer()) for e in (t.GetStart(), t.GetEnd())]
    if cands:
        dd, e, t = min(cands)
        if 0 < dd <= nm(GAP) and not pad.HitTest(e): add_track(e, pp, t.GetLayer(), net, t.GetWidth()); n['pad'] += 1
# --- vias too close to the board edge: nudge inward
n['edge'] = 0
bb = b.GetBoardEdgesBoundingBox(); EDGE = nm(0.3 + 0.45 / 2 + 0.02)
for v in b.Tracks():
    if v.GetClass() != 'PCB_VIA': continue
    p = v.GetPosition(); nx, ny = p.x, p.y
    if p.x - bb.GetX() < EDGE: nx = bb.GetX() + EDGE
    if bb.GetRight() - p.x < EDGE: nx = bb.GetRight() - EDGE
    if p.y - bb.GetY() < EDGE: ny = bb.GetY() + EDGE
    if bb.GetBottom() - p.y < EDGE: ny = bb.GetBottom() - EDGE
    if (nx, ny) != (p.x, p.y):
        q = V(nx, ny)
        for t in tracks(v.GetNetname()):
            if t.GetStart() == p: t.SetStart(q)
            if t.GetEnd() == p: t.SetEnd(q)
        v.SetPosition(q); n['edge'] += 1
# --- islands of plane-net zones with no via: a via inside
for z in b.Zones():
    if z.GetNetname() not in planes: continue
    for lid in z.GetLayerSet().Seq():
        polys = z.GetFilledPolysList(lid)
        for i in range(polys.OutlineCount()):
            o = polys.Outline(i)
            if abs(o.Area()) < nm(1.5) * nm(1.5): continue   # slivers: leave them
            has_via = any(t.GetClass() == 'PCB_VIA' and t.GetNetname() == z.GetNetname() and o.PointInside(t.GetPosition()) for t in b.Tracks())
            if has_via: continue
            bb = o.BBox(); cands = [bb.Centre()] + [V(bb.GetX() + bb.GetWidth() * fx, bb.GetY() + bb.GetHeight() * fy) for fx in (0.25, 0.5, 0.75) for fy in (0.25, 0.5, 0.75)]
            for q in cands:
                if o.PointInside(q) and clean_spot(q, z.GetNetname()):
                    add_via(q, z.GetNetname()); n['island'] += 1; break
for z in b.Zones(): z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(dst, b)
print('stitch:', ', '.join(f'{k} {v}' for k, v in n.items()), '->', dst)
