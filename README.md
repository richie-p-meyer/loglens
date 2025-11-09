# **LogLens — Root-Cause Log Explorer (Python)**

A lightweight, SRE-focused tool for fast log exploration, anomaly detection, and healthy-vs-failing system comparison.  
Built for real-world debugging workflows used in production environments.

---

##  **Overview**

LogLens helps engineers quickly understand what went wrong inside a distributed system by providing:

- **Fast log loading** from JSONL or plain-text logs  
- **Filtering** (level, keyword, time range, request ID, latency)  
- **Summaries** (counts, top messages, latency percentiles)  
- **Spike detection** (minutes with abnormally high ERROR/WARN events)  
- **Healthy vs failing diff** (new messages, elevated frequency, latency deltas)

**Use cases match real SRE + production support workflows:**

- Incident response  
- Root-cause analysis  
- Latency investigations  
- Debugging multi-service pipelines  
- Reliability engineering exercises  

---

##  **Why I Built This**

This project demonstrates my technical approach to reliability engineering:

- Debugging distributed systems  
- Investigating event patterns and anomalies  
- Surfacing real signal from noisy logs  
- Structuring tools that support on-call workflows  
- Thinking like an SRE (observable systems, fast triage, clear root causes)

I built it as part of my **SRE-track portfolio** while applying for roles in production support, DevOps, and SRE — including Tesla’s **Software Support Engineer — Cell Software** team.

---

##  **Features**

### **1. Log Loading**
Supports:
- `.jsonl` with structured fields  
- Plain-text logs with timestamps and best-effort parsing  

---

### **2. Advanced Filtering**
Filter by:
- Log level (`ERROR`, `WARN`, `INFO`, etc.)  
- Keywords  
- Request ID  
- Latency  
- Time window  

---

### **3. Summaries at a Glance**
Outputs:
- Total log count  
- Distribution by level  
- Top normalized messages  
- Latency percentiles (p50, p95, p99)  
- Spike detection (WARN/ERROR activity)  

---

### **4. Healthy vs Failing Diff**
Shows:
- New messages only appearing in the failing run  
- Messages whose frequency increased significantly  
- Latency shifts (p95 deltas)  
- Critical spike minutes in the failing system  

Perfect for spotting regressions, outages, and service degradation.

---

##  **Tech Stack**

- **Python 3.9+**  
- Standard library only (no external dependencies)  
- Regex parsing, datetime handling, counters, dataclasses  
- Command-line interface using `argparse`  
- Works on macOS, Linux, and Windows  

---

##  **Usage**

### **Stats view**
```bash
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
│   ├── healthy.jsonl
│   └── failing.jsonl

