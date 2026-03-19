# Network Monitoring System - TCP Client-Server Architecture

## Overview

This is a distributed network monitoring application where multiple clients (agents) collect CPU and RAM metrics and send them to a central server for aggregation and analysis.

## Protocol Specification

### Messages Client → Server

- **HELLO \<agent_id\> \<hostname\>** - Agent registration
- **REPORT \<agent_id\> \<timestamp\> \<cpu_pct\> \<ram_mb\>** - Metrics report
- **BYE \<agent_id\>** - Graceful disconnect

### Responses Server → Client

- **OK** - Message accepted
- **ERROR** - Message rejected

### Constraints

- `agent_id`: alphanumeric, no spaces
- `cpu_pct`: float 0-100
- `ram_mb`: float ≥ 0
- Agent is active if REPORT received within 30 seconds

## Setup

### Requirements

```bash
pip install psutil
```

### Windows Batch Script

Create `run_all.bat`:

```batch
@echo off
start python server.py
timeout /t 2
start python client.py
```

Then run:

```bash
run_all.bat
```

## Running Manually

### Terminal 1 - Start Server

```bash
python server.py
```

Server output:

```
Server listening on 127.0.0.1:5050
Active window: 30 seconds

New connection from ('127.0.0.1', 54321)
[('127.0.0.1', 54321)] Received: HELLO agent1 WORKSTATION
[('127.0.0.1', 54321)] Agent registered: agent1 (WORKSTATION)

[2026-03-19 14:30:45] ===== STATISTICS =====
Active Agents: 1
Average CPU: 25.50%
Average RAM: 2048.00MB
  agent1 (WORKSTATION): CPU=25.5% RAM=2048MB
```

### Terminal 2 - Start Client

```bash
python client.py
```

Client output:

```
Enter agent ID (default: agent1): agent1

Agent Configuration:
  ID: agent1
  Hostname: WORKSTATION
  Report Interval: 10s
  Connecting to 127.0.0.1:5050

Connected to server

Successfully registered as agent1

Agent is running... Press Ctrl+C to disconnect

[14:30:35] Report sent: CPU=25.5% RAM=2048MB
[14:30:45] Report sent: CPU=26.2% RAM=2100MB
```

## Testing Scenarios

### 1. Single Client Connection

```bash
# Terminal 1
python server.py

# Terminal 2
python client.py
# Enter: agent1
# Wait 30 seconds, then Ctrl+C
```

### 2. Multiple Clients

```bash
# Terminal 1
python server.py

# Terminal 2
python client.py
# Enter: agent1

# Terminal 3
python client.py
# Enter: agent2

# Terminal 4
python client.py
# Enter: agent3
```

### 3. Malformed Messages

Modify client to send bad REPORT:

```python
# Send manually
sock.send(b'REPORT agent1 999 150 -50\n')  # Invalid CPU/RAM
```

### 4. Sudden Client Disconnection

```bash
# Run client, then kill process after registration
# Server should detect timeout in 30 seconds
```

### 5. Verify Statistics

Server displays every 10 seconds with:

- Number of active agents
- Average CPU usage
- Average RAM usage
- Per-agent details

## Architecture

### Server (server.py)

- **Main thread**: Accepts connections
- **Client handler threads**: One per connection
- **Statistics thread**: Displays aggregate metrics every 10s
- **Global state**: Thread-safe agent dictionary with lock

### Client (client.py)

- **Main thread**: Handles user input and connection
- **Report thread**: Sends metrics every 10s
- **Metrics collection**: Uses psutil for real system stats

## Configuration

Edit constants in source code:

**server.py:**

```python
HOST = '127.0.0.1'
PORT = 5050
ACTIVE_WINDOW = 30  # seconds
```

**client.py:**

```python
HOST = '127.0.0.1'
PORT = 5050
REPORT_INTERVAL = 10  # seconds
```

## Error Handling

| Scenario           | Behavior                              |
| ------------------ | ------------------------------------- |
| Server not running | Client: "Connection refused"          |
| Malformed message  | Server: Sends ERROR, continues        |
| Client crash       | Server: Detects in 30s, removes agent |
| Network loss       | Connection closes, both sides cleanup |

## Metrics

CPU and RAM metrics are collected using `psutil`:

- **CPU**: System-wide usage percentage (0-100)
- **RAM**: Total used RAM in MB

## Threading Model

```
Server:
├─ Main (listener loop)
├─ Client-1 handler
├─ Client-2 handler
├─ Client-3 handler
└─ Statistics (periodic display)

Client:
├─ Main (connection + input)
└─ Reporter (metrics sender)
```

## Known Limitations

- No authentication/encryption
- IPv4 only
- Requires psutil for metrics
- No database persistence
- In-memory storage only

## Extensions

1. **UDP Mode**: Add parallel UDP sender for comparison
2. **UUID Support**: Use `uuid.uuid4()` instead of string IDs
3. **CSV Export**: Dump statistics to file
4. **Inactivity Detection**: Auto-remove agents after timeout
5. **Stress Testing**: Simulate rapid reports/connections

## Troubleshooting

**Port already in use:**

```bash
# Find process on port 5050
netstat -ano | findstr :5050
# Kill process
taskkill /PID <PID> /F
```

**psutil not found:**

```bash
pip install --upgrade pip
pip install psutil
```

**Connection refused:**

- Ensure server started first
- Check firewall allows localhost:5050

## Files

- `server.py` - Central monitoring server
- `client.py` - Agent client
- `README.md` - This file
