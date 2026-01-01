# Linux Perf-Based Performance Analysis UI

## Goals
Design a VTune-like desktop application that uses Linux `perf` to collect and analyze performance data, then surfaces interactive visualizations for hotspots, timelines, flame graphs, and hardware counters. The solution prioritizes low overhead, scalability for long-running workloads, and extensibility for new event types.

## Recommended Tech Stack
- **Desktop shell**: Tauri (Rust) to deliver a lightweight desktop app with system-level capabilities and secure IPC.
- **Frontend**: React + TypeScript + Vite; component libraries such as Fluent UI or MUI for data-dense panels; D3/visx for timelines and flame graphs.
- **Backend/engine**: Rust for the perf runner, parsers, symbolication, aggregation, and query engine.
- **Data interchange**: Apache Arrow/Parquet for columnar storage of samples and aggregates; JSON for lightweight summaries; Protobuf/Cap'n Proto for IPC messages.
- **Scripting/automation**: CLI companion (Rust) that shares the core engine and can emit JSON/Parquet for headless workflows.

## High-Level Architecture
```
+------------------------+        +-----------------------+
|        Desktop UI      |<------>|    Local IPC (Tauri)  |
|  React + visx/D3 views |        |   commands & queries  |
+-----------^------------+        +-----------^-----------+
            |                                 |
            | read/query                      | control/profile
            |                                 |
+-----------+-------------+        +-----------+-----------+
|     Query & Cache Layer |<------>|   Perf Orchestrator   |
|  Arrow scan, filters,   |        | run perf, manage PIDs |
|  derived metrics        |        | collect raw records   |
+-----------^-------------+        +-----------^-----------+
            |                                 |
            | materialize                     | emit raw data
            |                                 |
+-----------+-------------+        +-----------+-----------+
|  Symbolication & Parser |<------>|     perf (stat/record)|
|  DWARF, frame pointers, |        |     perf script       |
|  inline expansion       |        |     perf report       |
+-----------^-------------+        +-----------+-----------+
            |                                 |
            | structured samples               (kernel & user events)
            v
+----------------------------------------------------------+
| Storage: Arrow/Parquet files + run metadata (JSON)       |
+----------------------------------------------------------+
```

### Layer Responsibilities
- **Perf Orchestrator**: wraps `perf stat/record/script` and manages lifecycle (launch or attach). Captures hardware/software events, call stacks, and context switches. Stores raw data under a run directory with metadata (command, environment, perf version, kernel info).
- **Parser & Symbolication**: converts `perf script` output into structured records; resolves symbols using debug info, BPF frame pointers, and `perf buildid-cache`; expands inline frames; attributes to DSOs and inlined functions.
- **Storage**: writes samples and aggregates to Arrow/Parquet partitions keyed by run, time slice, CPU, thread, and event type. Lightweight JSON summaries store run manifest and quick stats.
- **Query & Cache Layer**: provides slice/filter/aggregate operations (time range, CPU/thread, event, module, function). Maintains derived views (hotspots, call graphs, per-core timelines) and caches query results for smooth UI interaction.
- **Desktop UI**: renders views (timeline, hotspot table, flame graph/call graph, per-thread/core, counter dashboards). Supports zoom/pan, click-through navigation, filtering, diff mode, and run/session management.

## Data Flow
1. **Profile start**: User launches profiling or attaches to a PID. The orchestrator prepares a run directory and captures manifest (command line, cwd, env, perf version, kernel, CPU topology).
2. **Collection**: Orchestrator runs `perf record` with configured event set and stack capture; optional `perf stat` for interval counters. Raw data (`perf.data`, `perf_stat.json`) is stored.
3. **Extraction**: `perf script` produces text or JSON streams. A streaming parser transforms records into structured samples (timestamp, CPU, TID, PID, event, count, IP, call chain, DSO, symbol offsets).
4. **Symbolication**: Resolver maps IPs to functions/files/lines, expands inline frames, and tags shared libraries. Unresolved symbols fall back to raw addresses but are cached for later resolution.
5. **Storage & indexing**: Samples are written to Arrow/Parquet partitions; indexes built for time ranges, CPU/thread, event types, and symbols. Aggregations (per-function, per-module, per-thread, per-core, per-event) are precomputed for responsiveness.
6. **Query/UI**: UI requests time slices, hotspot tables, or call graphs via IPC. Query layer applies filters and returns aggregates plus raw slices for detailed views. Diff mode aligns two runs and computes deltas.

## UI Layout (textual mock)
```
+--------------------------------------------------------------------------------+
| Top bar: Run selector | Event set | Filter chips (CPU, TID, event) | Time range |
+--------------------------------------------------------------------------------+
| Timeline: stacked area/line for cycles/instructions/cache-misses; zoom/pan      |
|          vertical markers for context switches and phases                       |
+----------------------------------+---------------------------------------------+
| Hotspots (table): Function | Module | Event % | Samples | Branch miss % | ...    |
| - sortable, filterable; click row -> focus time slice + open call graph         |
+----------------------------------+---------------------------------------------+
| Call graph / Flame graph (toggle) | Right pane: per-thread/per-core mini charts |
| - hover for inclusive/exclusive    | - small multiples for CPU/TID timelines    |
| - click to jump to source/file     | - select to filter main views              |
+----------------------------------+---------------------------------------------+
| Bottom drawer: Event inspector, raw samples preview, diff controls              |
+--------------------------------------------------------------------------------+
```

## MVP Feature List
- Launch or attach profiling for a target command or PID using `perf record` with configurable event sets (cycles, instructions, cache-misses, branches, context-switches, faults) and stack capture.
- Parse `perf script` output into structured samples; resolve symbols with DWARF/frame pointers and attribute to shared libraries.
- Store runs in a structured directory with manifest + Arrow/Parquet sample data and pre-aggregated hotspot tables.
- Timeline view with zoom/pan showing event rates over time; filter by CPU/thread/event/time range.
- Hotspot table with inclusive/exclusive metrics per function/module; click-through to call graph/flame graph.
- Call graph and flame graph views with navigation to source file/line where available.
- Per-thread and per-core summaries showing utilization and key event counts.
- Hardware counter dashboard (IPC, cache miss rate, branch miss rate) derived from collected events.
- Diff mode to compare two runs (hotspots and timelines) with percent/absolute deltas.
- Export/import runs for offline analysis; CLI headless mode shares the engine.

## Future Extensions
- NUMA awareness (per-node views, memory locality metrics) and memory bandwidth counters.
- GPU offload traces (CUDA/HIP/Level Zero) and PCIe bandwidth events.
- Off-CPU analysis (blocked/wait reasons), scheduler latency, and wakeup chains.
- eBPF-based sampling for lower overhead or kernel-only tracing; integration with LBR/PEBS where available.
- Live profiling mode with streaming updates into the UI for long-running services.
- Source annotation with per-line metrics and inline expansion toggles.
- Team workflows: run sharing, annotations/bookmarks, and baseline comparisons across builds.
