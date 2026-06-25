"""Syntax-check the vanilla front-end JS (no JS test runner otherwise).

A JS syntax error ships silently — the Python suite never executes the browser code,
and static files serve fine regardless — so a broken bundle blanks the page at runtime
(as happened to the parent app). ``node --check`` catches it. Skips where node is absent.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

_WEB = Path(__file__).resolve().parents[2] / "src" / "projectbuddy"
_JS = sorted((_WEB / "web" / "js").glob("*.js")) + sorted((_WEB / "parent" / "js").glob("*.js"))


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
@pytest.mark.parametrize("js", _JS, ids=lambda p: p.name)
def test_js_parses(js: Path) -> None:
    result = subprocess.run(["node", "--check", str(js)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
