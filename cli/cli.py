"""
TestGhost CLI — testghost start | stop | generate | sessions
"""

import json
import os
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

import click
import httpx
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

load_dotenv()

console = Console(force_terminal=True)

_STATE_FILE = Path(".testghost_session")
_LAST_SESSION_FILE = Path(".testghost_last_session")
BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")


def _read_state() -> dict:
    if _STATE_FILE.exists():
        return json.loads(_STATE_FILE.read_text())
    return {}


def _write_state(data: dict) -> None:
    _STATE_FILE.write_text(json.dumps(data))


def _clear_state() -> None:
    if _STATE_FILE.exists():
        _STATE_FILE.unlink()


def _ensure_backend_running(backend_url: str = BACKEND_URL) -> None:
    """Ensure the backend is running, starting it if necessary."""
    try:
        resp = httpx.get(f"{backend_url}/health", timeout=1.5)
        if resp.status_code == 200:
            return
    except Exception:
        pass

    import urllib.parse
    parsed = urllib.parse.urlparse(backend_url)
    port = parsed.port or 8000

    console.print(f"[bold dim]Starting TestGhost backend on port {port}...[/bold dim]")
    backend_log = open("backend.log", "a")
    subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app",
         "--host", "0.0.0.0", "--port", str(port), "--no-access-log"],
        stdout=backend_log,
        stderr=backend_log,
    )
    for _ in range(15):
        try:
            resp = httpx.get(f"{backend_url}/health", timeout=1)
            if resp.status_code == 200:
                return
        except Exception:
            time.sleep(1)

    console.print("[red]Failed to reach backend server. Check backend.log.[/red]")
    sys.exit(1)


@click.group()
def cli() -> None:
    """TestGhost — AI-native test generation from real HTTP traffic."""


@cli.command()
@click.option("--session", "session_name", required=True, help="Name for this recording session")
@click.option("--port", default=8080, show_default=True, help="mitmproxy port")
@click.option("--backend-port", default=8000, show_default=True, help="FastAPI port")
def start(session_name: str, port: int, backend_port: int) -> None:
    """Start a recording session. Launches the backend + proxy."""
    backend_url = f"http://127.0.0.1:{backend_port}"

    # Start FastAPI backend
    console.print(f"[bold]Starting TestGhost backend on port {backend_port}...[/bold]")
    backend_log = open("backend.log", "w")
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app",
         "--host", "0.0.0.0", "--port", str(backend_port), "--no-access-log"],
        stdout=backend_log,
        stderr=backend_log,
    )
    # Poll backend /health endpoint until ready (up to 15 seconds)
    backend_ready = False
    for _ in range(15):
        try:
            resp = httpx.get(f"{backend_url}/health", timeout=2)
            if resp.status_code == 200:
                backend_ready = True
                break
        except Exception:
            time.sleep(1)

    if not backend_ready:
        console.print("[red]Failed to start backend: timed out waiting for server to be ready. Check backend.log.[/red]")
        backend_proc.kill()
        sys.exit(1)

    # Wait for embedding model to be ready (up to 180 seconds)
    console.print("[bold dim]Loading embedding model (first run can take a minute or two)...[/bold dim]")
    model_ready = False
    for _ in range(180):
        try:
            resp = httpx.get(f"{backend_url}/ready", timeout=2)
            if resp.status_code == 200:
                model_ready = True
                break
        except Exception:
            pass
        time.sleep(1)

    if not model_ready:
        console.print("[red]Failed to initialize embedding model: timed out waiting for backend to be ready. Check backend.log.[/red]")
        backend_proc.kill()
        sys.exit(1)

    # Create session
    try:
        resp = httpx.post(f"{backend_url}/session/start", json={"name": session_name}, timeout=10)
        resp.raise_for_status()
        session_id = resp.json()["session_id"]
    except Exception as exc:
        console.print(f"[red]Failed to create session: {exc}[/red]")
        backend_proc.kill()
        sys.exit(1)

    # Start mitmproxy
    console.print(f"[bold]Starting proxy on port {port}...[/bold]")
    env = {**os.environ, "SESSION_ID": session_id, "BACKEND_URL": backend_url}
    proxy_log = open("proxy.log", "w")
    proxy_proc = subprocess.Popen(
        [sys.executable, "-u", "-c", "from mitmproxy.tools.main import mitmdump; mitmdump()",
         "-p", str(port), "-s", "proxy/addon.py"],
        env=env,
        stdout=proxy_log,
        stderr=proxy_log,
    )

    # Health check: verify proxy is listening on port and backend /health is still healthy
    proxy_ready = False
    for _ in range(15):
        if proxy_proc.poll() is not None:
            break
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                resp = httpx.get(f"{backend_url}/health", timeout=1)
                if resp.status_code == 200:
                    proxy_ready = True
                    break
        except (OSError, ConnectionRefusedError, httpx.RequestError):
            time.sleep(1)

    if not proxy_ready:
        console.print(f"[red]Failed to start proxy: port {port} is not listening or backend is unhealthy. Check proxy.log and backend.log.[/red]")
        try:
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/PID", str(proxy_proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["taskkill", "/F", "/PID", str(backend_proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                proxy_proc.kill()
                backend_proc.kill()
        except Exception:
            pass
        sys.exit(1)

    _write_state({
        "session_id": session_id,
        "session_name": session_name,
        "backend_pid": backend_proc.pid,
        "proxy_pid": proxy_proc.pid,
        "backend_url": backend_url,
        "proxy_port": port,
    })

    console.print(f"\n[green][OK] TestGhost session started[/green]")
    console.print(f"  Session:   [cyan]{session_name}[/cyan] ({session_id})")
    console.print(f"  Proxy:     [cyan]localhost:{port}[/cyan] — configure your browser to use this")
    console.print(f"  Backend:   [cyan]{backend_url}[/cyan]")
    console.print(f"\n  Browse your app, then run: [bold]testghost stop[/bold]")


