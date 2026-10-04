import json
import subprocess
import sys

import pytest

from ww3.bridge.worker import Worker
from ww3.persistence import loads


def request(worker, command, params=None, *, request_id=None, revision=None):
    return worker.handle({"protocol_version": 1, "id": request_id or f"{command}-{worker.session.revision}",
        "command": command, "expected_revision": worker.session.revision if revision is None else revision,
        "params": params or {}})


def test_duplicate_commit_returns_original_reply_and_stale_edit_is_rejected(tmp_path):
    worker = Worker(tmp_path)
    first = request(worker, "commit", {"faction": "EU"}, request_id="end-1", revision=0)
    assert first["ok"] and first["result"]["game"]["round"] == 2
    assert request(worker, "commit", {"faction": "EU"}, request_id="end-1", revision=0) == first
    stale = request(worker, "commit", {"faction": "EU"}, request_id="end-2", revision=0)
    assert stale["error"]["code"] == "revision_conflict"
    assert worker.session.snapshot().round == 2
    reused = request(worker, "state", request_id="end-1")
    assert reused["error"]["code"] == "request_id_reused"


def test_reload_recovers_invalid_draft_and_portable_export(tmp_path):
    worker = Worker(tmp_path)
    edited = request(worker, "edit", {"faction": "EU", "changes": {"investments": {"factory": 10, "research": 10}}})
    assert edited["ok"] and edited["result"]["forecast"] is None
    assert "productivity" in edited["result"]["forecast_error"]
    recovered = Worker(tmp_path)
    assert recovered.session.export() == worker.session.export()
    exported = request(recovered, "export")["result"]["save"]
    assert loads(exported, allow_invalid_drafts=True) == worker.session.snapshot()
    assert request(recovered, "load", {"save": exported})["ok"]


def test_disk_failure_reports_successful_turn_with_explicit_unsaved_state(tmp_path, monkeypatch):
    worker = Worker(tmp_path)
    def fail(*args):
        raise OSError("Disk is full")
    monkeypatch.setattr(worker.recovery, "save", fail)
    reply = request(worker, "commit", {"faction": "EU"})
    assert reply["ok"] and reply["revision"] == 1
    assert reply["result"]["game"]["round"] == 2
    assert reply["result"]["checkpoint_error"] == "Disk is full"
    assert request(worker, "export")["ok"]


@pytest.mark.parametrize("payload", [
    [], {}, {"id": []}, {"id": "x", "protocol_version": True, "command": "commit"},
    {"id": "x", "protocol_version": 1, "command": []},
    {"id": "x", "protocol_version": 1, "command": "state", "params": []},
    {"id": "x", "protocol_version": 1, "command": "edit", "params": {}, "expected_revision": 0},
])
def test_malformed_messages_do_not_modify_campaign(tmp_path, payload):
    worker = Worker(tmp_path)
    before = worker.session.export()
    assert not worker.handle(payload)["ok"]
    assert worker.session.export() == before and worker.session.revision == 0


def test_new_load_and_recover_keep_revisions_monotonic(tmp_path):
    worker = Worker(tmp_path)
    save = request(worker, "export")["result"]["save"]
    assert request(worker, "new", {"mode": "hotseat", "player": "China"})["revision"] == 1
    assert request(worker, "load", {"save": save})["revision"] == 2
    assert request(worker, "recover", {"previous": True})["revision"] == 3
    assert worker.session.snapshot().player == "China"


def test_worker_process_framing_unicode_eof_and_core_imports_without_ui(tmp_path):
    commands = [b'broken\n', json.dumps({"protocol_version": 1, "id": "état", "command": "state"}).encode() + b'\n']
    completed = subprocess.run([sys.executable, "-m", "ww3.bridge", "--save-dir", str(tmp_path)],
        input=b"".join(commands), capture_output=True, timeout=15, cwd=tmp_path)
    assert completed.returncode == 0 and not completed.stderr
    replies = [json.loads(line) for line in completed.stdout.splitlines()]
    assert len(replies) == 2 and replies[0]["error"]["code"] == "invalid_json"
    assert replies[1]["id"] == "état" and replies[1]["ok"]
    program = """
import builtins
original = builtins.__import__
def headless(name, *args, **kwargs):
    if name.split('.')[0] in ('streamlit', 'pandas', 'ww3_streamlit'):
        raise AssertionError('UI dependency in simulation: ' + name)
    return original(name, *args, **kwargs)
builtins.__import__ = headless
from ww3.application.session import GameSession
session = GameSession.new()
assert session.forecast()
session.commit('EU')
"""
    result = subprocess.run([sys.executable, "-c", program], capture_output=True, text=True, cwd=tmp_path, timeout=15)
    assert result.returncode == 0, result.stderr
