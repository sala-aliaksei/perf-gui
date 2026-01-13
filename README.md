# perf-gui

Prototype implementation of a VTune-like Linux performance analysis UI built on `perf`.

## What’s included
- **Python backend (minimal HTTP server)** to serve runs, hotspots, timelines, and flamegraph data from perf script output.
- **Sample data** under `data/sample_run` with a minimal perf script and manifest.
- **Static UI prototype** in `ui/index.html` consuming the API to render timelines, hotspots, and a flame tree.
- **Design blueprint** in [`docs/design.md`](docs/design.md) describing architecture and roadmap.

## Quick start
1. (Optional) Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
2. Run the API server (serves sample data by default) without third-party deps:
   ```bash
   python -m perf_gui.server
   ```
3. Open the UI prototype (simple static file):
   ```bash
   python -m http.server 3000 --directory ui
   ```
4. Visit http://localhost:3000 and the UI will call the API at http://localhost:8000.

## Notes
- The backend expects runs to be stored as `data/<run_id>/perf.script` plus `manifest.json`.
- Collection helpers in `perf_gui.collect` sketch how to invoke `perf record` and save manifests.
- Parsing and aggregation live in `perf_gui.parse` and `perf_gui.aggregate` and can be extended for richer metrics.
