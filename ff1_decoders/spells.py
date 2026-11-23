"""Spells in Final Fantasy (NES, USA): names, and which class may learn which spell.

There are 64 spells, 8 per level (L1-L8). Within a level, slots 1-4 are white magic
and 5-8 black magic, in the order the magic shops list them. Spell n (1-64) is
level (n - 1) // 8 + 1, slot (n - 1) % 8 + 1; its name is entry $AF + n of the ROM's
item name list (the spells follow the items: spell 1, CURE, is item $B0).

The class permission table is at PRG offset 0x3AD18 (the iNES header skipped):
12 classes x 8 bytes, one byte per spell level. The bits are INVERTED: a set bit
means the class can NOT learn that spell. The most significant bit is the level's
first slot (bit 7 - (slot - 1)). The magic shop reads this table when it answers
"You can't learn that".

A character can hold at most three spells per level: buying a fourth gets "This level
spell is full". The character's spell bytes (SRAM $6300 + $40 * slot, 4 bytes a level,
32 in all) hold each learned spell's slot number 1-8 within its level.
"""
from __future__ import annotations

from .text import DialogueRom, header_size

SPELL_PERMS = 0x3AD18
N_CLASSES = 12
LEVELS = 8
SLOTS = 8
SPELLS_PER_LEVEL_MAX = 3     # "This level spell is full" on a fourth
CLASSES = ("Fighter", "Thief", "Black Belt", "Red Mage", "White Mage", "Black Mage",
           "Knight", "Ninja", "Master", "Red Wizard", "White Wizard", "Black Wizard")


def spell_number(level: int, slot: int) -> int:
    """Spell n (1-64) for a level (1-8) and slot (1-8)."""
    if not (1 <= level <= LEVELS and 1 <= slot <= SLOTS):
        raise ValueError(f"level and slot are 1-8, got {level}, {slot}")
    return (level - 1) * SLOTS + slot


def is_white(n: int) -> bool:
    """Whether spell n (1-64) is white magic (slots 1-4 of its level)."""
    return (n - 1) % SLOTS < 4


def class_id(job: int | str) -> int:
    """A class id (0-11) from an id or a name such as "Red Mage" (any case)."""
    if isinstance(job, int):
        if not 0 <= job < N_CLASSES:
            raise ValueError(f"class id is 0-11, got {job}")
        return job
    names = {c.lower(): i for i, c in enumerate(CLASSES)}
    try:
        return names[job.strip().lower()]
    except KeyError:
        raise ValueError(f"unknown class {job!r}; one of {', '.join(CLASSES)}") from None


class SpellTable:
    """Spell names and class permissions read from a ROM image."""

    def __init__(self, rom: bytes, text: DialogueRom | None = None):
        hdr = header_size(rom)
        self.text = text or DialogueRom(rom)
        o = hdr + SPELL_PERMS
        self.perms = bytes(rom[o:o + N_CLASSES * LEVELS])

    def name(self, n: int) -> str:
        """Spell n's name (1-64)."""
        return self.text.spell_name(n)

    def names(self) -> dict[int, str]:
        return {n: self.name(n) for n in range(1, 65)}

    def by_level(self) -> dict[int, list[str]]:
        """Level -> its 8 spells in slot order (white 1-4, black 5-8)."""
        return {lv: [self.name(spell_number(lv, s)) for s in range(1, SLOTS + 1)]
                for lv in range(1, LEVELS + 1)}

    def can_learn_spell(self, job: int | str, n: int) -> bool:
        """Whether class `job` may learn spell n (1-64)."""
        j = class_id(job)
        lv, slot = (n - 1) // SLOTS, (n - 1) % SLOTS
        return not self.perms[j * LEVELS + lv] >> (7 - slot) & 1

    def learnable(self, job: int | str) -> list[int]:
        """The spell numbers class `job` may learn, in shop order."""
        return [n for n in range(1, 65) if self.can_learn_spell(job, n)]

    def can_learn(self, job: int | str) -> list[str]:
        """The names of the spells class `job` may learn, in shop order."""
        return [self.name(n) for n in self.learnable(job)]

    def learnable_by_level(self, job: int | str) -> dict[int, list[str]]:
        """Level -> the names class `job` may learn there (levels with none left out)."""
        out: dict[int, list[str]] = {}
        for n in self.learnable(job):
            out.setdefault((n - 1) // SLOTS + 1, []).append(self.name(n))
        return out

    def who_can_learn(self, n: int) -> list[str]:
        """The classes that may learn spell n."""
        return [c for j, c in enumerate(CLASSES) if self.can_learn_spell(j, n)]
