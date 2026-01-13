from __future__ import annotations

import json
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import parse_qs, urlparse

from .aggregate import build_flamegraph, build_timeline, compute_hotspots
from .models import FlameNode, RunData, RunMetadata
from .parse import parse_perf_script_file

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def _load_run(run_id: str) -> RunData:
    run_dir = DATA_DIR / run_id
    script_path = run_dir / "perf.script"
    manifest_path = run_dir / "manifest.json"
    if not script_path.exists() or not manifest_path.exists():
        raise FileNotFoundError(f"Run {run_id} not found")

    manifest = json.loads(manifest_path.read_text())
    metadata = RunMetadata(
        run_id=run_id,
        command=manifest["command"],
        started_at=datetime.fromisoformat(manifest["started_at"]),
        hostname=manifest["hostname"],
        kernel=manifest.get("kernel", "unknown"),
        perf_version=manifest.get("perf_version", "unknown"),
        notes=manifest.get("notes"),
    )
    return parse_perf_script_file(script_path, metadata)


def _list_runs() -> List[Dict]:
    runs: List[Dict] = []
    for run_dir in sorted(DATA_DIR.glob("*")):
        manifest = run_dir / "manifest.json"
        if not manifest.exists():
            continue
        meta = json.loads(manifest.read_text())
        runs.append(
            {
                "run_id": run_dir.name,
                "command": meta["command"],
                "started_at": meta["started_at"],
                "hostname": meta["hostname"],
            }
        )
    return runs


def _hotspots(run_id: str) -> List[Dict]:
    run = _load_run(run_id)
    hotspots = compute_hotspots(run)
    return [
        {
            "function": h.function,
            "module": h.module,
            "samples": h.samples,
            "pct": round(h.pct, 2),
        }
        for h in hotspots
    ]


def _timeline(run_id: str, event: str) -> List[Dict]:
    run = _load_run(run_id)
    points = build_timeline(run, event=event)
    return [
        {"timestamp_ns": p.timestamp_ns, "value": p.value, "event": p.event}
        for p in points
    ]


def _flamegraph(run_id: str) -> Dict:
    run = _load_run(run_id)
    flame = build_flamegraph(run)

    def convert(node: FlameNode) -> Dict:
        return {
            "name": node.name,
            "value": node.value,
            "children": [convert(c) for c in node.children] if node.children else [],
        }

    return convert(flame)


class PerfRequestHandler(BaseHTTPRequestHandler):
    def _send(self, status: HTTPStatus, payload: Dict | List) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT.value)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path_parts = [p for p in parsed.path.split("/") if p]
        query = parse_qs(parsed.query)

        try:
            if path_parts == ["runs"]:
                self._send(HTTPStatus.OK, _list_runs())
                return

            if len(path_parts) == 3 and path_parts[0] == "runs":
                run_id, section = path_parts[1], path_parts[2]
                if section == "hotspots":
                    self._send(HTTPStatus.OK, _hotspots(run_id))
                    return
                if section == "timeline":
                    event = query.get("event", ["cycles"])[0]
                    self._send(HTTPStatus.OK, _timeline(run_id, event))
                    return
                if section == "flamegraph":
                    self._send(HTTPStatus.OK, _flamegraph(run_id))
                    return

            self._send(HTTPStatus.NOT_FOUND, {"error": "not found"})
        except FileNotFoundError:
            self._send(HTTPStatus.NOT_FOUND, {"error": "run not found"})
        except Exception as exc:  # pragma: no cover - debug aid
            self._send(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})


def create_server(host: str = "0.0.0.0", port: int = 8000) -> HTTPServer:
    return HTTPServer((host, port), PerfRequestHandler)


def main() -> None:
    server = create_server()
    try:
        print("Serving perf-gui API on http://{}:{}".format(*server.server_address))
        server.serve_forever()
    except KeyboardInterrupt:  # pragma: no cover - manual stop
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
