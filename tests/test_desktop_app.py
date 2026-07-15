from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from desktop.diffusiongemma_agent_gui import cli_command, summarize_doctor, validate_task


class DesktopAppTests(unittest.TestCase):
    def test_doctor_summary_distinguishes_required_checks(self) -> None:
        payload = {
            "checks": {
                "windows": {"ok": True, "detail": "Windows"},
                "wsl": {"ok": True, "detail": "wsl.exe"},
                "nvidia": {"ok": True, "detail": "RTX, 16384 MiB"},
                "disk": {"ok": True, "detail": "50 GiB"},
                "runtime_download": {"ok": True, "detail": "tag"},
                "installed": {"ok": False, "detail": "not installed", "required": False},
                "backend": {"ok": False, "required": False},
                "gateway": {"ok": False, "required": False},
            }
        }
        rows, compatible = summarize_doctor(payload)
        self.assertTrue(compatible)
        self.assertEqual(len(rows), 8)
        self.assertFalse(next(row for row in rows if row["name"] == "installed")["required"])

    def test_doctor_summary_fails_for_required_gpu_check(self) -> None:
        rows, compatible = summarize_doctor({"checks": {"nvidia": {"ok": False, "detail": "missing"}}})
        self.assertFalse(compatible)
        self.assertFalse(next(row for row in rows if row["name"] == "nvidia")["ok"])

    def test_task_validation_requires_git_repo_and_text(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, error = validate_task(str(root), "fix it")
            self.assertIn("Git repository", error or "")
            (root / ".git").mkdir()
            _, error = validate_task(str(root), "")
            self.assertIn("Describe", error or "")
            repo, error = validate_task(str(root), "fix it")
            self.assertIsNone(error)
            self.assertEqual(repo, root.resolve())

    def test_source_cli_command_uses_module_entrypoint(self) -> None:
        command = cli_command("doctor", "--json")
        self.assertEqual(command[-3:], ["diffusiongemma_agent", "doctor", "--json"])


if __name__ == "__main__":
    unittest.main()
