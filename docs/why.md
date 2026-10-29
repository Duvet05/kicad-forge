# Why this exists

HeyPCB (heypcb.ai) showed us the shape of an agent-driven PCB flow: real KiCad underneath, the
LCSC catalogue, a journal of edits, and a language-model agent on top. Its engine is closed and
metered. This repo is the free layer we need for iterating boards we already designed: route the
new nets, check against the fab's rules, package for JLCPCB, fetch parts, all from a shell so an
agent (Claude Code in our case) can drive it.

Not in scope: auto-placement with decoupling awareness, curated part library, schematic layout.
Placement is done by hand or through KiCad's Python API per board.

First board through it: capri-mini v1.4 (github.com/Duvet05/capri-mini-hw), 2026-10-29.
