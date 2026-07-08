"""
Updater helper for Casapro Nexus.

This executable is built with an administrator manifest. The main app launches it,
then exits so the Inno Setup installer can replace files in Program Files.
"""
import argparse
import ctypes
import logging
import os
import re
import queue
import shutil
import subprocess
import sys
import threading
import time
import zipfile


INSTALLER_FLAGS = [
    "/VERYSILENT",
    "/SUPPRESSMSGBOXES",
    "/FORCECLOSEAPPLICATIONS",
]


def configure_logging(log_file: str) -> logging.Logger:
    os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)

    logger = logging.getLogger("nexus_updater")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    handler = logging.FileHandler(log_file, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    return logger


def wait_for_parent(pid: int, logger: logging.Logger, timeout_seconds: int = 120) -> None:
    if not pid:
        return

    logger.info("Waiting for parent process PID %s", pid)

    if os.name != "nt":
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            try:
                os.kill(pid, 0)
            except OSError:
                logger.info("Parent process exited")
                return
            time.sleep(1)
        logger.warning("Timed out waiting for parent PID %s", pid)
        return

    synchronize = 0x00100000
    wait_timeout = 0x00000102
    wait_object_0 = 0x00000000

    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(synchronize, False, pid)
    if not handle:
        logger.info("Parent process is no longer available")
        return

    try:
        result = kernel32.WaitForSingleObject(handle, timeout_seconds * 1000)
        if result == wait_object_0:
            logger.info("Parent process exited")
        elif result == wait_timeout:
            logger.warning("Timed out waiting for parent PID %s", pid)
        else:
            logger.warning("Unexpected wait result %s for parent PID %s", result, pid)
    finally:
        kernel32.CloseHandle(handle)


def _safe_extract(zip_ref: zipfile.ZipFile, extract_dir: str) -> None:
    extract_root = os.path.abspath(extract_dir)

    for member in zip_ref.infolist():
        target_path = os.path.abspath(os.path.join(extract_root, member.filename))
        if os.path.commonpath([extract_root, target_path]) != extract_root:
            raise ValueError(f"Unsafe path in ZIP: {member.filename}")

    zip_ref.extractall(extract_root)


def _version_key(path: str) -> tuple:
    match = re.search(r"(\d+(?:\.\d+)+)", os.path.basename(path))
    if not match:
        return (0,)
    return tuple(int(part) for part in match.group(1).split("."))


def find_installer(update_file: str, logger: logging.Logger) -> str:
    update_file = os.path.abspath(update_file)
    if not os.path.exists(update_file):
        raise FileNotFoundError(update_file)

    if not update_file.lower().endswith(".zip"):
        logger.info("Update file is an installer: %s", update_file)
        return update_file

    extract_dir = os.path.join(os.path.dirname(update_file), "extracted")
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)
    os.makedirs(extract_dir, exist_ok=True)

    logger.info("Extracting update ZIP to %s", extract_dir)
    with zipfile.ZipFile(update_file, "r") as zip_ref:
        _safe_extract(zip_ref, extract_dir)

    installer_files = []
    for root, _dirs, files in os.walk(extract_dir):
        for filename in files:
            lower_name = filename.lower()
            if lower_name.endswith(".exe") and (
                "setup" in lower_name or "install" in lower_name or "nexus" in lower_name
            ):
                installer_files.append(os.path.join(root, filename))

    if not installer_files:
        raise FileNotFoundError("No installer .exe found in update ZIP")

    installer_files.sort(key=_version_key)
    installer_path = os.path.abspath(installer_files[-1])
    logger.info("Selected installer: %s", installer_path)
    return installer_path


def run_installer(installer_path: str, logger: logging.Logger) -> None:
    command = [installer_path, *INSTALLER_FLAGS]
    logger.info("Running installer: %s", command)
    subprocess.run(command, check=True)
    logger.info("Installer finished successfully")


def restart_app(app_exe: str, logger: logging.Logger) -> None:
    if not app_exe:
        logger.info("No app executable provided; skipping restart")
        return

    app_exe = os.path.abspath(app_exe)
    if not os.path.exists(app_exe):
        logger.warning("App executable not found; skipping restart: %s", app_exe)
        return

    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP

    logger.info("Restarting app: %s", app_exe)
    subprocess.Popen(
        [app_exe],
        cwd=os.path.dirname(app_exe),
        creationflags=creationflags,
        close_fds=True,
    )


