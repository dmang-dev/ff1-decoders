"""The world map: tiles, terrain and the entrances into maps."""
from __future__ import annotations

from ff1_decoders.world import World, air_lands, terrain, world_tiles


def test_terrain_from_the_property_bits():
    assert terrain(0x06, 0x00) == "land" and terrain(0x0E, 0x00) == "land"   # grass, forest
    assert terrain(0x0E, 0x8F) == "entrance"
    assert terrain(0x0D, 0x00) == "river" and terrain(0x0B, 0x00) == "sea"
    assert terrain(0x0F, 0x00) == "wall" and terrain(0x20, 0x00) == "dock"
    assert air_lands(0x06) and not air_lands(0x0E) and not air_lands(0x0B)


def test_a_non_ff1_image_does_not_decode():
    assert world_tiles(bytes(0x8000)) is None


def test_world_entrances_follow_the_rom_table(rom):
    w = rom.world
    assert len(w.tiles) == 256 * 256
    e = w.entrances()
    assert e[14] == [(188, 203), (189, 203)] and e[21] == [(30, 190)] and e[20] == [(168, 117)]
    assert e[60] == [(42, 174), (30, 175)]                  # both ends of one tunnel
    assert w.tile(215, 220)["terrain"] == "river (canoe)"
    assert w.tile(188, 203)["leads_to"] == 14
    assert w.tile(152, 159)["leads_to"] == 8                # Coneria Castle
    assert set(w.tile_kinds().values()) <= {"entrance", "river", "sea", "wall", "dock", "land"}


def test_world_works_from_bytes(rom_bytes):
    assert World(rom_bytes[16:]).tiles == World(rom_bytes).tiles     # headerless too
