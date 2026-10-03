import pytest


@pytest.fixture(autouse=True)
def isolated_recovery(tmp_path, monkeypatch):
    """UI tests cannot touch a developer's real campaign or one another."""
    monkeypatch.setenv("WW3_SAVE_DIR", str(tmp_path / "recovery"))
