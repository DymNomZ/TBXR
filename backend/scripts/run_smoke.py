from __future__ import annotations

"""
Run core TB-XR smoke suites with readable output.

Run from backend folder:

    python scripts/run_smoke.py
"""

import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

SMOKE_LABELS = [
    "apps.accounts.test_smoke",
    "apps.imaging.test_smoke.ReportSmokeTests",
    "apps.imaging.test_smoke.PhysicianDashboardSmokeTests",
    "apps.imaging.test_smoke.AIFailureRetrySmokeTests",
]

HINTS = {
    "apps.accounts.test_smoke": "Check logout route/auth decorators and session handling.",
    "apps.imaging.test_smoke.ReportSmokeTests": "Check report generation and report_detail workflow behavior.",
    "apps.imaging.test_smoke.PhysicianDashboardSmokeTests": "Check /api/physician/dashboard role restriction and report/notification fixtures.",
    "apps.imaging.test_smoke.AIFailureRetrySmokeTests": "Check analyse endpoint handling of AI failures and repeat retry calls.",
}


def run_label(label: str) -> tuple[bool, str]:
    command = [sys.executable, "manage.py", "test", label, "--verbosity", "1"]
    result = subprocess.run(
        command,
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
    )
    combined_output = "\n".join(part for part in [result.stdout, result.stderr] if part).strip()
    return result.returncode == 0, combined_output


def main() -> int:
    print("TB-XR Smoke Run")
    print("=" * 60)

    failures = []

    for label in SMOKE_LABELS:
        print(f"\n[RUN] {label}")
        ok, output = run_label(label)
        if ok:
            print("[PASS]", label)
            continue

        print("[FAIL]", label)
        print("Hint:", HINTS.get(label, "Check test output below."))
        if output:
            lines = output.splitlines()
            tail = "\n".join(lines[-40:])
            print("--- output (last 40 lines) ---")
            print(tail)
            print("--- end output ---")
        failures.append(label)

    print("\n" + "=" * 60)
    if failures:
        print("Smoke run finished with failures:")
        for label in failures:
            print(f"- {label}")
        return 1

    print("Smoke run passed: all selected suites are green.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
