"""Text in Final Fantasy (NES, USA): the font's character codes, field dialogue, item
names, and a few small graphics and stat tables that sit next to them.

FF1 draws dialogue straight from ROM to the PPU, so no decoded text exists in RAM.
What RAM does keep is the text pointer (WRAM $3E/$3F): once the box is up it points at
the $00 terminator of the string being shown. Matching it against the 256 terminators
in the ROM's dialogue table gives the string id, and the string is decoded from the
ROM here. The layout follows the community disassembly and was checked against
screenshots of a number of dialogue boxes, including a treasure box's item insert.
"""
from __future__ import annotations

import logging
import zlib
from functools import lru_cache
from pathlib import Path

log = logging.getLogger(__name__)

PRG_CRC32 = 0xCEBD2A31            # CRC32 of the USA ROM with the iNES header removed
DLG_BANK = 0x0A                   # WRAM $57 reads $0A after a dialogue draw
CHARS = {0xBE: "'", 0xBF: ",", 0xC0: ".", 0xC1: " ", 0xC2: "-", 0xC3: "...",
         0xC4: "!", 0xC5: "?", 0xE0: "%", 0xFF: " "}
CHARS.update({0x80 + i: chr(48 + i) for i in range(10)})
CHARS.update({0x8A + i: chr(65 + i) for i in range(26)})
CHARS.update({0xA4 + i: chr(97 + i) for i in range(26)})
# $D4-$DF are equipment-type icons and $E1 a potion icon; they have no letters.
# Equipment names end in a picture of the item's kind, so "Wooden" + staff and
# "Wooden" + nunchucks are two different weapons. The words below name the tiles as
# the game draws them (compared against CHR RAM on a shop screen), and agree with the
# ROM's own item list: $D4 ends Short/Long/Bane/Dragon, $D5 Iron/Silver hammer, $D6
# Small/Silver knife, $D7 Hand/Silver axe, $D8 Wooden/Wizard staff (the 5 G Wooden,
# weapon slot id 3), $D9 the 10 G Wooden, $DA the body armor after Cloth, $DB-$DE the
# shields, helmets, gloves and bracelets that follow. Written as Name[kind].
ICON_WORDS = {0xD4: "sword", 0xD5: "hammer", 0xD6: "knife", 0xD7: "axe", 0xD8: "staff",
              0xD9: "nunchucks", 0xDA: "armor", 0xDB: "shield", 0xDC: "helmet",
              0xDD: "gloves", 0xDE: "bracelet", 0xDF: "shirt"}
FONT_PRG = 0x24000       # the menu font: PRG bank 9 at $8000, loaded to CHR RAM $0000
WEAPON_ITEM0 = 0x1B      # weapon slot id n is item n + $1B (id 3 = item $1E, "Wooden" staff)
ARMOR_ITEM0 = 0x43       # armor slot id n is item n + $43 (id 1 = item $44, "Cloth")
SPELL_ITEM0 = 0xAF       # spell n (1-64, magic-shop order) is item n + $AF (1 = $B0, CURE)
# The weapon (8 bytes each) and armor (4 each) stat tables, 40 of each; a weapon's byte 4
# is the element it hits with, an armor's byte 2 the elements it resists (e.g. a
# fire sword hits with 0x10, an ice sword 0x20; the Ribbon resists 0xFF).
WEAPON_STATS, ARMOR_STATS, GEAR_N = 0x30000, 0x30140, 40
# The START menu's orb box: four orbs of 2x2 tiles (top-left, top-right, bottom-left,
# bottom-right), lit $64-$73 and unlit $76-$79, from PRG $37640 (bank 13), copied to
# CHR RAM $0640. The box lights them in this order as SRAM $6032-$6035 are set.
ORB_PRG = 0x37640
ORB_ORDER = ("fire", "water", "air", "earth")
ORB_DARK = 0x12          # $76 - $64


def header_size(rom: bytes) -> int:
    """16 for an iNES file, 0 for a headerless image."""
    return 16 if rom[:4] == b"NES\x1a" else 0


