#!/usr/bin/env python3
"""Merge ONLY the new routes of a Freerouting .ses into a .kicad_pcb, leaving existing copper
untouched (items tagged "(type protect)" in the session are skipped). Also drops track stubs that
end on pads whose net is unconnected-*, enforces a minimum track width, refills zones.

  ses_merge.py board.kicad_pcb board.ses out.kicad_pcb [min_width_mm]
Run with KiCad's bundled python (pcbnew).
"""
import re, sys
import pcbnew

def tokenize(s):
    return re.findall(r'\(|\)|"[^"]*"|[^\s()"]+', s)

def parse(tokens):
    stack = [[]]
    for t in tokens:
        if t == '(': stack.append([])
        elif t == ')':
            node = stack.pop(); stack[-1].append(node)
        else: stack[-1].append(t.strip('"'))
    return stack[0]

def find(node, name):
    for x in node:
        if isinstance(x, list) and x and x[0] == name: yield x

def find_deep(node, name):
    for x in node:
        if isinstance(x, list):
            if x and x[0] == name: yield x
            yield from find_deep(x, name)

def main(a):
    src, ses, dst = a[1], a[2], a[3]
    min_w = float(a[4]) if len(a) > 4 else 0.127
    b = pcbnew.LoadBoard(src)
    tree = parse(tokenize(open(ses, encoding='utf-8', errors='replace').read()))
    root = tree[0]
    res = next(find_deep(root, 'resolution'))
    unit, per = res[1], float(res[2])           # (resolution um 10) -> 10 units per um
    scale = {'um': 1000.0, 'mm': 1e6, 'mil': 25400.0, 'inch': 25.4e6}[unit] / per  # units -> nm
    def P(x, y): return pcbnew.VECTOR2I(int(round(float(x) * scale)), int(round(-float(y) * scale)))
    routes = next(find_deep(root, 'network_out'))
    nets = {n.GetNetname(): n for n in b.GetNetsByName().values()} if hasattr(b, 'GetNetsByName') else {}
    def netinfo(name):
        return b.FindNet(name)
    added_t = added_v = skipped = 0
    for net in find(routes, 'net'):
        name = net[1]; ni = netinfo(name)
        if ni is None: print('net not on board:', name); continue
        for w in find(net, 'wire'):
            if any(x[0] == 'type' and x[1] in ('protect', 'fix') for x in w if isinstance(x, list)): skipped += 1; continue
            path = next(find(w, 'path')); layer = path[1]; width_nm = int(float(path[2]) * scale)
            width_nm = max(width_nm, int(min_w * 1e6))
            pts = [P(path[i], path[i + 1]) for i in range(3, len(path) - 1, 2)]
            lid = b.GetLayerID(layer)
            for p0, p1 in zip(pts, pts[1:]):
                if p0 == p1: continue
                t = pcbnew.PCB_TRACK(b); t.SetStart(p0); t.SetEnd(p1); t.SetWidth(width_nm); t.SetLayer(lid); t.SetNet(ni); b.Add(t); added_t += 1
        for v in find(net, 'via'):
            if any(x[0] == 'type' and x[1] in ('protect', 'fix') for x in v if isinstance(x, list)): skipped += 1; continue
            m = re.search(r'_(\d+):(\d+)_um', v[1]); dia, drill = (int(m.group(1)) * 1000, int(m.group(2)) * 1000) if m else (450000, 300000)
            via = pcbnew.PCB_VIA(b); via.SetPosition(P(v[2], v[3])); via.SetWidth(dia); via.SetDrill(drill)
            via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); via.SetNet(ni); b.Add(via); added_v += 1
    # stubs on pads that are no longer connected in the schematic
    nc = [p for fp in b.GetFootprints() for p in fp.Pads() if p.GetNetname().startswith('unconnected-')]
    def mid(t): return pcbnew.VECTOR2I((t.GetStart().x + t.GetEnd().x) // 2, (t.GetStart().y + t.GetEnd().y) // 2)
    # only tracks that END on a now-unconnected pad (the old stub); anything else is left to stitch.py + DRC
    doomed = [t for t in b.Tracks() if t.GetClass() == 'PCB_TRACK' and any(p.HitTest(t.GetStart()) or p.HitTest(t.GetEnd()) for p in nc)]
    for t in doomed: b.Delete(t)
    for z in b.Zones():
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)   # KiCad reports kept islands as unconnected
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(dst, b)
    print(f"merged {added_t} track segments + {added_v} vias (skipped {skipped} protected), removed {len(doomed)} stubs on NC pads, zones refilled -> {dst}")

if __name__ == '__main__':
    sys.exit(main(sys.argv))
