"""Native local launcher for HackerGPT Local.

The script is intentionally stdlib-only and resolves paths relative to itself so it
can be called from any current working directory.
"""

from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.error import URLError
from urllib.request import urlopen

Status = Literal["PASS", "WARN", "FAIL"]

ROOT = Path(__file__).resolve().parents[1]
PID_FILE = ROOT / "data" / "runtime" / "hackergpt.pid"
LOG_FILE = ROOT / "data" / "logs" / "hackergpt.log"
DEFAULT_URL = "http://127.0.0.1:8000/api/v1/health"


@dataclass(frozen=True)
class Check:
    status: Status
    name: str
    detail: str

    def line(self) -> str:
        return f"{self.status:<4} {self.name}: {self.detail}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HackerGPT Local native launcher")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    sub.add_parser("status")
    start = sub.add_parser("start")
    start.add_argument("--host", default=os.getenv("HACKERGPT_API_HOST", "127.0.0.1"))
    start.add_argument("--port", type=int, default=int(os.getenv("HACKERGPT_API_PORT", "8000")))
    start.add_argument("--no-browser", action="store_true")
    start.add_argument(
        "--backup-before-migration",
        action="store_true",
        default=os.getenv("HACKERGPT_BACKUP_BEFORE_MIGRATION", "false").lower()
        in {"1", "true", "yes"},
    )
    stop = sub.add_parser("stop")
    stop.add_argument("--timeout", type=float, default=8.0)
    backup = sub.add_parser("backup")
    backup.add_argument("target", nargs="?", default=None)
    restore = sub.add_parser("restore")
    restore.add_argument("archive")
    args = parser.parse_args(argv)
    if args.command == "doctor":
        return doctor()
    if args.command == "status":
        return status()
    if args.command == "start":
        return start_server(
            args.host,
            args.port,
            open_browser=not args.no_browser,
            backup_before_migration=args.backup_before_migration,
        )
    if args.command == "stop":
        return stop_server(args.timeout)
    if args.command == "backup":
        return backup_data(args.target)
    if args.command == "restore":
        return restore_data(args.archive)
    return 2


def doctor() -> int:
    checks = [
        check_python(),
        check_command("git", ["git", "--version"]),
        check_command("node", ["node", "--version"]),
        check_command("npm", ["npm.cmd", "--version"] if os.name == "nt" else ["npm", "--version"]),
        check_command("docker", ["docker", "--version"], warn_when_missing=True),
        check_writable(ROOT / "data"),
        check_writable(ROOT / "data" / "databases"),
        check_port("127.0.0.1", 8000),
        check_ollama(),
        check_frontend_build(),
        check_migrations(),
    ]
    for check in checks:
        print(check.line())
    return 1 if any(check.status == "FAIL" for check in checks) else 0


def status() -> int:
    health = probe_http(DEFAULT_URL, timeout=2)
    pid = read_pid()
    print(f"Repository: {ROOT}")
    print(f"PID file: {pid if pid else 'none'}")
    print(f"Backend health: {health.detail}")
    return 0 if health.status == "PASS" else 1


def start_server(
    host: str,
    port: int,
    *,
    open_browser: bool,
    backup_before_migration: bool = False,
) -> int:
    if port < 1 or port > 65535:
        print("FAIL invalid port")
        return 2
    if is_port_open(host, port):
        print(f"FAIL port {host}:{port} is already in use")
        print(port_owner_hint(port))
        return 1
    ensure_dirs()
    if backup_before_migration:
        backup_target = ROOT / "data" / "backups" / timestamped_backup("pre-migration")
        backup_result = backup_data(str(backup_target))
        if backup_result != 0:
            print("FAIL pre-migration backup did not complete")
            return backup_result
    migration = run([sys.executable, "-m", "alembic", "upgrade", "head"], timeout=30)
    if migration.returncode != 0:
        print("FAIL migrations did not complete")
        print(migration.stderr.strip() or migration.stdout.strip())
        return migration.returncode
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.api.app:create_app",
        "--factory",
        "--host",
        host,
        "--port",
        str(port),
    ]
    with LOG_FILE.open("a", encoding="utf-8") as log:
        process = subprocess.Popen(  # noqa: S603
            command,
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
        )
    PID_FILE.write_text(str(process.pid), encoding="utf-8")
    url = f"http://{host}:{port}/api/v1/health"
    for _ in range(40):
        if probe_http(url, timeout=0.5).status == "PASS":
            print("System ready")
            print(f"UI: http://{host}:{port}/")
            if open_browser:
                open_url(f"http://{host}:{port}/")
            return 0
        if process.poll() is not None:
            print("FAIL backend exited during startup")
            return process.returncode or 1
        time.sleep(0.25)
    print("FAIL startup timed out")
    return 1


