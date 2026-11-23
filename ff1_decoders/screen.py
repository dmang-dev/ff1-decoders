"""Menu screens of Final Fantasy (NES) as text: the words in the boxes, read from the
PPU nametable.

FF1 draws menus, shops and the battle lists as background tiles, and its font tiles
are the same codes as its text ($80-$BD letters and digits, text.CHARS). So nametable 0
(where every menu screen is drawn, with no scroll) spells out what is in each box. Box
borders are tiles $F7-$FE, so a box's inside is a 4-connected run of other tiles that
does not reach the screen's edge (the space around the boxes does; blanks are $00 or
$FF on both sides of a border). Checked against screenshots of shops, the inn and
clinic, the START menu with ITEM/MAGIC/WEAPON/STATUS and the battle MAGIC/DRINK/ITEM
lists. Read it only while such a screen is up (see the screen-mode fields in the RAM
map: shop_open, menu_open, in_battle): on the walking screen nametable 0 holds stale
boxes.

Every function takes the nametable as bytes (at least 32 x 30 tiles; the 2 KB of
nametable RAM from an emulator works as is). Positions are a hand cursor sprite's
(x, y) in pixels, as OAM holds them.
"""
from __future__ import annotations

from .text import CHARS, ICON_WORDS

COLS, ROWS = 32, 30
BORDER = 0xF7            # $F7-$FE: box corners and edges ($FF is a blank)
OUTSIDE = 0x00
# Menu tiles beyond the text font: '/' between HP values, the 'L' of a level, the 'E'
# of 'E-' before an equipped weapon or armor (WEAPON/ARMOR screens: blank before EQUIP,
# $C7 $C2 after it), and two words drawn as one 5-tile picture each (START menu WEAPON
# and STATUS). Equipment names end in a type icon (ICONS), drawn as [kind]:
# Wooden[staff] and Wooden[nunchucks] are two weapons.
SCREEN_CHARS = dict(CHARS) | {0x7A: "/", 0xC6: "L", 0xC7: "E"}
WORDS = {bytes.fromhex("cfd0d1d2d3"): "WEAPON", bytes.fromhex("cacbcccdce"): "STATUS"}
ICONS = ICON_WORDS
def _decode(tiles: list[int]) -> list[tuple[int, str]]:
    """(column offset, text) per drawn glyph; icons and graphics tiles give ''."""
    out, i = [], 0
    while i < len(tiles):
        word = next((w for k, w in WORDS.items() if bytes(tiles[i:i + len(k)]) == k), None)
        if word:
            out.append((i, word))
            i += 5
            continue
        t = tiles[i]
        if t in ICONS:
            while out and out[-1][1] == " ":
                out.pop()             # "Iron  " + hammer reads "Iron[hammer]"
            out.append((i, f"[{ICONS[t]}]"))
        else:
            out.append((i, " " if t in (OUTSIDE, 0xFF) or t >= BORDER else SCREEN_CHARS.get(t, "")))
        i += 1
    return out


def _border(t: int) -> bool:
    return BORDER <= t < 0xFF


def _text(tiles: list[int]) -> str:
    return "".join(s for _, s in _decode(tiles))


def _squeeze(s: str) -> str:
    return " ".join(s.split())


def boxes(nt: bytes) -> list[str]:
    """The text of each box on nametable 0, top-left box first; empty boxes left out."""
    return [t for _, _, t in placed_boxes(nt)]


def box_at(nt: bytes, row: int, col: int) -> str:
    """The text of the box whose inside starts at (row, col), or ''."""
    return next((t for r, c, t in placed_boxes(nt) if (r, c) == (row, col)), "")


