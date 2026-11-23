"""The bundled RAM map (data/ram_map.toml): WRAM and SRAM addresses, enums (classes,
status, items, vehicles, shop types, map and object names) and story flags.

    >>> from ff1_decoders import ram_map
    >>> ram_map.field("gold")["addr"], ram_map.field("gold")["region"]
    (28, 'sram')
    >>> ram_map.enum("job")[3]
    'Red Mage'
"""
from __future__ import annotations

import tomllib
from functools import lru_cache
from importlib import resources

SRAM_BASE = 0x6000           # region "sram" addresses are offsets from CPU $6000


@lru_cache(maxsize=1)
def load() -> dict:
    """The whole RAM map as parsed TOML (a fresh parse is cached; don't mutate it)."""
    text = resources.files("ff1_decoders").joinpath("data/ram_map.toml").read_text(encoding="utf-8")
    return tomllib.loads(text)


def fields() -> dict[str, dict]:
    """All named single fields ([fields], [party_fields], [party_gear], [inventory],
    [field_objects]), each with a `table` key saying where it came from."""
    m = load()
    out = {}
    for table in ("fields", "party_fields", "party_gear", "inventory", "field_objects"):
        for name, spec in m.get(table, {}).items():
            out.setdefault(name, dict(spec, table=table))
    return out


def field(name: str) -> dict:
    """One field's spec, region defaulted to "wram" and size to 1."""
    spec = fields()[name]
    return {"region": "wram", "size": 1, **spec}


def cpu_address(spec: dict, slot: int | None = None) -> int:
    """The CPU address of a field (for party tables, of character `slot`)."""
    addr = spec["addr"]
    if spec.get("table") in ("party_fields", "party_gear"):
        p = load()["party"]
        addr += p["base"] + (slot or 0) * p["stride"]
    return addr + (SRAM_BASE if spec.get("region", "wram") == "sram" else 0)


def enum(name: str) -> dict:
    """An [enums.<name>] table with int keys where the keys are numbers ("0x0a" too)."""
    raw = load()["enums"][name]
    out = {}
    for k, v in raw.items():
        try:
            out[int(k, 0)] = v
        except ValueError:
            out[k] = v
    return out


def location_names() -> dict[int, str]:
    """Map id -> place name."""
    return enum("location")


def object_names() -> dict[str, str]:
    """Object id as "0x0a" -> name (the form Rom.objects looks names up by)."""
    return {f"{k:#04x}": v for k, v in enum("object").items()}


def flags() -> dict[str, dict]:
    """Story flags: name -> spec (addr, region, bit / clear / equals)."""
    return load()["flags"]


def read_flags(sram: bytes) -> dict[str, bool]:
    """Every story flag's state in an 8 KB SRAM image (a .srm/.sav file, or the live
    $6000-$7FFF)."""
    out = {}
    for name, spec in flags().items():
        byte = sram[spec["addr"]]
        if "equals" in spec:
            out[name] = byte == spec["equals"]
        else:
            out[name] = bool(byte & (1 << spec.get("bit", 0))) != bool(spec.get("clear"))
    return out
