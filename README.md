# Mini-Projet Reseaux TP RT2

Monitoring Reseau Client-Serveur avec Sockets

## 1. Objectif

Cette application implemente un monitoring reseau distribue base sur une architecture client-serveur.
Chaque client (agent) collecte periodiquement des metriques locales (CPU, RAM) et les envoie au serveur central.
Le serveur agrege les donnees, maintient la liste des agents actifs et affiche des statistiques globales.

## 2. Fonctionnalites obligatoires (cahier des charges)

- Communication client-serveur via sockets TCP
- Protocole applicatif: HELLO / REPORT / BYE
- Gestion de plusieurs connexions simultanees
- Un thread par client TCP cote serveur
- Validation des messages recus
- Robustesse: le serveur ne s'arrete pas sur erreur client
- Calcul periodique:
  - nombre d'agents actifs
  - moyenne CPU
  - moyenne RAM
- Un agent est actif si un REPORT est recu dans la fenetre 3 x T

## 3. Extensions implementees

- Mode UDP (comparaison TCP vs UDP)
- Detection et suppression d'agents inactifs
- Export CSV periodique des statistiques
- Utilisation possible d'un UUID comme agent_id
- Simulation d'attaque (envoi massif de REPORT)

## 4. Protocole

### Messages Client -> Serveur

- HELLO <agent_id> <hostname>
- REPORT <agent_id> <timestamp> <cpu_pct> <ram_mb>
- BYE <agent_id>

### Reponses Serveur -> Client

- OK
- ERROR

### Contraintes

- agent_id: sans espaces
- cpu_pct: reel entre 0 et 100
- ram_mb: reel >= 0
- actif si REPORT recu dans la fenetre 3 x T

## 5. Prerequis

- Python 3.8+
- Bibliotheques standards uniquement (aucun pip install necessaire)

## 6. Lancer le projet

### 6.1 Demarrer le serveur

```bash
python server.py
```

Configuration par defaut:

- HOST = 127.0.0.1
- PORT = 5051
- STATS_INTERVAL = 10s
- ACTIVE_WINDOW = 30s (3 x T)

### 6.2 Demarrer un client

```bash
python client.py
```

Le client vous demandera:

- agent_id (UUID auto propose par defaut)
- protocole (TCP par defaut, UDP possible)
- activation du mode attaque (burst de REPORT)

## 7. Tests

Lancer la suite de tests:

```bash
python test_suite.py
```

La suite couvre:

- connexion d'un seul client
- connexions multiples simultanees
- message mal forme
- arret brutal d'un client
- calcul/validation des metriques
- inactivite d'un agent (> 3 x T)
- extensions (UDP, UUID)

## 8. Structure du projet

```text
.
|- server.py
|- client.py
|- client_simple.py
|- test_suite.py
|- run_demo.bat
|- stats_export.csv
|- requirements.txt
|- README.md
```

## 9. Livrables (rappel)

- Code source complet (client + serveur)
- Rapport (5 a 10 pages):
  - architecture
  - protocole
  - choix techniques
  - captures d'ecran
  - difficultes rencontrees
- Rapport des tests (3 a 4 pages)
- README d'execution

## Auteurs

Azza Kachbouri - Dhia Selmi