@cli.command()
def stop() -> None:
    """Stop the active recording session."""
    state = _read_state()
    if not state:
        console.print("[red]No active session found. Run testghost start first.[/red]")
        sys.exit(1)

    backend_url = state.get("backend_url", BACKEND_URL)
    session_id = state["session_id"]

    try:
        resp = httpx.post(
            f"{backend_url}/session/stop",
            json={"session_id": session_id},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        console.print(f"\n[green][OK] Session stopped[/green]")
        console.print(f"  Captured: [cyan]{data['request_count']}[/cyan] requests")
        console.print(f"  Duration: [cyan]{data.get('duration_seconds', 0):.1f}s[/cyan]")
    except Exception as exc:
        console.print(f"[yellow]Warning: could not stop session via API: {exc}[/yellow]")

    # Kill proxy subprocess
    proxy_pid = state.get("proxy_pid")
    if proxy_pid:
        try:
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/PID", str(proxy_pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                import signal
                os.kill(proxy_pid, signal.SIGTERM)
        except Exception:
            pass

    _LAST_SESSION_FILE.write_text(session_id)
    _clear_state()
    console.print(f"\n  Run [bold]testghost generate --session {session_id}[/bold] to produce tests")


@cli.command()
@click.option("--session", "session_id", required=False, help="Session ID (defaults to last stopped)")
@click.option("--backend-url", default=None, help="Backend URL override")
def generate(session_id: str | None, backend_url: str | None) -> None:
    """Run the AI generation pipeline for a completed session."""
    url = backend_url or BACKEND_URL

    if not session_id and _LAST_SESSION_FILE.exists():
        session_id = _LAST_SESSION_FILE.read_text().strip()

    if not session_id:
        console.print("[red]Provide --session <session_id>[/red]")
        sys.exit(1)

    _ensure_backend_running(url)

    console.print(f"\n[bold]Running generation pipeline for session {session_id}...[/bold]")
    console.print("  This may take 30–120 seconds depending on the number of endpoints.\n")

    try:
        resp = httpx.post(
            f"{url}/generate",
            json={"session_id": session_id},
            timeout=300,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        console.print(f"[red]Generation failed: {exc}[/red]")
        sys.exit(1)

    console.print(f"[green][OK] Generation complete[/green]")
    console.print(f"  Clusters:   [cyan]{data['summary']['clusters']}[/cyan]")
    console.print(f"  Test files: [cyan]{len(data['test_files'])}[/cyan]")
    for f in data["test_files"]:
        console.print(f"    [dim]{f}[/dim]")
    console.print(f"\n  Report: [underline cyan]{data['report_path']}[/underline cyan]")
    console.print(f"\n  Run tests: [bold]pytest {data['test_files'][0] if data['test_files'] else 'output/tests/'}[/bold]")


@cli.command("sessions")
@click.option("--backend-url", default=None, help="Backend URL override")
def list_sessions(backend_url: str | None) -> None:
    """List all past recording sessions."""
    url = backend_url or BACKEND_URL
    _ensure_backend_running(url)

    try:
        resp = httpx.get(f"{url}/session/list", timeout=10)
        resp.raise_for_status()
        sessions = resp.json()
    except Exception as exc:
        console.print(f"[red]Could not fetch sessions: {exc}[/red]")
        sys.exit(1)

    if not sessions:
        console.print("[dim]No sessions found. Run testghost start to begin.[/dim]")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Name", style="cyan")
    table.add_column("Status")
    table.add_column("Requests", justify="right")
    table.add_column("Unique", justify="right")
    table.add_column("Anomalies", justify="right")
    table.add_column("Session ID", style="dim")

    for s in sessions:
        status_style = "green" if s["status"] == "complete" else "yellow"
        table.add_row(
            s["name"],
            f"[{status_style}]{s['status']}[/{status_style}]",
            str(s["request_count"]),
            str(s["unique_endpoints"]),
            str(s["anomaly_count"]),
            s["id"],
        )

    console.print(table)


if __name__ == "__main__":
    cli()
