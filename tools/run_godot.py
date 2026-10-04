"""Launch the Godot client or run its integration suites with disposable saves."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--godot", default=os.environ.get("WW3_GODOT") or shutil.which("godot") or shutil.which("godot4"))
    parser.add_argument("--smoke", action="store_true", help="Run both headless client integration suites with disposable saves")
    args = parser.parse_args()
    if not args.godot:
        parser.error("Install Godot 4.5+ or pass --godot /path/to/Godot.")
    try:
        import ww3.application.session  # noqa: F401
    except ImportError:
        parser.error("Install the game in this interpreter first: python -m pip install -e .")
    project = Path(__file__).resolve().parents[1] / "clients/godot"
    env = {**os.environ, "WW3_PYTHON": sys.executable}
    command = [args.godot, "--path", str(project)]
    if not args.smoke:
        return subprocess.run(command, env=env).returncode
    with tempfile.TemporaryDirectory(prefix="ww3-godot-test-") as directory:
        env["WW3_GODOT_SAVE_DIR"] = directory
        # Isolate Godot's own logs, caches and settings in CI as well.
        for name in ("XDG_DATA_HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME"):
            env[name] = str(Path(directory) / name.lower())
        # Import SVG resources before running a fresh checkout's scene. The
        # editor may report unavailable debug sockets in a network sandbox.
        imported = subprocess.run(command + ["--headless", "--editor", "--import"], env=env)
        if imported.returncode:
            return imported.returncode
        for suite in ("smoke", "features"):
            env["WW3_GODOT_SAVE_DIR"] = str(Path(directory) / suite)
            result = subprocess.run(command + ["--headless", "--script", f"res://tests/{suite}.gd"], env=env, timeout=150)
            if result.returncode:
                return result.returncode
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
