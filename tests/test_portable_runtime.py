from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PortableRuntimeTests(unittest.TestCase):
    def test_installer_uses_bundled_supported_python_and_pinned_dependencies(self) -> None:
        installer = (ROOT / "portable" / "Install-DiffusionGemmaAgent.ps1").read_text(encoding="utf-8")

        self.assertIn("cpython-3.12.13.tar.gz", installer)
        self.assertIn("aider-chat==0.86.2", installer)
        self.assertIn("haystack-ai==2.31.0", installer)
        self.assertNotIn("python3 -m venv", installer)
        self.assertIn("WSL cannot reach PyPI", installer)

    def test_installer_reuses_an_unchanged_payload(self) -> None:
        installer = (ROOT / "portable" / "Install-DiffusionGemmaAgent.ps1").read_text(encoding="utf-8")

        self.assertIn("installed-manifest.sha256", installer)
        self.assertIn("Get-FileHash", installer)
        self.assertIn("stat -c %s", installer)

    def test_launcher_keeps_wsl_attached_without_nested_shell_commands(self) -> None:
        powershell = (ROOT / "portable" / "dg.ps1").read_text(encoding="utf-8")
        launcher = (ROOT / "scripts" / "run_runtime_component.sh").read_text(encoding="utf-8")

        self.assertIn("Start-Process -FilePath wsl.exe", powershell)
        self.assertIn("run_runtime_component.sh", powershell)
        self.assertNotIn("bash -lc", powershell)
        self.assertIn('exec "${COMMAND[@]}"', launcher)
        self.assertNotIn("nohup", launcher)


if __name__ == "__main__":
    unittest.main()
