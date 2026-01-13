from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class Sample:
    timestamp_ns: int
    cpu: int
    pid: int
    tid: int
    event: str
    count: int
    ip: str
    function: Optional[str] = None
    module: Optional[str] = None
    stack: List[str] = field(default_factory=list)


@dataclass
class RunMetadata:
    run_id: str
    command: str
    started_at: datetime
    hostname: str
    kernel: str
    perf_version: str
    notes: Optional[str] = None


@dataclass
class RunData:
    metadata: RunMetadata
    samples: List[Sample]


@dataclass
class Hotspot:
    function: str
    module: Optional[str]
    samples: int
    pct: float
    branches: Optional[int] = None
    cache_misses: Optional[int] = None


@dataclass
class TimelinePoint:
    timestamp_ns: int
    value: float
    event: str


@dataclass
class FlameNode:
    name: str
    value: int
    children: List["FlameNode"] = field(default_factory=list)
