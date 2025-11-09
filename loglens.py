#!/usr/bin/env python
# coding: utf-8

# In[6]:


"""
LogLens — Root-Cause Log Explorer (CLI)

Features
- Load logs from JSONL or plain text (best-effort parse).
- Filter by time window, level, keyword(s), request_id, and latency threshold.
- Quick stats: counts by level, top messages, latency distribution.
- Spike scan: finds minutes with unusually high ERROR/WARN counts.
- Healthy vs Failing diff: shows messages/levels/spikes that appear in failing but not in healthy logs.

JSONL log line format (recommended):
{"timestamp":"2025-11-08T13:30:01.234Z","level":"ERROR","message":"DB timeout","request_id":"abc123","latency_ms":812}

Plain text best-effort expected pattern (flexible):
2025-11-08T13:30:01.234Z ERROR [req=abc123] DB timeout (latency=812ms)
"""

from __future__ import annotations
import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Iterable, List, Optional, Tuple


ISO_RE = re.compile(
    r"(?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)\s+(?P<level>[A-Za-z]+)\s+(?P<rest>.*)"
)
REQ_RE = re.compile(r"(?:req(?:uest)?[=_:\s])(?P<rid>[A-Za-z0-9\-\_]+)", re.I)
LAT_RE = re.compile(r"(?:latency|lat|dur|duration)[=\s:~]*(?P<ms>\d+)\s*ms", re.I)


@dataclass
class LogEntry:
    ts: datetime
    level: str
    message: str
    request_id: Optional[str] = None
    latency_ms: Optional[int] = None
    raw: str = ""

    @staticmethod
    def from_jsonl(line: str) -> Optional["LogEntry"]:
        try:
            obj = json.loads(line)
            ts = parse_ts(obj.get("timestamp") or obj.get("time") or obj.get("ts"))
            if not ts:
                return None
            level = str(obj.get("level", "INFO")).upper()
            msg = str(obj.get("message", obj.get("msg", "")))
            rid = obj.get("request_id") or obj.get("req_id") or obj.get("rid")
            lat = obj.get("latency_ms") or obj.get("lat_ms") or obj.get("duration_ms")
            if isinstance(lat, str) and lat.isdigit():
                lat = int(lat)
            if isinstance(lat, (int, float)):
                lat = int(lat)
            return LogEntry(ts, level, msg, rid, lat, raw=line.rstrip("\n"))
        except Exception:
            return None

    @staticmethod
    def from_text(line: str) -> Optional["LogEntry"]:
        m = ISO_RE.match(line)
        if not m:
            return None
        ts = parse_ts(m.group("ts"))
        if not ts:
            return None
        level = m.group("level").upper()
        rest = m.group("rest").strip()
        # request id
        rid = None
        r = REQ_RE.search(rest)
        if r:
            rid = r.group("rid")
        # latency
        lat = None
        l = LAT_RE.search(rest)
        if l:
            try:
                lat = int(l.group("ms"))
            except Exception:
                pass
        # message (strip common brackets and kv pairs)
        msg = rest
        return LogEntry(ts, level, msg, rid, lat, raw=line.rstrip("\n"))


