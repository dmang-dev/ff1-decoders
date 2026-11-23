"""Dialogue and item-name decoding: on a synthetic ROM layout, and on a real ROM."""
from __future__ import annotations

import pytest

from ff1_decoders import text
from ff1_decoders.text import CHARS, DialogueRom

GLYPH = {v: k for k, v in CHARS.items() if len(v) == 1 and k != 0xC1}


def _fake_rom() -> bytes:
    """Enough of the layout for the dialogue decoder: bank $0A's pointer table, two
    strings and an item name, and the DTE tables in bank 15."""
    rom = bytearray(16 + 16 * 0x4000)
    rom[:4] = b"NES\x1a"
    bank = 16 + 0x0A * 0x4000
    put = lambda cpu, data: rom.__setitem__(slice(bank + cpu - 0x8000, bank + cpu - 0x8000 + len(data)), data)
    for i in range(256):                                     # every id gets a 1-byte string
        put(0x8000 + 2 * i, (0x9000 + 2 * i).to_bytes(2, "little"))
        put(0x9000 + 2 * i, b"\xc0\x00")
    put(0x8000, (0xA000).to_bytes(2, "little"))
    put(0xA000, bytes([0x8A + 7, 0x1A, 0xC4, 0x01, 0xFF, 0x02, 0x00]))   # "H" + DTE "i" ... item
    put(0xB700 + 2 * 5, (0xB000).to_bytes(2, "little"))
    put(0xB000, bytes([0x8A + 8, 0xB5, 0xB2, 0xB1, 0xFF, 0xFF, 0x00]))   # "Iron  "
    fixed = 16 + 15 * 0x4000
    rom[fixed + 0xF0A0 - 0xC000] = 0xA4 + 8                  # DTE $1A = "i" + ""
    rom[fixed + 0xF050 - 0xC000] = 0x00
    return bytes(rom)


def test_dialogue_found_by_its_terminator():
    rom = DialogueRom(_fake_rom())
    assert rom.id_at(0xA006) == 0 and rom.id_at(0x9000 + 2 * 7 + 1) == 7
    assert rom.id_at(0xA003) is None                         # mid-string: still drawing
    assert rom.decode(0, item_id=5) == "Hi!\nIron"
    assert rom.decode(0) == "Hi!"


def test_headerless_images_decode_the_same():
    assert DialogueRom(_fake_rom()[16:]).decode(0, item_id=5) == "Hi!\nIron"


def test_item_names_carry_their_icon_as_a_word():
    rom = object.__new__(DialogueRom)
    rom.hdr, rom.rom = 0, bytearray(0x40000)
    rom.items = rom._bank(0xB700)
    for item, cpu, tiles in ((0x1E, 0x9000, "Wooden"), (0x1C, 0x9010, "Wooden"),
                             (0x44, 0x9020, "Cloth")):
        rom.rom[rom.items + 2 * item:rom.items + 2 * item + 2] = cpu.to_bytes(2, "little")
        icon = {0x1E: b"\xd8", 0x1C: b"\xd9", 0x44: b"\xff\xff"}[item]
        s = bytes(GLYPH[c] for c in tiles) + icon + b"\x00"
        rom.rom[rom._bank(cpu):rom._bank(cpu) + len(s)] = s
    assert rom.item_name(0x1E) == "Wooden[staff]"
    assert rom.item_name(0x1C) == "Wooden[nunchucks]"
    assert rom.item_name(0x44) == "Cloth"


def test_load_refuses_another_revision(tmp_path):
    p = tmp_path / "other.nes"
    p.write_bytes(_fake_rom())
    assert text.load(str(p)) is None
    assert text.load(str(tmp_path / "missing.nes")) is None


def test_real_rom_text(rom_bytes):
    import os
    assert text.prg_crc32(rom_bytes) == text.PRG_CRC32
    rom = text.load(os.environ["FF1_ROM"])
    assert rom is not None
    assert rom.decode(1).startswith("LIGHT WARRIORS")       # the King's first line
    assert rom.item_name(0x19) == "HEAL" and rom.spell_name(1) == "CURE"
    assert len(rom.terminators) == 256


def test_gear_elements_and_palettes(rom_bytes):
    rom = DialogueRom(rom_bytes)
    g = rom.gear_elements()
    assert g["Flame[sword]"] == 0x10 and g["Ice[sword]"] == 0x20 and g["Ribbon"] == 0xFF
    assert g["Flame[armor]"] == 0x20 and g["Opal[armor]"] == 0x40 and g["Iron[armor]"] == 0
    assert len(g) == 80
    p = rom.weapon_palettes()
    assert len(p) == 40 and p["Flame[sword]"] == 0x26 and p["Xcalber"] == 0x28


def test_graphics_tiles(rom_bytes):
    rom = DialogueRom(rom_bytes)
    orbs = rom.orb_tiles()
    assert set(orbs) == {"fire", "water", "air", "earth", "dark"}
    assert all(len(v) == 64 for v in orbs.values()) and orbs["fire"] != orbs["dark"]
    icons = rom.icon_tiles()
    assert set(icons) == set(text.ICON_WORDS.values()) and all(len(v) == 16 for v in icons.values())
    assert rom.font_tile(0x8A) != rom.font_tile(0x8B)        # "A" and "B" differ
