from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, List

from .models import RunData, RunMetadata, Sample

TIMESTAMP_RE = re.compile(r"^(?P<ts>[0-9]+\.[0-9]+):")
IP_RE = re.compile(r"ip=(?P<ip>0x[0-9a-fA-F]+)")
EVENT_RE = re.compile(r"event=(?P<event>[^ ]+)")
PID_TID_RE = re.compile(r"\[(?P<pid>\d+)(?:\s+(?P<tid>\d+))?\]")
CPU_RE = re.compile(r"CPU=(?P<cpu>\d+)")
FUNCTION_RE = re.compile(r"symbol=(?P<fn>[^\s]+)")
MODULE_RE = re.compile(r"dso=(?P<dso>[^\s]+)")
COUNT_RE = re.compile(r"period=(?P<count>\d+)")


def parse_perf_script(lines: Iterable[str], metadata: RunMetadata) -> RunData:
    samples: List[Sample] = []
    stack: List[str] = []
    for raw in lines:
        line = raw.strip()
        if not line:
            if stack and samples:
                samples[-1].stack = list(stack)
            stack.clear()
            continue
        if line.startswith("#"):
            continue
        if line.startswith("\t"):
            stack.append(line.strip())
            continue

        ts_match = TIMESTAMP_RE.search(line)
        pid_tid_match = PID_TID_RE.search(line)
        event_match = EVENT_RE.search(line)
        ip_match = IP_RE.search(line)
        cpu_match = CPU_RE.search(line)
        fn_match = FUNCTION_RE.search(line)
        module_match = MODULE_RE.search(line)
        count_match = COUNT_RE.search(line)

        if not (ts_match and pid_tid_match and event_match and ip_match and cpu_match):
            continue

        timestamp_ns = int(float(ts_match.group("ts")) * 1e9)
        pid = int(pid_tid_match.group("pid"))
        tid = int(pid_tid_match.group("tid") or pid)
        event = event_match.group("event")
        ip = ip_match.group("ip")
        cpu = int(cpu_match.group("cpu"))
        count = int(count_match.group("count")) if count_match else 1
        function = fn_match.group("fn") if fn_match else None
        module = module_match.group("dso") if module_match else None

        samples.append(
            Sample(
                timestamp_ns=timestamp_ns,
                cpu=cpu,
                pid=pid,
                tid=tid,
                event=event,
                count=count,
                ip=ip,
                function=function,
                module=module,
            )
        )
    return RunData(metadata=metadata, samples=samples)


def parse_perf_script_file(path: Path, metadata: RunMetadata) -> RunData:
    return parse_perf_script(path.read_text().splitlines(), metadata)
