"""The bundled RAM map, story flags read from SRAM images, and the save decoder."""
from __future__ import annotations

from ff1_decoders import decode_sram, ram_map

# SRAM bytes 0x00-0x3F and 0x200-0x21F of a new game, and of a save made partway
# through the game (ship, canoe, the earth ORB).
NEW_HDR = "00d2990000dded000098980e0166a40e929e00000100000000000000900100000000000000000000000000000000000000000000000000000000000000000000"
NEW_OBJ = "0101010101010101010101010101010101010000010101010100000101010101"
MID_HDR = "01f6d00000dded000198980e0066a40eefc901000400800000000000cd6a010000010100000100000000010000000000000000000001635d005c5d5300000000"
MID_OBJ = "0105040407050700000101010005050505010504040504010104000005050101"


def _sram(hdr: str, obj: str) -> bytearray:
    b = bytearray(0x2000)
    h = bytes.fromhex(hdr)
    b[:len(h)] = h
    b[0x200:0x220] = bytes.fromhex(obj)
    return b


def test_the_map_loads():
    g = ram_map.field("gold")
    assert (g["addr"], g["size"], g["region"]) == (0x1C, 3, "sram")
    assert ram_map.cpu_address(g) == 0x601C
    assert ram_map.cpu_address(ram_map.field("hp"), slot=2) == 0x6100 + 0x80 + 0x0A
    assert ram_map.cpu_address(ram_map.field("map_id")) == 0x48
    assert ram_map.enum("job")[3] == "Red Mage" and len(ram_map.enum("job")) == 12
    assert ram_map.location_names()[20] == "Matoya's Cave" and len(ram_map.location_names()) == 61
    assert ram_map.object_names()["0x0a"] == "Matoya"
    assert ram_map.enum("status_bits")[32] == "Asleep"


def test_every_object_flag_picks_one_bit_of_its_byte():
    for name, spec in ram_map.flags().items():
        assert spec.get("region") == "sram", name
        if 0x200 <= spec["addr"] < 0x300:
            assert spec.get("bit") in (0, 1), name          # bit 2 is a box's opened bit


def test_a_new_game_has_no_story_flag_set():
    flags = ram_map.read_flags(_sram(NEW_HDR, NEW_OBJ))
    assert len(flags) >= 28 and not any(flags.values())


def test_a_later_save_has_the_steps_it_reached_and_none_beyond():
    flags = ram_map.read_flags(_sram(MID_HDR, MID_OBJ))
    assert sorted(k for k, v in flags.items() if v) == [
        "bridge_built", "canal_digger_gone", "canal_opened", "canoe_obtained",
        "cave_boss_beaten", "earth_fiend_beaten", "garland_defeated", "orb_earth",
        "pirates_beaten", "princess_rescued", "rod_plate_used", "ship_obtained",
        "sleeper_woken", "thief_king_beaten", "tunnel_cleared"]


def _party_sram() -> bytearray:
    s = _sram(MID_HDR, MID_OBJ)
    c = 0x100                                         # character 0
    s[c + 0] = 3                                      # Red Mage
    s[c + 2:c + 6] = bytes([0x8A, 0x8B, 0x8C, 0x8D])  # "ABCD"
    s[c + 0x0A:c + 0x0C] = (30).to_bytes(2, "little")
    s[c + 0x0C:c + 0x0E] = (35).to_bytes(2, "little")
    s[c + 0x18] = 0x80 | 4                            # weapon id 4, equipped
    s[c + 0x1C] = 1                                   # armor id 1
    s[c + 0x26] = 4                                   # level 5
    s[c + 0x200:c + 0x203] = bytes([1, 3, 5])         # L1: slots 1, 3, 5
    s[c + 0x204] = 8                                  # L2: slot 8
    s[0x39] = 3                                       # HEAL x3
    return s


def test_decode_sram_without_a_rom():
    d = decode_sram(bytes(_party_sram()))
    assert d["gold"] == int.from_bytes(bytes.fromhex(MID_HDR)[0x1C:0x1F], "little")
    p = d["party"][0]
    assert (p["name"], p["job"], p["level"], p["hp"], p["max_hp"]) == ("ABCD", "Red Mage", 5, 30, 35)
    assert p["weapons"] == [4] and p["armor"] == [1] and p["spells"] == [1, 3, 5, 16]
    assert d["bag"]["HEAL"] == 3 and "orb_earth" in d["flags_set"]
    assert d["ship_at"] == tuple(bytes.fromhex(MID_HDR)[1:3])


def test_decode_sram_names_gear_and_spells_from_the_rom(rom_bytes):
    p = decode_sram(bytes(_party_sram()), rom_bytes)["party"][0]
    assert p["weapons"] == ["Rapier*"] and p["armor"] == ["Cloth"]
    assert p["spells"] == ["CURE", "FOG", "FIRE", "SLOW"]


def test_each_flag_byte_off_the_object_table_has_its_one_rom_write(rom_bytes):
    from ff1_decoders.text import header_size
    h = header_size(rom_bytes)
    prg = rom_bytes[h:h + 0x40000]
    for addr, n in ((0x6000, 1), (0x6004, 2), (0x600C, 1), (0x6012, 1),
                    (0x6032, 1), (0x6033, 1), (0x6034, 1), (0x6035, 1)):
        lo, hi = addr & 0xFF, addr >> 8
        hits = sum(prg.count(bytes([op, lo, hi])) for op in (0x8D, 0x8E, 0x8C, 0xEE, 0xCE))
        assert hits == n, hex(addr)