def stop_server(timeout: float) -> int:
    pid = read_pid()
    if pid is None:
        print("WARN no launcher-owned process is recorded")
        return 0
    try:
        process = subprocess.Popen(  # noqa: S603
            ["taskkill", "/PID", str(pid), "/T"] if os.name == "nt" else ["kill", str(pid)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        process.communicate(timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        print("FAIL could not stop launcher-owned process cleanly")
        return 1
    PID_FILE.unlink(missing_ok=True)
    print("Stopped HackerGPT Local")
    return 0


def backup_data(target: str | None) -> int:
    ensure_dirs()
    destination = Path(target) if target else ROOT / "data" / "backups" / timestamped_backup()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for folder in (ROOT / "data" / "databases", ROOT / "data" / "knowledge", ROOT / "config"):
            if not folder.exists():
                continue
            for path in folder.rglob("*"):
                if path.is_file():
                    archive.write(path, path.relative_to(ROOT))
    print(f"PASS backup written: {destination}")
    return 0


def restore_data(archive_path: str) -> int:
    archive = Path(archive_path).resolve(strict=True)
    allowed_prefixes = ("data/databases/", "data/knowledge/", "config/")
    with zipfile.ZipFile(archive) as zipped:
        for item in zipped.namelist():
            normalized = item.replace("\\", "/")
            if not normalized.startswith(allowed_prefixes):
                print(f"FAIL archive contains unsupported path: {item}")
                return 1
        zipped.extractall(ROOT)
    print("PASS restore completed")
    return 0


def check_python() -> Check:
    version = sys.version_info
    if version.major == 3 and version.minor >= 12:
        return Check("PASS", "python", sys.version.split()[0])
    return Check("FAIL", "python", "Python 3.12+ is required")


def check_command(name: str, command: list[str], *, warn_when_missing: bool = False) -> Check:
    if shutil.which(command[0]) is None:
        return Check("WARN" if warn_when_missing else "FAIL", name, "not found")
    result = run(command, timeout=5)
    if result.returncode != 0:
        return Check("WARN" if warn_when_missing else "FAIL", name, "command failed")
    return Check("PASS", name, (result.stdout or result.stderr).strip().splitlines()[0])


def check_writable(path: Path) -> Check:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return Check("PASS", f"writable {path.relative_to(ROOT)}", "ok")
    except OSError as exc:
        return Check("FAIL", f"writable {path}", str(exc))


def check_port(host: str, port: int) -> Check:
    if is_port_open(host, port):
        return Check("WARN", f"port {port}", f"in use; {port_owner_hint(port)}")
    return Check("PASS", f"port {port}", "available")


def check_ollama() -> Check:
    return probe_http("http://127.0.0.1:11434/api/version", timeout=2, name="ollama")


def check_frontend_build() -> Check:
    index = ROOT / "frontend" / "dist" / "index.html"
    if index.is_file():
        return Check("PASS", "frontend build", "available")
    return Check("WARN", "frontend build", "run cd frontend && npm.cmd run build")


def check_migrations() -> Check:
    result = run([sys.executable, "-m", "alembic", "current"], timeout=15)
    if result.returncode != 0:
        return Check("FAIL", "migrations", result.stderr.strip() or "alembic failed")
    lines = (result.stdout.strip() or result.stderr.strip() or "head").splitlines()
    return Check("PASS", "migrations", lines[0] if lines else "ok")


def probe_http(url: str, *, timeout: float, name: str = "http") -> Check:
    try:
        with urlopen(url, timeout=timeout) as response:  # noqa: S310
            code = getattr(response, "status", 200)
        if 200 <= code < 400:
            return Check("PASS", name, f"HTTP {code}")
        return Check("WARN", name, f"HTTP {code}")
    except (OSError, URLError) as exc:
        return Check("WARN", name, str(exc))


def is_port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.4)
        return sock.connect_ex((host, port)) == 0


def port_owner_hint(port: int) -> str:
    if os.name != "nt":
        return f"inspect with: lsof -i :{port}"
    command = ["netstat", "-ano", "-p", "tcp"]
    result = run(command, timeout=5)
    for line in result.stdout.splitlines():
        if f":{port} " in line and "LISTENING" in line:
            pid = line.split()[-1]
            return f"owning PID appears to be {pid}; inspect with Task Manager"
    return "owning PID unavailable"


def run(command: list[str], *, timeout: float) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(  # noqa: S603
            command,
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(command, 1, "", str(exc))


def read_pid() -> int | None:
    try:
        return int(PID_FILE.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def ensure_dirs() -> None:
    for path in (
        ROOT / "data" / "runtime",
        ROOT / "data" / "logs",
        ROOT / "data" / "databases",
        ROOT / "data" / "knowledge",
        ROOT / "data" / "backups",
    ):
        path.mkdir(parents=True, exist_ok=True)


def timestamped_backup(label: str = "backup") -> str:
    return f"hackergpt-{label}-{time.strftime('%Y%m%d-%H%M%S')}.zip"


def open_url(url: str) -> None:
    if os.name == "nt":
        os.startfile(url)  # type: ignore[attr-defined]  # noqa: S606
    elif sys.platform == "darwin":
        subprocess.Popen(["open", url])  # noqa: S603, S607
    else:
        subprocess.Popen(["xdg-open", url])  # noqa: S603, S607


if __name__ == "__main__":
    raise SystemExit(main())
