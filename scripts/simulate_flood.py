"""
Simule un flood / DoS applicatif contre le proxy.

Ce script ouvre un grand nombre de connexions TCP vers le proxy le plus
vite possible, en parallèle (threads). C'est ce que register_connection_open()
dans security_core.py surveille : au-delà de FLOOD_THRESHOLD_BLOCK connexions
par seconde (100 par défaut), l'IP est bloquée et un événement FLOOD_DETECTED
(T1498) est enregistré.

Usage :
    python scripts/simulate_flood.py --port 6000 --count 150

Note : le débit réel observable dépend de la machine (le proxy doit faire un
handshake TLS vers le serveur pour chaque connexion, ce qui prend du temps
sous forte charge). Si les logs du proxy montrent un pic de RATE_WARN sans
jamais atteindre FLOOD_DETECTED, relance le proxy avec un seuil de blocage
plus bas pour la démo, ex. :
    FLOOD_THRESHOLD_BLOCK=20 python proxy.py --listen-port 6000 --target-port 5051 --tls-cert server.crt

Après l'exécution, regarde :
  - les logs du terminal où tourne proxy.py (tu dois voir FLOOD_DETECTED)
  - events.jsonl (une nouvelle ligne avec "type": "FLOOD_DETECTED", "mitre_technique": "T1498")
  - Splunk (une fois le forwarder relancé) : source="monitoring-reseau-client-serveur" type=FLOOD_DETECTED
"""
import argparse
import socket
import threading
import time


def open_and_close(host, port, results, index):
    try:
        with socket.create_connection((host, port), timeout=2):
            results[index] = 'ok'
    except (ConnectionRefusedError, socket.timeout, OSError) as e:
        results[index] = f'refused ({e})'


def main():
    parser = argparse.ArgumentParser(description="Simule un flood/DoS contre le proxy")
    parser.add_argument('--host', default='127.0.0.1', help='Adresse du proxy (défaut: 127.0.0.1)')
    parser.add_argument('--port', type=int, required=True, help='Port d\'écoute du proxy (ex: 6000)')
    parser.add_argument('--count', type=int, default=150, help='Nombre de connexions à ouvrir en rafale (défaut: 150, seuil de blocage par défaut = 100/s)')
    args = parser.parse_args()

    print(f"[SIMULATION FLOOD] Cible : {args.host}:{args.port}")
    print(f"[SIMULATION FLOOD] Ouverture de {args.count} connexions en parallèle, aussi vite que possible...\n")

    results = [None] * args.count
    threads = []
    start = time.time()
    for i in range(args.count):
        t = threading.Thread(target=open_and_close, args=(args.host, args.port, results, i))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    duration = time.time() - start

    accepted = sum(1 for r in results if r == 'ok')
    refused = args.count - accepted

    print(f"[SIMULATION FLOOD] Terminé en {duration:.2f}s — {accepted} acceptées, {refused} refusées/bloquées.")
    if refused > 0:
        print("[SIMULATION FLOOD] ✅ Une partie des connexions a été refusée — signe que le blocage s'est déclenché en cours de rafale.")
    print("[SIMULATION FLOOD] Vérifie maintenant les logs du proxy, events.jsonl, et Splunk pour confirmer FLOOD_DETECTED.")


if __name__ == '__main__':
    main()