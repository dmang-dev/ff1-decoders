# ROM tables

What the decoders read and where. Offsets are into the 256 KB PRG (the 16-byte iNES
header, when there is one, is skipped); "bank n" is PRG offset n * $4000, and
"bank-relative" pointers treat $8000 as the bank's start. No table contents ship with
this package: generate them from your own ROM.

```sh
python -m ff1_decoders ff1.nes dump > tables.md      # shops, maps, monsters, spells
python -m ff1_decoders ff1.nes items                 # item, weapon and armor names by id
python -m ff1_decoders ff1.nes spells                # all 64 spells by level
```

## Offsets

| what | PRG offset | layout | decoder |
|---|---|---|---|
| world tile properties | $0000 | 2 bytes x 128 tiles | `world.world_props` |
| tile palettes (attribute) | $0400 | 128 bytes per tileset | `Rom.render` |
| map tile properties | $0800 | 2 bytes x 128 tiles, $100 per tileset | `Rom.props` |
| tile pictures (TSA) | $1000 | 4 x 128 bytes per tileset (one 8x8 per corner) | `Rom.render` |
| map palettes | $2000 | 48 bytes per map: outdoor, sprite, in-room | `Rom.render` |
| world entrances | $2C00 / $2C20 / $2C40 | x, y, map; 32 entries | `Rom.world_entrance`, `World.entrances` |
| exits to the world | $2C60 / $2C70 | world x, y | `Rom.world_exit` |
| tileset of each map | $2CC0 | 1 byte per map (0-7) | `Rom.tileset` |
| stairs / teleports | $2D00 / $2D40 / $2D80 | x, y, map | `Rom.teleport` |
| treasure boxes | $3100 | 256 item ids (gold for $6C and up: the box gives that id's price) | `Rom.box` |
| map objects | $3400 | 16 x 3 bytes per map: id, x \| flags, y \| flags | `Rom.objects` |
| world map rows | $4000 (bank 1) | 256 u16 row pointers, run-length coded rows | `world.world_tiles` |
| standard maps | $10000 (bank 4) | u16 bank-relative pointer per map, run-length coded | `Rom.map_tiles` |
| tile CHR | $C000 (bank 3) | 2 KB per tileset | `Rom.render` |
| dialogue | bank $0A $8000 | 256 u16 CPU pointers, $00-terminated strings | `DialogueRom.decode` |
| item names | bank $0A $B700 / $B800 | u16 CPU pointers, ids 0-127 / 128-255 | `DialogueRom.item_name` |
| DTE pairs | bank 15 $F0A0 / $F050 | first / second character of codes $1A-$79 | `DialogueRom` |
| menu font | $24000 (bank 9) | 16-byte 8x8 tiles by text code | `DialogueRom.font_tile` |
| battle domains | $2C000 (bank 11) | 8 battle groups per domain: world 0-63, map m at 64 + m | `Rom.domain` |
| battle groups | $2C400 | 128 x 16 bytes | `Rom.formation` |
| monster names | $2D4E0 | u16 bank-relative pointers | `Rom.enemy_name` |
| battle status labels | $2CF00 | in bit order | (see `enums.status_bits`) |
| weapon stats | $30000 | 40 x 8 bytes (byte 4 element, byte 7 palette) | `DialogueRom.gear_elements` |
| armor stats | $30140 | 40 x 4 bytes (byte 2 resisted elements) | `DialogueRom.gear_elements` |
| monster stats | $30520 (bank 12) | 128 x 20 bytes | `Rom.enemy` |
| orb pictures | $37640 | 2x2 tiles per orb, lit and unlit | `DialogueRom.orb_tiles` |
| prices | $37C00 (bank 13) | u16 per item id | `Rom.price` |
| shops | $38302 (bank 14) | u16 bank-relative pointer per shop; lists end in 0 | `Rom.shop` |
| class spell permissions | $3AD18 | 12 classes x 8 bytes (see below) | `spells.SpellTable` |

## Ids that point into the item name list

| id in RAM | item name entry | example |
|---|---|---|
| bag item n ($6020 + n) | n | 25 = HEAL |
| weapon slot id n | n + $1B | 3 = Wooden[staff] |
| armor slot id n | n + $43 | 1 = Cloth |
| spell n (1-64) | n + $AF | 1 = CURE |

The bag's ids 18-21 are the four ORBs, which have no menu name: the START menu draws
them as pictures.

## Monsters

Each 20-byte record: EXP (u16), gold (u16), HP (u16), morale, AI script ($FF none),
evade, defense, hits, hit rate, attack, critical rate, (byte 14, not decoded), ailment inflicted,
category bits (unknown, dragon, giant, undead, were, water, mage, regen), magic
defense, elements weak to, elements resisted (status, poison/stone, time, death,
fire, ice, bolt, earth).

A battle group (16 bytes): byte 0 high nibble the kind, bytes 2-5 the monster ids,
bytes 6-9 their counts (high nibble fewest, low nibble most), byte 12 surprise rate,
byte 13 bit 0 no running. A domain entry with bit 7 set picks the group's second
line-up: monsters 1-2 with counts from bytes 14-15.

## Shops

Shop n's kind is n // 10: weapon (0-9), armor, white magic, black magic, clinic, inn,
item (60+). A shop's door on a map is a tile with property byte 0 & $1F = $03 and
byte 1 = shop number + 1; `Rom.shops()` finds every shop that way and names the place
it is in. Clinics and inns have one price instead of a list.

## Class spell permissions

PRG $3AD18 holds 12 rows of 8 bytes, one row per class in this order: Fighter, Thief,
Black Belt, Red Mage, White Mage, Black Mage, Knight, Ninja, Master, Red Wizard, White
Wizard, Black Wizard (the class ids at $6100 + $40 * slot). Each byte is one spell level
(L1-L8). The bits are **inverted**: a set bit means the class can **not** learn that
spell. The most significant bit is the level's first slot: slot s is bit 7 - (s - 1).
Slots 1-4 are white magic and 5-8 black, in the magic shops' order.

Examples:

- Fighter, Thief, Black Belt and Master learn nothing (every bit set).
- Red Mage reaches L5, where only CUR3, FIR3 and SLO2 are open to it.
- Knight learns L1 CURE, FOG, RUSE; L2 LAMP, MUTE, ALIT, INVS; L3 CUR2, AFIR; nothing
  higher.
- White Wizard's L8 is LIF2, FADE, WALL, XFER.

A character holds at most **three spells per level**: the shop answers "This level spell
is full" to a fourth. The character's magic block ($6300 + $40 * slot) has 4 bytes per
level; each nonzero byte is a learned spell's slot (1-8), so spell n = (level - 1) * 8 +
value. The magic shop is the only code that stores a single spell byte (LDX $030A, LDA
$030B, STA $6300,X); the other stores to $6300-$631F clear or copy the whole block.

```python
from ff1_decoders import Rom
rom = Rom("ff1.nes")
rom.spells.learnable_by_level("Knight")   # {1: ['CURE', 'FOG', 'RUSE'], 2: [...], 3: [...]}
rom.spells.who_can_learn(33)              # spell 33 = L5 slot 1
```

## The world map

256 x 256 tiles. Property byte 0: bit 0 no walking, bit 1 no canoe, bit 2 no ship,
bit 3 no airship landing, bit 5 dock; grass reads $06 and forest $0E, so forest is not
one bit. Byte 1 bit 7 marks an entrance; its low 5 bits index the entrance table at
$2C40, which gives the map it leads into. Two entries (both ends of the tunnel through
Titan's Pass) lead to the same map. `World.tile(x, y)` returns the tile, its property
bytes, the terrain and, for an entrance, the map id.

Battle domains on the world map are 32 x 32-tile squares: domain (y // 32) * 8 + x // 32.

## Story flags

Read with `ram_map.read_flags(sram)`. All are in SRAM; `bit` set = true unless the
flag says `clear`, in which case the game clears the bit to mark the event.

| flag | address | test |
|---|---|---|
| garland_defeated | $6202 | bit 0 clear |
| princess_rescued | $6212 | bit 0 set |
| bridge_built | $6008 | == 1 |
| ship_obtained | $6000 | bit 0 set |
| canal_opened | $600C | bit 0 clear |
| canoe_obtained | $6012 | bit 0 set |
| airship_obtained | $6004 | bit 0 set |
| orb_fire / water / air / earth | $6032-$6035 | bit 0 set |
| pirates_beaten | $6204 | bit 1 set |
| sleeper_woken | $6206 | bit 1 set |
| thief_king_beaten | $6207 | bit 0 clear |
| canal_digger_gone | $6208 | bit 0 clear |
| smith_forged | $6209 | bit 1 set |
| scholar_taught | $620B | bit 1 set |
| cave_boss_beaten | $620C | bit 0 clear |
| class_change | $620E | bit 1 set |
| engineer_moved | $6210 | bit 0 clear |
| fairy_freed | $6213 | bit 0 set |
| tunnel_cleared | $6214 | bit 0 clear |
| rod_plate_used | $6216 | bit 0 clear |
| lute_plate_used | $6217 | bit 0 clear |
| earth / fire / water / air fiend beaten | $621B-$621E | bit 0 clear |

The flags outside the object table ($6000-$6035) each have exactly one write in the
ROM (two for the airship: the raise and its scene), which is how the ones not yet seen
change in play were tied to their events.

## Map names

The ROM has no place-name text. The RAM map's `enums.location` names the 61 standard
maps after the community map lists of the NES version; the ROM's tileset-per-map
table fixes which block each id belongs to (towns 0-7, castles 8-11, and so on), and
floor numbers follow the stair warp table. `Rom` uses these names by default; pass
`map_names=` to use your own.
