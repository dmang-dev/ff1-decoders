# Map objects ($6F00) and game flags ($6200)

Source: the community FF1 disassembly
(<https://github.com/Entroper/FF1Disassembly>: `variables.inc`, `Constants.inc`,
`bank_0E.asm`, `some formats.txt`). Points marked **ROM** were checked on the USA ROM
in an emulator.

Addresses: the disassembly's `unsram` is CPU $6000, the RAM map's `region = "sram"`
offset 0. So $6200 is sram 0x200 and $6F00 is sram 0xF00.

## $6F00 `mapobj`: the people on the current map

16 slots of 16 bytes ($100 bytes). Loaded when a town, castle or dungeon map loads,
and stale on the world map (it keeps the last map's table).

| off | name | meaning |
|---|---|---|
| +0 | `mapobj_id` | object ID (0 = empty slot); the index into $6200 and the talk tables |
| +1 | `mapobj_flgs` | $80 = in a room (drawn only when `inroom` $0D bit 7 matches), $40 = never moves |
| +2/+3 | `physX/Y` | the tile it stands on |
| +4/+5 | `gfxX/Y` | where it is drawn (mid-step it is between tiles) |
| +6/+7 | `ctrX/Y` | movement counters |
| +8/+9 | `spdX/Y` | step speed / direction |
| +A | `rawid` | the ID as loaded from the map's object list |
| +B | `movectr` | countdown to its next random step |
| +C | `face` | the way it faces |
| +D | `pl` | bit 7 = talking to the player (turns to face them); other bits = being pushed |
| +E/+F | `tsaptr` | sprite graphics pointer |

The ROM's per-map object lists (16 x 3 bytes per map at PRG $3400: id, x | flags,
y | flags) are what these slots are loaded from; `Rom.objects(m)` reads them.

## Object IDs ($00-$CF)

`lut_MapObjTalkJumpTbl` gives each ID a talk handler. The named ones (the RAM map's
`enums.object`):

| ID | object | talk handler does |
|---|---|---|
| $01 | King of Coneria | builds the bridge (`bridge_vis` +1) once the rescued princess is visible |
| $02 | Garland (Temple of Fiends) | hides himself |
| $03 | kidnapped princess (Temple) | hides herself, shows $12 |
| $04 | Bikke the pirate | sets his event flag, `ship_vis` +1, shows $3F-$41 |
| $05 | Elf doctor | takes the HERB, sets $06's event (the prince wakes) |
| $06 | Elf prince | once awake: gives the MYSTIC KEY |
| $07 | Astos | takes the CROWN, gives the CRYSTAL, hides |
| $08 | Nerrick | takes the TNT, opens the canal, hides |
| $09 | Smith | takes ADAMANT, gives XCALBER, sets his event |
| $0A | Matoya | takes the CRYSTAL, gives the HERB; sets no flag |
| $0B | Dr. Unne | takes the SLAB, teaches Lefeinish (his event) |
| $0C | Vampire (Earth Cave) | hides |
| $0D | Sarda | gives the ROD once the vampire is gone |
| $0E | Bahamut | takes the TAIL, class change (his event) |
| $10 | submarine engineer (Onrac) | with the OXYALE: steps aside (hides) |
| $11 | robot (Sky Castle) | gives the CUBE |
| $12 | rescued princess (Coneria Castle) | gives the LUTE |
| $13 | fairy (from the bottle) | gives the OXYALE |
| $14 | Titan | takes the RUBY, hides |
| $15 | canoe sage | gives the canoe (`has_canoe`) |
| $16 / $17 | ROD plate / LUTE plate | removed by those items |
| $18-$19 | "Replace" objects | hide one object, show another |
| $1A-$1E | fight objects | |
| $20-$39 | Coneria townspeople | lines change with visibility, items, the bridge |
| $3A-$3E | the five Sky Warriors | change with the four ORBs |
| $3F-$41 | Pravoka people terrorised by the pirates | appear after Bikke is beaten |
| $CA | the black ORB (Temple of Fiends) | "nothing happens" until the four ORBs are lit |

