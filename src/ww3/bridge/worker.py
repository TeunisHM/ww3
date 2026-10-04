"""One offline game session, served as newline-delimited JSON over stdin/stdout."""

import argparse
from collections import OrderedDict
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import sys

from ww3.application.session import GameSession, RevisionConflict, SessionError
from ww3.application.command_view import catalog, command_view, default_ui, scenario_rules, ui_values
from ww3.core.catalog import FACTIONS, FRONTS
from ww3.core.engine import InvalidOrder
from ww3.persistence import dumps
from ww3.persistence.recovery import RecoverySession, RecoveryStore

PROTOCOL_VERSION = 1
MAX_REQUEST_BYTES = 4_100_000
MUTATIONS = {"new", "load", "edit", "commit", "reopen", "undo", "reset", "remember", "restore", "recover", "ui"}
PARAMETERS = {
    "state": set(), "forecast": set(), "export": set(), "quit": set(),
    "new": {"mode", "player", "seed", "rules"}, "load": {"save"}, "ui": {"values"},
    "edit": {"faction", "changes"}, "commit": {"faction"},
    "reopen": {"faction"}, "undo": {"faction"}, "reset": {"faction"},
    "remember": {"faction"}, "restore": {"faction"}, "compare": {"faction"},
    "recover": {"previous"},
}


