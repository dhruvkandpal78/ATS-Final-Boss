"""A synthetic child checks both Python and native diagnostic channels."""
import subprocess
import sys


def test_private_child_diagnostics_cannot_reach_parent_logs():
    code = (
        "from src.app.server import _silence_private_worker_output; "
        "import logging, os; _silence_private_worker_output(); "
        "logging.error('synthetic-sensitive-marker'); "
        "os.write(1, b'synthetic-sensitive-marker'); "
        "os.write(2, b'synthetic-sensitive-marker')"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, timeout=15)
    assert result.returncode == 0
    assert result.stdout == b"" and result.stderr == b""