Generic handlers: `Talk_norm` (always line [1]); `Talk_ifvis`, `Talk_ifitem`,
`Talk_ifevent`, `Talk_ifbridge`, `Talk_ifcanoe`, `Talk_ifcanal`, `Talk_ifairship`,
`Talk_ifkeytnt`, `Talk_ifearthvamp`, `Talk_ifearthfire` (line [1] or [2] depending on
that condition); `Talk_4Orb` (lit ORBs); `Talk_Invis`; `Talk_GoBridge`; `Talk_CoOGuy`.

## Talk data: four dialogue IDs per object

`lut_MapObjTalkData`, bank $0E $95D5 (file offset 0x395E5 with the iNES header), 4
bytes x $D0 objects. Byte 0 is a parameter (an item or object ID the handler checks);
bytes 1-3 are dialogue IDs [1]-[3], which `DialogueRom.decode` turns into text. For
example the King's entry is `00 01 02 03`: his first line is dialogue 1.

A handler that sets no flag leaves no trace in RAM: a full SRAM diff around a talk
with Matoya changed only a walking object's step counter. Her handler picks its line
from the HERB, the CRYSTAL and the Elf prince's event flag alone.

## $6200 `game_flags`: one byte per object ID (and per treasure box)

| bit | name | meaning |
|---|---|---|
| 0 ($01) | `GMFLG_OBJVISIBLE` | the object is on its map (`IsObjectVisible`, `Show/HideMapObject`) |
| 1 ($02) | `GMFLG_EVENT` | that object's event done (`Check/SetGameEventFlag`; clearing is never used) |
| 2 ($04) | `GMFLG_TCOPEN` | treasure box opened, indexed by box number, not object ID |

Events (bit 1) are set only for $04 Bikke, $06 the Elf prince (by the doctor), $09
Smith, $0B Unne and $0E Bahamut. Every other story step is an object shown or hidden
(bit 0) or an item gained or lost. The RAM map's `[flags.*]` tables name them; a new
game has none of them set.

## Other `unsram` fields next to these (variables.inc)

| sram | name | note |
|---|---|---|
| 0x00-0x02 | `ship_vis`, `ship_x/y` | ship obtained and where it is |
| 0x04-0x06 | `airship_vis`, x/y | |
| 0x08-0x0A | `bridge_vis`, x/y | the `bridge_built` flag |
| 0x0C-0x0E | `canal_vis`, x/y | 1 at a new game (the canal is blocked until Nerrick) |
| 0x12 | `has_canoe` | not the same as the CANOE item byte (0x31) |
| 0x14 | `unsram_vehicle` | the saved copy of the vehicle |
| 0x16 | `bridgescene` | 00 not yet, 01 when the move ends, $80 done |
| 0x1C | `gold` | 3 bytes |
| 0x20+ | `items` | one count per item id (`enums.item`) |

## Tile property bytes (from `some formats.txt`)

World map byte 0 `SSdf ascw`: w no walk, c no canoe, s no ship, a no airship, f forest,
d dock ship; SS 01 need chime, 10 caravan, 11 raise airship. Byte 1: $80 teleport (an
entrance; low bits say which), $40 battles ($41/$43 river, $42 ocean).

Town/dungeon byte 0 `TTBs sssm`: m no move; TT 11 exit, 10 normal teleport (stairs),
01 warp. ssss (`b0 & $1E`, shifted right one): 1 door/shop, 2 locked door, 3 close room,
4 treasure box, 5 battle, 6 damage floor, 7 need CROWN, 8 need CUBE, 9 need 4 ORBs,
A use ROD, B use LUTE, C-F the earth, fire, water and air ORB altars. `Rom.spots(m)`
reports these; byte 1 is the teleport, box or shop number.
