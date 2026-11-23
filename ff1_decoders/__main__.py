"""Command line: python -m ff1_decoders ROM <command> [args]

Commands:
  info                     check the ROM (CRC32) and print a summary
  shops                    every shop with its place, goods and prices
  monsters [ID]            the monster list, or one monster's full stats
  map M                    map M's stairs, boxes, special spots, people and battles
  render M OUT.png         draw map M to a PNG (needs Pillow) [--room] [--scale N]
  spells [CLASS]           spells by level, or what a class may learn ("Red Mage" or 3)
  items                    bag items, weapons and armor by id
  dialogue ID              dialogue string ID (0-255) as text
  world X Y                the world-map tile at (X, Y) and where it leads
  save FILE.srm            decode a battery save [--save-copy]
  dump                     everything above as Markdown (stdout)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .rom import N_MAPS, Rom
from .spells import CLASSES, class_id
from .text import PRG_CRC32, prg_crc32


def _out(obj) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ff1_decoders",
                                 description="Decode tables from your own Final Fantasy (NES, USA) ROM.",
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split("\n", 2)[2])
    ap.add_argument("rom", help="path to your FF1 ROM (.nes, with or without the iNES header)")
    ap.add_argument("command")
    ap.add_argument("args", nargs="*")
    ap.add_argument("--room", action="store_true", help="render: use the in-room palette")
    ap.add_argument("--scale", type=int, default=1, help="render: integer scale factor")
    ap.add_argument("--save-copy", action="store_true", help="save: read the saved copy at $6400")
    ap.add_argument("--json", action="store_true", help="print JSON where a table is printed")
    a = ap.parse_args(argv)

    raw = Path(a.rom).read_bytes()
    crc = prg_crc32(raw)
    if crc != PRG_CRC32:
        print(f"warning: CRC32 {crc:08X} is not the USA ROM's {PRG_CRC32:08X}; "
              "tables may decode wrong", file=sys.stderr)
    rom = Rom(raw)
    cmd, args = a.command, a.args

    def need(n: int, usage: str) -> None:
        if len(args) < n:
            ap.error(f"usage: {usage}")

    if cmd == "info":
        print(f"PRG CRC32 {crc:08X} ({'USA release' if crc == PRG_CRC32 else 'unknown'})")
        print(f"{N_MAPS} standard maps, {len(rom.shops())} shops, 128 monsters, 64 spells")
    elif cmd == "shops":
        shops = rom.shops()
        if a.json:
            return _out(shops) or 0
        for s in shops:
            what = (f"{s['price']} G" if "price" in s else
                    ", ".join(f"{n} {p} G" for n, p in s["goods"]))
            print(f"{s['id']:3} {s['place']:<20} {s['kind']:<12} {what}")
    elif cmd == "monsters":
        if args:
            _out(rom.enemy(int(args[0], 0)))
        else:
            for e in rom.enemies():
                print(f"{e['id']:3} {e['name']:<9} HP {e['hp']:5}  EXP {e['exp']:5}  G {e['gold']:5}"
                      + (f"  weak {' '.join(e['weak'])}" if e["weak"] else ""))
    elif cmd == "map":
        need(1, "map M")
        m = int(args[0], 0)
        out = {"map": m, "name": rom.name(m), "tileset": rom.tileset(m),
               "spots": [s for s in rom.spots(m) if s["kind"] not in ("way back",)],
               "objects": rom.objects(m),
               "battles": [", ".join(f"{n} {lo}-{hi}" for n, (lo, hi) in f["enemies"])
                           for f in rom.domain(m)]}
        _out(out)
    elif cmd == "render":
        need(2, "render M OUT.png")
        img = rom.render(int(args[0], 0), in_room=a.room, scale=a.scale)
        img.save(args[1])
        print(f"wrote {args[1]} ({img.width}x{img.height})")
    elif cmd == "spells":
        st = rom.spells
        if args:
            job = " ".join(args)
            j = class_id(int(job) if job.isdigit() else job)
            print(CLASSES[j])
            for lv, names in st.learnable_by_level(j).items():
                print(f"  L{lv} {' '.join(names)}")
            if not st.learnable(j):
                print("  (no spells)")
        else:
            for lv, names in st.by_level().items():
                print(f"L{lv} white {' '.join(names[:4]):<22} black {' '.join(names[4:])}")
    elif cmd == "items":
        out = {"items": rom.items(),
               "weapons": {n: rom.weapon(n) for n in range(1, 41)},
               "armor": {n: rom.armor(n) for n in range(1, 41)}}
        _out(out)
    elif cmd == "dialogue":
        need(1, "dialogue ID")
        print(rom.text.decode(int(args[0], 0)))
    elif cmd == "world":
        need(2, "world X Y")
        t = rom.world.tile(int(args[0], 0), int(args[1], 0))
        if "leads_to" in t:
            t["leads_to"] = f"{t['leads_to']} {rom.name(t['leads_to'])}"
        _out(t)
    elif cmd == "save":
        need(1, "save FILE.srm")
        from .save import decode_sram
        _out(decode_sram(Path(args[0]).read_bytes(), raw, use_save_copy=a.save_copy))
    elif cmd == "dump":
        sys.stdout.write(rom.markdown())
        st = rom.spells
        print("\n## Who can learn each spell\n\n| class | spells |\n|---|---|")
        for j, name in enumerate(CLASSES):
            print(f"| {name} | {' '.join(st.can_learn(j)) or '(none)'} |")
    else:
        ap.error(f"unknown command {cmd!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
