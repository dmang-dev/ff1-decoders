"""python -m ff1_decoders ROM <command>."""
from __future__ import annotations

import json
import os

import pytest

from ff1_decoders.__main__ import main


def run(capsys, *args) -> str:
    assert main([os.environ["FF1_ROM"], *args]) == 0
    return capsys.readouterr().out


def test_cli(rom_bytes, capsys, tmp_path):
    assert "USA release" in run(capsys, "info")
    assert "Rapier 10 G" in run(capsys, "shops")
    assert json.loads(run(capsys, "monsters", "0"))["name"] == "IMP"
    assert json.loads(run(capsys, "map", "20"))["objects"][0]["name"] == "Matoya"
    out = run(capsys, "spells", "Knight")
    assert "L3 CUR2 AFIR" in out and "L4" not in out
    assert "L8 white LIF2 FADE WALL XFER" in run(capsys, "spells")
    assert json.loads(run(capsys, "items"))["weapons"]["4"] == "Rapier"
    assert run(capsys, "dialogue", "1").startswith("LIGHT WARRIORS")
    assert json.loads(run(capsys, "world", "188", "203"))["leads_to"] == "14 Gurgu Volcano B1"
    assert "| Red Mage |" in run(capsys, "dump")
    srm = tmp_path / "ff1.srm"
    srm.write_bytes(bytes(0x2000))
    assert json.loads(run(capsys, "save", str(srm)))["gold"] == 0


def test_cli_render(rom_bytes, capsys, tmp_path):
    pytest.importorskip("PIL")
    out = tmp_path / "map8.png"
    assert "1024x1024" in run(capsys, "render", "8", str(out))
    assert out.stat().st_size > 1000
