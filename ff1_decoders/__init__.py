"""Decoders for Final Fantasy (NES, USA): ROM tables (maps, treasure, people, monsters,
battle groups, shops, spells, the world map, dialogue text), the RAM map, save files
and menu screens read from the nametable.

No game data ships with this package: every table is read at run time from a ROM
image you supply.

    from ff1_decoders import Rom
    rom = Rom("ff1.nes")
    rom.shop(0)          # {'id': 0, 'kind': 'weapon', 'goods': [...]}
"""
from __future__ import annotations

from .rom import Rom
from .save import decode_sram
from .spells import CLASSES, SpellTable
from .text import PRG_CRC32, DialogueRom, load, prg_crc32
from .world import World

__version__ = "0.1.0"
__all__ = ["CLASSES", "DialogueRom", "PRG_CRC32", "Rom", "SpellTable", "World",
           "decode_sram", "load", "prg_crc32", "__version__"]
