"""
Launches mitmproxy as a subprocess for TestGhost.
"""

import os
import subprocess
import sys
from pathlib import Path


def start_proxy(session_id: str, port: int = 8080, backend_url: str = "http://localhost:8000") -> subprocess.Popen:  # type: ignore[type-arg]
    """
    Start mitmdump with the TestGhost addon.
    Returns the subprocess so the caller can kill it on stop.
    """
    addon_path = Path(__file__).parent / "addon.py"

    env = {**os.environ, "SESSION_ID": session_id, "BACKEND_URL": backend_url}

    proc = subprocess.Popen(
        [sys.executable, "-m", "mitmproxy.tools.main", "mitmdump", "-p", str(port), "-s", str(addon_path)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return proc
