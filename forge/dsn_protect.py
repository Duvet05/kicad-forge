#!/usr/bin/env python3
"""Mark existing copper in a Specctra DSN as (type protect), except nets listed (those stay routable).
  dsn_protect.py in.dsn out.dsn [NET,NET,...]"""
import sys, re
src, dst = sys.argv[1], sys.argv[2]; free = set(sys.argv[3].split(',')) if len(sys.argv) > 3 and sys.argv[3] else set()
s = open(src, encoding='utf-8', errors='replace').read()
out = []; i = 0; n = 0
while True:
    j = min([k for k in (s.find('(wire', i), s.find('(via', i)) if k >= 0] or [-1])
    if j < 0: out.append(s[i:]); break
    # find matching paren
    depth = 0; k = j
    while True:
        if s[k] == '(': depth += 1
        elif s[k] == ')':
            depth -= 1
            if depth == 0: break
        k += 1
    blk = s[j:k + 1]; m = re.search(r'\(net\s+("[^"]*"|[^\s()]+)', blk); net = m.group(1).strip('"') if m else ''
    if net not in free: blk = blk.replace('(type route)', '(type protect)'); n += 1
    out.append(s[i:j]); out.append(blk); i = k + 1
open(dst, 'w').write(''.join(out)); print(f'protected {n} items; free nets: {sorted(free) or "none"}')
