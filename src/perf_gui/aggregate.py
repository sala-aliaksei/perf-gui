from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict, Iterable, List, Tuple

from .models import FlameNode, Hotspot, RunData, TimelinePoint


def compute_hotspots(run: RunData) -> List[Hotspot]:
    counter: Counter[Tuple[str, str]] = Counter()
    totals = 0
    for s in run.samples:
        key = (s.function or s.ip, s.module or "unknown")
        counter[key] += s.count
        totals += s.count

    hotspots: List[Hotspot] = []
    for (fn, module), samples in counter.most_common():
        pct = (samples / totals * 100.0) if totals else 0.0
        hotspots.append(Hotspot(function=fn, module=module, samples=samples, pct=pct))
    return hotspots


def build_timeline(run: RunData, event: str) -> List[TimelinePoint]:
    buckets: Dict[int, int] = defaultdict(int)
    for s in run.samples:
        if s.event != event:
            continue
        bucket = s.timestamp_ns // 1_000_000  # ms buckets
        buckets[bucket] += s.count
    points = [TimelinePoint(timestamp_ns=k * 1_000_000, value=v, event=event) for k, v in sorted(buckets.items())]
    return points


def build_flamegraph(run: RunData) -> FlameNode:
    root = FlameNode(name="root", value=0, children=[])

    def add_stack(stack: List[str], value: int) -> None:
        node = root
        node.value += value
        for frame in stack:
            child = next((c for c in node.children if c.name == frame), None)
            if not child:
                child = FlameNode(name=frame, value=0, children=[])
                node.children.append(child)
            child.value += value
            node = child

    for s in run.samples:
        add_stack(s.stack or [s.function or s.ip], s.count)

    return root
