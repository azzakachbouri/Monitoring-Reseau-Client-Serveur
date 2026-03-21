import socket
import threading
import time
import csv
from datetime import datetime

# Server configuration
HOST = '127.0.0.1'
PORT = 5050
ACTIVE_WINDOW = 30  # 3 × T seconds (T = 10s, so 30s window for active agents)
STATS_INTERVAL = 10
CSV_FILE = 'stats_export.csv'

# Global state
agents_lock = threading.Lock()
agents = {}  # agent_id -> {hostname, last_report_time, cpu_pct, ram_mb, protocol, addr}
metrics_lock = threading.Lock()
total_reports = 0


def write_csv_row(timestamp, num_active, avg_cpu, avg_ram):
    """Append one statistics line to CSV export file."""
    file_exists = False
    try:
        with open(CSV_FILE, 'r', encoding='utf-8'):
            file_exists = True
    except FileNotFoundError:
        file_exists = False

    with open(CSV_FILE, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(['timestamp', 'active_agents', 'avg_cpu_pct', 'avg_ram_mb', 'total_reports'])
        with metrics_lock:
            writer.writerow([timestamp, num_active, f"{avg_cpu:.2f}", f"{avg_ram:.2f}", total_reports])


def validate_report(cpu_pct, ram_mb):
    """Validate metric ranges."""
    return 0 <= cpu_pct <= 100 and ram_mb >= 0


def process_message(message, addr, protocol='TCP'):
    """Process one protocol message and return (response, should_close)."""
    global total_reports

    message = message.strip()
    if not message:
        return 'ERROR', False

    print(f"[{protocol} {addr}] Received: {message}")
    tokens = message.split()

    if message.startswith('HELLO'):
        if len(tokens) < 3:
            print(f"[{protocol} {addr}] ERROR: Malformed HELLO message")
            return 'ERROR', False

        agent_id = tokens[1]
        hostname = tokens[2]

        with agents_lock:
            agents[agent_id] = {
                'hostname': hostname,
                'last_report_time': time.time(),
                'cpu_pct': 0.0,
                'ram_mb': 0.0,
                'protocol': protocol,
                'addr': str(addr)
            }

        print(f"[{protocol} {addr}] Agent registered: {agent_id} ({hostname})")
        return 'OK', False

    if message.startswith('REPORT'):
        if len(tokens) < 5:
            print(f"[{protocol} {addr}] ERROR: Malformed REPORT message")
            return 'ERROR', False

        try:
            agent_id = tokens[1]
            _timestamp = int(tokens[2])
            cpu_pct = float(tokens[3])
            ram_mb = float(tokens[4])

            if not validate_report(cpu_pct, ram_mb):
                print(f"[{protocol} {addr}] ERROR: Invalid metric values")
                return 'ERROR', False

            with agents_lock:
                if agent_id in agents:
                    agents[agent_id]['last_report_time'] = time.time()
                    agents[agent_id]['cpu_pct'] = cpu_pct
                    agents[agent_id]['ram_mb'] = ram_mb
                    agents[agent_id]['protocol'] = protocol
                    agents[agent_id]['addr'] = str(addr)
                else:
                    print(f"[{protocol} {addr}] WARNING: Report from unregistered agent {agent_id}")
                    return 'ERROR', False

            with metrics_lock:
                total_reports += 1

            print(f"[{protocol} {addr}] Report recorded: {agent_id} CPU={cpu_pct}% RAM={ram_mb}MB")
            return 'OK', False

        except ValueError:
            print(f"[{protocol} {addr}] ERROR: Invalid metric format")
            return 'ERROR', False

    if message.startswith('BYE'):
        if len(tokens) < 2:
            print(f"[{protocol} {addr}] ERROR: Malformed BYE message")
            return 'ERROR', False

        agent_id = tokens[1]
        with agents_lock:
            if agent_id in agents:
                del agents[agent_id]

        print(f"[{protocol} {addr}] Agent unregistered: {agent_id}")
        return 'OK', protocol == 'TCP'

    print(f"[{protocol} {addr}] ERROR: Unknown command")
    return 'ERROR', False


def is_agent_active(agent_id):
    """Check if an agent is still active based on the activity window."""
    with agents_lock:
        if agent_id not in agents:
            return False
        last_report = agents[agent_id]['last_report_time']
        return (time.time() - last_report) < ACTIVE_WINDOW


def handle_client(conn, addr):
    """Handle a single client connection in a separate thread."""
    try:
        buffer = ''
        while True:
            data = conn.recv(1024)
            if not data:
                break
            buffer += data.decode('utf-8')

            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                response, should_close = process_message(line, addr, protocol='TCP')
                conn.send((response + '\n').encode('utf-8'))
                if should_close:
                    return
    
    except Exception as e:
        print(f"[TCP {addr}] Exception: {e}")
    
    finally:
        conn.close()
        print(f"[TCP {addr}] Connection closed")


def udp_listener(udp_socket):
    """Handle UDP datagrams."""
    while True:
        try:
            data, addr = udp_socket.recvfrom(2048)
            message = data.decode('utf-8').strip()
            response, _ = process_message(message, addr, protocol='UDP')
            udp_socket.sendto((response + '\n').encode('utf-8'), addr)
        except Exception as e:
            print(f"[UDP] Listener exception: {e}")


def inactive_cleanup_thread():
    """Remove inactive agents periodically."""
    while True:
        time.sleep(5)
        now = time.time()
        removed_agents = []

        with agents_lock:
            for agent_id, info in list(agents.items()):
                if (now - info['last_report_time']) >= ACTIVE_WINDOW:
                    removed_agents.append((agent_id, info['hostname']))
                    del agents[agent_id]

        for agent_id, hostname in removed_agents:
            print(f"[CLEANUP] Agent inactive removed: {agent_id} ({hostname})")


def statistics_thread():
    """Periodically display statistics about active agents."""
    while True:
        time.sleep(STATS_INTERVAL)
        
        with agents_lock:
            active_agents = dict(agents)
            num_active = len(active_agents)

            if num_active > 0:
                avg_cpu = sum(info['cpu_pct'] for info in active_agents.values()) / num_active
                avg_ram = sum(info['ram_mb'] for info in active_agents.values()) / num_active
            else:
                avg_cpu = 0.0
                avg_ram = 0.0
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n[{timestamp}] ===== STATISTICS =====")
        print(f"Active Agents: {num_active}")
        print(f"Average CPU: {avg_cpu:.2f}%")
        print(f"Average RAM: {avg_ram:.2f}MB")
        with metrics_lock:
            print(f"Total REPORT received: {total_reports}")
        if active_agents:
            for agent_id, info in active_agents.items():
                print(
                    f"  {agent_id} ({info['hostname']}) [{info['protocol']}]: "
                    f"CPU={info['cpu_pct']:.1f}% RAM={info['ram_mb']:.0f}MB"
                )
        print("=" * 23 + "\n")

        try:
            write_csv_row(timestamp, num_active, avg_cpu, avg_ram)
        except Exception as e:
            print(f"[CSV] Export error: {e}")


def main():
    """Start the server."""
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tcp_socket.bind((HOST, PORT))
    tcp_socket.listen(10)

    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp_socket.bind((HOST, PORT))

    print(f"Server listening on {HOST}:{PORT} (TCP + UDP)")
    print(f"Active window: {ACTIVE_WINDOW} seconds")
    print(f"CSV export file: {CSV_FILE}\n")

    threading.Thread(target=statistics_thread, daemon=True).start()
    threading.Thread(target=inactive_cleanup_thread, daemon=True).start()
    threading.Thread(target=udp_listener, args=(udp_socket,), daemon=True).start()

    try:
        while True:
            conn, addr = tcp_socket.accept()
            print(f"[TCP] New connection from {addr}")

            client_thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            client_thread.start()

    except KeyboardInterrupt:
        print("\nServer shutting down...")

    finally:
        tcp_socket.close()
        udp_socket.close()


if __name__ == '__main__':
    main()
