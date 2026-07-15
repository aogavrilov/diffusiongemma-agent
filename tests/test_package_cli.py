from __future__ import annotations

import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from diffusiongemma_agent import __version__
from diffusiongemma_agent import cli


class PackageCliTests(unittest.TestCase):
    @staticmethod
    def create_runtime_bundle(root: Path) -> Path:
        model = root / "payload" / "models" / cli.MODEL_FILENAME
        model.parent.mkdir(parents=True)
        model.write_bytes(b"test")
        (root / "payload" / "app").mkdir(parents=True)
        (root / "payload" / "app" / "server.py").write_text("", encoding="utf-8")
        (root / "payload" / "bin").mkdir(parents=True)
        (root / "payload" / "bin" / "llama-diffusion-gemma-visual-server").write_text("", encoding="utf-8")
        (root / "Install-DiffusionGemmaAgent.ps1").write_text("", encoding="utf-8")
        (root / "dg.ps1").write_text("", encoding="utf-8")
        cli.write_json(root / "manifest.json", {"model": cli.MODEL_FILENAME})
        return model

    def test_parser_exposes_distribution_commands(self) -> None:
        parser = cli.parser()
        for command in ("install", "update", "start", "stop", "run", "status", "doctor", "discover", "logs", "uninstall"):
            argv = [command]
            if command == "run":
                argv.extend(["--task", "fix it"])
            self.assertEqual(parser.parse_args(argv).command, command)
        args = parser.parse_args(["run", "--task", "fix it", "--file", "src/x.py", "--max-steps", "5"])
        self.assertEqual(args.task, "fix it")
        self.assertEqual(args.file, "src/x.py")
        self.assertEqual(args.max_steps, 5)

        with self.assertRaises(SystemExit):
            parser.parse_args(["run", "--task", "fix it", "--max-steps", "6"])

    def test_install_requires_explicit_license_acceptance(self) -> None:
        args = cli.parser().parse_args(["install"])
        with patch("diffusiongemma_agent.cli.platform.system", return_value="Windows"):
            with self.assertRaisesRegex(RuntimeError, "accept-licenses"):
                cli.install_runtime(args)

    def test_runtime_config_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / "config.json"
            with patch("diffusiongemma_agent.cli.config_path", return_value=config):
                cli.write_json(config, {"version": 1, "runtime_dir": temporary})
                self.assertEqual(cli.read_json(config)["version"], 1)
                self.assertEqual(cli.runtime_dir_from_config(), Path(temporary))

    def test_status_handles_stale_runtime_config(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / "config.json"
            cli.write_json(config, {"runtime_dir": str(Path(temporary) / "missing")})
            with patch("diffusiongemma_agent.cli.config_path", return_value=config):
                with patch("diffusiongemma_agent.cli.endpoint_health", return_value={"ok": False}):
                    self.assertEqual(cli.status(as_json=True), 1)

    def test_uninstall_requires_confirmation(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "--yes"):
            cli.uninstall_runtime(Namespace(yes=False, remove_download=False))

    def test_wsl_removal_path_rejects_dangerous_roots(self) -> None:
        for value in ("", "/", "/root", "relative/path", "/tmp/../root"):
            with self.subTest(value=value):
                with self.assertRaises(RuntimeError):
                    cli.validate_wsl_removal_path(value)
        self.assertEqual(
            str(cli.validate_wsl_removal_path("/home/user/.local/share/diffusiongemma-agent")),
            "/home/user/.local/share/diffusiongemma-agent",
        )

    def test_update_reuses_configured_installation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary) / "runtime"
            runtime.mkdir()
            config = Path(temporary) / "config.json"
            cli.write_json(
                config,
                {
                    "runtime_dir": str(runtime),
                    "runtime_repo": "owner/runtime",
                    "wsl_root": "/home/user/.local/share/diffusiongemma-agent",
                },
            )
            args = Namespace(
                runtime_repo="",
                revision="v-test",
                token="",
                accept_licenses=True,
                force_download=False,
                no_start=True,
            )
            with patch("diffusiongemma_agent.cli.config_path", return_value=config):
                with patch("diffusiongemma_agent.cli.install_runtime", return_value=0) as install:
                    self.assertEqual(cli.update_runtime(args), 0)
            forwarded = install.call_args.args[0]
            self.assertEqual(forwarded.runtime_repo, "owner/runtime")
            self.assertEqual(forwarded.local_dir, str(runtime))
            self.assertEqual(forwarded.revision, "v-test")

    def test_discovery_prefers_a_complete_runtime_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "downloaded-runtime"
            model = self.create_runtime_bundle(root)
            with patch.object(cli, "MODEL_BYTES", 4):
                discovery = cli.local_runtime_discovery([Path(temporary)])
        self.assertTrue(discovery["found"])
        self.assertEqual(discovery["best"]["kind"], "runtime")
        self.assertEqual(Path(discovery["best"]["runtime_dir"]), root)
        self.assertEqual(Path(discovery["best"]["model_file"]), model)

    def test_discovery_accepts_a_standalone_compatible_gguf(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            model = Path(temporary) / "renamed-local-copy.gguf"
            model.write_bytes(b"test")
            with patch.object(cli, "MODEL_BYTES", 4):
                discovery = cli.local_runtime_discovery([Path(temporary)])
        self.assertEqual(discovery["best"]["kind"], "model")
        self.assertEqual(Path(discovery["best"]["model_file"]), model)

    def test_install_skips_download_for_a_complete_local_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "downloaded-runtime"
            self.create_runtime_bundle(root)
            config = Path(temporary) / "state" / "config.json"
            args = Namespace(
                runtime_repo="owner/runtime",
                revision="v-test",
                local_dir=str(root),
                wsl_root="",
                token="",
                accept_licenses=True,
                force_download=False,
                no_start=True,
                model_file="",
            )
            with patch.object(cli, "MODEL_BYTES", 4):
                with patch("diffusiongemma_agent.cli.require_install_prerequisites"):
                    with patch("diffusiongemma_agent.cli.snapshot_download") as download:
                        with patch("diffusiongemma_agent.cli.powershell", return_value="powershell"):
                            with patch("diffusiongemma_agent.cli.invoke", return_value=SimpleNamespace(returncode=0)):
                                with patch("diffusiongemma_agent.cli.config_path", return_value=config):
                                    self.assertEqual(cli.install_runtime(args), 0)
            download.assert_not_called()
            self.assertEqual(cli.read_json(config)["runtime_dir"], str(root.resolve()))

    def test_standalone_model_is_staged_without_changing_its_contents(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "downloaded.gguf"
            source.write_bytes(b"test")
            with patch.object(cli, "MODEL_BYTES", 4):
                target, method = cli.stage_local_model(source, root / "runtime")
                self.assertTrue(cli.compatible_model(target))
            self.assertIn(method, {"hardlink", "copy"})
            self.assertEqual(target.read_bytes(), source.read_bytes())

    def test_version_is_semver_like(self) -> None:
        self.assertEqual(__version__, "0.1.2")


if __name__ == "__main__":
    unittest.main()
