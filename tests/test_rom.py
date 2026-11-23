"""ROM tables: people on the maps, treasure, stairs and special spots, monsters and
battle groups, shops, map rendering and the Markdown dump."""
from __future__ import annotations

import re

import pytest


def test_people_stand_where_the_game_puts_them(rom):
    assert rom.find_object(0x0A) == [(20, 8, 1)]                # Matoya, in her cave
    assert [m for m, _, _ in rom.find_object(0x01)] == [24]     # the King, Coneria Castle 2F
    assert [m for m, _, _ in rom.find_object(0x02)] == [12]     # Garland, Temple of Fiends
    king = rom.objects(24)[0]
    assert king["name"] == "King of Coneria" and king["still"] and king["in_room"]
    assert rom.objects(24, names={})[0]["name"] == ""


def test_treasure_boxes(rom):
    boxes = {(b["x"], b["y"]): b["holds"] for b in rom.boxes(54)}
    assert set(boxes) == {(17, 15), (23, 15)}
    assert all(re.fullmatch(r"\d+ G", v) for v in boxes.values())     # gold boxes
    assert {"x": 1, "y": 4, "kind": "treasure box", "box": 43, "holds": "HEAL"} in rom.boxes(20)


def test_stairs_and_special_spots(rom):
    links = rom.links()
    assert links[44] == [43, 45]                         # Sea Shrine 1F: B1 down, 2F up
    assert 52 in links[12]                               # the four ORBS warp
    kinds = lambda m: {s["kind"] for s in rom.spots(m)}
    assert "four ORBS" in kinds(12) and "ROD wall" in kinds(30) and "LUTE seal" in kinds(54)
    assert "CUBE warp" in kinds(41) and "earth ORB" in kinds(32) and "air ORB" in kinds(51)
    exits = [s for s in rom.spots(8) if s["kind"] == "exit to the world"]
    assert exits and exits[0]["to_xy"] == (153, 159)    # out of Coneria Castle
    assert "battle floor" not in kinds(32)
    assert "battle floor" in {s["kind"] for s in rom.spots(32, battle_floor=True)}


def test_map_tiles_decode_to_64_by_64(rom):
    for m in (0, 8, 20, 60):
        assert len(rom.map_tiles(m)) == 64 * 64
    assert 0 <= rom.tileset(0) <= 7


def test_monsters_and_battle_groups(rom):
    imp = rom.enemy(0)
    assert (imp["name"], imp["exp"], imp["gold"], imp["hp"]) == ("IMP", 6, 6, 8)
    seen = lambda m: {n for f in rom.domain(m) for n, _ in f["enemies"]}
    assert {"WORM", "Frost D"} <= seen(52) and {"BADMAN", "Gas D"} <= seen(54)
    assert seen(0) and len(rom.enemies()) == 128
    assert "IMP" in {n for f in rom.domain(world_xy=(155, 165)) for n, _ in f["enemies"]}


def test_shops_found_from_the_signs_on_the_maps(rom):
    shops = {s["id"]: s for s in rom.shops()}
    assert shops[0]["place"] == "Coneria" and shops[0]["kind"] == "weapon"
    assert ("Rapier", 10) in shops[0]["goods"]
    assert shops[50]["kind"] == "inn" and shops[50]["price"] == 30
    assert ("LIFE", 8000) in shops[23]["goods"] and shops[23]["place"] == "Melmond"
    assert all(s["place"] for s in shops.values())


def test_names(rom):
    assert (rom.weapon(1), rom.armor(1), rom.spells.name(1)) == ("Wooden[nunchucks]", "Cloth", "CURE")
    assert rom.weapon(3) == "Wooden[staff]" and rom.weapon(4) == "Rapier"
    assert rom.item(10) == "ROD" and rom.items()[0x15] == "ORB (earth)"
    assert all(rom.weapon(n) for n in range(1, 41)) and all(rom.armor(n) for n in range(1, 41))
    assert rom.name(20) == "Matoya's Cave" and rom.name(99) == "map 99"


def test_render_and_dump(rom):
    pytest.importorskip("PIL")
    img = rom.render(8)
    assert img.size == (1024, 1024) and len(img.crop((0, 0, 512, 512)).getcolors(1 << 16)) > 3
    assert rom.render(0, scale=2).size == (2048, 2048)
    md = rom.markdown()
    assert "### 20 Matoya's Cave" in md and "| Coneria | 0 | weapon |" in md


def test_a_short_image_is_refused():
    from ff1_decoders import Rom
    with pytest.raises(ValueError):
        Rom(b"NES\x1a" + bytes(1000))
