"""One local recovery slot, atomic replacement and a previous validated copy.

Optimistic tokens prevent an older browser session overwriting newer work.
The lock serializes sessions in the local Streamlit server. Portable exports
remain independent of this installation's recovery slot.
"""

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import tempfile
from threading import RLock

from ww3.persistence import MAX_SAVE_BYTES, dumps, loads
from ww3.persistence.preferences import DEFAULTS as PRESENTATION_DEFAULTS, valid_preferences

_LOCK = RLock()
UI_KEYS = {"commander", "page", "selected_front", "guide_enabled", "handoff", "review_open", "review_step"} | PRESENTATION_DEFAULTS.keys()


class RecoveryConflict(OSError):
    pass


@dataclass
class Recovery:
    game: object = None
    ui: dict = None
    token: str | None = None
    warning: str = ""


@dataclass
class RecoverySession:
    """Keep the disk token current before returning to interruptible UI code."""

    token: str | None = None
    signature: str | None = None

    def save(self, store, game, ui):
        signature = dumps(game) + repr(sorted(ui.items()))
        with _LOCK:
            if signature == self.signature:
                return
            # Streamlit session-state assignments are rerun yield points.
            # Update this existing object without calling back into Streamlit
            # between the atomic write and recording its new token.
            self.token = store.save(game, ui, self.token)
            self.signature = signature


def _token(payload):
    return hashlib.sha256(payload).hexdigest() if payload is not None else None


def encode(game, ui):
    # Compact JSON keeps the bounded 100-report history within the save limit.
    document = {"recovery_version": 1, "game": game.to_dict(), "ui": {k: v for k, v in ui.items() if k in UI_KEYS}}
    payload = json.dumps(document, allow_nan=False, separators=(",", ":")).encode()
    decode(payload)
    return payload


def decode(payload):
    if len(payload) > MAX_SAVE_BYTES + 4096:
        raise ValueError("Recovery file exceeds its size limit.")
    try:
        data = json.loads(payload)
        if not isinstance(data, dict) or set(data) != {"recovery_version", "game", "ui"} or data["recovery_version"] != 1:
            raise ValueError("Unsupported recovery file.")
        ui = data["ui"]
        if not isinstance(ui, dict) or not set(ui) <= UI_KEYS or not all(isinstance(v, (str, bool, int)) for v in ui.values()):
            raise ValueError("Invalid recovery preferences.")
        if not valid_preferences(ui):
            raise ValueError("Invalid sound or display preferences.")
        return loads(json.dumps(data["game"], separators=(",", ":")), allow_invalid_drafts=True), ui
    except (TypeError, KeyError, UnicodeError, RecursionError) as exc:
        raise ValueError("Malformed recovery file.") from exc


class RecoveryStore:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.current = self.directory / "current.json"
        self.previous = self.directory / "previous.json"

    @staticmethod
    def _read(path):
        try:
            with path.open("rb") as stream:
                return stream.read(MAX_SAVE_BYTES + 4097)
        except FileNotFoundError:
            return None

    def recover(self, *, previous=False):
        with _LOCK:
            primary = self._read(self.current)
            token = _token(primary)
            warning = ""
            for path in (self.current, self.previous):
                if previous and path == self.current:
                    continue
                payload = primary if path == self.current else self._read(path)
                if payload is None:
                    continue
                try:
                    game, ui = decode(payload)
                    if path == self.previous:
                        warning = "Recovered the previous valid checkpoint. The latest edit may need to be repeated."
                    return Recovery(game, ui, token, warning)
                except ValueError:
                    warning = "The latest recovery file is damaged."
            if warning or previous:
                warning += " No valid checkpoint was found. Import a manual save or start a new campaign."
            return Recovery(token=token, ui={}, warning=warning.strip())

    def _atomic_write(self, path, payload):
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=self.directory, prefix=".pending-", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
            temporary = None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def save(self, game, ui, expected_token):
        payload = encode(game, ui)
        with _LOCK:
            self.directory.mkdir(parents=True, exist_ok=True)
            primary = self._read(self.current)
            if _token(primary) != expected_token:
                raise RecoveryConflict("A newer checkpoint exists in another session. Download this draft or reload the latest checkpoint before continuing autosave.")
            if primary == payload:
                return _token(payload)
            if primary is not None:
                try:
                    decode(primary)
                except ValueError:
                    pass  # Never rotate corrupt data over the valid fallback.
                else:
                    self._atomic_write(self.previous, primary)
            self._atomic_write(self.current, payload)
            # Persist directory entries on systems that support directory fsync.
            if os.name == "posix":
                descriptor = os.open(self.directory, os.O_RDONLY)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
            return _token(payload)

    def export_previous(self):
        recovered = self.recover(previous=True)
        return dumps(recovered.game) if recovered.game else None
