import socket
import threading
import time
import psutil
import uuid
from datetime import datetime

# Server configuration
HOST = '127.0.0.1'
PORT = 5050
REPORT_INTERVAL = 10  # Send report every 10 seconds


def get_system_metrics():
    """Collect CPU and RAM usage metrics."""
    try:
        cpu_pct = psutil.cpu_percent(interval=1)
        ram_info = psutil.virtual_memory()
        ram_mb = ram_info.used / (1024 * 1024)  # Convert to MB
        return cpu_pct, ram_mb
    except Exception as e:
        print(f"Error collecting metrics: {e}")
        return 0.0, 0.0


def send_message_tcp(sock, message):
    """Send a message to the server and receive response."""
    try:
        sock.send((message + '\n').encode('utf-8'))
        response = sock.recv(1024).decode('utf-8').strip()
        return response
    except Exception as e:
        print(f"Error communicating with server: {e}")
        return None


def send_message_udp(sock, message):
    """Send a UDP message and receive one response datagram."""
    try:
        sock.send(message.encode('utf-8'))
        response = sock.recv(1024).decode('utf-8').strip()
        return response
    except Exception as e:
        print(f"Error communicating with server (UDP): {e}")
        return None


def report_thread(sock, agent_id, protocol='TCP'):
    """Periodically send REPORT messages."""
    while True:
        try:
            time.sleep(REPORT_INTERVAL)
            
            cpu_pct, ram_mb = get_system_metrics()
            timestamp = int(time.time())
            
            message = f"REPORT {agent_id} {timestamp} {cpu_pct:.1f} {ram_mb:.0f}"
            if protocol == 'UDP':
                response = send_message_udp(sock, message)
            else:
                response = send_message_tcp(sock, message)
            
            if response == 'OK':
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Report sent: CPU={cpu_pct:.1f}% RAM={ram_mb:.0f}MB")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Report rejected: {response}")
        
        except Exception as e:
            print(f"Error in report thread: {e}")
            break


def run_attack_mode(sock, agent_id, protocol, burst_count):
    """Send a massive burst of REPORT messages."""
    print(f"\n[ATTACK] Sending {burst_count} REPORT messages using {protocol}...")
    start = time.time()
    ok_count = 0

    for _ in range(burst_count):
        cpu_pct, ram_mb = get_system_metrics()
        timestamp = int(time.time())
        message = f"REPORT {agent_id} {timestamp} {cpu_pct:.1f} {ram_mb:.0f}"

        if protocol == 'UDP':
            response = send_message_udp(sock, message)
        else:
            response = send_message_tcp(sock, message)

        if response == 'OK':
            ok_count += 1

    elapsed = time.time() - start
    print(f"[ATTACK] Completed in {elapsed:.2f}s - accepted: {ok_count}/{burst_count}")


def main():
    """Main client function."""
    # Get agent configuration
    generated_uuid = str(uuid.uuid4())
    agent_id = input(f"Enter agent ID (default UUID: {generated_uuid}): ").strip() or generated_uuid
    protocol = input("Protocol TCP or UDP? (default: TCP): ").strip().upper() or 'TCP'
    if protocol not in ('TCP', 'UDP'):
        protocol = 'TCP'

    attack_choice = input("Enable attack simulation (massive REPORT burst)? (y/N): ").strip().lower()
    burst_count = 0
    if attack_choice == 'y':
        burst_count_text = input("How many REPORT messages for attack (default: 100): ").strip()
        burst_count = int(burst_count_text) if burst_count_text.isdigit() else 100

    hostname = socket.gethostname()
    
    print(f"Agent Configuration:")
    print(f"  ID: {agent_id}")
    print(f"  Protocol: {protocol}")
    print(f"  Hostname: {hostname}")
    print(f"  Report Interval: {REPORT_INTERVAL}s")
    print(f"  Connecting to {HOST}:{PORT}\n")
    
    try:
        # Create socket and connect/bind to server
        if protocol == 'UDP':
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            client_socket.settimeout(2)
            client_socket.connect((HOST, PORT))
            print("UDP socket ready\n")
        else:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((HOST, PORT))
            print("Connected to server\n")
        
        # Send HELLO message
        hello_msg = f"HELLO {agent_id} {hostname}"
        if protocol == 'UDP':
            response = send_message_udp(client_socket, hello_msg)
        else:
            response = send_message_tcp(client_socket, hello_msg)
        
        if response != 'OK':
            print(f"Registration failed: {response}")
            client_socket.close()
            return
        
        print(f"Successfully registered as {agent_id}\n")

        if burst_count > 0:
            run_attack_mode(client_socket, agent_id, protocol, burst_count)
        
        # Start background thread for periodic reports
        report_thread_obj = threading.Thread(
            target=report_thread,
            args=(client_socket, agent_id, protocol),
            daemon=True
        )
        report_thread_obj.start()
        
        # Main loop - keep connection alive and handle user input
        print("Agent is running... Press Ctrl+C to disconnect\n")
        while True:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                print("\n\nShutting down agent...")
                break
        
        # Send BYE message
        bye_msg = f"BYE {agent_id}"
        if protocol == 'UDP':
            response = send_message_udp(client_socket, bye_msg)
        else:
            response = send_message_tcp(client_socket, bye_msg)
        
        if response == 'OK':
            print("Successfully unregistered from server")
        else:
            print(f"Unregistration error: {response}")
    
    except ConnectionRefusedError:
        print(f"Error: Could not connect to server at {HOST}:{PORT}")
        print("Make sure the server is running")
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        try:
            client_socket.close()
        except:
            pass
        print("Connection closed")


if __name__ == '__main__':
    main()
