from __future__ import annotations

import ctypes
import json
import os
import platform
import queue
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, X, Y, BooleanVar, StringVar, Text, Tk, filedialog, messagebox
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from typing import Any, Callable

from diffusiongemma_agent import __version__ as core_version
from diffusiongemma_agent.cli import exact_git_root, infer_task_mode


APP_VERSION = "0.1.4"
RUNTIME_SIZE = "13.2 GB"
BG = "#f4f6f8"
SURFACE = "#ffffff"
TEXT = "#17212b"
MUTED = "#5f6b76"
ACCENT = "#146c4b"
ACCENT_ACTIVE = "#0f5a3e"
INFO = "#145ca8"
DANGER = "#b42318"
BORDER = "#d6dce2"


def cli_command(*arguments: str) -> list[str]:
    if getattr(sys, "frozen", False):
        core = Path(sys.executable).with_name("dg-agent-core.exe")
        return [str(core), *arguments]
    return [sys.executable, "-m", "diffusiongemma_agent", *arguments]


def validate_task(repo_value: str, task_value: str, mode: str = "edit") -> tuple[Path | None, str | None]:
    repo = Path(repo_value).expanduser()
    if not repo_value.strip():
        return None, "Choose a repository folder."
    if not repo.is_dir():
        return None, "The selected repository folder does not exist."
    if not task_value.strip():
        return None, "Describe the change you want the agent to make."
    if mode == "edit":
        root = exact_git_root(repo)
        if root is None:
            return None, "Code changes require a Git repository. Choose its exact Git root folder."
        if os.path.normcase(str(root)) != os.path.normcase(str(repo.resolve())):
            return None, f"Choose the exact Git root for code changes: {root}"
    return repo.resolve(), None


