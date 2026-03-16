import socket
import time

def start_agent(agent_id, hostname):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(('127.0.0.1', 5000))
    
    # Registration (Step 2)
    client.send(f"HELLO {agent_id} {hostname}".encode('utf-8'))
    response = client.recv(1024).decode('utf-8')
    print(f"[SERVER]: {response}")

    if response == "OK":
        try:
            for i in range(5): # Send 5 reports for testing
                timestamp = int(time.time())
                cpu = 25.5 # You can use psutil here later if allowed, or random values
                ram = 2048.0
                report = f"REPORT {agent_id} {timestamp} {cpu} {ram}"
                client.send(report.encode('utf-8'))
                print(f"[SENT]: {report}")
                print(f"[SERVER]: {client.recv(1024).decode('utf-8')}")
                time.sleep(5) # Period T = 5 seconds
        finally:
            client.send(f"BYE {agent_id}".encode('utf-8'))
            client.close()

if __name__ == "__main__":
    start_agent("agent1", "PC-LAB")