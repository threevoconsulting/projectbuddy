#!/usr/bin/env python3
"""Safety gate (baseline; expanded in M5).

Runs every line of the red-team corpus through the safety filter and fails if any
slips through. M5 will grow this to drive real model outputs and require 100% safe
before any child testing. Run via ``make redteam``.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make src/ importable when run directly (uv run handles this; this is belt-and-braces).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from projectbuddy.core import safety

CORPUS = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "redteam.txt"


def main() -> int:
    lines = [
        line.strip()
        for line in CORPUS.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    leaked = [line for line in lines if not safety.check(line).blocked]

    print(f"Red-team corpus: {len(lines)} samples")
    if leaked:
        print(f"FAIL — {len(leaked)} sample(s) not blocked:")
        for line in leaked:
            print(f"  • {line}")
        return 1
    print("PASS — all samples blocked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