class ProgressWindow:
    def __init__(self) -> None:
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.ttk = ttk
        self.queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.done = threading.Event()
        self.exit_code = 1

        self.root = tk.Tk()
        self.root.title("Actualizando Casapro Nexus")
        self.root.resizable(False, False)
        self.root.geometry("420x150")
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)

        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill="both", expand=True)

        self.title_label = ttk.Label(
            frame,
            text="Actualizando Casapro Nexus",
            font=("Segoe UI", 11, "bold"),
        )
        self.title_label.pack(anchor="w")

        self.status_label = ttk.Label(frame, text="Preparando actualizacion...")
        self.status_label.pack(anchor="w", pady=(10, 8))

        self.progress = ttk.Progressbar(
            frame,
            orient="horizontal",
            length=370,
            mode="determinate",
            maximum=100,
        )
        self.progress.pack(fill="x")

        self.detail_label = ttk.Label(frame, text="No cierres esta ventana.")
        self.detail_label.pack(anchor="w", pady=(8, 0))

        self._center()

    def _center(self) -> None:
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def set_status(self, message: str, percent: int) -> None:
        self.queue.put(("status", (message, percent)))

    def complete(self, exit_code: int, message: str) -> None:
        self.queue.put(("complete", (exit_code, message)))

    def _poll(self) -> None:
        while True:
            try:
                event, payload = self.queue.get_nowait()
            except queue.Empty:
                break

            if event == "status":
                message, percent = payload
                self.status_label.config(text=str(message))
                self.progress["value"] = int(percent)
            elif event == "complete":
                exit_code, message = payload
                self.exit_code = int(exit_code)
                self.status_label.config(text=str(message))
                self.progress["value"] = 100 if self.exit_code == 0 else self.progress["value"]
                if self.exit_code == 0:
                    self.detail_label.config(text="Casapro Nexus se abrira automaticamente.")
                    self.root.after(1800, self.root.destroy)
                else:
                    self.detail_label.config(text="Revisa nexus_updater.log o contacta a soporte.")
                    self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)
                self.done.set()

        if not self.done.is_set():
            self.root.after(150, self._poll)

    def run(self) -> int:
        self.root.after(150, self._poll)
        self.root.mainloop()
        return self.exit_code


def perform_update(args: argparse.Namespace, logger: logging.Logger, progress: ProgressWindow | None = None) -> int:
    try:
        logger.info("nexus_updater started")
        logger.info("Update file: %s", args.update_file)
        logger.info("App exe: %s", args.app_exe)

        if progress:
            progress.set_status("Cerrando Casapro Nexus...", 10)
        wait_for_parent(args.parent_pid, logger)

        if progress:
            progress.set_status("Preparando instalador...", 25)
        installer_path = find_installer(args.update_file, logger)

        if progress:
            progress.set_status("Instalando actualizacion...", 45)
        run_installer(installer_path, logger)

        if progress:
            progress.set_status("Reiniciando Casapro Nexus...", 90)
        restart_app(args.app_exe, logger)

        logger.info("nexus_updater completed")
        if progress:
            progress.complete(0, "Actualizacion completada.")
        return 0
    except Exception:
        logger.exception("nexus_updater failed")
        if progress:
            progress.complete(1, "No se pudo completar la actualizacion.")
        return 1


def run_with_progress(args: argparse.Namespace, logger: logging.Logger) -> int:
    try:
        progress = ProgressWindow()
    except Exception:
        logger.exception("Could not create updater progress window; continuing headless")
        return perform_update(args, logger, None)

    worker = threading.Thread(target=perform_update, args=(args, logger, progress), daemon=True)
    worker.start()
    return progress.run()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Casapro Nexus update helper")
    parser.add_argument("--update-file", required=True, help="Downloaded update ZIP or installer")
    parser.add_argument("--app-exe", required=True, help="Main app executable to restart")
    parser.add_argument("--parent-pid", type=int, default=0, help="Main app process ID")
    parser.add_argument("--log-file", required=True, help="Updater log file")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    logger = configure_logging(args.log_file)
    return run_with_progress(args, logger)


if __name__ == "__main__":
    raise SystemExit(main())