def parse_ts(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    v = value.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(v)
        if not dt.tzinfo:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def load_entries(path: Path) -> List[LogEntry]:
    entries: List[LogEntry] = []
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            e = LogEntry.from_jsonl(line)
            if not e:
                e = LogEntry.from_text(line)
            if e:
                entries.append(e)
    entries.sort(key=lambda x: x.ts)
    return entries


def filter_entries(
    entries: Iterable[LogEntry],
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    levels: Optional[List[str]] = None,
    keywords: Optional[List[str]] = None,
    request_id: Optional[str] = None,
    min_latency: Optional[int] = None,
) -> List[LogEntry]:
    lvset = {lv.upper() for lv in (levels or [])}
    kw = [k.lower() for k in (keywords or [])]
    out: List[LogEntry] = []
    for e in entries:
        if since and e.ts < since:
            continue
        if until and e.ts > until:
            continue
        if lvset and e.level.upper() not in lvset:
            continue
        if request_id and (e.request_id or "") != request_id:
            continue
        if min_latency is not None and (e.latency_ms or -1) < min_latency:
            continue
        if kw and not any(k in (e.message.lower()) for k in kw):
            continue
        out.append(e)
    return out


def summarize(entries: List[LogEntry]) -> str:
    if not entries:
        return "No entries."
    by_level = Counter(e.level for e in entries)
    top_msgs = Counter(normalize_message(e.message) for e in entries).most_common(8)
    latencies = [e.latency_ms for e in entries if e.latency_ms is not None]
    lat_summary = ""
    if latencies:
        latencies.sort()
        p50 = latencies[int(0.5 * (len(latencies)-1))]
        p95 = latencies[int(0.95 * (len(latencies)-1))]
        p99 = latencies[int(0.99 * (len(latencies)-1))]
        lat_summary = f"\nLatency (ms): p50={p50}, p95={p95}, p99={p99}"
    out = []
    out.append(f"Entries: {len(entries)}")
    out.append("By level: " + ", ".join(f"{k}={v}" for k, v in by_level.most_common()))
    if top_msgs:
        out.append("Top messages:")
        for msg, cnt in top_msgs:
            out.append(f"  - {cnt:>5} × {msg}")
    if lat_summary:
        out.append(lat_summary)
    spikes = scan_spikes(entries)
    if spikes:
        out.append("Spike minutes (ERROR/WARN):")
        for ts_min, count, baseline in spikes[:10]:
            out.append(f"  - {ts_min}Z : {count} (baseline≈{baseline:.1f}x)")
    return "\n".join(out)


def normalize_message(msg: str) -> str:
    # Collapse numbers/ids to reduce noise for top-message grouping
    msg = re.sub(r"\b[0-9a-f]{6,}\b", "<id>", msg, flags=re.I)
    msg = re.sub(r"\b\d+\b", "<n>", msg)
    return msg.strip()


def truncate_to_minute(dt: datetime) -> datetime:
    return dt.replace(second=0, microsecond=0)


def scan_spikes(entries: List[LogEntry]) -> List[Tuple[str, int, float]]:
    """
    Find minutes where WARN+ERROR counts spike vs median.
    Returns list of (minute_iso, count, multiple_of_median) sorted desc.
    """
    per_min = defaultdict(int)
    for e in entries:
        if e.level in ("ERROR", "WARN", "WARNING"):
            m = truncate_to_minute(e.ts)
            per_min[m] += 1
    if not per_min:
        return []
    counts = list(per_min.values())
    med = max(median(counts), 1)  # avoid div by zero
    spikes = []
    for minute, cnt in per_min.items():
        multiple = cnt / med
        if multiple >= 2.0 and cnt >= 3:
            spikes.append((minute.isoformat().replace("+00:00", ""), cnt, multiple))
    spikes.sort(key=lambda x: (-x[1], -x[2], x[0]))
    return spikes


def diff_healthy_vs_failing(healthy: List[LogEntry], failing: List[LogEntry]) -> str:
    if not healthy or not failing:
        return "Need both healthy and failing logs."

    # Levels diff
    lvl_h = Counter(e.level for e in healthy)
    lvl_f = Counter(e.level for e in failing)

    # Messages diff
    msg_h = Counter(normalize_message(e.message) for e in healthy)
    msg_f = Counter(normalize_message(e.message) for e in failing)

    new_msgs = [(m, c) for m, c in msg_f.items() if m not in msg_h]
    elevated_msgs = [(m, msg_f[m] - msg_h[m]) for m in msg_f if m in msg_h and msg_f[m] > msg_h[m]]
    new_msgs.sort(key=lambda x: -x[1])
    elevated_msgs.sort(key=lambda x: -x[1])

    # Latency compare
    lat_h = [e.latency_ms for e in healthy if e.latency_ms is not None]
    lat_f = [e.latency_ms for e in failing if e.latency_ms is not None]
    lat_line = ""
    if lat_h and lat_f:
        lat_h.sort(), lat_f.sort()
        p95_h = lat_h[int(0.95 * (len(lat_h)-1))]
        p95_f = lat_f[int(0.95 * (len(lat_f)-1))]
        lat_line = f"Latency p95: healthy={p95_h}ms → failing={p95_f}ms (Δ={p95_f - p95_h}ms)"

    # Spike scan on failing
    spikes_f = scan_spikes(failing)

    lines = []
    lines.append("=== Levels ===")
    lines.append("Healthy: " + ", ".join(f"{k}={v}" for k, v in lvl_h.most_common()))
    lines.append("Failing: " + ", ".join(f"{k}={v}" for k, v in lvl_f.most_common()))
    lines.append("")
    lines.append("=== New Messages in FAILING ===")
    if new_msgs:
        for m, c in new_msgs[:15]:
            lines.append(f"  - {c:>5} × {m}")
    else:
        lines.append("  (none)")
    lines.append("")
    lines.append("=== Elevated Messages (more frequent in FAILING) ===")
    if elevated_msgs:
        for m, d in elevated_msgs[:15]:
            lines.append(f"  - +{d:>4} × {m}")
    else:
        lines.append("  (none)")
    lines.append("")
    if lat_line:
        lines.append("=== Latency ===")
        lines.append(lat_line)
        lines.append("")
    lines.append("=== Spike Minutes in FAILING (WARN/ERROR) ===")
    if spikes_f:
        for ts_min, cnt, mult in spikes_f[:10]:
            lines.append(f"  - {ts_min}Z : {cnt} events (~{mult:.1f}× baseline)")
    else:
        lines.append("  (none)")
    return "\n".join(lines)


def parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return parse_ts(value)


def main():
    p = argparse.ArgumentParser(description="LogLens — Root-Cause Log Explorer")
    sub = p.add_subparsers(dest="cmd", required=True)

    # stats
    ps = sub.add_parser("stats", help="Show summary stats for a log file.")
    ps.add_argument("--file", required=True, type=Path)
    ps.add_argument("--since", help='ISO timestamp, e.g. "2025-11-08T13:00:00Z"')
    ps.add_argument("--until", help='ISO timestamp')
    ps.add_argument("--levels", nargs="*", help="Filter by levels, e.g. ERROR WARN INFO")
    ps.add_argument("--keywords", nargs="*", help="Filter by keyword(s)")
    ps.add_argument("--request-id", help="Filter by request id")
    ps.add_argument("--min-latency", type=int, help="Only entries with latency >= ms")

    # filter
    pf = sub.add_parser("filter", help="Print matching log lines (after filters).")
    pf.add_argument("--file", required=True, type=Path)
    pf.add_argument("--since", help='ISO timestamp')
    pf.add_argument("--until", help='ISO timestamp')
    pf.add_argument("--levels", nargs="*", help="Levels")
    pf.add_argument("--keywords", nargs="*", help="Keywords")
    pf.add_argument("--request-id", help="Request id")
    pf.add_argument("--min-latency", type=int, help="Latency >= ms")
    pf.add_argument("--limit", type=int, default=100, help="Max lines to print")

    # diff healthy vs failing
    pd = sub.add_parser("diff", help="Compare healthy vs failing logs.")
    pd.add_argument("--healthy", required=True, type=Path)
    pd.add_argument("--failing", required=True, type=Path)

    args = p.parse_args()

    if args.cmd in ("stats", "filter"):
        entries = load_entries(args.file)
        since = parse_dt(args.since)
        until = parse_dt(args.until)
        out = filter_entries(
            entries,
            since=since,
            until=until,
            levels=args.levels,
            keywords=args.keywords,
            request_id=args.request_id,
            min_latency=args.min_latency,
        )
        if args.cmd == "stats":
            print(summarize(out))
        else:
            for e in out[: args.limit]:
                lat = f" latency={e.latency_ms}ms" if e.latency_ms is not None else ""
                rid = f" req={e.request_id}" if e.request_id else ""
                print(
                    f"{e.ts.isoformat().replace('+00:00','Z')} {e.level} {e.message}{rid}{lat}"
                )

    elif args.cmd == "diff":
        h = load_entries(args.healthy)
        f = load_entries(args.failing)
        print(diff_healthy_vs_failing(h, f))


if __name__ == "__main__":
    main()


# In[ ]:




