import socket
import threading
import time
from datetime import datetime
import sys

# Server configuration
HOST = '127.0.0.1'
PORT = 5050
ACTIVE_WINDOW = 30  # 3 × T seconds (T = 10s, so 30s window for active agents)

# Global state
agents_lock = threading.Lock()
agents = {}  # agent_id -> {hostname, last_report_time, cpu_pct, ram_mb}


def is_agent_active(agent_id):
    """Check if an agent is still active based on the activity window."""
    with agents_lock:
        if agent_id not in agents:
            return False
        last_report = agents[agent_id]['last_report_time']
        return (time.time() - last_report) < ACTIVE_WINDOW


def handle_client(conn, addr):
    """Handle a single client connection in a separate thread."""
    agent_id = None
    try:
        while True:
            # Receive data from client
            data = conn.recv(1024)
            if not data:
                break
            
            message = data.decode('utf-8').strip()
            print(f"[{addr}] Received: {message}")
            
            tokens = message.split()
            
            # Parse HELLO message
            if message.startswith('HELLO'):
                if len(tokens) < 3:
                    print(f"[{addr}] ERROR: Malformed HELLO message")
                    conn.send(b'ERROR\n')
                    continue
                
                agent_id = tokens[1]
                hostname = tokens[2]
                
                with agents_lock:
                    agents[agent_id] = {
                        'hostname': hostname,
                        'last_report_time': time.time(),
                        'cpu_pct': 0.0,
                        'ram_mb': 0.0
                    }
                
                print(f"[{addr}] Agent registered: {agent_id} ({hostname})")
                conn.send(b'OK\n')
            
            # Parse REPORT message
            elif message.startswith('REPORT'):
                if len(tokens) < 5:
                    print(f"[{addr}] ERROR: Malformed REPORT message")
                    conn.send(b'ERROR\n')
                    continue
                
                try:
                    agent_id = tokens[1]
                    timestamp = int(tokens[2])
                    cpu_pct = float(tokens[3])
                    ram_mb = float(tokens[4])
                    
                    # Validate metrics
                    if cpu_pct < 0 or cpu_pct > 100 or ram_mb < 0:
                        print(f"[{addr}] ERROR: Invalid metric values")
                        conn.send(b'ERROR\n')
                        continue
                    
                    with agents_lock:
                        if agent_id in agents:
                            agents[agent_id]['last_report_time'] = time.time()
                            agents[agent_id]['cpu_pct'] = cpu_pct
                            agents[agent_id]['ram_mb'] = ram_mb
                        else:
                            print(f"[{addr}] WARNING: Report from unregistered agent {agent_id}")
                            conn.send(b'ERROR\n')
                            continue
                    
                    print(f"[{addr}] Report recorded: {agent_id} CPU={cpu_pct}% RAM={ram_mb}MB")
                    conn.send(b'OK\n')
                
                except ValueError:
                    print(f"[{addr}] ERROR: Invalid metric format")
                    conn.send(b'ERROR\n')
            
            # Parse BYE message
            elif message.startswith('BYE'):
                if len(tokens) < 2:
                    print(f"[{addr}] ERROR: Malformed BYE message")
                    conn.send(b'ERROR\n')
                    continue
                
                agent_id = tokens[1]
                with agents_lock:
                    if agent_id in agents:
                        del agents[agent_id]
                
                print(f"[{addr}] Agent unregistered: {agent_id}")
                conn.send(b'OK\n')
                break
            
            else:
                print(f"[{addr}] ERROR: Unknown command")
                conn.send(b'ERROR\n')
    
    except Exception as e:
        print(f"[{addr}] Exception: {e}")
    
    finally:
        conn.close()
        if agent_id and agent_id in agents:
            with agents_lock:
                if agent_id in agents:
                    del agents[agent_id]
        print(f"[{addr}] Connection closed")


def statistics_thread():
    """Periodically display statistics about active agents."""
    while True:
        time.sleep(10)  # Display stats every 10 seconds
        
        with agents_lock:
            active_agents = {aid: info for aid, info in agents.items() 
                           if (time.time() - info['last_report_time']) < ACTIVE_WINDOW}
            
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
        if active_agents:
            for agent_id, info in active_agents.items():
                print(f"  {agent_id} ({info['hostname']}): CPU={info['cpu_pct']:.1f}% RAM={info['ram_mb']:.0f}MB")
        print("=" * 23 + "\n")


def main():
    """Start the server."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    
    print(f"Server listening on {HOST}:{PORT}")
    print(f"Active window: {ACTIVE_WINDOW} seconds\n")
    
    # Start statistics thread
    stats_thread = threading.Thread(target=statistics_thread, daemon=True)
    stats_thread.start()
    
    try:
        while True:
            conn, addr = server_socket.accept()
            print(f"New connection from {addr}")
            
            # Handle each client in a separate thread
            client_thread = threading.Thread(target=handle_client, args=(conn, addr))
            client_thread.daemon = True
            client_thread.start()
    
    except KeyboardInterrupt:
        print("\nServer shutting down...")
    
    finally:
        server_socket.close()


if __name__ == '__main__':
    main()
