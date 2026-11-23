"""Menu text read from synthetic nametables drawn the way the game draws its boxes."""
from __future__ import annotations

from ff1_decoders import screen
from ff1_decoders.text import CHARS

GLYPH = {v: k for k, v in CHARS.items() if len(v) == 1 and k != 0xC1}


def draw_box(nt: bytearray, c0: int, r0: int, c1: int, r1: int, lines: dict[int, str]) -> None:
    """A box: border tiles $F7-$FE, $FF blanks, text rows {row: text}."""
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            nt[r * 32 + c] = (0xF7 if (r, c) == (r0, c0) else 0xF9 if (r, c) == (r0, c1)
                              else 0xFC if (r, c) == (r1, c0) else 0xFE if (r, c) == (r1, c1)
                              else 0xF8 if r == r0 else 0xFD if r == r1
                              else 0xFA if c == c0 else 0xFB if c == c1 else 0xFF)
    for r, text in lines.items():
        for k, ch in enumerate(text):
            nt[r * 32 + c0 + 1 + k] = GLYPH.get(ch, 0xFF)


def put(nt: bytearray, c: int, r: int, text: str | bytes) -> None:
    tiles = text if isinstance(text, bytes) else bytes(GLYPH.get(ch, 0xFF) for ch in text)
    nt[r * 32 + c:r * 32 + c + len(tiles)] = tiles


def shop_screen(message: str, options: list[str], goods: list[tuple[str, int]] | None,
                gold: int) -> bytearray:
    nt = bytearray(0x800)
    draw_box(nt, 12, 2, 19, 5, {4: "ITEM"})
    draw_box(nt, 1, 4, 9, 15, {6 + i: w for i, w in enumerate(message.split())})
    if goods:
        lines = {}
        for i, (name, price) in enumerate(goods):
            lines[4 + 4 * i] = name
            lines[6 + 4 * i] = f"{price:>7}"
        draw_box(nt, 22, 2, 30, 23, lines)
    if options:
        draw_box(nt, 6, 18, 14, 27, {20 + 2 * i: o for i, o in enumerate(options)})
    draw_box(nt, 18, 24, 27, 27, {26: f"{gold:>4} G"})
    return nt


def test_boxes_and_the_entry_under_a_hand():
    nt = shop_screen("What do you want?", [], [("HEAL", 60), ("PURE", 75)], 400)
    assert screen.boxes(bytes(nt)) == ["ITEM", "HEAL 60 PURE 75", "What do you want?", "400 G"]
    assert screen.entry_at(bytes(nt), 168, 32) == "HEAL 60"      # name + the price below
    assert screen.entry_at(bytes(nt), 168, 64) == "PURE 75"
    assert screen.entry_at(bytes(nt), 168, 128) == ""             # nothing drawn there
    nt = shop_screen("Welcome", ["Buy", "Exit"], None, 400)
    assert screen.entry_at(bytes(nt), 40, 160) == "Buy"
    assert screen.entry_at(bytes(nt), 40, 176) == "Exit"
    # two entries on one row (the START menu's ITEM list): up to the double blank
    nt = bytearray(0x800)
    draw_box(nt, 1, 3, 30, 21, {6: "  HEAL 3  PURE 1"})
    assert screen.entry_at(bytes(nt), 16, 48) == "HEAL 3"
    assert screen.entry_at(bytes(nt), 80, 48) == "PURE 1"
    # the START menu's picture words
    nt = bytearray(0x800)
    draw_box(nt, 2, 15, 9, 28, {18: " ITEM"})
    nt[22 * 32 + 4:22 * 32 + 9] = bytes.fromhex("cfd0d1d2d3")
    assert screen.entry_at(bytes(nt), 16, 176) == "WEAPON"
    assert screen.boxes(bytes(nt)) == ["ITEM WEAPON"]


def test_item_pictures_are_named_in_a_goods_list():
    nt = bytearray(0x800)
    rows = {4: ("Wooden", [0xD8]), 8: ("Small", [0xFF, 0xD6]), 12: ("Wooden", [0xD9]),
            16: ("Rapier", [0xFF]), 20: ("Iron", [0xFF, 0xFF, 0xD5])}
    draw_box(nt, 22, 2, 30, 23, {r + 2: f"{p:>7}" for r, p in zip(rows, (5, 5, 10, 10, 10))})
    for r, (name, tail) in rows.items():
        tiles = [GLYPH[c] for c in name] + tail
        nt[r * 32 + 23:r * 32 + 23 + len(tiles)] = bytes(tiles)
    assert screen.boxes(bytes(nt)) == [
        "Wooden[staff] 5 Small[knife] 5 Wooden[nunchucks] 10 Rapier 10 Iron[hammer] 10"]
    assert screen.entry_at(bytes(nt), 168, 32) == "Wooden[staff] 5"
    assert screen.entry_at(bytes(nt), 168, 160) == "Iron[hammer] 10"


def test_box_at_and_options_at():
    nt = shop_screen("You can't afford that.", ["Buy", "Exit"], [("HEAL", 60)], 40)
    assert screen.box_at(bytes(nt), 5, 2) == "You can't afford that."
    assert screen.box_at(bytes(nt), 6, 6) == ""
    names = ["ALEX", "BETH", "CARL", "DORA"]
    nt = shop_screen("Who will take it?", names, None, 400)
    assert screen.options_at(bytes(nt), 40, 176) == names
    assert screen.options_at(bytes(nt), 0, 0) == []


def test_battle_spell_list_rows_and_words():
    nt = bytearray(0x800)
    draw_box(nt, 2, 19, 23, 28, {21: "L1 CURE FOG       2", 23: "L2                0"})
    assert screen.row_at(bytes(nt), 32, 166) == "L1 CURE FOG 2"
    assert screen.row_at(bytes(nt), 32, 120) == ""
    assert screen.entry_at(bytes(nt), 32, 166, below=False) == "CURE FOG"
    assert screen.word_at(bytes(nt), 32, 166) == "CURE"


def test_equip_screen_label_left_of_a_slot():
    nt = bytearray(0x800)
    draw_box(nt, 1, 1, 7, 4, {})
    put(nt, 2, 3, bytes.fromhex("cfd0d1d2d3"))
    draw_box(nt, 8, 1, 30, 4, {})
    put(nt, 11, 3, "EQUIP  TRADE  DROP")
    for i, name in enumerate(("ALEX", "BETH", "CARL", "DORA")):
        r = 5 + 6 * i
        draw_box(nt, 1, r, 8, r + 3, {})
        put(nt, 3, r + 2, name)
        draw_box(nt, 8, r, 30, r + 5, {})
    put(nt, 10, 7, b"\xc7\xc2" + bytes(GLYPH[c] for c in "Wooden") + b"\xd8")   # E-Wooden[staff]
    nt = bytes(nt)
    assert screen.entry_at(nt, 64, 56) == "E-Wooden[staff]"
    assert screen.label_left(nt, 64, 56) == "ALEX"
    assert screen.label_left(nt, 64, 104) == "BETH"
    assert screen.boxes(nt)[:4] == ["WEAPON", "EQUIP TRADE DROP", "ALEX", "E-Wooden[staff]"]
