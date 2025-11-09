# LogLens — Root-Cause Log Explorer (CLI)

A small, no-dependency Python CLI for triaging logs like an SRE:
- Filter by **time window**, **level**, **keywords**, **request_id**, **latency**
- Quick **stats**: levels, top messages, latency p50/p95/p99
- **Spike** scan: finds minutes with unusual WARN/ERROR bursts
- **Diff** healthy vs failing logs: new/elevated messages, latency shift, spikes

## Install / Run
```bash
python3 loglens.py --help
