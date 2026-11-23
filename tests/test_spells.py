"""The class spell-permission table (PRG 0x3AD18, inverted bits, MSB = slot 1)."""
from __future__ import annotations

import pytest

from ff1_decoders.spells import (CLASSES, SPELL_PERMS, SpellTable, class_id, is_white,
                                 spell_number)


def test_spell_numbers_and_classes():
    assert spell_number(1, 1) == 1 and spell_number(5, 8) == 40 and spell_number(8, 8) == 64
    assert is_white(1) and is_white(4) and not is_white(5) and is_white(9)
    assert class_id("red mage") == 3 and class_id(" Black Wizard ") == 11 and class_id(6) == 6
    assert len(CLASSES) == 12
    with pytest.raises(ValueError):
        class_id("Dragoon")
    with pytest.raises(ValueError):
        spell_number(0, 1)


class _Names:
    """Stands in for DialogueRom: spell n is named 'S<n>'."""
    def spell_name(self, n):
        return f"S{n}"


def test_inverted_bits_msb_first_on_a_synthetic_table():
    rom = bytearray(SPELL_PERMS + 12 * 8)
    rom[SPELL_PERMS:SPELL_PERMS + 12 * 8] = b"\xff" * 96       # nobody learns anything
    rom[SPELL_PERMS + 8 * 3 + 0] = 0x7F                          # Red Mage: L1 slot 1 only
    rom[SPELL_PERMS + 8 * 3 + 4] = 0xFE                          # ... and L5 slot 8
    t = SpellTable(bytes(rom), text=_Names())
    assert t.learnable(3) == [1, 40]
    assert t.can_learn("Red Mage") == ["S1", "S40"]
    assert t.learnable_by_level(3) == {1: ["S1"], 5: ["S40"]}
    assert t.who_can_learn(1) == ["Red Mage"] and t.learnable(0) == []


def test_the_real_table(rom):
    st = rom.spells
    assert st.by_level()[1] == ["CURE", "HARM", "FOG", "RUSE", "FIRE", "SLEP", "LOCK", "LIT"]
    by = st.learnable_by_level
    assert by("Red Mage")[5] == ["CUR3", "FIR3", "SLO2"]
    assert max(by("Red Mage")) == 5
    assert by("Knight") == {1: ["CURE", "FOG", "RUSE"], 2: ["LAMP", "MUTE", "ALIT", "INVS"],
                            3: ["CUR2", "AFIR"]}
    for job in ("Fighter", "Thief", "Black Belt", "Master"):
        assert st.can_learn(job) == [], job
    assert by("White Wizard")[8] == ["LIF2", "FADE", "WALL", "XFER"]


def test_who_learns_life(rom):
    st = rom.spells
    red, wiz = st.can_learn("Red Mage"), st.can_learn("Red Wizard")
    assert "CUR3" in red and not {"LIFE", "HRM3", "HEL2"} & set(red)
    assert "LIFE" in wiz and "LIF2" not in wiz and "LIF2" in st.can_learn("White Wizard")
    assert len(st.can_learn("White Mage")) == 25 and "LIFE" in st.can_learn("White Mage")
    assert all(is_white(n) for n in st.learnable("White Wizard"))
    assert not any(is_white(n) for n in st.learnable("Black Wizard"))


def test_only_the_magic_shop_stores_a_single_spell_byte(rom_bytes):
    """A spell value goes into $6300+ only at the magic shop (LDX $030A, LDA $030B,
    STA $6300,X); the other stores there clear or copy the whole block (new game,
    save), so nothing takes a learned spell away."""
    from ff1_decoders.text import header_size
    h = header_size(rom_bytes)
    prg = rom_bytes[h:h + 0x40000]
    stores = [i for i in range(len(prg) - 2)
              if prg[i] in (0x8D, 0x9D, 0x99) and prg[i + 2] == 0x63 and prg[i + 1] < 0x20]
    assert stores == [0x39BF8, 0x3A3A6, 0x3C044, 0x3C0A3]
    assert prg[0x3A3A0:0x3A3A9] == bytes.fromhex("ae0a03ad0b039d0063")
