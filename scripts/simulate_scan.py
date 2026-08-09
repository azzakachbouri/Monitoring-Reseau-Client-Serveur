"""
Simule un scan de service (type nmap -sT connect scan) contre le proxy.

Ce script ouvre plusieurs connexions TCP vers le proxy, n'envoie AUCUNE
donnée, et ferme chaque connexion presque aussitôt. C'est exactement la
signature que security_core.py surveille pour déclarer un SCAN_DETECTED
(T1046) : plusieurs "sondes" 0-octet très courtes depuis la même IP en
peu de temps.

Usage :
    python scripts/simulate_scan.py --port 6000 --count 6

Après l'exécution, regarde :
  - les logs du terminal où tourne proxy.py (tu dois voir SCAN_DETECTED)
  - events.jsonl (une nouvelle ligne avec "type": "SCAN_DETECTED", "mitre_technique": "T1046")
  - Splunk (une fois le forwarder relancé) : source="monitoring-reseau-client-serveur" type=SCAN_DETECTED
"""
import argparse
import socket
import time


def probe(host, port, index):
    try:
        with socket.create_connection((host, port), timeout=2) as s:
            print(f"  [{index}] Connexion ouverte vers {host}:{port} — fermeture immédiate, aucune donnée envoyée.")
        return True
    except (ConnectionRefusedError, socket.timeout, OSError) as e:
        print(f"  [{index}] Échec de connexion : {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Simule un scan de service contre le proxy")
    parser.add_argument('--host', default='127.0.0.1', help='Adresse du proxy (défaut: 127.0.0.1)')
    parser.add_argument('--port', type=int, required=True, help='Port d\'écoute du proxy (ex: 6000)')
    parser.add_argument('--count', type=int, default=6, help='Nombre de sondes à envoyer (défaut: 6, seuil par défaut = 5)')
    parser.add_argument('--delay', type=float, default=0.3, help='Pause entre chaque sonde en secondes (défaut: 0.3)')
    args = parser.parse_args()

    print(f"[SIMULATION SCAN] Cible : {args.host}:{args.port}")
    print(f"[SIMULATION SCAN] Envoi de {args.count} sondes 0-octet, {args.delay}s d'intervalle...\n")

    blocked_early = False
    for i in range(1, args.count + 1):
        ok = probe(args.host, args.port, i)
        if not ok and i > 1:
            print("\n[SIMULATION SCAN] La connexion a été refusée — l'IP est probablement déjà bloquée par le proxy.")
            blocked_early = True
            break
        time.sleep(args.delay)

    print("\n[SIMULATION SCAN] Terminé.")
    if blocked_early:
        print("[SIMULATION SCAN] ✅ Comportement attendu : le proxy a bloqué l'IP avant la fin des sondes.")
    else:
        print("[SIMULATION SCAN] Vérifie maintenant les logs du proxy, events.jsonl, et Splunk pour confirmer SCAN_DETECTED.")


if __name__ == '__main__':
    main()