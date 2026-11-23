"""The 256x256 world map of Final Fantasy (NES, USA): its tiles, their properties
(terrain) and the entrances into towns, castles and dungeons.

The world map lives in PRG bank 1: 256 row pointers (CPU $8000-based, little-endian),
each row run-length coded: a byte under $80 is one tile; $80 + t is followed by a
count (0 = 256) of tile t; $FF ends the row. Every row decodes to exactly 256 tiles,
and the rows match the RAM copy the game keeps around the party ($7000, a ring of 16
rows). The tile property table (2 bytes x 128 tiles) is the first 256 bytes of bank 0;
the game copies it to WRAM $0400 while on the world map.
"""
from __future__ import annotations

from .text import header_size

WORLD_W = 256
WORLD_ROWS = 0x4000          # PRG: bank 1 starts with the row pointer table
WORLD_PROPS = 0x0000         # PRG bank 0: 2 bytes per world tile id
ENTRANCE_MAPS = 0x2C40       # PRG bank 0: 32 bytes, world entrance n (tile props byte 1
                             # low bits) -> the map it leads to (the same table the ROM's
                             # entrance code reads; see rom.ENTER_MAP)

# World-map tile property byte 0: bit 0 no walking, bit 1 no canoe, bit 2 no ship,
# bit 3 no airship landing, bit 5 dock. Forest is not one bit: grass reads $06 and forest
# $0E, so it is left as walkable land here. Byte 1 bit 7 = an entrance.
TERRAIN = {"entrance": "an entrance", "river": "river (canoe)", "sea": "sea (ship)",
           "wall": "blocked (mountain, rock, ...)", "dock": "dock",
           "land": "walkable land"}


def world_tiles(rom: bytes) -> bytes | None:
    """The whole 256x256 world map's tile ids, row by row, or None when the data does
    not decode (not an FF1 ROM)."""
    hdr = header_size(rom)
    base = hdr + WORLD_ROWS
    out = bytearray()
    try:
        for i in range(WORLD_W):
            ptr = rom[base + 2 * i] | rom[base + 2 * i + 1] << 8
            if not 0x8000 <= ptr < 0xC000:           # not a pointer into the bank
                return None
            o = base + ptr - 0x8000
            row = bytearray()
            while len(row) < WORLD_W:
                b = rom[o]
                o += 1
                if b == 0xFF:
                    break
                if b & 0x80:
                    row += bytes([b & 0x7F]) * (rom[o] or 256)
                    o += 1
                else:
                    row.append(b)
            if len(row) != WORLD_W:
                return None
            out += row
    except IndexError:
        return None
    return bytes(out)


def world_props(rom: bytes) -> bytes:
    """World-map tile properties, 2 bytes for each of 128 tile ids (PRG bank 0)."""
    hdr = header_size(rom)
    return bytes(rom[hdr + WORLD_PROPS:hdr + WORLD_PROPS + 256])


def terrain(b0: int, b1: int) -> str:
    """A key of TERRAIN for a world tile with property bytes b0, b1."""
    if b1 & 0x80:
        return "entrance"
    if b0 & 1:
        if b0 & 0x07 == 0x05:
            return "river"
        if not b0 & 0x04:
            return "sea"
        return "wall"
    if b0 & 0x20:
        return "dock"
    return "land"


def air_lands(b0: int) -> bool:
    """Whether the airship can land on a world tile with props byte 0 `b0`: walkable
    (bit 0 clear) and bit 3 clear. Grass ($06) allows it; sea, mountain and forest do
    not."""
    return not b0 & 0x09


class World:
    """The world map of a ROM image, with its terrain and entrances."""

    def __init__(self, rom: bytes):
        hdr = header_size(rom)
        self.tiles = world_tiles(rom) or b""
        self.props = world_props(rom)
        self.entrance_maps = bytes(rom[hdr + ENTRANCE_MAPS:hdr + ENTRANCE_MAPS + 32])

    def entrance_map(self, b1: int) -> int:
        """The map a world entrance with props byte 1 `b1` leads into."""
        return self.entrance_maps[b1 & 0x1F]

    def tile_id(self, x: int, y: int) -> int:
        return self.tiles[(y % WORLD_W) * WORLD_W + x % WORLD_W]

    def entrances(self) -> dict[int, list[tuple[int, int]]]:
        """map id -> the world tiles that lead into it."""
        out: dict[int, list[tuple[int, int]]] = {}
        for y in range(WORLD_W):
            for x in range(WORLD_W):
                b1 = self.props[2 * self.tiles[y * WORLD_W + x] + 1]
                if b1 & 0x80:
                    out.setdefault(self.entrance_map(b1), []).append((x, y))
        return dict(sorted(out.items()))

    def tile(self, x: int, y: int) -> dict:
        """What is at world (x, y): tile id, property bytes, terrain and, for an
        entrance, the map id it leads into (`leads_to`)."""
        t = self.tile_id(x, y)
        b0, b1 = self.props[2 * t], self.props[2 * t + 1]
        kind = terrain(b0, b1)
        out = {"x": x % WORLD_W, "y": y % WORLD_W, "tile": t, "props": f"{b0:02x} {b1:02x}",
               "terrain": TERRAIN[kind]}
        if kind == "entrance":
            out["leads_to"] = self.entrance_map(b1)
        return out

    def tile_kinds(self) -> dict[int, str]:
        """Tile id (0-127) -> TERRAIN key."""
        return {t: terrain(self.props[2 * t], self.props[2 * t + 1]) for t in range(128)}
