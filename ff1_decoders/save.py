"""Decode a Final Fantasy (NES) save: the 8 KB battery RAM image ($6000-$7FFF) that
emulators write as a .srm or .sav file.

The live game state sits at $6000-$63FF; the game copies it to $6400-$67FF when it
saves (inn, TENT, CABIN, HOUSE) and back when a game is continued. A .srm written by an
emulator holds both; the live copy is what the game was doing when the file was
written, which after a fresh boot is the saved game.
"""
from __future__ import annotations

from . import ram_map
from .text import ARMOR_ITEM0, CHARS, WEAPON_ITEM0, DialogueRom

SRAM_SIZE = 0x2000
SAVE_COPY = 0x400            # the save slot's copy of $6000-$63FF


def _name(codes: bytes) -> str:
    return "".join(CHARS.get(c, "") for c in codes).rstrip()


def decode_sram(sram: bytes, rom: bytes | None = None, use_save_copy: bool = False) -> dict:
    """Gold, story flags, the bag and the party of an SRAM image. With `rom` (the ROM
    image's bytes) weapons, armor and spells are named; without it they are ids.
    `use_save_copy` reads the saved copy at $6400 instead of the live block."""
    if len(sram) < SRAM_SIZE // 2:
        raise ValueError(f"expected an 8 KB SRAM image, got {len(sram)} bytes")
    if use_save_copy:
        sram = bytes(sram[SAVE_COPY:SAVE_COPY + 0x400])
    text = DialogueRom(rom) if rom else None
    m = ram_map.load()
    jobs, statuses = ram_map.enum("job"), ram_map.enum("status")

    def gear(b: int, item0: int) -> str | int:
        n = b & 0x7F
        name = text.item_name(n + item0) if text else n
        return f"{name}*" if (b & 0x80 and text) else name

    bag = {name: sram[spec["addr"]] for name, spec in m["inventory"].items() if sram[spec["addr"]]}
    p = m["party"]
    party = []
    for i in range(p["count"]):
        base = p["base"] + p["stride"] * i
        rec = sram[base:base + p["stride"]]
        magic = sram[base + 0x200:base + 0x220]
        spells = []
        for k, v in enumerate(magic):
            if 0 < v <= 8:
                n = (k // 4) * 8 + v
                spells.append(text.spell_name(n) if text else n)
        party.append({
            "name": _name(rec[2:6]),
            "job": jobs.get(rec[0], rec[0]),
            "status": statuses.get(rec[1], rec[1]),
            "level": rec[0x26] + 1,
            "exp": int.from_bytes(rec[7:10], "little"),
            "hp": int.from_bytes(rec[0x0A:0x0C], "little"),
            "max_hp": int.from_bytes(rec[0x0C:0x0E], "little"),
            "weapons": [gear(b, WEAPON_ITEM0) for b in rec[0x18:0x1C] if b & 0x7F],
            "armor": [gear(b, ARMOR_ITEM0) for b in rec[0x1C:0x20] if b & 0x7F],
            "spells": spells,
            "mp": list(sram[base + 0x220:base + 0x228]),
            "max_mp": list(sram[base + 0x228:base + 0x230]),
        })
    flags = ram_map.read_flags(sram)
    return {"gold": int.from_bytes(sram[0x1C:0x1F], "little"),
            "flags_set": sorted(k for k, v in flags.items() if v),
            "flags_not_yet": sorted(k for k, v in flags.items() if not v),
            "bag": bag, "party": party,
            "ship_at": tuple(sram[1:3]) if sram[0] else None}
