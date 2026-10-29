# Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md.
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(autouse=True)
def isolated_lab(tmp_path, monkeypatch):
    monkeypatch.setenv('SIMLAB_DATA_DIR', str(tmp_path / 'lab'))
    monkeypatch.setenv('MODEL_PROVIDER', 'codex')
    monkeypatch.setenv('SIMLAB_MAX_CALLS', '24')
    monkeypatch.setenv('SIMLAB_MODEL_RETRIES', '0')