def placed_boxes(nt: bytes) -> list[tuple[int, int, str]]:
    """(row, column, text) of each box: where its inside starts, top-left box first."""
    grid = nt[:COLS * ROWS]
    inside = [not _border(t) for t in grid]
    seen = [False] * len(grid)
    found = []
    for start in range(len(grid)):
        if not inside[start] or seen[start]:
            continue
        cells, todo = [], [start]
        seen[start] = True
        while todo:
            i = todo.pop()
            cells.append(i)
            r, c = divmod(i, COLS)
            for rr, cc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                j = rr * COLS + cc
                if 0 <= rr < ROWS and 0 <= cc < COLS and inside[j] and not seen[j]:
                    seen[j] = True
                    todo.append(j)
        rows: dict[int, list[int]] = {}
        for i in sorted(cells):
            rows.setdefault(i // COLS, []).append(i)
        lines = []
        for r in sorted(rows):
            idx = rows[r]
            # a row of one box is contiguous; a gap would be another box's wall
            text = _text([grid[i] for i in range(idx[0], idx[-1] + 1)])
            if text.strip():
                lines.append(_squeeze(text))
        edge = any(i < COLS or i >= COLS * (ROWS - 1) or i % COLS in (0, COLS - 1)
                   for i in cells)
        if lines and not edge:
            found.append((min(cells) // COLS, min(i % COLS for i in cells), " ".join(lines)))
    return sorted(found)


def options_at(nt: bytes, x: int, y: int) -> list[str]:
    """The entries of the one-per-row menu box a hand at sprite (x, y) points into
    (a shop's Buy / Sell / Exit, Yes / No, the party list), top to bottom; [] when
    the hand points at no box."""
    grid = nt[:COLS * ROWS]
    c = min(COLS - 1, x // 8 + 2)
    for r in (y // 8, y // 8 + 1):
        if not 0 <= r < ROWS or _border(grid[r * COLS + c]):
            continue
        top = r
        while top > 0 and not _border(grid[(top - 1) * COLS + c]):
            top -= 1
        out = []
        for rr in range(top, ROWS):
            row = grid[rr * COLS:(rr + 1) * COLS]
            if _border(row[c]):
                break
            left = next((k for k in range(c, -1, -1) if _border(row[k])), -1)
            right = next((k for k in range(c, COLS) if _border(row[k])), COLS)
            text = _squeeze(_text(list(row[left + 1:right])))
            if text:
                out.append(text)
        return out
    return []


def entry_at(nt: bytes, x: int, y: int, below: bool = True) -> str:
    """The menu entry a hand cursor at sprite (x, y) points at: the words right of
    the hand on its row (or the row below: the hand is 16 px tall), up to the next
    gap of two blanks, plus lines under it that start further right (a price under
    an item name; below=False leaves those out). '' when nothing is drawn there."""
    grid = nt[:COLS * ROWS]
    c0 = min(COLS - 1, x // 8 + 2)

    def segment(r: int) -> list[tuple[int, str]]:
        if not 0 <= r < ROWS:
            return []
        row = list(grid[r * COLS + c0:(r + 1) * COLS])
        # a hand beside a box (the START menu's character grid) points across its wall
        skip = 1 if row and _border(row[0]) else 0
        end = next((k for k, t in enumerate(row) if k >= skip and _border(t)), len(row))
        return _decode(row[skip:end])

    def first_words(seg: list[tuple[int, str]], near: bool = True) -> tuple[int | None, str]:
        text, start = "", None
        for col, s in seg:
            if start is None:
                if s.strip():
                    start, text = col, s
                elif near and col > 3:
                    return None, ""          # nothing near the hand on this row
                continue
            text += s
            if text.endswith("  "):
                break
        return start, text.strip()

    for r in (y // 8, y // 8 + 1):
        start, words = first_words(segment(r))
        if words:
            break
    else:
        return ""
    extra = []
    for rr in range(r + 1, r + 4 if below else r + 1):
        s2, w2 = first_words(segment(rr), near=False)
        if not w2:
            continue
        if s2 is not None and s2 > start:
            extra.append(w2)
            continue
        break
    return _squeeze(" ".join([words] + extra))


def label_left(nt: bytes, x: int, y: int) -> str:
    """The words in the leftmost box beside a hand at sprite (x, y), on its rows or the
    nearest row above with any: whose slot it is on the WEAPON / ARMOR screens, where
    each character's name box sits left of their four slots. '' when nothing is drawn."""
    grid = nt[:COLS * ROWS]
    c1 = max(0, min(COLS, x // 8))
    for r in range(min(ROWS - 1, y // 8 + 1), -1, -1):
        row, chunk, chunks = grid[r * COLS:r * COLS + c1], [], []
        for t in list(row) + [BORDER]:
            if _border(t):
                chunks.append(_squeeze(_text(chunk)))
                chunk = []
            else:
                chunk.append(t)
        text = next((c for c in chunks if c), "")
        if text:
            return text
    return ""


def word_at(nt: bytes, x: int, y: int) -> str:
    """The one word right of a hand at sprite (x, y). Spell lists stand names one blank
    apart (battle: 'L1 CURE FOG FIRE 3'), where entry_at reads 'CURE FOG'. '' when no
    word starts there."""
    grid = nt[:COLS * ROWS]
    c0 = min(COLS - 1, x // 8 + 2)
    for r in (y // 8, y // 8 + 1):
        if not 0 <= r < ROWS:
            continue
        row = list(grid[r * COLS + c0:(r + 1) * COLS])
        end = next((k for k, t in enumerate(row) if _border(t)), len(row))
        text = "".join(s for _, s in _decode(row[:end]))
        if text[:1].strip() and text.split():
            return text.split()[0]
    return ""


def row_at(nt: bytes, x: int, y: int) -> str:
    """The whole line of the box a hand cursor at sprite (x, y) points into, border to
    border (the row entry_at reads). In the battle spell list that is a spell level's
    row: 'L1 CURE 2' (the level, its spells, the number drawn at its end); the lines
    below it are other levels, not part of the entry. '' when nothing is drawn."""
    grid = nt[:COLS * ROWS]
    c0 = min(COLS - 1, x // 8 + 2)
    for r in (y // 8, y // 8 + 1):
        if not 0 <= r < ROWS:
            continue
        row = list(grid[r * COLS:(r + 1) * COLS])
        if _border(row[c0]):
            continue
        a = c0
        while a > 0 and not _border(row[a - 1]):
            a -= 1
        b = c0
        while b < COLS and not _border(row[b]):
            b += 1
        text = _squeeze(_text(row[a:b]))
        if text and _text(row[c0:b]).strip():
            return text
    return ""
