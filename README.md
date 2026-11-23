# ff1-decoders

Python decoders for **Final Fantasy (NES, USA)**: read the game's tables out of your own
ROM, decode save files, and turn RAM and screen memory into something readable.

**No game data ships with this package.** There is no ROM, no extracted table, no
rendered map in this repository. Every decoder reads the ROM image you point it at,
at run time.

## What it decodes

From the ROM (`ff1_decoders.Rom`):

- **Maps**: the 61 town / castle / dungeon maps (64x64, run-length coded), their
  tilesets and tile properties, and every spot that does something: stairs and
  teleports (with where they land), exits to the world, doors, locked doors, shops,
  treasure boxes (with contents), the key-item and ORB spots. Maps render to PNG.
- **People**: the objects (NPCs) on each map, whether they stand still or live inside
  a room, and their names.
- **Monsters**: all 128, with HP, EXP, gold, stats, categories, weaknesses and
  resistances.
- **Battles**: the 128 battle groups and the 8 groups each map or world region can
  throw at the party.
- **Shops**: goods and prices of every shop, found from the shop doors on the maps;
  inn and clinic prices.
- **Text**: field dialogue (with its DTE compression and item-name inserts), item,
  weapon, armor and spell names as the menus draw them (`Wooden[staff]`), the font,
  gear elements and palettes, the START menu's orb pictures.
- **Spells**: the 64 spells by level, and the class permission table (who may learn
  what).
- **World map**: the 256x256 world, its terrain, and which tiles lead into which maps.

Not from the ROM:

- **RAM map** (`ff1_decoders.ram_map`, `data/ram_map.toml`): WRAM and SRAM addresses
  (party records, gear, magic, inventory, map objects, screen-mode tests, cursors),
  enums (classes, status, items, vehicles, shop types, map and object names) and the
  story flags.
- **Saves** (`ff1_decoders.decode_sram`): gold, story flags, the bag and the party of a
  `.srm` / `.sav` battery file.
- **Menu screens** (`ff1_decoders.screen`): the text of each box on the PPU nametable
  (shops, the START menu, battle lists) and the entry a hand cursor points at.

## Install

```sh
pip install .                 # the decoders (standard library only)
pip install ".[render]"       # plus Pillow, for rendering maps to PNG
```

Python 3.11 or newer.

## Your ROM

The decoders expect the USA release of Final Fantasy for the NES: a 256 KB PRG image,
with or without the 16-byte iNES header (CRC32 of the image without the header:
`CEBD2A31`). Other revisions or hacks may decode wrong; `info` checks the CRC.

```python
from ff1_decoders import Rom

rom = Rom("path/to/ff1.nes")
rom.shop(0)                    # {'id': 0, 'kind': 'weapon', 'goods': [(name, price), ...]}
rom.enemy(0)["name"]           # 'IMP'
rom.spots(8)                   # stairs, doors, boxes ... in Coneria Castle 1F
rom.spells.can_learn("Knight")
rom.world.tile(152, 159)       # an entrance: {'leads_to': 8, ...}
rom.text.decode(1)             # a line of dialogue
rom.render(0).save("coneria.png")    # needs Pillow
```

## Command line

```sh
python -m ff1_decoders ff1.nes info
python -m ff1_decoders ff1.nes shops
python -m ff1_decoders ff1.nes monsters          # list; or: monsters 0
python -m ff1_decoders ff1.nes map 20            # spots, people, battles (JSON)
python -m ff1_decoders ff1.nes render 8 castle.png --scale 2
python -m ff1_decoders ff1.nes spells            # by level
python -m ff1_decoders ff1.nes spells "Red Mage"
python -m ff1_decoders ff1.nes items
python -m ff1_decoders ff1.nes dialogue 1
python -m ff1_decoders ff1.nes world 188 203
python -m ff1_decoders ff1.nes save ff1.srm
python -m ff1_decoders ff1.nes dump > tables.md  # everything, as Markdown
```

## Tests

```sh
pip install ".[test]"
pytest                                   # ROM tests skip
FF1_ROM=path/to/ff1.nes pytest           # all tests
```

The tests that need the game read its path from `FF1_ROM` and are skipped when it is
unset.

## Docs

- [docs/rom-tables.md](docs/rom-tables.md): every ROM offset and layout, the spell
  permission table, story flags.
- [docs/ram-map.md](docs/ram-map.md): the RAM map, screen-mode tests, and how to
  confirm a field yourself.
- [docs/objects-and-flags.md](docs/objects-and-flags.md): map objects, talk handlers
  and the game flags at $6200.

## Credits and prior art

- The community FF1 disassembly
  ([FF1Disassembly](https://github.com/Entroper/FF1Disassembly)), whose labels and notes
  (`variables.inc`, `Constants.inc`, `some formats.txt`) name most of what is decoded
  here.
- [Data Crystal](https://datacrystal.tcrf.net/wiki/Final_Fantasy) (the TCRF wiki's ROM
  and RAM maps for Final Fantasy).
- The community map lists of the NES version, for the place names.

Every offset here was checked against the USA ROM; where these notes and the prior art
disagree, the notes say what was observed.

## License

MIT; see [LICENSE](LICENSE). Final Fantasy is a trademark of Square Enix; this project
is not affiliated with or endorsed by it.
