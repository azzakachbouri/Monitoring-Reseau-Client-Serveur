# 🛡️ Client-Server Network Monitoring — TCP Proxy with Scan/Flood Detection + Splunk

![CI](https://github.com/azzakachbouri/Monitoring-Reseau-Client-Serveur/actions/workflows/ci.yml/badge.svg)

[🇫🇷 Version française](README.md) | 🇬🇧 English

> A lightweight TCP proxy that sits in front of any service, detects port scans and connection floods in real time, classifies them against **MITRE ATT&CK** (T1046, T1498), auto-blocks offending IPs (fail-open on internal errors), and forwards every event to **Splunk** via HTTP Event Collector. Ships with Docker Compose, a Flask/Chart.js monitoring dashboard for the underlying client-server layer, and 28 automated tests.

Built by **Azza Kachbouri** and **Dhia Selmi**.

---

## 📋 Table of contents

- [1. Project at a glance](#1-project-at-a-glance)
- [2. Demo](#2-demo)
- [3. Architecture](#3-architecture)
- [4. Anomaly detection — scan vs flood](#4-anomaly-detection--scan-vs-flood)
- [5. Splunk forwarder (HEC)](#5-splunk-forwarder-hec)
- [6. Installation and running it](#6-installation-and-running-it)
- [7. The client-server monitoring layer (legacy)](#7-the-client-server-monitoring-layer-legacy)
- [8. Tests](#8-tests)
- [9. Project structure](#9-project-structure)
- [10. What's left to do](#10-whats-left-to-do)
- [11. Authors](#11-authors)

---

## 1. Project at a glance

The project started as a classic networking assignment (client-server TCP/UDP monitoring), then got repositioned into something closer to a real network security tool:

**A TCP proxy that can be attached to any service**, which:

- 🔍 **Detects** service scans (short, 0-byte connections — the typical `nmap -sT` signature) and connection floods/DoS (abnormal connection rate)
- 🏷️ **Classifies** every anomaly against **MITRE ATT&CK** (T1046 – Network Service Discovery, T1498 – Network Denial of Service)
- 🚫 **Auto-blocks** the source IP, with a **fail-open** design: if the detector crashes, traffic keeps flowing instead of cutting off legitimate clients
- 📤 **Forwards events in real time** to **Splunk** (HTTP Event Collector), with no loss or duplication even if Splunk is temporarily unreachable
- 🔒 Supports end-to-end **TLS** (client → proxy → server)
- 🐳 Deploys entirely through **Docker Compose** (proxy, server, dashboard, Splunk, forwarder)

Everything is covered by automated tests (28 in total) and designed to run entirely on free tooling locally.

---

## 2. Demo

### Live detection

**Scan detected** (`SCAN_DETECTED`, T1046) — several 0-byte probes from the same IP:

![Scan detected](docs/screenshots/scan_detected.png)

**Flood detected** (`FLOOD_DETECTED`, T1498) — abnormal connection rate:

![Flood detected](docs/screenshots/flood_detected.png)

### Structured events

Every event is written as JSON (`events.jsonl`) with its MITRE ATT&CK technique:

![JSON events](docs/screenshots/events_jsonl.png)

### In Splunk

Searching security events forwarded in real time:

![Splunk search](docs/screenshots/splunk_search.png)

Breakdown by MITRE ATT&CK technique:

![MITRE breakdown](docs/screenshots/splunk_mitre_chart.png)

Detection timeline:

![Splunk timeline](docs/screenshots/splunk_timeline.png)

### Reproduce this demo yourself

```bash
# Terminal 1
python server.py

# Terminal 2
python proxy.py --listen-port 6000 --target-port 5051 --tls-cert server.crt

# Terminal 3 — simulate a scan
python scripts/simulate_scan.py --port 6000 --count 6 --delay 0.2

# Terminal 3 — simulate a flood (lower the threshold if your machine is fast, otherwise it may never trigger)
python scripts/simulate_flood.py --port 6000 --count 150
```

---

## 3. Architecture

```
                 ┌──────────────┐        ┌──────────────┐
  Client/Agent ──▶│  proxy.py    │───────▶│  server.py    │
  (or nmap, etc.) │  (TCP proxy) │  TLS   │  (TCP/UDP)    │
                 └──────┬───────┘        └──────────────┘
                        │ detects / blocks
                        ▼
                 ┌──────────────┐
                 │security_core │  → events.jsonl (MITRE ATT&CK)
                 └──────┬───────┘
                        ▼
                 ┌──────────────┐        ┌──────────────┐
                 │splunk_forward│───────▶│   Splunk     │
                 │  (HEC)       │  HTTPS │  (dashboards) │
                 └──────────────┘        └──────────────┘
```

The proxy is **agnostic to the protected service**: it relays any TCP traffic while observing it, with no dependency on the application-level protocol.

---

## 4. Anomaly detection — scan vs flood

A scan and a flood don't have the same network signature, so two separate mechanisms handle them:

|                       | Scan (T1046)                                            | Flood (T1498)                           |
| --------------------- | ------------------------------------------------------- | --------------------------------------- |
| **Signature**         | Very short connection (< 0.5s), **0 bytes** transferred | Abnormal rate of new connections/second |
| **Detected at**       | Connection close                                        | Connection open                         |
| **Default threshold** | 5 probes in 10s                                         | 100 connections/s                       |
| **Action**            | IP blocked for 60s                                      | IP blocked for 60s                      |

All thresholds are externalized in `config.py` / `.env` — nothing is hardcoded.

**Fail-open:** every call to the detector from `proxy.py` is wrapped in a `try/except`. If `security_core.py` raises an exception, traffic keeps flowing instead of being blocked by mistake — a detection bug should never turn into a denial of service for legitimate users.

---

## 5. Splunk forwarder (HEC)

`splunk_forwarder.py` continuously tails `events.jsonl` (lightweight polling, no direct dependency on the proxy) and forwards each new event to Splunk via HTTP Event Collector.

- **No loss, no duplicates**: the read offset only advances once Splunk confirms receipt (HTTP 200 + `code: 0`). If Splunk is unreachable, it retries on the next pass.
- **Batched**: up to 50 events per HTTP request.

### Useful SPL queries

```spl
# All security events
source="monitoring-reseau-client-serveur"

# Breakdown by MITRE technique
source="monitoring-reseau-client-serveur" (type=SCAN_DETECTED OR type=FLOOD_DETECTED)
| stats count by mitre_technique, type

# Timeline
source="monitoring-reseau-client-serveur" | timechart span=1m count by type

# Top blocked IPs
source="monitoring-reseau-client-serveur" (type=SCAN_DETECTED OR type=FLOOD_DETECTED)
| stats count by source_ip, type | sort -count
```

---

## 6. Installation and running it

### Option A — Docker Compose (recommended, all-in-one)

```bash
copy .env.example .env   # then fill in AGENT_AUTH_TOKEN, SPLUNK_PASSWORD, SPLUNK_HEC_TOKEN
docker compose up --build
```

| Service              | URL                    |
| -------------------- | ---------------------- |
| Monitoring dashboard | http://localhost:8000  |
| TCP/UDP server       | localhost:5051         |
| Proxy (TLS)          | localhost:6000         |
| Splunk Web           | http://localhost:8001  |
| Splunk HEC           | https://localhost:8088 |

### Option B — Manual

```bash
pip install -r requirements.txt
python generate_cert.py          # generates server.crt / server.key
python server.py                 # terminal 1
python proxy.py --listen-port 6000 --target-port 5051 --tls-cert server.crt   # terminal 2
python splunk_forwarder.py       # terminal 3 (needs SPLUNK_HEC_TOKEN in .env)
```

---

## 7. The client-server monitoring layer (legacy)

The proxy protects a TCP/UDP monitoring server originally built as a networking assignment: agents (`client.py` / `client_simple.py`) periodically report CPU/RAM to the server, which aggregates the data and exposes a real-time dashboard (Flask + Chart.js on port 8000).

- Protocol: `HELLO` / `REPORT` / `HEALTH` / `BYE`, TCP and UDP simultaneously
- Auto-cleanup of inactive agents (3×T window)
- Automatic alerts: `CPU_HIGH`, `AGENT_INACTIVE`, `ERROR_STORM`
- CSV export of statistics

---

## 8. Tests

```bash
python test_suite.py            # 17 tests — client-server monitoring layer
python test_security_core.py    # 7 tests — scan/flood detector
python test_splunk_forwarder.py # 7 tests — Splunk forwarder (mocked, no live Splunk needed)
```

**28 tests in total**, all automated. `test_security_core.py` and `test_splunk_forwarder.py` need neither a running server nor a live Splunk instance — the logic is tested in isolation.

> ⚠️ `test_suite.py` requires `server.py` to be running first.

---

## 9. Project structure

```
.
├── server.py                  # Serveur TCP + UDP (monitoring)
├── client.py / client_simple.py   # Agents
├── flask_api.py                # Dashboard web
├── proxy.py                    # Proxy TCP attachable — détecte, bloque, relaie
├── security_core.py            # Détecteur scan/flood + tags MITRE ATT&CK
├── splunk_forwarder.py         # Forwarder events.jsonl → Splunk HEC
├── config.py                   # Toute la configuration (seuils, tokens, URLs)
├── events_store.py             # Stockage/gestion des events (lecture/écriture events.jsonl)
├── generate_cert.py            # Génère server.crt / server.key (TLS)
├── generate_rapport.py         # Génère security_report.md
├── scripts/
│   ├── simulate_scan.py        # Simule un scan pour la démo
│   └── simulate_flood.py       # Simule un flood pour la démo
├── templates/                  # Templates HTML du dashboard (flask_api.py)
├── test_suite.py                # Tests monitoring (17)
├── test_security_core.py        # Tests détecteur (7)
├── test_splunk_forwarder.py     # Tests forwarder (7)
├── docker-compose.yml
├── Dockerfile
├── requirements.txt             # Dépendances Python
├── run_demo.bat                 # Lance la démo complète (Windows)
├── .github/workflows/ci.yml     # Pipeline CI (tests + lint automatiques)
└── docs/screenshots/            # Captures pour ce README
```

---

## 10. Authors

**Azza Kachbouri** — anomaly detector (scan/flood, MITRE ATT&CK tagging), Splunk forwarder
**Dhia Selmi** — TCP proxy, authentication, TLS, Docker
