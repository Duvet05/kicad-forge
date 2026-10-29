# kicad-forge

Headless PCB pipeline on top of KiCad 9 or 10, Freerouting and the LCSC catalogue, driven from the
terminal or from an AI coding agent. Built by Choom Labs for its own boards (ESP32-S3 audio
boards for an AI plush toy); published so the method is visible. Internal tool first: no
support promises, breaking changes without notice.

What it does, with zero paid services:

| Step | Tool | Command |
|---|---|---|
| Fetch a part (symbol + footprint + 3D) by LCSC number | easyeda2kicad | `bin/forge part C365743` |
| Export the board to Specctra, route the open connections, import the result | pcbnew API + Freerouting | `bin/forge route board.kicad_pcb` |
| DRC + ERC with JLCPCB's capabilities as rules | kicad-cli | `bin/forge check board.kicad_pcb` |
| Gerbers, drill, BOM, CPL, STEP for JLCPCB | kicad-cli | `bin/forge fab board.kicad_pcb out/` |

Requirements: KiCad 9 or 10 (macOS app bundle or `kicad-cli` on PATH), Java 21, `uv`.
Freerouting's jar is downloaded on first use into `~/.cache/kicad-forge/`.

JLCPCB rules in `rules/` are transcribed from jlcpcb.com/capabilities; re-check them before an
order, the fab's numbers win.

Spanish-speaking maintainers; issues in Spanish or English.

License: MIT.