def summarize_doctor(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    labels = {
        "windows": "Windows 10/11",
        "wsl": "WSL2",
        "nvidia": "NVIDIA GPU and 16 GB VRAM",
        "disk": "Free disk space",
        "runtime_download": "Runtime download",
        "local_weights": "Existing model files",
        "installed": "Local runtime",
        "backend": "Model service",
        "gateway": "Agent gateway",
    }
    checks = payload.get("checks") if isinstance(payload.get("checks"), dict) else {}
    optional = {"local_weights", "installed", "backend", "gateway"}
    rows: list[dict[str, Any]] = []
    compatible = True
    for name in labels:
        raw = checks.get(name) if isinstance(checks.get(name), dict) else {}
        required = bool(raw.get("required", name not in optional))
        ok = bool(raw.get("ok"))
        if required and not ok:
            compatible = False
        rows.append(
            {
                "name": name,
                "label": labels[name],
                "ok": ok,
                "required": required,
                "detail": str(raw.get("detail") or raw.get("error") or "Not checked"),
            }
        )
    return rows, compatible


def setup_summary(rows: list[dict[str, Any]]) -> tuple[str, str]:
    failed = [str(row["label"]) for row in rows if row["required"] and not row["ok"]]
    if failed:
        return "This computer needs attention", "Required: " + ", ".join(failed) + "."
    installed = next((row for row in rows if row["name"] == "installed"), None)
    if installed and installed["ok"]:
        return "The agent is installed", "Open the Agent tab to choose a repository and run a task."
    local = next((row for row in rows if row["name"] == "local_weights"), None)
    if local and local["ok"]:
        return "Ready to install", "Compatible files were found on this computer and will be reused."
    return "Ready to install", f"The required runtime download is approximately {RUNTIME_SIZE}."


def concise_error(output: str) -> str:
    ignored = ("+", "CategoryInfo", "FullyQualifiedErrorId", "At ", "Traceback")
    for line in reversed(output.splitlines()):
        value = line.strip()
        if value and not value.startswith(ignored):
            return value[:300]
    return "Open Diagnostics for technical details."


def hidden_process_flags() -> dict[str, Any]:
    if platform.system() != "Windows":
        return {}
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return {"startupinfo": startup, "creationflags": subprocess.CREATE_NO_WINDOW}


class AgentDesktop:
    def __init__(self, root: Tk, *, startup_checks: bool = True) -> None:
        self.root = root
        self.root.title("DiffusionGemma Agent")
        self.root.geometry("960x720")
        self.root.minsize(820, 620)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.active_process: subprocess.Popen[str] | None = None
        self.busy = False
        self.active_label = ""
        self.preflight_ok = False
        self.runtime_installed = False
        self.service_ready = False
        self.last_diff = ""
        self.active_task_mode = ""
        self.setup_options_visible = False
        self.task_options_visible = False

        self.status_var = StringVar(value="Not checked")
        self.footer_var = StringVar(value="Ready")
        self.setup_status_var = StringVar(value="Checking this computer...")
        self.setup_detail_var = StringVar(value="This takes a few seconds.")
        self.diagnostics_summary_var = StringVar(value="Service status has not been checked.")
        self.cache_var = StringVar(value=str(self.default_cache_path()))
        self.license_var = BooleanVar(value=False)
        self.repo_var = StringVar(value="")
        self.file_var = StringVar(value="")
        self.steps_var = StringVar(value="3")
        self.existing_files_var = StringVar(value="Searching common download and Hugging Face cache folders...")
        self.detected_model_file = ""
        self.detected_runtime_dir = ""

        self._configure_styles()
        self._build_ui()
        self.root.after(100, self._drain_events)
        if startup_checks:
            self.root.after(350, self.run_preflight)

    @staticmethod
    def default_cache_path() -> Path:
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
        return base / "diffusiongemma-agent" / "runtime"

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("App.TFrame", background=BG)
        style.configure("Surface.TFrame", background=SURFACE)
        style.configure("Header.TLabel", background=BG, foreground=TEXT, font=("Segoe UI Semibold", 19))
        style.configure("Subtitle.TLabel", background=BG, foreground=MUTED, font=("Segoe UI", 10))
        style.configure("Section.TLabel", background=SURFACE, foreground=TEXT, font=("Segoe UI Semibold", 13))
        style.configure("SetupStatus.TLabel", background=SURFACE, foreground=TEXT, font=("Segoe UI Semibold", 16))
        style.configure("Body.TLabel", background=SURFACE, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=SURFACE, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("Status.TLabel", background=BG, foreground=MUTED, font=("Segoe UI Semibold", 9))
        style.configure("Accent.TButton", font=("Segoe UI Semibold", 10), padding=(16, 8))
        style.map(
            "Accent.TButton",
            foreground=[("disabled", MUTED), ("!disabled", TEXT)],
            background=[("!disabled", ACCENT), ("active", ACCENT_ACTIVE)],
        )
        style.configure("Command.TButton", font=("Segoe UI", 9), padding=(11, 6))
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", font=("Segoe UI Semibold", 10), padding=(18, 8))
        style.configure("TEntry", padding=6)

    def _build_ui(self) -> None:
        header = ttk.Frame(self.root, style="App.TFrame", padding=(24, 16, 24, 10))
        header.pack(fill=X)
        header.columnconfigure(0, weight=1)
        title_area = ttk.Frame(header, style="App.TFrame")
        title_area.grid(row=0, column=0, sticky="ew", padx=(0, 16))
        ttk.Label(title_area, text="DiffusionGemma Agent", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            title_area,
            text="Private local coding agent",
            style="Subtitle.TLabel",
            wraplength=600,
            justify=LEFT,
        ).pack(anchor="w", pady=(3, 0))

        service_area = ttk.Frame(header, style="App.TFrame")
        service_area.grid(row=0, column=1, sticky="e")
        self.status_dot = Text(service_area, width=1, height=1, borderwidth=0, background=BG, foreground=MUTED)
        self.status_dot.insert("1.0", "o")
        self.status_dot.configure(state="disabled", font=("Segoe UI", 11))
        self.status_dot.pack(side=LEFT, padx=(0, 5))
        ttk.Label(service_area, textvariable=self.status_var, style="Status.TLabel").pack(side=LEFT)

        ttk.Separator(self.root).pack(fill=X)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=BOTH, expand=True, padx=18, pady=(12, 6))
        self.setup_tab = ttk.Frame(self.notebook, style="Surface.TFrame", padding=26)
        self.agent_tab = ttk.Frame(self.notebook, style="Surface.TFrame", padding=26)
        self.service_tab = ttk.Frame(self.notebook, style="Surface.TFrame", padding=26)
        self.notebook.add(self.setup_tab, text="Setup")
        self.notebook.add(self.agent_tab, text="Agent")
        self.notebook.add(self.service_tab, text="Diagnostics")
        self._build_setup_tab()
        self._build_agent_tab()
        self._build_service_tab()

        footer = ttk.Frame(self.root, style="App.TFrame", padding=(24, 3, 24, 10))
        footer.pack(fill=X)
        ttk.Label(footer, textvariable=self.footer_var, style="Subtitle.TLabel").pack(side=LEFT)

    def _build_setup_tab(self) -> None:
        self.setup_tab.columnconfigure(0, weight=1)
        status_area = ttk.Frame(self.setup_tab, style="Surface.TFrame")
        status_area.grid(row=0, column=0, sticky="ew", pady=(4, 18))
        status_area.columnconfigure(1, weight=1)
        self.setup_marker = Text(status_area, width=2, height=1, borderwidth=0, background=SURFACE, foreground=MUTED)
        self.setup_marker.insert("1.0", "-")
        self.setup_marker.configure(state="disabled", font=("Segoe UI Semibold", 14))
        self.setup_marker.grid(row=0, column=0, rowspan=2, sticky="nw", padx=(0, 8), pady=2)
        ttk.Label(status_area, textvariable=self.setup_status_var, style="SetupStatus.TLabel").grid(row=0, column=1, sticky="w")
        ttk.Label(
            status_area,
            textvariable=self.setup_detail_var,
            style="Body.TLabel",
            wraplength=700,
            justify=LEFT,
        ).grid(row=1, column=1, sticky="ew", pady=(5, 0))

        ttk.Separator(self.setup_tab).grid(row=1, column=0, sticky="ew", pady=(0, 16))
        self.license_row = ttk.Frame(self.setup_tab, style="Surface.TFrame")
        self.license_row.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        ttk.Checkbutton(
            self.license_row,
            text="I accept the model and CUDA runtime licenses.",
            variable=self.license_var,
            command=self._update_install_button,
        ).pack(side=LEFT)
        link = ttk.Label(self.license_row, text="Review", foreground=INFO, background=SURFACE, cursor="hand2")
        link.pack(side=LEFT, padx=8)
        link.bind("<Button-1>", lambda _event: webbrowser.open("https://huggingface.co/aogavrilov/diffusiongemma-agent-iq3-cuda13/tree/main/LICENSES"))

        install_row = ttk.Frame(self.setup_tab, style="Surface.TFrame")
        install_row.grid(row=3, column=0, sticky="ew")
        self.install_button = ttk.Button(
            install_row,
            text="Install agent",
            style="Accent.TButton",
            command=self.setup_primary_action,
            state="disabled",
        )
        self.install_button.pack(side=LEFT)
        self.setup_cancel_button = ttk.Button(install_row, text="Cancel", style="Command.TButton", command=self.cancel_operation)
        self.setup_cancel_button.pack(side=LEFT, padx=8)
        self.setup_cancel_button.pack_forget()
        self.check_button = ttk.Button(install_row, text="Check again", style="Command.TButton", command=self.run_preflight)
        self.check_button.pack(side=LEFT, padx=8)
        self.wsl_button = ttk.Button(install_row, text="Install WSL2", style="Command.TButton", command=self.install_wsl)
        self.wsl_button.pack(side=LEFT)
        self.wsl_button.pack_forget()
        self.setup_progress = ttk.Progressbar(install_row, mode="indeterminate", length=180)
        self.setup_progress.pack(side=RIGHT)
        self.setup_progress.pack_forget()

        self.setup_options_button = ttk.Button(
            self.setup_tab,
            text="Installation options",
            style="Command.TButton",
            command=self.toggle_setup_options,
        )
        self.setup_options_button.grid(row=4, column=0, sticky="w", pady=(18, 0))
        self.setup_options = ttk.Frame(self.setup_tab, style="Surface.TFrame")
        self.setup_options.grid(row=5, column=0, sticky="ew", pady=(10, 0))
        self.setup_options.columnconfigure(1, weight=1)
        ttk.Label(self.setup_options, text="Runtime location", style="Body.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 10))
        ttk.Entry(self.setup_options, textvariable=self.cache_var).grid(row=0, column=1, sticky="ew")
        ttk.Button(self.setup_options, text="Browse", style="Command.TButton", command=self.choose_cache).grid(row=0, column=2, padx=(8, 0))
        ttk.Label(
            self.setup_options,
            textvariable=self.existing_files_var,
            style="Muted.TLabel",
            wraplength=700,
            justify=LEFT,
        ).grid(row=1, column=0, columnspan=3, sticky="ew", pady=(7, 0))
        self.setup_options.grid_remove()

    def _build_agent_tab(self) -> None:
        self.agent_tab.columnconfigure(0, weight=1)
        self.agent_tab.rowconfigure(8, weight=1)
        ttk.Label(self.agent_tab, text="Repository task", style="Section.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 12))

        repo_row = ttk.Frame(self.agent_tab, style="Surface.TFrame")
        repo_row.grid(row=1, column=0, sticky="ew", pady=3)
        repo_row.columnconfigure(1, weight=1)
        ttk.Label(repo_row, text="Repository", style="Body.TLabel", width=11).grid(row=0, column=0, sticky="w")
        ttk.Entry(repo_row, textvariable=self.repo_var).grid(row=0, column=1, sticky="ew")
        ttk.Button(repo_row, text="Browse", style="Command.TButton", command=self.choose_repo).grid(row=0, column=2, padx=(8, 0))

        ttk.Label(self.agent_tab, text="Task", style="Body.TLabel").grid(row=2, column=0, sticky="w", pady=(10, 3))
        self.task_text = Text(self.agent_tab, height=4, wrap="word", font=("Segoe UI", 10), borderwidth=1, relief="solid", padx=8, pady=8)
        self.task_text.grid(row=3, column=0, sticky="ew")

        command_row = ttk.Frame(self.agent_tab, style="Surface.TFrame")
        command_row.grid(row=4, column=0, sticky="ew", pady=(10, 6))
        self.run_button = ttk.Button(command_row, text="Run task", style="Accent.TButton", command=self.run_task)
        self.run_button.pack(side=LEFT)
        self.cancel_button = ttk.Button(command_row, text="Cancel", style="Command.TButton", command=self.cancel_operation, state="disabled")
        self.cancel_button.pack(side=LEFT, padx=8)
        self.cancel_button.pack_forget()
        ttk.Button(command_row, text="Open repository", style="Command.TButton", command=self.open_repo).pack(side=RIGHT)

        self.task_options_button = ttk.Button(
            self.agent_tab,
            text="Task options",
            style="Command.TButton",
            command=self.toggle_task_options,
        )
        self.task_options_button.grid(row=5, column=0, sticky="w", pady=(0, 8))
        self.task_options = ttk.Frame(self.agent_tab, style="Surface.TFrame")
        self.task_options.grid(row=6, column=0, sticky="ew", pady=(0, 8))
        self.task_options.columnconfigure(1, weight=1)
        ttk.Label(self.task_options, text="Focus file", style="Body.TLabel", width=11).grid(row=0, column=0, sticky="w")
        ttk.Entry(self.task_options, textvariable=self.file_var).grid(row=0, column=1, sticky="ew")
        ttk.Label(self.task_options, text="Attempts", style="Body.TLabel").grid(row=0, column=2, sticky="w", padx=(14, 5))
        ttk.Spinbox(self.task_options, from_=1, to=5, width=4, textvariable=self.steps_var).grid(row=0, column=3, sticky="w")
        self.task_options.grid_remove()

        ttk.Separator(self.agent_tab).grid(row=7, column=0, sticky="ew", pady=(0, 8))
        result_tabs = ttk.Notebook(self.agent_tab)
        result_tabs.grid(row=8, column=0, sticky="nsew")
        activity_frame = ttk.Frame(result_tabs, style="Surface.TFrame", padding=3)
        diff_frame = ttk.Frame(result_tabs, style="Surface.TFrame", padding=3)
        result_tabs.add(activity_frame, text="Activity")
        result_tabs.add(diff_frame, text="Changes")
        self.activity_output = ScrolledText(activity_frame, wrap="word", font=("Consolas", 9), borderwidth=0)
        self.activity_output.pack(fill=BOTH, expand=True)
        self.activity_output.insert(END, "The task activity will appear here.\n")
        self.activity_output.configure(state="disabled")
        diff_toolbar = ttk.Frame(diff_frame, style="Surface.TFrame")
        diff_toolbar.pack(fill=X, pady=(0, 4))
        ttk.Label(diff_toolbar, text="Review changes before committing them.", style="Muted.TLabel").pack(side=LEFT)
        ttk.Button(diff_toolbar, text="Copy diff", style="Command.TButton", command=self.copy_diff).pack(side=RIGHT)
        self.diff_output = ScrolledText(diff_frame, wrap="none", font=("Consolas", 9), borderwidth=0)
        self.diff_output.pack(fill=BOTH, expand=True)
        self.diff_output.configure(state="disabled")

    def _build_service_tab(self) -> None:
        self.service_tab.columnconfigure(0, weight=1)
        self.service_tab.rowconfigure(4, weight=1)
        ttk.Label(self.service_tab, text="Diagnostics", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            self.service_tab,
            textvariable=self.diagnostics_summary_var,
            style="Body.TLabel",
            wraplength=760,
            justify=LEFT,
        ).grid(row=1, column=0, sticky="ew", pady=(5, 12))
        controls = ttk.Frame(self.service_tab, style="Surface.TFrame")
        controls.grid(row=2, column=0, sticky="w", pady=(0, 12))
        self.service_toggle_button = ttk.Button(controls, text="Start service", style="Accent.TButton", command=self.toggle_service)
        self.service_toggle_button.pack(side=LEFT)
        ttk.Button(controls, text="Refresh", style="Command.TButton", command=self.refresh_service).pack(side=LEFT, padx=8)
        ttk.Button(controls, text="Load logs", style="Command.TButton", command=self.load_logs).pack(side=LEFT)
        ttk.Separator(self.service_tab).grid(row=3, column=0, sticky="ew", pady=(0, 8))
        self.service_output = ScrolledText(self.service_tab, wrap="word", font=("Consolas", 9), borderwidth=0)
        self.service_output.grid(row=4, column=0, sticky="nsew")
        self.service_output.insert(END, "Technical details will appear here.\n")
        self.service_output.configure(state="disabled")
        ttk.Label(
            self.service_tab,
            text=f"Desktop {APP_VERSION} | Core {core_version}",
            style="Muted.TLabel",
        ).grid(row=5, column=0, sticky="e", pady=(8, 0))

    def _replace_output(self, widget: ScrolledText, text: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", END)
        widget.insert(END, text)
        widget.see(END)
        widget.configure(state="disabled")

    def _append_output(self, widget: ScrolledText, text: str) -> None:
        widget.configure(state="normal")
        widget.insert(END, text)
        widget.see(END)
        widget.configure(state="disabled")

    def _set_marker(self, marker: Text, text: str, color: str) -> None:
        marker.configure(state="normal", foreground=color)
        marker.delete("1.0", END)
        marker.insert("1.0", text)
        marker.configure(state="disabled")

    def _update_install_button(self) -> None:
        ready = self.runtime_installed or (self.preflight_ok and self.license_var.get())
        state = "normal" if ready and not self._is_busy() else "disabled"
        self.install_button.configure(state=state)

    def _is_busy(self) -> bool:
        return self.busy

    def _set_busy(self, busy: bool, label: str = "") -> None:
        self.busy = busy
        self.footer_var.set(label if busy else "Ready")
        self.check_button.configure(state="disabled" if busy else "normal")
        self.run_button.configure(state="disabled" if busy else "normal")
        self.service_toggle_button.configure(state="disabled" if busy else "normal")
        setup_operation = busy and any(word in label.lower() for word in ("checking", "installing", "downloading", "reusing"))
        task_operation = busy and any(
            phrase in label.lower() for phrase in ("repository task", "repository question", "code change")
        )
        if setup_operation:
            self.setup_cancel_button.pack(side=LEFT, padx=8, after=self.install_button)
            self.check_button.pack_forget()
        else:
            self.setup_cancel_button.pack_forget()
            if not self.check_button.winfo_manager():
                self.check_button.pack(side=LEFT, padx=8, after=self.install_button)
        if task_operation:
            self.cancel_button.configure(state="normal")
            self.cancel_button.pack(side=LEFT, padx=8, after=self.run_button)
        else:
            self.cancel_button.pack_forget()
        if setup_operation:
            if not self.setup_progress.winfo_manager():
                self.setup_progress.pack(side=RIGHT)
            self.setup_progress.start(10)
        else:
            self.setup_progress.stop()
            self.setup_progress.pack_forget()
        self._update_install_button()

    def toggle_setup_options(self) -> None:
        self.setup_options_visible = not self.setup_options_visible
        if self.setup_options_visible:
            self.setup_options.grid()
            self.setup_options_button.configure(text="Hide installation options")
        else:
            self.setup_options.grid_remove()
            self.setup_options_button.configure(text="Installation options")

    def toggle_task_options(self) -> None:
        self.task_options_visible = not self.task_options_visible
        if self.task_options_visible:
            self.task_options.grid()
            self.task_options_button.configure(text="Hide task options")
        else:
            self.task_options.grid_remove()
            self.task_options_button.configure(text="Task options")

    def setup_primary_action(self) -> None:
        if self.runtime_installed:
            self.notebook.select(self.agent_tab)
            return
        self.install_runtime()

    def _start_command(
        self,
        arguments: list[str],
        *,
        label: str,
        output: ScrolledText,
        on_complete: Callable[[int, str], None] | None = None,
        replace_output: bool = True,
    ) -> None:
        if self._is_busy():
            messagebox.showinfo("Operation in progress", f"Wait for '{self.active_label}' to finish or cancel it.")
            return
        if replace_output:
            self._replace_output(output, f"{label}...\n")
        self.active_label = label
        self._set_busy(True, label)

        def worker() -> None:
            lines: list[str] = []
            try:
                command = cli_command(*arguments)
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    **hidden_process_flags(),
                )
                self.active_process = process
                assert process.stdout is not None
                for line in process.stdout:
                    lines.append(line)
                    self.events.put(("line", (output, line)))
                code = process.wait()
            except OSError as exc:
                code = 2
                line = f"Could not start the operation: {exc}\n"
                lines.append(line)
                self.events.put(("line", (output, line)))
            self.events.put(("done", (code, "".join(lines), on_complete)))

        threading.Thread(target=worker, daemon=True).start()

    def _drain_events(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "line":
                    widget, line = payload
                    self._append_output(widget, line)
                elif kind == "done":
                    code, output, callback = payload
                    self.active_process = None
                    self.active_label = ""
                    self._set_busy(False)
                    if callback:
                        callback(code, output)
        except queue.Empty:
            pass
        self.root.after(100, self._drain_events)

    def run_preflight(self) -> None:
        self.setup_status_var.set("Checking...")
        self.setup_detail_var.set("Checking Windows, WSL2, GPU and available files.")
        self._set_marker(self.setup_marker, "-", MUTED)
        self._start_command(
            ["doctor", "--json"],
            label="Checking computer",
            output=self.service_output,
            on_complete=self._preflight_finished,
        )

    def _preflight_finished(self, _code: int, output: str) -> None:
        try:
            payload = json.loads(output)
            rows, compatible = summarize_doctor(payload)
        except (TypeError, ValueError, json.JSONDecodeError):
            self.preflight_ok = False
            self.runtime_installed = False
            self.setup_status_var.set("The computer check failed")
            self.setup_detail_var.set(concise_error(output))
            self._set_marker(self.setup_marker, "X", DANGER)
            self._update_install_button()
            return
        self.preflight_ok = compatible
        self.runtime_installed = bool(next((row["ok"] for row in rows if row["name"] == "installed"), False))
        title, detail_text = setup_summary(rows)
        self.setup_status_var.set(title)
        self.setup_detail_var.set(detail_text)
        self._set_marker(self.setup_marker, "OK" if compatible else "X", ACCENT if compatible else DANGER)
        local_weights: dict[str, Any] = {}
        for row in rows:
            if row["name"] == "local_weights":
                checks = payload.get("checks") if isinstance(payload.get("checks"), dict) else {}
                raw_local = checks.get("local_weights") if isinstance(checks.get("local_weights"), dict) else {}
                local_weights = raw_local
        if local_weights.get("ok"):
            self.detected_model_file = str(local_weights.get("model_file") or "")
            detected_runtime = str(local_weights.get("runtime_dir") or "")
            self.detected_runtime_dir = detected_runtime
            if detected_runtime:
                self.cache_var.set(detected_runtime)
                self.existing_files_var.set(f"Complete compatible runtime found: {detected_runtime}")
            else:
                self.existing_files_var.set(f"Compatible model found: {self.detected_model_file}")
        else:
            self.detected_model_file = ""
            self.detected_runtime_dir = ""
            self.existing_files_var.set("No compatible local files found; the runtime will be downloaded.")
        self.install_button.configure(text="Open Agent" if self.runtime_installed else "Install agent")
        if self.runtime_installed:
            self.license_row.grid_remove()
            self.setup_options_button.grid_remove()
            self.setup_options.grid_remove()
            self.check_button.pack_forget()
            self.notebook.select(self.agent_tab)
        else:
            self.license_row.grid()
            self.setup_options_button.grid()
            if not self.check_button.winfo_manager():
                self.check_button.pack(side=LEFT, padx=8, after=self.install_button)
        wsl_failed = any(row["name"] == "wsl" and row["required"] and not row["ok"] for row in rows)
        if wsl_failed:
            self.wsl_button.pack(side=LEFT)
        else:
            self.wsl_button.pack_forget()
        self._update_install_button()
        self.root.after(150, self.refresh_service)

    def install_wsl(self) -> None:
        if platform.system() != "Windows":
            messagebox.showerror("Windows required", "This installer currently supports Windows 10/11 only.")
            return
        result = ctypes.windll.shell32.ShellExecuteW(None, "runas", "wsl.exe", "--install -d Ubuntu", None, 1)
        if result <= 32:
            messagebox.showerror("WSL2 installation", "Windows could not start the elevated WSL2 installer.")
            return
        messagebox.showinfo(
            "WSL2 installation started",
            "Approve the Windows prompt. Restart the computer if requested, open this app again, then click 'Check again'.",
        )

    def choose_cache(self) -> None:
        selected = filedialog.askdirectory(title="Choose the runtime download folder", initialdir=str(self.cache_var.get()))
        if selected:
            self.cache_var.set(selected)

    def install_runtime(self) -> None:
        if not self.license_var.get():
            messagebox.showwarning("Licenses", "Review and accept the model and CUDA runtime licenses first.")
            return
        if not self.preflight_ok:
            messagebox.showwarning("Compatibility", "Run the computer check and resolve all failed requirements first.")
            return
        if self.detected_runtime_dir:
            operation_label = "Installing the local agent from existing files"
        elif self.detected_model_file:
            operation_label = "Reusing the existing model and installing the local agent"
        else:
            operation_label = "Downloading and installing the local agent"
        arguments = ["install", "--accept-licenses", "--local-dir", self.cache_var.get()]
        if self.detected_model_file:
            arguments.extend(["--model-file", self.detected_model_file])
        self._start_command(
            arguments,
            label=operation_label,
            output=self.service_output,
            on_complete=self._install_finished,
        )

    def _install_finished(self, code: int, output: str) -> None:
        if code == 0:
            self.preflight_ok = True
            self.runtime_installed = True
            self.setup_status_var.set("The agent is installed")
            self.setup_detail_var.set("Choose a repository and describe the task you want to run.")
            self._set_marker(self.setup_marker, "OK", ACCENT)
            self.install_button.configure(text="Open Agent")
            self.license_row.grid_remove()
            self.setup_options_button.grid_remove()
            self.setup_options.grid_remove()
            self.notebook.select(self.agent_tab)
            self.refresh_service()
        else:
            error = concise_error(output)
            self.setup_status_var.set("Installation failed")
            self.setup_detail_var.set(error)
            self._set_marker(self.setup_marker, "X", DANGER)
            messagebox.showerror("Installation failed", f"{error}\n\nTechnical details are available in Diagnostics.")
            self.notebook.select(self.service_tab)

    def choose_repo(self) -> None:
        initial = self.repo_var.get() or str(Path.home())
        selected = filedialog.askdirectory(title="Choose a Git repository", initialdir=initial)
        if selected:
            self.repo_var.set(selected)

    def run_task(self) -> None:
        task = self.task_text.get("1.0", END).strip()
        mode = infer_task_mode(task)
        repo, error = validate_task(self.repo_var.get(), task, mode)
        if error:
            messagebox.showwarning("Task is incomplete", error)
            return
        assert repo is not None
        try:
            steps = int(self.steps_var.get())
        except ValueError:
            steps = 3
        steps = max(1, min(5, steps))
        arguments = ["run", "--repo", str(repo), "--task", task, "--max-steps", str(steps), "--mode", mode]
        if self.file_var.get().strip():
            arguments.extend(["--file", self.file_var.get().strip()])
        self.active_task_mode = mode
        if mode == "read":
            label = "Answering repository question"
            self._replace_output(self.diff_output, "Read-only task: no files will be changed.\n")
        else:
            label = "Running checkpointed code change"
            self._replace_output(self.diff_output, "The repository diff will appear after the task.\n")
        self._start_command(
            arguments,
            label=label,
            output=self.activity_output,
            on_complete=lambda code, output: self._task_finished(code, output, repo),
        )

    def _task_finished(self, code: int, output: str, repo: Path) -> None:
        if code == 0:
            if self.active_task_mode == "read":
                self._append_output(
                    self.activity_output,
                    "\n---\nRoute: repository question (read-only)\n"
                    "Action: inspect relevant repository files with local tools\n"
                    "Repository question completed.\n",
                )
                self.footer_var.set("Repository answer completed.")
            else:
                self._append_output(self.activity_output, "\nCode change completed. Review the Changes tab.\n")
                self.footer_var.set("Task completed. Review the changes before committing.")
        else:
            detail = concise_error(output)
            self._append_output(self.activity_output, f"\nTask stopped: {detail}\n")
            self.footer_var.set("Task stopped. Review Activity for the reason.")
        if self.active_task_mode == "edit":
            self._load_diff(repo)

    def _load_diff(self, repo: Path) -> None:
        def worker() -> None:
            process = subprocess.run(
                ["git", "-C", str(repo), "diff", "--no-ext-diff", "--"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                **hidden_process_flags(),
            )
            value = process.stdout or "No uncommitted tracked-file changes were found.\n"
            self.root.after(0, lambda: self._show_diff(value))

        threading.Thread(target=worker, daemon=True).start()

    def _show_diff(self, value: str) -> None:
        self.last_diff = value
        self._replace_output(self.diff_output, value)

    def copy_diff(self) -> None:
        if not self.last_diff:
            messagebox.showinfo("Changes", "No diff is available yet.")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.last_diff)
        self.footer_var.set("Diff copied to the clipboard.")

    def open_repo(self) -> None:
        repo = Path(self.repo_var.get())
        if not repo.is_dir():
            messagebox.showwarning("Repository", "Choose an existing repository folder first.")
            return
        os.startfile(repo)  # type: ignore[attr-defined]

    def refresh_service(self) -> None:
        self._start_command(
            ["status", "--json"],
            label="Refreshing service status",
            output=self.service_output,
            on_complete=self._status_finished,
        )

    def _status_finished(self, _code: int, output: str) -> None:
        try:
            payload = json.loads(output)
        except (TypeError, ValueError, json.JSONDecodeError):
            self.service_ready = False
            self.status_var.set("Unavailable")
            self._set_status_dot(MUTED)
            self.diagnostics_summary_var.set("The service status could not be read. Load the logs for technical details.")
            self.service_toggle_button.configure(text="Start service", state="disabled")
            return
        installed = bool(payload.get("installed"))
        backend = bool((payload.get("backend") or {}).get("ok"))
        gateway = bool((payload.get("gateway") or {}).get("ok"))
        self.service_ready = installed and backend and gateway
        if self.service_ready:
            self.status_var.set("Ready")
            self._set_status_dot(ACCENT)
            self.diagnostics_summary_var.set("The model and agent services are running.")
            self.service_toggle_button.configure(text="Stop service", state="normal")
        elif installed:
            self.status_var.set("Stopped")
            self._set_status_dot(MUTED)
            self.diagnostics_summary_var.set("The agent is installed. Start the service when you need it.")
            self.service_toggle_button.configure(text="Start service", state="normal")
        else:
            self.status_var.set("Setup required")
            self._set_status_dot(DANGER)
            self.diagnostics_summary_var.set("Install the agent from Setup before starting the service.")
            self.service_toggle_button.configure(text="Start service", state="disabled")

    def _set_status_dot(self, color: str) -> None:
        self.status_dot.configure(state="normal", foreground=color)
        self.status_dot.delete("1.0", END)
        self.status_dot.insert("1.0", "o")
        self.status_dot.configure(state="disabled")

    def start_service(self) -> None:
        self._start_command(
            ["start"],
            label="Starting the model and agent services",
            output=self.service_output,
            on_complete=lambda code, _output: self._service_action_finished(code, "started"),
        )

    def stop_service(self) -> None:
        self._start_command(
            ["stop"],
            label="Stopping services and releasing GPU memory",
            output=self.service_output,
            on_complete=lambda code, _output: self._service_action_finished(code, "stopped"),
        )

    def toggle_service(self) -> None:
        if self.service_ready:
            self.stop_service()
        else:
            self.start_service()

    def _service_action_finished(self, code: int, action: str) -> None:
        if code == 0:
            self.footer_var.set(f"Services {action}.")
        else:
            self.footer_var.set(f"Services could not be {action}. Review the logs.")
        self.root.after(200, self.refresh_service)

    def load_logs(self) -> None:
        self._start_command(["logs", "--lines", "160"], label="Loading service logs", output=self.service_output)

    def cancel_operation(self) -> None:
        if not self._is_busy() or self.active_process is None:
            messagebox.showinfo("Operation", "There is no active operation to cancel.")
            return
        detail = "Cancel the current operation?"
        if any(word in self.active_label.lower() for word in ("installing", "downloading", "reusing")):
            detail += " Partial downloads remain resumable."
        if not messagebox.askyesno("Cancel operation", detail):
            return
        self.active_process.terminate()
        self.footer_var.set("Cancelling the current operation...")

    def close(self) -> None:
        if self._is_busy() and not messagebox.askyesno("Operation in progress", "An operation is still running. Close the window anyway?"):
            return
        self.root.destroy()


def smoke_test() -> int:
    root = Tk()
    root.withdraw()
    app = AgentDesktop(root, startup_checks=False)
    root.update_idletasks()
    report = {
        "app_version": APP_VERSION,
        "core_version": core_version,
        "tabs": [app.notebook.tab(index, "text") for index in range(app.notebook.index("end"))],
        "geometry": root.geometry(),
        "setup_raw_output_visible": hasattr(app, "setup_output"),
        "setup_options_visible": bool(app.setup_options.winfo_manager()),
        "task_options_visible": bool(app.task_options.winfo_manager()),
        "setup_progress_visible": bool(app.setup_progress.winfo_manager()),
        "cli": cli_command("--version"),
    }
    print(json.dumps(report, indent=2))
    root.destroy()
    return 0


def main() -> int:
    executable = Path(sys.executable).name.lower()
    arguments = sys.argv[1:]
    if executable.startswith("dg-agent-core") or (arguments and arguments[0] == "--cli"):
        if arguments and arguments[0] == "--cli":
            arguments = arguments[1:]
        from diffusiongemma_agent.cli import main as cli_main

        return cli_main(arguments)
    if arguments == ["--smoke-test"]:
        return smoke_test()
    root = Tk()
    AgentDesktop(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
