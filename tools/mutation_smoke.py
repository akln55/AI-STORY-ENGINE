"""Small mutation smoke test for the project's regression suite.

The goal is not a full mutation-testing engine. It deliberately introduces a
few known-bad mutations into critical engine paths in temporary copies and
requires the normal pytest suite to fail. A mutation that survives means the
suite has a blind spot worth addressing.

Usage:
    python tools/mutation_smoke.py

No third-party dependency is required beyond the project's normal pytest
runner. The temporary copies are deleted automatically.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Mutation:
    name: str
    relative_path: str
    needle: str
    replacement: str
    tests: tuple[str, ...]


MUTATIONS = (
    Mutation(
        "remove reachable-location validation",
        "engine/core/validation.py",
        '        if current and current != dest and not state.world.reachable(current, dest):\n',
        '        if False and current and current != dest and not state.world.reachable(current, dest):\n',
        ("tests/test_validation.py::test_unreachable_move_rejected",),
    ),
    Mutation(
        "disable atomic rejection",
        "engine/core/validation.py",
        '    if report.rejected:\n        report.accepted = []\n        return report\n',
        '    if False and report.rejected:\n        report.accepted = []\n        return report\n',
        ("tests/test_validation.py::test_atomic_batch_rejects_all_on_any_failure",),
    ),
    Mutation(
        "allow resurrection through npc flag",
        "engine/core/validation.py",
        '            if field_value is True and not npc.alive:\n                return False, None, (\n                    f"cannot resurrect dead npc \'{effect.target}\' via ordinary npc effect")\n',
        '            if field_value is True and not npc.alive:\n                pass\n',
        ("tests/test_validation.py::test_resurrect_dead_npc_rejected",),
    ),
)


def main() -> int:
    failures = []
    for mutation in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix="rpg_mutation_") as td:
            work = Path(td) / "project"
            shutil.copytree(
                ROOT,
                work,
                ignore=shutil.ignore_patterns(".git", ".pytest_cache", "__pycache__", "*.pyc"),
            )
            target = work / mutation.relative_path
            source = target.read_text()
            if mutation.needle not in source:
                failures.append(f"{mutation.name}: mutation needle not found")
                continue
            target.write_text(source.replace(mutation.needle, mutation.replacement, 1))
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", *mutation.tests],
                cwd=work,
                capture_output=True,
                text=True,
                timeout=180,
            )
            if proc.returncode == 0:
                failures.append(f"{mutation.name}: SURVIVED")
                print(f"FAIL {mutation.name}: mutation survived")
            else:
                print(f"PASS {mutation.name}: suite detected mutation")

    if failures:
        print("\nMutation smoke failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(f"\nMutation smoke passed: {len(MUTATIONS)}/{len(MUTATIONS)} detected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
