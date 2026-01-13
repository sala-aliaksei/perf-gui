from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Iterable, List, Optional

from .models import RunMetadata


DEFAULT_EVENTS = [
    "cycles",
    "instructions",
    "cache-misses",
    "branches",
    "branch-misses",
    "context-switches",
    "page-faults",
]


def build_perf_record_command(
    output: Path,
    target: List[str],
    events: Iterable[str] = DEFAULT_EVENTS,
    freq: Optional[int] = None,
    call_graph: str = "fp",
) -> List[str]:
    cmd = [
        "perf",
        "record",
        "-g",
        f"--call-graph={call_graph}",
        "-o",
        str(output),
        "-e",
        ",".join(events),
    ]
    if freq:
        cmd.extend(["-F", str(freq)])
    cmd.extend(target)
    return cmd


def run_perf_record(
    output: Path,
    target: List[str],
    events: Iterable[str] = DEFAULT_EVENTS,
    freq: Optional[int] = None,
    call_graph: str = "fp",
) -> subprocess.CompletedProcess:
    cmd = build_perf_record_command(output, target, events, freq, call_graph)
    return subprocess.run(cmd, check=False)


def run_perf_stat(
    target: List[str],
    events: Iterable[str] = DEFAULT_EVENTS,
    interval_ms: int = 1000,
) -> subprocess.Popen:
    cmd = [
        "perf",
        "stat",
        "-I",
        str(interval_ms),
        "-e",
        ",".join(events),
        *target,
    ]
    return subprocess.Popen(cmd)


def save_manifest(path: Path, metadata: RunMetadata) -> None:
    path.write_text(
        json.dumps(
            {
                "run_id": metadata.run_id,
                "command": metadata.command,
                "started_at": metadata.started_at.isoformat(),
                "hostname": metadata.hostname,
                "kernel": metadata.kernel,
                "perf_version": metadata.perf_version,
                "notes": metadata.notes,
            },
            indent=2,
        )
    )
