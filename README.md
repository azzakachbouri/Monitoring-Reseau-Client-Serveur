# 🖥️ Mini-Projet Réseaux TP RT2 — Monitoring Réseau Client–Serveur

> Système de monitoring réseau distribué basé sur une architecture client–serveur TCP.  
> Chaque agent collecte périodiquement des métriques (CPU, RAM) et les envoie au serveur central.
> Le serveur agrège les données, maintient la liste des agents actifs et affiche des statistiques.

---

## 📋 Table des matières

- [1. Environnement et exécution](#1-environnement-et-exécution)
- [2. Fonctionnalités obligatoires](#2-fonctionnalités-obligatoires)
- [3. Extensions implémentées](#3-extensions-implémentées)
- [4. Spécification du protocole](#4-spécification-du-protocole)
- [5. Tests](#5-tests)
- [6. Choix techniques](#6-choix-techniques)
- [7. Structure du projet](#7-structure-du-projet)

---

## 1. Environnement et exécution

### Prérequis

- Python 3.8+
- **Zéro dépendance externe** (standard library uniquement)
  - `socket`, `threading`, `time`, `datetime`, `csv`, `uuid`, `platform`, `subprocess`, `ctypes`

### Démarrage du serveur

```bash
python server.py
```

Le serveur démarre sur `127.0.0.1:5051` (TCP + UDP).

### Démarrage d'un ou plusieurs agents

Terminal 1:

```bash
python client.py
```

L'agent demandera interactivement: protocol (TCP/UDP), agent_id, mode attaque.

Alternativement, utiliser le client simple (simulation de métriques):

```bash
python client_simple.py
```

### Exemple d'une séquence complète

**Terminal 1 (serveur):**

```bash
python server.py
```

**Terminal 2 (agent 1):**

```bash
python client.py
# → Enter agent ID: agent1
# → Protocol TCP or UDP? (default: TCP): TCP
# → Enable attack simulation (y/N): N
```

**Terminal 3 (agent 2):**

```bash
python client_simple.py
```

---

## 2. Fonctionnalités obligatoires (cahier des charges)

### Architecture

- ✅ Communication **TCP** (primaire) + UDP (extension)
- ✅ Protocole simple HELLO / REPORT / BYE
- ✅ Gestion **plusieurs connexions simultanées** via threads
- ✅ Un thread par client TCP au serveur
- ✅ **Robustesse**: serveur ne s'arrête pas en cas d'erreur client
- ✅ **Validation** des messages (format, plage de valeurs)

### Statistiques périodiques (tous les 10s)

Le serveur affiche:

- Nombre d'agents actifs
- Moyenne CPU (%)
- Moyenne RAM (MB)
- Total de REPORT reçus

### Activation d'un agent

- Un agent est considéré **actif** si un REPORT est reçu dans la fenêtre **3 × T** secondes (défaut: T=10s → fenêtre=30s)
- Après 30s sans REPORT, l'agent est automatiquement supprimé de la liste active

---

## 3. Extensions implémentées

### A. Mode UDP (section 3 du cahier)

- Clients TCP et UDP gérés **simultanément** par le même serveur
- Protocole identique (HELLO, REPORT, BYE)
- Stateless pour UDP: pas de persistance de connexion
- Comparison TCP vs UDP: fiabilité vs latence

### B. Auto-cleanup des agents inactifs (section 3)

- Daemon thread `inactive_cleanup_thread()` parcourt les agents toutes les 5s
- Supprime automatiquement agents avec `(now - last_report_time) >= 30s`
- Logs pour chaque suppression

### C. Export CSV des statistiques (section 3)

- Fichier `stats_export.csv` créé automatiquement
- Colonnes: `timestamp, active_agents, avg_cpu_pct, avg_ram_mb, total_reports`
- Ajout d'une ligne toutes les 10s
- Format compatible Excel/Pandas

### D. UUID optionnel comme agent_id (section 3)

- Clients peuvent fournir UUID au lieu d'ID manuel
- Génération auto-UUID dans `client.py` si l'utilisateur laisse vide
- Pas de contrainte de format sur agent_id (sauf pas d'espaces)

### E. Simulation d'attaque (section 3)

- Mode "attack" dans `client.py`: envoi massif de REPORT (ex.: 100+ par seconde)
- Mesure capacité serveur + validation anti-flood
- Utile pour tester robustesse

### F. Système d'alertes

- Alerte `CPU_HIGH` si `cpu_pct` dépasse le seuil configuré (`CPU_ALERT_THRESHOLD`, défaut: 85.0)
- Alerte `AGENT_INACTIVE` lorsqu'un agent est supprimé pour inactivité prolongée
- Alerte `ERROR_STORM` si trop de réponses `ERROR` sont produites dans une fenêtre courte
- Les alertes sont journalisées en temps réel et affichées dans le bloc de statistiques périodiques

Paramètres serveur (dans `server.py`):

- `CPU_ALERT_THRESHOLD` (défaut: 85.0)
- `ERROR_ALERT_THRESHOLD` (défaut: 5)
- `ERROR_ALERT_WINDOW` en secondes (défaut: 10)
- `ERROR_ALERT_COOLDOWN` en secondes (défaut: 10)

---

## 4. Spécification du protocole

### Messages Client → Serveur

| Message | Format                                             | Exemple                              |
| ------- | -------------------------------------------------- | ------------------------------------ |
| HELLO   | `HELLO <agent_id> <hostname>`                      | `HELLO agent1 PC-LAB`                |
| REPORT  | `REPORT <agent_id> <timestamp> <cpu_pct> <ram_mb>` | `REPORT agent1 1700000000 25.5 2048` |
| BYE     | `BYE <agent_id>`                                   | `BYE agent1`                         |

### Réponses Serveur → Client

| Réponse | Signification            |
| ------- | ------------------------ |
| `OK`    | Message accepté          |
| `ERROR` | Format invalide ou rejet |

### Contraintes de validation

- **agent_id**: pas d'espaces (alphanumérique + `-`, `_`, UUID OK)
- **cpu_pct**: réel dans `[0.0, 100.0]`
- **ram_mb**: réel ≥ `0.0`
- **timestamp**: entier (epoch secondes)

---

## 5. Tests

### Tests obligatoires (cahier des charges)

```bash
python test_suite.py
```

| #   | Test                 | Description                            | Statut |
| --- | -------------------- | -------------------------------------- | ------ |
| 1   | Single Client        | Connexion, HELLO, REPORT, BYE          | ✅     |
| 2   | Multiple Clients     | 3+ clients simultanément               | ✅     |
| 3   | Malformed Messages   | HELLO incomplet, REPORT invalide, etc. | ✅     |
| 4   | Unregistered Agent   | REPORT sans HELLO préalable            | ✅     |
| 5   | Metric Validation    | CPU > 100, RAM < 0, etc.               | ✅     |
| 6   | Disconnect/Reconnect | Même agent_id, reconnexion             | ✅     |

### Tests d'extensions (bonus)

| #   | Test                 | Description                      | Statut |
| --- | -------------------- | -------------------------------- | ------ |
| 7   | UDP Flow             | HELLO/REPORT/BYE en UDP          | ✅     |
| 8   | UUID Agent ID        | UUID comme agent_id              | ✅     |
| 9   | Abrupt Disconnect    | Close sans BYE (server timeout)  | ✅     |
| 10  | Average Calculation  | Vérification moyennes correctes  | ✅     |
| 11  | Inactivity Detection | Auto-removal après 3×T           | ✅     |
| 12  | CPU Alert            | Déclenchement si CPU > seuil     | ✅     |
| 13  | Inactive Alert       | Alerte lors suppression inactive | ✅     |
| 14  | Error Storm Alert    | Trop de réponses ERROR           | ✅     |

---

## 6. Choix techniques

### Collecte de métriques (sans psutil)

Le projet respecte **"bibliothèques standards uniquement"** du cahier.

- **Windows**: `ctypes.windll.kernel32.GlobalMemoryStatusEx()` + `typeperf` (RAM + CPU)
- **Linux**: `/proc/meminfo`, `/proc/stat` (RAM + CPU)
- **macOS**: `sysctl` + `vm_stat` (RAM + CPU)

### Gestion concurrence

- **Server**: `threading.Thread` pour chaque client TCP
- **Synchronisation**: `threading.Lock` pour accès dict `agents` et `metrics`
- **Daemon threads**: cleanup, stats, UDP listener

### Robustesse

- Serveur captures exceptions par client → ne s'arrête pas
- Timeout inactivité (30s) → suppression auto des agents fantômes
- Validation stricte: toute erreur message → réponse `ERROR`

---

## 7. Structure du projet

```
.
├── server.py                # Serveur (TCP + UDP)
│   ├── handle_client()      # Thread-handler pour TCP
│   ├── udp_listener()       # Thread-daemon pour UDP
│   ├── statistics_thread()  # Affiche stats toutes les 10s
│   └── inactive_cleanup_thread()  # Supprime agents inactifs
│
├── client.py                # Client (TCP/UDP + auto-metrics)
│   ├── get_cpu_usage_pct()  # Metrics cross-platform
│   ├── get_used_memory_mb()
│   └── run_attack_mode()    # Mode simulation d'attaque
│
├── client_simple.py         # Client simplifié (métriques aléatoires)
│
├── test_suite.py            # 11 tests (6 obligatoires + 5 extensions)
│
├── stats_export.csv         # ✨ Généré automatiquement
├── requirements.txt         # ✅ Zéro dépendances
└── README.md                # Ce fichier

```

---

## 8. Résumé conformité au cahier des charges

✅ **Obligatoire:**

- Réaliser monitoring distribué client–serveur TCP
- Protocole HELLO/REPORT/BYE
- Gestion threads (1 par client)
- Validation robuste
- Statistiques périodiques (avg CPU, RAM)
- Tests démontrés (6 obligatoires)
- Zero external dependencies

✅ **Extensions implémentées:**

- UDP mode
- Inactivité detection + auto-cleanup
- CSV export
- UUID support
- Attack simulation

---

## Auteurs

**AZZA KACHBOURI** — **DHIA SELMI**  
Mini-Projet Réseaux — TP RT2

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
