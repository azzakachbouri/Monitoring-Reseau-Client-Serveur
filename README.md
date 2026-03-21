# 🖥️ Network Monitoring — Client–Server with TCP Sockets

> A distributed network monitoring application built with a TCP client–server architecture.  
> Each agent collects local system metrics (CPU, RAM) and reports them to a central server in real time.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Protocol Specification](#protocol-specification)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Possible Extensions](#possible-extensions)
- [Authors](#authors)

---

## Overview

This project implements a **distributed network monitoring system** using raw TCP sockets and threads. It was developed as part of the **TP RT2 – Réseaux** module.

Key capabilities:

- Multiple agents connect simultaneously to a central server
- Each agent reports CPU usage and RAM every `T` seconds
- The server aggregates metrics, tracks active agents, and computes global averages
- The server never crashes due to a single client error (fault-tolerant design)

---

## Architecture

```
┌──────────────┐        TCP        ┌─────────────────────────┐
│  Agent 1     │ ────────────────► │                         │
├──────────────┤                   │   Server (Collector)    │
│  Agent 2     │ ────────────────► │                         │
├──────────────┤                   │  - Thread per client    │
│  Agent N     │ ────────────────► │  - Active agent list    │
└──────────────┘                   │  - Global stats (avg)   │
                                   └─────────────────────────┘
```

### Client (Agent)

Each agent:

1. Connects to the server via TCP
2. Sends a `HELLO` registration message
3. Periodically sends `REPORT` messages (CPU %, RAM MB) every `T` seconds
4. Sends a `BYE` message on clean disconnect

### Server (Collector)

The server:

1. Listens for and accepts multiple simultaneous connections
2. Spawns a dedicated thread per client
3. Maintains a live registry of active agents
4. Periodically computes: active agent count, average CPU, average RAM
5. Handles malformed messages and disconnections gracefully

---

## Protocol Specification

### Client → Server Messages

| Message  | Format                                             | Description         |
| -------- | -------------------------------------------------- | ------------------- |
| `HELLO`  | `HELLO <agent_id> <hostname>`                      | Agent registration  |
| `REPORT` | `REPORT <agent_id> <timestamp> <cpu_pct> <ram_mb>` | Metric report       |
| `BYE`    | `BYE <agent_id>`                                   | Clean disconnection |

### Server → Client Responses

| Response | Meaning                       |
| -------- | ----------------------------- |
| `OK`     | Message accepted              |
| `ERROR`  | Malformed or rejected message |

### Constraints

- `agent_id` — no spaces allowed
- `cpu_pct` — float in range `[0.0, 100.0]`
- `ram_mb` — float ≥ `0.0`
- An agent is considered **active** if a `REPORT` was received within the last `3 × T` seconds

### Example Exchange

```
Client  →  HELLO agent1 PC-LAB
Server  →  OK

Client  →  REPORT agent1 1700000000 25.5 2048
Server  →  OK

Client  →  BYE agent1
Server  →  OK
```

---

## Prerequisites

**Python version**

```
Python 3.8+
```

Only **standard library** modules are used:

- `socket`
- `threading`
- `time`
- `datetime`

No external dependencies required — no `pip install` needed.

---

## Getting Started

**1. Clone the repository**

```bash
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>
```

**2. Start the server**

```bash
python server.py
```

The server will start listening on `localhost:9999` by default.

**3. Start one or more agents** (in separate terminals)

```bash
python client.py --id agent1 --host localhost --port 9999 --interval 5
```

| Argument     | Default     | Description                       |
| ------------ | ----------- | --------------------------------- |
| `--id`       | `agent1`    | Unique agent identifier           |
| `--host`     | `localhost` | Server address                    |
| `--port`     | `9999`      | Server port                       |
| `--interval` | `5`         | Reporting interval in seconds (T) |

---

## Usage

### Running multiple agents simultaneously

Open several terminals and run:

```bash
# Terminal 1
python client.py --id agent1 --host localhost --port 9999 --interval 5

# Terminal 2
python client.py --id agent2 --host localhost --port 9999 --interval 3

# Terminal 3
python client.py --id agent3 --host localhost --port 9999 --interval 7
```

The server console will display live statistics:

```
[SERVER] Active agents: 3
[SERVER] Average CPU:   34.2%
[SERVER] Average RAM:   1876.5 MB
```

### Stopping an agent

Press `Ctrl+C` in the agent terminal. The agent will send a `BYE` message before exiting.

---

## Testing

The following test scenarios must be demonstrated:

| #   | Test Case                     | Expected Result                                        |
| --- | ----------------------------- | ------------------------------------------------------ |
| 1   | Single client connection      | Server registers agent, responds `OK`                  |
| 2   | Multiple simultaneous clients | All agents handled concurrently via threads            |
| 3   | Abrupt client disconnect      | Server detects timeout, removes agent from active list |
| 4   | Malformed message sent        | Server responds `ERROR`, stays running                 |
| 5   | Average calculation           | Server computes correct CPU/RAM averages               |
| 6   | Agent inactivity (> 3×T)      | Agent marked as inactive automatically                 |

To run all tests:

```bash
python tests.py
```

---

## Project Structure

```
.
├── server.py          # Server — accepts connections, manages threads & stats
├── client.py          # Client agent — collects and sends metrics
├── tests.py           # Automated test suite
├── README.md          # This file
└── rapport/
    ├── rapport.pdf    # Technical report (architecture, protocol, choices)
    └── tests.pdf      # Test report with screenshots
```

---

## Possible Extensions

| Extension               | Description                                                |
| ----------------------- | ---------------------------------------------------------- |
| 🔁 UDP Mode             | Add a UDP transport option and compare reliability vs TCP  |
| 🕵️ Inactivity Detection | Auto-flag and alert on silent agents                       |
| 📊 CSV Export           | Periodically dump stats to a `.csv` file for analysis      |
| 🔑 UUID Agents          | Replace manual `agent_id` with auto-generated UUIDs        |
| 💥 Stress Test          | Simulate a flood attack with mass `REPORT` sending         |
| 🌐 Web Dashboard        | Add a simple HTTP endpoint to visualize stats in a browser |
| 🔐 Auth Layer           | Add a shared secret / token for agent authentication       |

---

## Authors

AZZA KACHBOURI \_ DHIA SELMI
Developed as part of **Mini-Projet Réseaux — TP RT2**
