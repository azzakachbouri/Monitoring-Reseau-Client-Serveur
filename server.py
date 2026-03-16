import socket
import threading

def handle_client(conn, addr):
    print(f"[*] New connection from {addr}")
    try:
        while True:
            data = conn.recv(1024).decode('utf-8')
            if not data:
                break
            
            print(f"[RECV] {data}")
            
            # Simple protocol logic (Step 2)
            if data.startswith("HELLO"):
                conn.send("OK".encode('utf-8'))
            elif data.startswith("REPORT"):
                # Logic to parse and store metrics goes here
                conn.send("OK".encode('utf-8'))
            elif data.startswith("BYE"):
                conn.send("OK".encode('utf-8'))
                break
            else:
                conn.send("ERROR".encode('utf-8'))
    except ConnectionResetError:
        print(f"[!] Client {addr} disconnected abruptly.")
    finally:
        conn.close()

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('0.0.0.0', 5000)) # Listen on all interfaces, port 5000
    server.listen()
    print("[*] Server is listening on port 5000...")
    
    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()

if __name__ == "__main__":
    start_server()