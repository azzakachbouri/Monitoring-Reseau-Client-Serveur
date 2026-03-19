"""
Simplified Client without psutil dependency
For testing when psutil is not available
Simulates metrics with random values
"""

import socket
import threading
import time
import random
import os
from datetime import datetime


def send_message(sock, message):
    """Send a message to the server and receive response."""
    try:
        sock.send((message + '\n').encode('utf-8'))
        response = sock.recv(1024).decode('utf-8').strip()
        return response
    except Exception as e:
        print(f"Error communicating with server: {e}")
        return None


def get_random_metrics():
    """Generate random metrics for testing (no psutil required)."""
    cpu_pct = round(random.uniform(10, 80), 1)
    ram_mb = round(random.uniform(1024, 4096), 0)
    return cpu_pct, ram_mb


def report_thread(sock, agent_id):
    """Periodically send REPORT messages with simulated metrics."""
    while True:
        try:
            time.sleep(10)  # Send every 10 seconds
            
            cpu_pct, ram_mb = get_random_metrics()
            timestamp = int(time.time())
            
            message = f"REPORT {agent_id} {timestamp} {cpu_pct} {ram_mb}"
            response = send_message(sock, message)
            
            if response == 'OK':
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Report sent: CPU={cpu_pct}% RAM={ram_mb:.0f}MB")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Report rejected: {response}")
        
        except Exception as e:
            print(f"Error in report thread: {e}")
            break


def main():
    """Main client function."""
    HOST = '127.0.0.1'
    PORT = 5050
    
    # Get agent configuration
    agent_id = input("Enter agent ID (default: agent1): ").strip() or "agent1"
    hostname = socket.gethostname()
    
    print(f"\nAgent Configuration:")
    print(f"  ID: {agent_id}")
    print(f"  Hostname: {hostname}")
    print(f"  Report Interval: 10s (with simulated metrics)")
    print(f"  Connecting to {HOST}:{PORT}\n")
    
    try:
        # Create socket and connect to server
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((HOST, PORT))
        print("Connected to server\n")
        
        # Send HELLO message
        hello_msg = f"HELLO {agent_id} {hostname}"
        response = send_message(client_socket, hello_msg)
        
        if response != 'OK':
            print(f"Registration failed: {response}")
            client_socket.close()
            return
        
        print(f"Successfully registered as {agent_id}\n")
        
        # Start background thread for periodic reports
        report_thread_obj = threading.Thread(target=report_thread, args=(client_socket, agent_id), daemon=True)
        report_thread_obj.start()
        
        # Main loop - keep connection alive
        print("Agent is running... Press Ctrl+C to disconnect\n")
        while True:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                print("\n\nShutting down agent...")
                break
        
        # Send BYE message
        bye_msg = f"BYE {agent_id}"
        response = send_message(client_socket, bye_msg)
        
        if response == 'OK':
            print("Successfully unregistered from server")
        else:
            print(f"Unregistration error: {response}")
    
    except ConnectionRefusedError:
        print(f"Error: Could not connect to server at {HOST}:{PORT}")
        print("Make sure the server is running: python server.py")
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
