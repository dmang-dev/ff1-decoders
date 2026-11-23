"""Tests that need the game read its path from the FF1_ROM environment variable (your
own Final Fantasy (NES, USA) ROM) and are skipped when it is unset."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

ROM_PATH = os.environ.get("FF1_ROM")

needs_rom = pytest.mark.skipif(not (ROM_PATH and Path(ROM_PATH).is_file()),
                               reason="set FF1_ROM to your Final Fantasy (NES, USA) ROM")


@pytest.fixture(scope="session")
def rom_bytes() -> bytes:
    if not (ROM_PATH and Path(ROM_PATH).is_file()):
        pytest.skip("set FF1_ROM to your Final Fantasy (NES, USA) ROM")
    return Path(ROM_PATH).read_bytes()


@pytest.fixture(scope="session")
def rom(rom_bytes):
    from ff1_decoders import Rom
    return Rom(rom_bytes)
