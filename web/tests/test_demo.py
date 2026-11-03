"""The local demo of the README (scripts/dev_server.py): the home page examples replay their recorded research.
Offline here (AUTOLAB_DEMO_OFFLINE): tests never call a model; the hybrid mode is tested in tests/test_hybrid.py."""

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autolab import config

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def demo():
    os.environ["AUTOLAB_DEMO_OFFLINE"] = "1"
    sys.path.insert(0, str(ROOT / "scripts"))
    import dev_server

    assert dev_server.LIVE is None

    return TestClient(dev_server.app)


@pytest.mark.parametrize("text,cid", config.REPLAY_EXAMPLES)
def test_each_home_example_replays_its_research_with_its_3d_files(demo, text, cid):
    v = demo.post("/api/conversations", json={"message": text}).json()
    assert v["conversation"]["scope"]["reused_from"]["id"] == cid and v["conversation"]["status"] == "done"
    assert [m["kind"] for m in v["messages"]][-3:] == ["summary", "report", "review"]
    index = demo.get(f"/api/conversations/{v['conversation']['id']}/files/index.json").json()
    assert index["structures"] and v["events_count"] > 50


def test_the_pages_of_the_demo_answer(demo):
    for path in ("/", "/results", "/benchmarks", "/settings", "/api/champions", "/api/benchmarks", "/api/settings"):
        assert demo.get(path).status_code == 200, path


def test_the_readme_install_command_names_existing_extras():
    import tomllib

    extras = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["optional-dependencies"]
    assert 'pip install -e ".[web,dev]"' in (ROOT / "README.md").read_text(encoding="utf-8")
    assert {"web", "dev"} <= set(extras) and {"fastapi", "uvicorn"} <= set(extras["web"])
