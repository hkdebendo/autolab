"""Shared pytest setup: GPU and paid-API tests are skipped unless explicitly requested."""

import json
from pathlib import Path

import pytest

from autolab import config

DATA = Path(__file__).parent / "data"

requires_mp = pytest.mark.skipif(
    not config.has_key("MP_API_KEY"), reason="MP_API_KEY missing: fill it in .env (see .env.example)"
)


def pytest_addoption(parser):
    parser.addoption("--gpu", action="store_true", help="run UMA tests (NVIDIA GPU)")
    parser.addoption("--api", action="store_true", help="run real paid LLM calls")


def pytest_collection_modifyitems(config, items):
    for marker, option in (("gpu", "--gpu"), ("api", "--api")):
        if config.getoption(option):
            continue
        skip = pytest.mark.skip(reason=f"{marker} test: run with {option}")
        for item in items:
            if marker in item.keywords:
                item.add_marker(skip)


def load_structure(name: str):
    """Structure saved in tests/data (fetched once from Materials Project)."""
    from pymatgen.core import Structure

    return Structure.from_dict(json.loads((DATA / f"{name}.json").read_text(encoding="utf-8")))
