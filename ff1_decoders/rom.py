"""ROM decoders for Final Fantasy (NES, USA): the town / castle / dungeon maps and what
is on them (stairs, doors, treasure boxes, shops, people, special spots), map pictures,
the monsters, the battle groups each place can throw at the party, and the shops'
goods and prices.

Offsets are into the 256 KB PRG (the iNES header, when there is one, is skipped). The
names of the tile-property values follow the community FF1 disassembly; where they sit
in the maps (the ROD's rock wall on map 30, the LUTE's seal on map 54, one ORB spot on
each FIEND's floor) agrees with them. The world map is decoded in `world.py`.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from .text import ARMOR_ITEM0, CHARS, GEAR_N, WEAPON_ITEM0, DialogueRom, header_size

N_MAPS = 61                 # standard maps 0-60
MAP_W = 64
MAP_PTRS = 0x10000          # bank 4: u16 per map, bank-relative; RLE data follows
TILESET_OF_MAP = 0x2CC0     # bank 0: one byte per map, the tileset (0-7)
TILE_PROPS = 0x0800         # bank 0: 2 bytes x 128 tiles per tileset
TILE_ATTR = 0x0400          # bank 0: the palette (low 2 bits) of each of 128 tiles
TILE_TSA = 0x1000           # bank 0: 4 x 128 bytes per tileset: the 8x8 picture in each corner
TILE_CHR = 0xC000           # bank 3: 2 KB of 8x8 pictures per tileset
MAP_PALETTES = 0x2000       # bank 0: 48 bytes per map: 16 outdoor, 16 sprite, 16 in-room
OBJECTS = 0x3400            # bank 0: 16 x 3 bytes per map: object id, x | flags, y | flags
TREASURE = 0x3100           # bank 0: 256 boxes -> item id (gold for $6C up, see price)
TELE_X, TELE_Y, TELE_MAP = 0x2D00, 0x2D40, 0x2D80     # stairs and teleports inside maps
ENTER_X, ENTER_Y, ENTER_MAP = 0x2C00, 0x2C20, 0x2C40  # world entrance n -> map, x, y
EXIT_X, EXIT_Y = 0x2C60, 0x2C70                        # "exit to the world" n -> world x, y
ENEMY_STATS = 0x30520       # bank 12: 128 monsters x 20 bytes
ENEMY_NAMES = 0x2D4E0       # bank 11: u16 pointers, bank-relative ($8000 = bank start)
DOMAINS = 0x2C000           # bank 11: 8 battle groups per domain (world 0-63, map m at 64+m)
FORMATIONS = 0x2C400        # bank 11: 128 battle groups x 16 bytes
SHOP_PTRS = 0x38302         # bank 14: u16 per shop (bank-relative), lists end in 0
PRICES = 0x37C00            # bank 13: u16 per item id

# Tile property byte 0: bit 0 no walking; bits 1-4 a special spot; bits 6-7 a teleport
SPECIAL = {0x02: "door", 0x04: "locked door", 0x06: "room exit", 0x08: "treasure box",
           0x0A: "battle floor", 0x0C: "damage floor", 0x0E: "CROWN check",
           0x10: "CUBE warp", 0x12: "four ORBS", 0x14: "ROD wall", 0x16: "LUTE seal",
           0x18: "earth ORB", 0x1A: "fire ORB", 0x1C: "water ORB", 0x1E: "air ORB"}
TELE_NORMAL, TELE_BACK, TELE_EXIT = 0x80, 0x40, 0xC0
SHOP_KINDS = ("weapon", "armor", "white magic", "black magic", "clinic", "inn", "item")
# Monster byte 16 (category) and bytes 18 / 19 (elements weak to / resisted)
CATEGORIES = ("unknown", "dragon", "giant", "undead", "were", "water", "mage", "regen")
ELEMENTS = ("status", "poison/stone", "time", "death", "fire", "ice", "bolt", "earth")

# The 2C02 colours as FCEUX (https://fceux.com/) draws them by default, $00-$3F
NES_RGB = [int(h, 16) for h in (
    "747474 24188C 0000A8 44009C 8C0074 A80010 A40000 7C0800 402C00 004400 005000 003C14 "
    "183C5C 000000 000000 000000 BCBCBC 0070EC 2038EC 8000F0 BC00BC E40058 D82800 C84C0C "
    "887000 009400 00A800 009038 008088 000000 000000 000000 FCFCFC 3CBCFC 5C94FC CC88FC "
    "F478FC FC74B4 FC7460 FC9838 F0BC3C 80D010 4CDC48 58F898 00E8D8 787878 000000 000000 "
    "FCFCFC A8E4FC C4D4FC D4C8FC FCC4FC FCC4D8 FCBCB0 FCD8A8 FCE4A0 E0FCA0 A8F0BC B0FCCC "
    "9CFCF0 C4C4C4 000000 000000").split()]


def nes_rgb(c: int) -> tuple[int, int, int]:
    v = NES_RGB[c & 0x3F]
    return v >> 16, v >> 8 & 0xFF, v & 0xFF


def _bits(b: int, names) -> list[str]:
    return [n for i, n in enumerate(names) if b >> i & 1]


class Rom:
    """The map, monster, battle and shop tables of a ROM image (bytes or a path).

    `map_names` maps map ids to place names (default: the names in the bundled RAM
    map, see `ram_map.location_names`); `object_names` maps "0x0a"-style object ids
    to names (default: `ram_map.object_names`)."""

    def __init__(self, rom: bytes | str | Path, map_names: dict | None = None,
                 object_names: dict | None = None):
        if not isinstance(rom, (bytes, bytearray)):
            rom = Path(rom).read_bytes()
        hdr = header_size(rom)
        self.raw = bytes(rom)
        self.prg = self.raw[hdr:hdr + 0x40000]
        if len(self.prg) < 0x40000:
            raise ValueError(f"expected a 256 KB PRG image, got {len(self.prg)} bytes")
        self.text = DialogueRom(self.raw)
        if map_names is None or object_names is None:
            from . import ram_map
            map_names = ram_map.location_names() if map_names is None else map_names
            object_names = ram_map.object_names() if object_names is None else object_names
        self.map_names = {int(k): v for k, v in map_names.items()}
        self.object_names = dict(object_names)

    def _u16(self, o: int) -> int:
        return self.prg[o] | self.prg[o + 1] << 8

    def _bank_ptr(self, table: int, i: int) -> int:
        """A u16 bank-relative pointer ($8000 = the bank's start) as a PRG offset."""
        return (table & ~0x3FFF) + self._u16(table + 2 * i) - 0x8000

    def name(self, m: int) -> str:
        return self.map_names.get(m, f"map {m}")

    # -- names and prices -------------------------------------------------------------
    def item(self, item_id: int) -> str:
        return self.text.item_name(item_id)

    def weapon(self, n: int) -> str:
        """Weapon slot id n's name (1-40; SRAM weapon slots hold n | $80 when equipped)."""
        return self.item(n + WEAPON_ITEM0) if 1 <= n <= GEAR_N else ""

    def armor(self, n: int) -> str:
        """Armor slot id n's name (1-40)."""
        return self.item(n + ARMOR_ITEM0) if 1 <= n <= GEAR_N else ""

    def items(self) -> dict[int, str]:
        """Bag item ids 1-27 (SRAM $6020 + id). The ORBs (18-21) have no menu name: the
        START menu draws them as pictures."""
        orbs = {0x12: "ORB (fire)", 0x13: "ORB (water)", 0x14: "ORB (air)", 0x15: "ORB (earth)"}
        return {i: orbs.get(i) or self.item(i) for i in range(1, 0x1C)}

    @property
    def spells(self):
        """The spell names and class permissions (a spells.SpellTable)."""
        from .spells import SpellTable
        if not hasattr(self, "_spells"):
            self._spells = SpellTable(self.raw, self.text)
        return self._spells

    @property
    def world(self):
        """The world map (a world.World)."""
        from .world import World
        if not hasattr(self, "_world"):
            self._world = World(self.raw)
        return self._world

    def price(self, item_id: int) -> int:
        return self._u16(PRICES + 2 * item_id)

    def box(self, index: int) -> str:
        """What treasure box `index` holds: an item, or gold for ids $6C up (the box gives
        that id's price)."""
        it = self.prg[TREASURE + index]
        return f"{self.price(it)} G" if it >= 0x6C else self.item(it)

    # -- standard maps ----------------------------------------------------------------
    @lru_cache(maxsize=None)
    def map_tiles(self, m: int) -> bytes:
        """The 64x64 tile ids of standard map `m` (row by row). The data is run-length
        coded: a byte under $80 is one tile, $80 + t is followed by a count (0 = 256)
        of tile t, and $FF ends the map."""
        o = (MAP_PTRS & ~0x3FFF) + self._u16(MAP_PTRS + 2 * m)
        out = bytearray()
        while len(out) < MAP_W * MAP_W:
            b = self.prg[o]
            o += 1
            if b == 0xFF:
                break
            if b < 0x80:
                out.append(b)
            else:
                n = self.prg[o]
                o += 1
                out += bytes([b & 0x7F]) * (n or 256)
        return bytes(out[:MAP_W * MAP_W].ljust(MAP_W * MAP_W, b"\0"))

    def tileset(self, m: int) -> int:
        return self.prg[TILESET_OF_MAP + m]

    def props(self, m: int, tile: int) -> tuple[int, int]:
        """Tile property bytes 0 and 1 of `tile` in map `m`'s tileset."""
        o = TILE_PROPS + 0x100 * self.tileset(m) + 2 * tile
        return self.prg[o], self.prg[o + 1]

    def teleport(self, i: int) -> tuple[int, int, int]:
        """Stairs / teleport `i` inside the maps: (map, x, y) it lands on."""
        return self.prg[TELE_MAP + i], self.prg[TELE_X + i] & 0x3F, self.prg[TELE_Y + i] & 0x3F

    def world_exit(self, i: int) -> tuple[int, int]:
        """Exit `i` to the world map: the world (x, y) it lands on."""
        return self.prg[EXIT_X + i], self.prg[EXIT_Y + i]

    def world_entrance(self, i: int) -> tuple[int, int, int]:
        """World entrance `i` (world tile props byte 1 low bits): (map, x, y) it lands on."""
        return self.prg[ENTER_MAP + i], self.prg[ENTER_X + i] & 0x3F, self.prg[ENTER_Y + i] & 0x3F

    def spots(self, m: int, battle_floor: bool = False) -> list[dict]:
        """Every tile of map `m` that does something: teleports (stairs, ladders, holes,
        warps), doors, treasure boxes, shops, the key-item and ORB spots. The battle and
        damage floors are many tiles each; `battle_floor` keeps the battle floor's."""
        out = []
        for i, t in enumerate(self.map_tiles(m)):
            b0, b1 = self.props(m, t)
            x, y = i % MAP_W, i // MAP_W
            tele, spec = b0 & 0xC0, b0 & 0x1E
            if tele == TELE_NORMAL:
                to, tx, ty = self.teleport(b1)
                out.append({"x": x, "y": y, "kind": "teleport", "to": to, "to_xy": (tx, ty)})
            elif tele == TELE_EXIT:
                out.append({"x": x, "y": y, "kind": "exit to the world", "to_xy": self.world_exit(b1)})
            elif tele == TELE_BACK and not self._edge(m, x, y):
                out.append({"x": x, "y": y, "kind": "way back"})
            if b0 & 0x1F == 0x03 and b1:
                out.append({"x": x, "y": y, "kind": "shop", "shop": b1 - 1})
            elif spec == 0x08:
                out.append({"x": x, "y": y, "kind": "treasure box", "box": b1, "holds": self.box(b1)})
            elif spec and spec != 0x0C and (spec != 0x0A or battle_floor):
                out.append({"x": x, "y": y, "kind": SPECIAL[spec]})
        return out

    def _edge(self, m: int, x: int, y: int) -> bool:
        """A town's or castle's outside: the way-back tiles around it (thousands of them)."""
        tiles = self.map_tiles(m)
        n = 0
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            t = tiles[((y + dy) % MAP_W) * MAP_W + (x + dx) % MAP_W]
            n += self.props(m, t)[0] & 0xC0 == TELE_BACK
        return n >= 2

    def boxes(self, m: int) -> list[dict]:
        return [s for s in self.spots(m) if s["kind"] == "treasure box"]

    def links(self) -> dict[int, list[int]]:
        """map -> the maps its stairs and teleports lead to (the way back and the exits to
        the world left out)."""
        out = {}
        for m in range(N_MAPS):
            to = sorted({s["to"] for s in self.spots(m) if s["kind"] == "teleport"})
            if to:
                out[m] = to
        return out

    def objects(self, m: int, names: dict | None = None) -> list[dict]:
        """The people and things standing on map `m`: object id, where, and whether it
        stays put (flag bit 6 of x) or lives inside a room (bit 7 of x)."""
        names = self.object_names if names is None else names
        out = []
        for i in range(16):
            o = OBJECTS + 0x30 * m + 3 * i
            oid, bx, by = self.prg[o], self.prg[o + 1], self.prg[o + 2]
            if not oid:
                continue
            out.append({"id": oid, "name": names.get(f"{oid:#04x}", ""), "x": bx & 0x3F,
                        "y": by & 0x3F, "still": bool(bx & 0x40), "in_room": bool(bx & 0x80)})
        return out

    def find_object(self, oid: int) -> list[tuple[int, int, int]]:
        """(map, x, y) of every placement of object `oid`."""
        return [(m, o["x"], o["y"]) for m in range(N_MAPS) for o in self.objects(m) if o["id"] == oid]

    def render(self, m: int, in_room: bool = False, scale: int = 1):
        """Map `m` as a PIL image, 16 px per tile (needs Pillow: pip install
        ff1-decoders[render]). `in_room` uses the palette drawn inside rooms."""
        from PIL import Image
        t = self.tileset(m)
        pal = self.prg[MAP_PALETTES + 0x30 * m + (0x20 if in_room else 0):][:16]
        cache = {}
        img = Image.new("RGB", (MAP_W * 16, MAP_W * 16))
        for i, tid in enumerate(self.map_tiles(m)):
            if tid not in cache:
                cache[tid] = self._tile_image(t, tid, pal)
            img.paste(cache[tid], ((i % MAP_W) * 16, (i // MAP_W) * 16))
        return img.resize((img.width * scale, img.height * scale), Image.NEAREST) if scale != 1 else img

    def _tile_image(self, t: int, tid: int, pal: bytes):
        from PIL import Image
        attr = self.prg[TILE_ATTR + 0x80 * t + tid] & 3
        im = Image.new("RGB", (16, 16))
        px = im.load()
        for q in range(4):
            pt = self.prg[TILE_TSA + 0x200 * t + 0x80 * q + tid] & 0x7F
            base = TILE_CHR + 0x800 * t + 16 * pt
            for r in range(8):
                lo, hi = self.prg[base + r], self.prg[base + 8 + r]
                for c in range(8):
                    v = (lo >> (7 - c) & 1) | (hi >> (7 - c) & 1) << 1
                    px[(q & 1) * 8 + c, (q >> 1) * 8 + r] = nes_rgb(pal[4 * attr + v] if v else pal[0])
        return im

    # -- monsters and battles ---------------------------------------------------------
    @lru_cache(maxsize=None)
    def enemy_name(self, e: int) -> str:
        o, s = self._bank_ptr(ENEMY_NAMES, e), ""
        while self.prg[o] and len(s) < 16:
            s += CHARS.get(self.prg[o], "?")
            o += 1
        return s

    def enemy(self, e: int) -> dict:
        """Monster `e` (0-127): name and the 20-byte stat record."""
        o = ENEMY_STATS + 20 * e
        b = self.prg[o:o + 20]
        return {"id": e, "name": self.enemy_name(e), "exp": self._u16(o), "gold": self._u16(o + 2),
                "hp": self._u16(o + 4), "morale": b[6], "ai": None if b[7] == 0xFF else b[7],
                "evade": b[8], "defense": b[9], "hits": b[10], "hit_rate": b[11], "attack": b[12],
                "crit": b[13], "ailment": b[15], "category": _bits(b[16], CATEGORIES),
                "magic_defense": b[17], "weak": _bits(b[18], ELEMENTS), "resists": _bits(b[19], ELEMENTS)}

    def enemies(self) -> list[dict]:
        return [self.enemy(e) for e in range(128)]

    def formation(self, f: int) -> dict:
        """Battle group `f` & $7F; bit 7 picks its second line-up (enemies 1-2 with their
        own counts, bytes 14-15). Counts are (fewest, most)."""
        o = FORMATIONS + 16 * (f & 0x7F)
        b = self.prg[o:o + 16]
        rng = lambda q: (q >> 4, q & 0x0F)
        if f & 0x80:
            pairs = [(b[2], b[14]), (b[3], b[15])]
        else:
            pairs = list(zip(b[2:6], b[6:10]))
        return {"id": f & 0x7F, "second": bool(f & 0x80), "kind": b[0] >> 4,
                "enemies": [(self.enemy_name(e), rng(q)) for e, q in pairs if q],
                "surprise": b[12], "no_run": bool(b[13] & 1)}

    def domain(self, m: int | None = None, world_xy: tuple[int, int] | None = None) -> list[dict]:
        """The 8 battle groups of a standard map (`m`) or of the world tile `world_xy`
        (32x32 tile domains); the first ones come up most often."""
        d = 64 + m if m is not None else (world_xy[1] // 32) * 8 + world_xy[0] // 32
        return [self.formation(f) for f in self.prg[DOMAINS + 8 * d:DOMAINS + 8 * d + 8]]

    # -- shops ------------------------------------------------------------------------
    def shop(self, n: int) -> dict:
        """Shop `n`: its kind (from n // 10) and goods with prices, or the clinic's or
        inn's one price."""
        o = self._bank_ptr(SHOP_PTRS, n)
        kind = SHOP_KINDS[min(n // 10, 6)]
        if kind in ("clinic", "inn"):
            return {"id": n, "kind": kind, "price": self._u16(o)}
        goods = []
        while self.prg[o] and len(goods) < 8:
            it = self.prg[o]
            goods.append((self.item(it), self.price(it)))
            o += 1
        return {"id": n, "kind": kind, "goods": goods}

    def shops(self) -> list[dict]:
        """Every shop that a map's shop sign leads to, with the map it is on."""
        where = {}
        for m in range(N_MAPS):
            for s in self.spots(m):
                if s["kind"] == "shop":
                    where.setdefault(s["shop"], (m, s["x"], s["y"]))
        out = []
        for n in sorted(where):
            s = self.shop(n)
            m, x, y = where[n]
            s.update(map=m, place=self.name(m), at=(x, y))
            out.append(s)
        return out

    # -- all of it --------------------------------------------------------------------
    def markdown(self, object_names: dict | None = None) -> str:
        """Shops, every map's spots, people and battles, and the monsters, as Markdown."""
        L = ["# FF1 ROM tables", "", "Generated from your ROM by `python -m ff1_decoders ROM dump`.", ""]
        L += ["## Shops", "", "| place | shop | kind | goods / price |", "|---|---|---|---|"]
        for s in self.shops():
            what = (f"{s['price']} G" if "price" in s else
                    ", ".join(f"{n} {p} G" for n, p in s["goods"]))
            L.append(f"| {s['place']} | {s['id']} | {s['kind']} | {what} |")
        L += ["", "## Maps", ""]
        for m in range(N_MAPS):
            spots = [s for s in self.spots(m) if s["kind"] not in ("shop", "door", "room exit")]
            objs = self.objects(m, object_names)
            groups = {", ".join(f"{n} {a}-{b}" for n, (a, b) in f["enemies"])
                      for f in self.domain(m)} if any(s["kind"] == "battle floor"
                                                      for s in self.spots(m, True)) else set()
            L += [f"### {m} {self.name(m)}", ""]
            for s in spots:
                if s["kind"] == "teleport":
                    L.append(f"- ({s['x']},{s['y']}) to {self.name(s['to'])} at {s['to_xy']}")
                elif s["kind"] == "treasure box":
                    L.append(f"- ({s['x']},{s['y']}) box {s['box']}: {s['holds']}")
                elif s["kind"] == "exit to the world":
                    L.append(f"- ({s['x']},{s['y']}) out to the world at {s['to_xy']}")
                elif s["kind"] != "way back":
                    L.append(f"- ({s['x']},{s['y']}) {s['kind']}")
            for o in objs:
                L.append(f"- ({o['x']},{o['y']}) object {o['id']:#04x} {o['name']}".rstrip())
            if groups:
                L.append("- battles: " + "; ".join(sorted(groups)))
            L.append("")
        L += ["## Monsters", "", "| id | name | HP | EXP | G | weak | resists |", "|---|---|---|---|---|---|---|"]
        for e in self.enemies():
            L.append(f"| {e['id']} | {e['name']} | {e['hp']} | {e['exp']} | {e['gold']} | "
                     f"{' '.join(e['weak'])} | {' '.join(e['resists'])} |")
        return "\n".join(L) + "\n"