class DialogueRom:
    def __init__(self, rom: bytes):
        self.hdr = header_size(rom)
        self.rom = rom
        self.ptrs = self._bank(0x8000)           # 256 x u16 LE CPU pointers
        self.items = self._bank(0xB700)          # item names 0-127; 128-255 at $B800
        self.dte_first = self._fixed(0xF0A0)     # pair bytes $1A-$79: first char
        self.dte_second = self._fixed(0xF050)    # ... and second char
        self.terminators = {}
        for i in range(256):
            q = self._ptr(self.ptrs, i)
            while self.rom[self._bank(q)]:
                q += 1
            self.terminators[q] = i              # all 256 are distinct on the USA ROM

    def _bank(self, cpu: int) -> int:
        return self.hdr + DLG_BANK * 0x4000 + (cpu - 0x8000)

    def _fixed(self, cpu: int) -> int:
        return self.hdr + 15 * 0x4000 + (cpu - 0xC000)

    def _ptr(self, table: int, i: int) -> int:
        return self.rom[table + 2 * i] | self.rom[table + 2 * i + 1] << 8

    def font_tile(self, code: int) -> bytes:
        """The menu font's 8x8 tile for a text code, as the NES stores it (16 bytes: low
        plane then high plane). The font is bank 9's first $1000 bytes, which the game
        copies to CHR RAM $0000."""
        off = self.hdr + FONT_PRG + code * 16
        return bytes(self.rom[off:off + 16])

    def icon_tiles(self) -> dict[str, bytes]:
        """The equipment icons ($D4-$DF) by the words item names use for them."""
        return {word: self.font_tile(code) for code, word in ICON_WORDS.items()}

    def gear_elements(self) -> dict[str, int]:
        """Every weapon's and armor's element byte by its name as the menus draw it
        (e.g. 'Flame[sword]': 0x10): a weapon's attack element, an armor's resistances."""
        out = {}
        for n in range(1, GEAR_N + 1):
            w = self.hdr + WEAPON_STATS + (n - 1) * 8 + 4
            a = self.hdr + ARMOR_STATS + (n - 1) * 4 + 2
            out[self.item_name(n + WEAPON_ITEM0)] = self.rom[w]
            out.setdefault(self.item_name(n + ARMOR_ITEM0), self.rom[a])
        return out

    def weapon_palettes(self) -> dict[str, int]:
        """Every weapon's battle-sprite palette byte (its stats' last byte, an NES colour
        like $26) by its menu name: the colour the weapon is drawn in when swung."""
        return {self.item_name(n + WEAPON_ITEM0): self.rom[self.hdr + WEAPON_STATS + (n - 1) * 8 + 7]
                for n in range(1, GEAR_N + 1)}

    def orb_tiles(self) -> dict[str, bytes]:
        """The menu's orbs, lit by element and unlit as "dark": four 16-byte tiles each,
        top-left, top-right, bottom-left, bottom-right."""
        def tiles(first: int) -> bytes:
            off = self.hdr + ORB_PRG + first * 16
            return bytes(self.rom[off:off + 64])
        out = {name: tiles(i * 4) for i, name in enumerate(ORB_ORDER)}
        out["dark"] = tiles(ORB_DARK)
        return out

    def item_name(self, item_id: int) -> str:
        """An item's name as the menus draw it, its type icon as [kind]: Wooden[staff]."""
        table = self.items + (0x100 if item_id >= 0x80 else 0)
        off = self._bank(self._ptr(table, item_id & 0x7F))
        out = []
        for _ in range(16):
            v = self.rom[off]
            off += 1
            if v == 0x00:
                break
            if v in ICON_WORDS:
                out = list("".join(out).rstrip()) + [f"[{ICON_WORDS[v]}]"]
            else:
                out.append(CHARS.get(v, ""))
        return " ".join("".join(out).split())

    def spell_name(self, n: int) -> str:
        """Spell n (1-64, the magic shops' order: 8 per level, white 1-4, black 5-8)."""
        return self.item_name(n + SPELL_ITEM0) if 1 <= n <= 64 else ""

    def id_at(self, text_ptr: int) -> int | None:
        """The dialogue id whose terminator `text_ptr` (WRAM $3E/$3F) points at, or None
        while the string is still being drawn."""
        return self.terminators.get(text_ptr)

    def decode(self, dialogue_id: int, item_id: int | None = None) -> str:
        """Dialogue string `dialogue_id` as text. `item_id` fills the $02 "item name"
        code (WRAM $61 holds it while a treasure box's message is up)."""
        out: list[str] = []
        self._render(self._bank(self._ptr(self.ptrs, dialogue_id & 0xFF)), out, item_id)
        return "\n".join(line.strip() for line in "".join(out).split("\n")).strip()

    def _render(self, off: int, out: list[str], item_id: int | None, depth: int = 0) -> None:
        rom = self.rom
        while True:
            v = rom[off]
            off += 1
            if v == 0x00:
                return
            if v >= 0x7A:
                out.append(CHARS.get(v, ""))
            elif v >= 0x1A:                     # DTE pair
                k = v - 0x1A
                out.append(CHARS.get(rom[self.dte_first + k], "")
                           + CHARS.get(rom[self.dte_second + k], ""))
            elif v == 0x02:                     # item name; the id is in WRAM $61
                if item_id is None or depth:
                    continue
                table = self.items + (0x100 if item_id >= 0x80 else 0)
                sub: list[str] = []
                self._render(self._bank(self._ptr(table, item_id & 0x7F)), sub, None, depth + 1)
                out.append("".join(sub).strip())
            elif v == 0x03:                     # leader's name; no dialogue string uses it
                return
            else:                               # $01 and $05 seen: line break
                out.append("\n")


def prg_crc32(rom: bytes) -> int:
    """CRC32 of the ROM image without its iNES header."""
    return zlib.crc32(rom[header_size(rom):]) & 0xFFFFFFFF


@lru_cache(maxsize=2)
def load(path: str) -> DialogueRom | None:
    """The decoder for the ROM at `path`, or None if it can't be read or isn't the USA
    release the layout was read from (another revision would decode garbage)."""
    try:
        rom = Path(path).read_bytes()
    except OSError as e:
        log.warning("can't read %s: %s", path, e)
        return None
    crc = prg_crc32(rom)
    if crc != PRG_CRC32:
        log.warning("%s has CRC32 %08X (headerless); these decoders know %08X",
                    path, crc, PRG_CRC32)
        return None
    return DialogueRom(rom)
