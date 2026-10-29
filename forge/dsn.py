#!/usr/bin/env python3
"""Specctra bridge using KiCad's own pcbnew module (run with KiCad's bundled python).

  dsn.py export  board.kicad_pcb  board.dsn
  dsn.py import  board.kicad_pcb  board.ses  [out.kicad_pcb]
"""
import sys
import pcbnew

def main(argv):
    if len(argv) < 4:
        print(__doc__); return 2
    cmd, pcb = argv[1], argv[2]
    board = pcbnew.LoadBoard(pcb)
    if cmd == "export":
        ok = pcbnew.ExportSpecctraDSN(board, argv[3])
    elif cmd == "import":
        ok = pcbnew.ImportSpecctraSES(board, argv[3])
        if ok:
            pcbnew.SaveBoard(argv[4] if len(argv) > 4 else pcb, board)
    else:
        print(__doc__); return 2
    tracks = sum(1 for t in board.GetTracks() if t.GetClass() == "PCB_TRACK")
    vias = sum(1 for t in board.GetTracks() if t.GetClass() == "PCB_VIA")
    print(f"{cmd}: {'ok' if ok else 'FAILED'}; board now has {tracks} track segments, {vias} vias")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main(sys.argv))
