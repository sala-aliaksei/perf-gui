import json
import threading
import time
from urllib.error import HTTPError
from urllib.request import urlopen

from perf_gui.server import create_server


class ServerThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.server = create_server(host="127.0.0.1", port=0)

    @property
    def url(self) -> str:
        host, port = self.server.server_address
        return f"http://{host}:{port}"

    def run(self) -> None:  # pragma: no cover - threading loop
        self.server.serve_forever()

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()


def fetch_json(url: str):
    with urlopen(url) as resp:
        return json.loads(resp.read())


def test_runs_and_hotspots():
    server = ServerThread()
    server.start()
    time.sleep(0.1)
    try:
        runs = fetch_json(server.url + "/runs")
        assert runs, "expected sample run"
        run_id = runs[0]["run_id"]

        hotspots = fetch_json(f"{server.url}/runs/{run_id}/hotspots")
        assert hotspots
        top = hotspots[0]
        assert "function" in top and "samples" in top
    finally:
        server.stop()


def test_timeline_and_flamegraph():
    server = ServerThread()
    server.start()
    time.sleep(0.1)
    try:
        run_id = fetch_json(server.url + "/runs")[0]["run_id"]
        timeline = fetch_json(f"{server.url}/runs/{run_id}/timeline?event=cycles")
        assert timeline and all("timestamp_ns" in p for p in timeline)

        flame = fetch_json(f"{server.url}/runs/{run_id}/flamegraph")
        assert flame["name"] == "root"
        assert flame["children"]
    finally:
        server.stop()


def test_missing_run_returns_404():
    server = ServerThread()
    server.start()
    time.sleep(0.1)
    try:
        try:
            fetch_json(server.url + "/runs/does-not-exist/hotspots")
            assert False, "expected HTTPError"
        except HTTPError as exc:
            assert exc.code == 404
    finally:
        server.stop()
