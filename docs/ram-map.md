# The RAM map

`ff1_decoders/data/ram_map.toml` lists the WRAM and SRAM addresses of Final Fantasy
(NES, USA), with enums and story flags. Load it with `ff1_decoders.ram_map`:

```python
from ff1_decoders import ram_map

ram_map.field("gold")            # {'addr': 28, 'size': 3, 'region': 'sram', ...}
ram_map.cpu_address(ram_map.field("hp"), slot=1)   # 0x614A
ram_map.enum("job")              # {0: 'Fighter', 1: 'Thief', ...}
ram_map.read_flags(sram_bytes)   # {'garland_defeated': True, ...}
```

## Regions and keys

- `wram` (the default): NES internal RAM, CPU $0000-$07FF.
- `sram`: cartridge RAM, CPU $6000-$7FFF, written as an **offset from $6000**. So the
  party block at $6100 is `addr = 0x100, region = "sram"`. An emulator's `.srm` / `.sav`
  file is exactly this 8 KB.
- `size` in bytes (default 1); multi-byte numbers are little-endian.
- `add`: a constant to add (scroll + 7 = the player's tile; level + 1).
- `equals`: the value a screen test compares against (a byte, or a hex string for a
  run of bytes such as a palette).
- `verified = true`: confirmed by watching the byte change in play and re-checked in
  other situations (other maps, battles, vehicles). Fields without it are leads.

`[party]` gives the character records' base ($6100) and stride ($40); `[party_fields]`
and `[party_gear]` offsets are relative to a record. The magic block is $200 further
on ($6300 + $40 * slot).

## Screen modes

The most reliable signal of what screen is up turned out to be the sprite table (OAM
at $0200-$02FF): each screen parks its unused sprites at its own Y or attribute value.

| field | test | screen |
|---|---|---|
| `in_battle` | $02B0 (sprite 44's Y) == $F0 | battle (plus ~10 black frames either side) |
| `dialog_open` | $02FE (sprite 63's attribute) == $D8 | a dialogue box |
| `menu_open` | palette buffer $03C0-$03C7 == `0f3001220f000130` | the START menu |
| `shop_open` | palette buffer $03C4-$03CF == `0f0004300f000a300f000130` | any shop, inn or clinic |
| `name_screen` | palette buffer $03C0-$03C7 == `0f001630ffff0101` | party creation / name entry |

Stack-based rules (return addresses at $01FA-$01FC) looked promising but broke on
nested dungeon floors: the return address moves down 7 bytes per stair level.

## Text on screen

- **Dialogue** is drawn straight from ROM; RAM keeps only the text pointer ($3E/$3F),
  which points at the shown string's $00 terminator once the box is up.
  `DialogueRom.id_at(ptr)` turns it into a dialogue id and `decode(id)` into text. No
  RAM byte holds the dialogue id itself.
- **Menus, shops and battle lists** are drawn as background tiles whose codes are the
  font's, so nametable 0 spells out each box. `ff1_decoders.screen` splits it into
  boxes (borders are tiles $F7-$FE) and reads the entry a hand cursor points at. Read
  it only while a screen mode above says such a screen is up: on the walking screen
  nametable 0 holds stale boxes.
- **Equipment icons.** Item names end in a picture of the item's kind ($D4-$DF),
  written `Name[kind]`: `Wooden[staff]` and `Wooden[nunchucks]` are different weapons.

## Things worth knowing

- **Standard maps wrap at 64.** The player tile inside a town or dungeon is
  `(scroll + 7) & 0x3F`; without the mask a tile with x or y below 7 reads 64 too high.
- **Menus write SRAM when they close.** Equipping or using an item shows on screen at
  once, but the bytes change only when B goes back to the main list.
- **The pad byte paces input.** `joy` ($20) is the pad as the game last read it; the
  game reads it only while it takes input, so after a release it reads 0 again exactly
  when the next press will count.
- **The cursor sprite is not a readiness signal.** The hand stays drawn for ~55 frames
  after A while the next screen draws, and a dialogue box ignores A for its first 50.
- **People inside rooms.** `inroom` ($0D) is $81 inside a room; a map object is drawn
  only when bit 7 of its flags byte matches.
- **The party is re-sorted after battles** (OK, Poison, Stone, Dead), so a slot is not
  a character.

## Confirming a field yourself

Any emulator with a RAM viewer or snapshot diff works (FCEUX's RAM Search and RAM
Watch, Mesen's memory tools, or a libretro core driven from a script):

1. Snapshot WRAM and SRAM, do one thing in the game, snapshot again.
2. Diff: keep the bytes that changed the way the action should change them (walk one
   tile right: a byte +1; buy something: gold bytes down by the price).
3. Repeat in a different place (another town, a dungeon floor, a boss battle, on the
   ship). A field that only looks right in one place isn't confirmed.

| field | how to confirm |
|---|---|
| `ow_scroll_x/y` | walk one tile each way on the world map; exactly one byte moves by +-1 |
| `sm_scroll_x/y`, `mapflags` | enter a town: `mapflags` bit 0 flips and the town scroll bytes start moving |
| `map_id` | enter two different towns: the byte differs and stays constant inside each |
| `gold` | buy something and diff SRAM for a decrease |
| party `hp` | take damage in battle: record bytes +$0A drop |
| party `name` | name a character `ABCD`: $6102-$6105 read `8A 8B 8C 8D` |
| story flags | snapshot before and after a story event; keep the new bits that stay set |
