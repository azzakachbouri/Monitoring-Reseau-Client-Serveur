"""
Test Suite for Network Monitoring System
Tests all required scenarios from project specification
"""

import socket
import time
import threading
import subprocess
import sys


class TestClient:
    """Helper class for testing protocol messages."""
    
    def __init__(self, host='127.0.0.1', port=5050):
        self.host = host
        self.port = port
        self.sock = None
    
    def connect(self):
        """Connect to server."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
    
    def send_raw(self, message):
        """Send raw message and get response."""
        try:
            self.sock.send((message + '\n').encode('utf-8'))
            response = self.sock.recv(1024).decode('utf-8').strip()
            return response
        except Exception as e:
            print(f"Send error: {e}")
            return None
    
    def close(self):
        """Close connection."""
        try:
            if self.sock:
                self.sock.close()
        except:
            pass


def test_1_single_client_connection():
    """Test 1: Single client connection and registration."""
    print("\n" + "="*60)
    print("TEST 1: Single Client Connection")
    print("="*60)
    
    client = TestClient()
    if not client.connect():
        print("❌ FAILED: Could not connect")
        return False
    
    # Send HELLO
    response = client.send_raw("HELLO agent1 WORKSTATION")
    if response == 'OK':
        print("✓ PASSED: Agent registered successfully")
        print(f"  Response: {response}")
    else:
        print(f"❌ FAILED: Expected OK, got {response}")
        client.close()
        return False
    
    # Send REPORT
    response = client.send_raw("REPORT agent1 1700000000 25.5 2048")
    if response == 'OK':
        print("✓ PASSED: Report accepted")
        print(f"  Response: {response}")
    else:
        print(f"❌ FAILED: Expected OK, got {response}")
        client.close()
        return False
    
    # Send BYE
    response = client.send_raw("BYE agent1")
    if response == 'OK':
        print("✓ PASSED: Graceful disconnect")
        print(f"  Response: {response}")
    else:
        print(f"❌ FAILED: Expected OK, got {response}")
        client.close()
        return False
    
    client.close()
    return True


def test_2_multiple_concurrent_clients():
    """Test 2: Multiple clients connecting simultaneously."""
    print("\n" + "="*60)
    print("TEST 2: Multiple Concurrent Clients")
    print("="*60)
    
    clients = []
    agent_ids = ['agent_multi_1', 'agent_multi_2', 'agent_multi_3']
    
    # Connect all clients
    for agent_id in agent_ids:
        client = TestClient()
        if not client.connect():
            print(f"❌ FAILED: Could not connect client {agent_id}")
            return False
        clients.append((agent_id, client))
    
    print(f"✓ Connected {len(clients)} clients")
    
    # Register all clients
    for agent_id, client in clients:
        response = client.send_raw(f"HELLO {agent_id} WORKSTATION")
        if response != 'OK':
            print(f"❌ FAILED: Could not register {agent_id}")
            return False
    
    print(f"✓ Registered {len(clients)} clients")
    
    # Send reports from all
    for agent_id, client in clients:
        response = client.send_raw(f"REPORT {agent_id} 1700000000 20.0 1500")
        if response != 'OK':
            print(f"❌ FAILED: Report from {agent_id} rejected")
            return False
    
    print(f"✓ All {len(clients)} reports accepted")
    
    # Disconnect all
    for agent_id, client in clients:
        response = client.send_raw(f"BYE {agent_id}")
        if response != 'OK':
            print(f"❌ FAILED: Could not disconnect {agent_id}")
            return False
        client.close()
    
    print(f"✓ PASSED: All {len(clients)} clients disconnected gracefully")
    return True


def test_3_malformed_messages():
    """Test 3: Malformed message handling."""
    print("\n" + "="*60)
    print("TEST 3: Malformed Message Handling")
    print("="*60)
    
    test_cases = [
        ("HELLO agent1", "Missing hostname"),
        ("REPORT agent1 100", "Missing metrics"),
        ("REPORT agent1 abc 25.5 2048", "Invalid timestamp"),
        ("REPORT agent1 100 150 2048", "CPU > 100"),
        ("REPORT agent1 100 25.5 -100", "Negative RAM"),
        ("INVALID agent1", "Unknown command"),
        ("BYE", "Missing agent_id"),
    ]
    
    for message, description in test_cases:
        client = TestClient()
        if not client.connect():
            print(f"❌ Could not connect for test: {description}")
            continue
        
        response = client.send_raw(message)
        if response == 'ERROR':
            print(f"✓ Correctly rejected: {description}")
            print(f"  Message: {message}")
            print(f"  Response: {response}")
        else:
            print(f"❌ Should reject: {description}")
            print(f"  Message: {message}")
            print(f"  Got: {response}")
        
        client.close()
    
    return True


def test_4_unregistered_agent():
    """Test 4: Report from unregistered agent."""
    print("\n" + "="*60)
    print("TEST 4: Unregistered Agent Report")
    print("="*60)
    
    client = TestClient()
    if not client.connect():
        print("❌ FAILED: Could not connect")
        return False
    
    # Try to send report without HELLO first
    response = client.send_raw("REPORT unknown_agent 1700000000 30 2000")
    if response == 'ERROR':
        print("✓ PASSED: Report from unregistered agent rejected")
        print(f"  Response: {response}")
    else:
        print(f"❌ FAILED: Should reject unregistered agent, got {response}")
        client.close()
        return False
    
    # Now register and try again
    response = client.send_raw("HELLO unknown_agent WORKSTATION")
    if response != 'OK':
        print("❌ FAILED: Registration failed")
        client.close()
        return False
    
    response = client.send_raw("REPORT unknown_agent 1700000000 30 2000")
    if response == 'OK':
        print("✓ PASSED: Report accepted after registration")
        print(f"  Response: {response}")
    else:
        print(f"❌ FAILED: Report should be accepted, got {response}")
        client.close()
        return False
    
    client.close()
    return True


def test_5_metric_validation():
    """Test 5: Metric value validation."""
    print("\n" + "="*60)
    print("TEST 5: Metric Validation")
    print("="*60)
    
    test_cases = [
        (0.0, 0.0, True, "Min values"),
        (100.0, 1000.0, True, "Normal values"),
        (50.5, 2048.5, True, "Float values"),
        (-10.0, 2000.0, False, "Negative CPU"),
        (150.0, 2000.0, False, "CPU > 100"),
        (50.0, -500.0, False, "Negative RAM"),
    ]
    
    for i, (cpu, ram, should_pass, description) in enumerate(test_cases):
        client = TestClient()
        if not client.connect():
            continue
        
        # Register first
        client.send_raw(f"HELLO metric_test_{i} WORKSTATION")
        
        # Send report with test values
        response = client.send_raw(f"REPORT metric_test_{i} 1700000000 {cpu} {ram}")
        
        if should_pass and response == 'OK':
            print(f"✓ Accepted: {description} (CPU={cpu}%, RAM={ram}MB)")
        elif not should_pass and response == 'ERROR':
            print(f"✓ Rejected: {description} (CPU={cpu}%, RAM={ram}MB)")
        else:
            status = "accepted" if response == 'OK' else "rejected"
            expected = "accepted" if should_pass else "rejected"
            print(f"❌ {description}: {status}, but expected {expected}")
        
        client.close()
    
    return True


def test_6_disconnect_and_reconnect():
    """Test 6: Disconnect and reconnect with same agent_id."""
    print("\n" + "="*60)
    print("TEST 6: Disconnect and Reconnect")
    print("="*60)
    
    agent_id = "reconnect_test"
    
    # First connection
    client1 = TestClient()
    if not client1.connect():
        print("❌ FAILED: Could not connect first time")
        return False
    
    response = client1.send_raw(f"HELLO {agent_id} WORKSTATION")
    if response != 'OK':
        print("❌ FAILED: First registration failed")
        return False
    
    print(f"✓ First connection and registration successful")
    
    # Send report
    response = client1.send_raw(f"REPORT {agent_id} 1700000000 25 2000")
    if response != 'OK':
        print("❌ FAILED: First report failed")
        return False
    
    print(f"✓ First report sent")
    
    # Disconnect
    client1.send_raw(f"BYE {agent_id}")
    client1.close()
    
    print(f"✓ Disconnected")
    
    # Wait a moment
    time.sleep(1)
    
    # Reconnect with same agent_id
    client2 = TestClient()
    if not client2.connect():
        print("❌ FAILED: Could not reconnect")
        return False
    
    response = client2.send_raw(f"HELLO {agent_id} WORKSTATION")
    if response != 'OK':
        print("❌ FAILED: Second registration failed")
        return False
    
    print(f"✓ PASSED: Reconnected and re-registered with same agent_id")
    
    response = client2.send_raw(f"REPORT {agent_id} 1700000000 30 2100")
    if response == 'OK':
        print(f"✓ Second report sent successfully")
    
    client2.close()
    return True


def run_all_tests():
    """Run all tests."""
    print("\n\n")
    print("#" * 60)
    print("# NETWORK MONITORING SYSTEM - TEST SUITE")
    print("#" * 60)
    print("\nMake sure server is running: python server.py")
    print("Tests will start in 2 seconds...\n")
    
    time.sleep(2)
    
    results = {
        "Test 1: Single Client": test_1_single_client_connection(),
        "Test 2: Multiple Clients": test_2_multiple_concurrent_clients(),
        "Test 3: Malformed Messages": test_3_malformed_messages(),
        "Test 4: Unregistered Agent": test_4_unregistered_agent(),
        "Test 5: Metric Validation": test_5_metric_validation(),
        "Test 6: Disconnect/Reconnect": test_6_disconnect_and_reconnect(),
    }
    
    # Summary
    print("\n\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, result in results.items():
        status = "✓ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    total = len(results)
    passed = sum(1 for r in results.values() if r)
    print(f"\nTotal: {passed}/{total} tests passed")
    print("="*60 + "\n")


if __name__ == '__main__':
    try:
        run_all_tests()
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
    except Exception as e:
        print(f"\nError running tests: {e}")
