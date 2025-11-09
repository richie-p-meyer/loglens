LogLens — Root-Cause Log Explorer (Python)

A lightweight, SRE-focused tool for fast log exploration, anomaly detection, and healthy-vs-failing system comparison. Built for real-world debugging workflows used in production environments.

Overview

LogLens helps engineers quickly understand what went wrong inside a distributed system by providing:
-Fast log loading from JSONL or plain-text logs
-Filtering (level, keyword, time range, request ID, latency)
-Summaries (counts, top messages, latency percentiles)
-Spike detection (minutes with abnormally high ERROR/WARN events)
-Healthy vs failing diff (new messages, elevated frequency, latency deltas)

Use cases match real SRE + production support workflows, including:

-Incident response
-Root-cause analysis
-Latency investigations
-Debugging multi-service pipelines
-Reliability engineering exercises

Why I Built This

This project demonstrates my technical approach to reliability engineering:
-Debugging distributed systems
-Investigating event patterns + anomalies
-Surfacing real signal from noisy logs
-Structuring tools that support on-call workflows

Thinking like an SRE (observable systems, fast triage, clear root causes)

I built it as part of my SRE-track portfolio while applying for roles in production support, DevOps, and SRE, including Tesla's Software Support Engineer — Cell Software team.

Features

1. Log Loading
Supports:
-.jsonl with structured fields
-Plain-text logs with timestamps and best-effort parsing

2. Advanced Filtering

Filter by:
-Log level (ERROR, WARN, INFO, etc.)
-Keywords
-Request ID
-Latency
-Time window

3. Summaries at a Glance

Outputs:
-Total log count
-Distribution by level
-Top normalized messages
-Latency percentiles (p50, p95, p99)
-Spike detection (WARN/ERROR activity)

4. Healthy vs Failing Diff

Shows:
-New messages only appearing in the failing run
-Messages whose frequency increased significantly
-Latency shifts (p95 deltas)
-Critical spike minutes in the failing system
-Perfect for spotting regressions, outages, and service degradation.

Tech Stack

-Python 3.9+
-Standard library only (no external deps)
-Regex parsing, datetime handling, counters, dataclasses
-Command-line interface using argparse
-Works on macOS, Linux, Windows.

Usage
Stats view
python3 loglens.py stats --file sample_logs/failing.jsonl

Filtered view
python3 loglens.py filter --file sample_logs/failing.jsonl --levels ERROR --keywords timeout

Healthy vs failing diff
python3 loglens.py diff --healthy healthy.jsonl --failing failing.jsonl

Project Structure
loglens/
│
├── loglens.py            # Main CLI tool
├── README.md             # This file
│
├── sample_logs/
   ├── healthy.jsonl
   └── failing.jsonl


Sample Output

Summaries

Entries: 4231
By level: ERROR=189, WARN=321, INFO=3721
Top messages:
    -  134 × DB timeout <n>ms
    -   92 × Could not acquire lock <id>
Latency (ms): p50=82, p95=510, p99=1472
Spike minutes:
    - 2025-11-08T13:42Z : 22 events (baseline≈3.4x)


Diff

=== New Messages in FAILING ===
  -   42 × DB timeout <n>ms
  -   11 × state mismatch <id> vs <id>

=== Elevated Messages ===
  -  +24 × failed to write segment <id>

=== Latency ===
p95: healthy=410ms → failing=1270ms (Δ=860ms)

Future Improvements

-Add structured JSON output for API/automation usage
-Add mini web UI for interactive filtering
-Add correlation by request_id across services
-Add Grafana-style ASCII sparkline visualizations
-Add noise suppression for noisy INFO logs
-Allow reading rotated log directories

About the Author — Richard Wilders

-Marine Corps veteran (Afghanistan deployment — mission-critical language ops)
-Data science + distributed system debugging background
-Reliability-minded engineer focused on SRE/DevOps
-Python + SQL + observability enthusiast
-Ten 10-day Vipassana meditation courses → stays calm during incidents
-Based in Reno/Sparks, NV

Connect

GitHub: https://github.com/richie-p-meyer

LinkedIn: https://www.linkedin.com/in/richard-wilders-915395106/