def encode(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def reject_constant(value):
    raise ValueError(f"Invalid JSON number: {value}.")


class Worker:
    def __init__(self, save_dir):
        self.store = RecoveryStore(save_dir)
        self.session = GameSession.new()
        self.recovery = RecoverySession()
        self.notice = ""
        self.checkpoint_error = None
        self.stopping = False
        self._replies = OrderedDict()
        self.ui = default_ui()
        self.first_launch = True
        try:
            recovered = self.store.recover()
            self.recovery = RecoverySession(recovered.token)
            self.notice = recovered.warning
            if recovered.game is not None:
                self.session = GameSession(recovered.game)
                self.first_launch = False
                self.ui = default_ui(recovered.game.player)
                self.ui.update(ui_values(recovered.ui))
        except (OSError, ValueError) as exc:
            self.checkpoint_error = str(exc)

    def view(self):
        game = self.session.snapshot()
        try:
            forecast, error = self.session.forecast(), None
        except (InvalidOrder, ValueError) as exc:
            forecast, error = None, str(exc)
        history = self.session.draft_history
        return {
            "game": game.to_dict(), "year": game.year,
            "factions": list(FACTIONS), "fronts": list(FRONTS),
            "forecast": forecast, "forecast_error": error,
            "can_undo": {f: bool(history.undo[f]) and f not in game.submitted for f in FACTIONS},
            "can_restore": {f: f in history.remembered and f not in game.submitted for f in FACTIONS},
            "notice": self.notice, "checkpoint_error": self.checkpoint_error,
            "catalog": catalog(), "desk": command_view(game, forecast),
            "ui": self.ui.copy(), "first_launch": self.first_launch,
        }

    def _checkpoint(self):
        try:
            self.recovery.save(self.store, self.session.snapshot(), self.ui)
            self.checkpoint_error = None
        except (OSError, ValueError) as exc:
            # The command has succeeded in memory. Report its new revision and
            # the save error together, so a caller never repeats a resolved turn.
            self.checkpoint_error = str(exc)

    def error(self, request_id, code, message):
        return {"protocol_version": PROTOCOL_VERSION, "id": request_id, "ok": False,
                "revision": self.session.revision, "error": {"code": code, "message": message}}

    def handle(self, request):
        request_id = request.get("id") if isinstance(request, dict) else None
        if not isinstance(request_id, str) or not 1 <= len(request_id) <= 128:
            return self.error(None, "invalid_request", "A string request id of 1–128 characters is required.")
        try:
            fingerprint = hashlib.sha256(encode(request).encode()).hexdigest()
        except (TypeError, ValueError, RecursionError):
            return self.error(request_id, "invalid_request", "Request must contain finite JSON values.")
        if request_id in self._replies:
            old_fingerprint, old_reply = self._replies[request_id]
            if fingerprint != old_fingerprint:
                return self.error(request_id, "request_id_reused", "Use a new id for each distinct command.")
            return json.loads(old_reply)
        try:
            allowed = {"protocol_version", "id", "command", "expected_revision", "params"}
            if not set(request) <= allowed or type(request.get("protocol_version")) is not int or request["protocol_version"] != PROTOCOL_VERSION:
                raise SessionError("Unsupported protocol version or request fields.")
            command, params = request.get("command"), request.get("params", {})
            if not isinstance(command, str) or command not in PARAMETERS:
                raise SessionError("Unknown command.")
            if not isinstance(params, dict) or not set(params) <= PARAMETERS[command]:
                raise SessionError("Unknown command parameters.")
            if command in MUTATIONS:
                self.session.check_revision(request.get("expected_revision"))
            result = self._dispatch(command, params)
            response = {"protocol_version": PROTOCOL_VERSION, "id": request_id, "ok": True,
                        "revision": self.session.revision, "result": result}
        except RevisionConflict as exc:
            response = self.error(request_id, "revision_conflict", str(exc))
        except (InvalidOrder, SessionError, ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError) as exc:
            response = self.error(request_id, "invalid_command", str(exc))
        except OSError as exc:
            response = self.error(request_id, "storage_error", str(exc))
        # A bounded retry cache. Older mutation retries are still protected by
        # their expected revision, including after a turn has advanced.
        encoded = encode(response)
        self._replies[request_id] = (fingerprint, encoded)
        while len(self._replies) > 32:
            self._replies.popitem(last=False)
        return json.loads(encoded)

    def _dispatch(self, command, params):
        if command == "quit":
            self.stopping = True
            return {"stopping": True}
        if command == "export":
            return {"save": self.session.export()}
        if command == "compare":
            return self.session.compare(params["faction"])
        if command == "ui":
            self.ui.update(ui_values(params["values"]))
            self._checkpoint()
            return {"ui": self.ui.copy(), "checkpoint_error": self.checkpoint_error}
        turn = None
        if command == "new":
            if "seed" in params and type(params["seed"]) is not int:
                raise SessionError("Seed must be an integer between 0 and 100000.")
            if "rules" in params and not isinstance(params["rules"], dict):
                raise SessionError("Scenario rules must be an object.")
            rules = scenario_rules(params.get("rules"), params.get("seed"))
            fresh = GameSession.new(params.get("mode", "solo"), params.get("player", "EU"), rules)
            self.session.load(fresh.export())
        elif command == "load":
            if not isinstance(params["save"], str):
                raise SessionError("save must contain a portable JSON save as a string.")
            self.session.load(params["save"])
        elif command == "edit":
            self.session.edit_order(params["faction"], params["changes"])
        elif command == "commit":
            turn = asdict(self.session.commit(params["faction"]))
            self.ui.update(commander=turn["next_commander"], handoff=self.session.snapshot().mode == "hotseat")
            if turn["resolved"]:
                self.ui.update(review_open=True, review_step=0)
        elif command in ("undo", "reopen", "remember", "restore", "reset"):
            operation = {"restore": "restore_remembered", "reset": "reset_draft"}.get(command, command)
            getattr(self.session, operation)(params["faction"])
            if command == "reopen":
                self.ui["handoff"] = False
        elif command == "recover":
            previous = params.get("previous", False)
            if type(previous) is not bool:
                raise SessionError("previous must be a boolean.")
            recovered = self.store.recover(previous=previous)
            if recovered.game is None:
                raise SessionError(recovered.warning or "No saved campaign is available.")
            self.session.load(dumps(recovered.game))
            self.recovery = RecoverySession(recovered.token)
            self.notice = recovered.warning
            self.ui = {**default_ui(recovered.game.player), **ui_values(recovered.ui)}
        if command in ("new", "load"):
            prior = self.ui
            self.ui = default_ui(self.session.snapshot().player)
            self.ui.update({key: prior[key] for key in ("sound_enabled", "sound_volume", "text_scale", "reduce_motion", "guide_enabled")})
            self.notice = ""
        if command in ("new", "load", "recover", "commit"):
            self.first_launch = False
        if command in MUTATIONS:
            self._checkpoint()
        result = self.view()
        if turn is not None:
            result["turn"] = turn
        return result


def default_save_dir():
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library/Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    return base / "ww3" / "godot"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--save-dir", type=Path, default=default_save_dir())
    args = parser.parse_args()
    worker = Worker(args.save_dir)
    source, destination = sys.stdin.buffer, sys.stdout.buffer
    while not worker.stopping:
        line = source.readline(MAX_REQUEST_BYTES + 1)
        if not line:
            break
        if len(line) > MAX_REQUEST_BYTES:
            response = worker.error(None, "request_too_large", "Request exceeds the protocol size limit.")
            # Framing cannot be trusted after an oversized request. Reply once
            # and close instead of interpreting the remainder as commands.
            worker.stopping = True
        else:
            try:
                request = json.loads(line, parse_constant=reject_constant)
                response = worker.handle(request)
            except (ValueError, UnicodeError, RecursionError):
                response = worker.error(None, "invalid_json", "Expected one UTF-8 JSON object per line.")
        try:
            destination.write((encode(response) + "\n").encode("utf-8"))
            destination.flush()
        except BrokenPipeError:
            break


if __name__ == "__main__":
    main()
