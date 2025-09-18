# Projet INFO901 - Système de Communication Distribué

## Auteurs

- **RASOAMIARAMANANA Hery ny aina**
- **ROUSSEAU Maxime**

## Description du Projet

Ce projet implémente un **système de communication distribué** en Python avec les fonctionnalités suivantes :

- **Communication inter-processus** (point-à-point et diffusion)
- **Synchronisation distribuée** (barrières de synchronisation)
- **Exclusion mutuelle distribuée** (section critique)
- **Gestion des messages** avec horloge logique de Lamport
- **Tolérance aux pannes** avec timeouts et gestion d'erreurs

## Architecture du Système

### Classes Principales

1. **`Message.py`** - Encapsulation des messages

   - Types de messages (normal, sync, section critique, broadcast, etc.)
   - Horodatage avec horloge logique de Lamport
   - Métadonnées (expéditeur, destinataire, contenu)

2. **`Mailbox.py`** - Boîte aux lettres thread-safe

   - Réception et stockage des messages
   - Méthodes de récupération (FIFO, par expéditeur, par type)
   - Synchronisation avec conditions et verrous

3. **`Com.py`** - Classe de communication principale

   - Communication asynchrone (`sendTo`) et synchrone (`sendToSync`)
   - Algorithme de synchronisation par barrière
   - Exclusion mutuelle avec algorithme de Ricart-Agrawala
   - Diffusion de messages (`broadcast`)

4. **`Process.py`** - Processus distribués

   - Hérite de `Thread` pour l'exécution parallèle
   - Logique métier de chaque processus
   - Gestion du cycle de vie

5. **`main.py`** - Tests et démonstrations
   - Scénarios de test complets
   - Validation des fonctionnalités

## Algorithmes Implémentés

### 1. Synchronisation Distribuée

- **Barrière de synchronisation** : Tous les processus doivent atteindre un point de synchronisation avant de continuer
- Échange de messages `BARRIER` entre tous les processus
- Attente active jusqu'à réception de tous les signaux

### 2. Exclusion Mutuelle - Algorithme de Ricart-Agrawala

- **Demande de section critique** : Envoi de requêtes à tous les processus
- **Gestion des priorités** : Basée sur l'horloge logique et l'ID processus
- **Réponses différées** : Les réponses sont différées si le processus est en SC ou a une priorité plus haute

### 3. Horloge Logique de Lamport

- Chaque processus maintient une horloge logique
- Incrémentation à chaque événement local
- Synchronisation lors de la réception de messages

## Installation et Utilisation

### Prérequis

- Python 3.8 ou supérieur
- Modules standard (threading, time, collections, enum, typing)

### Installation

```bash
git clone https://github.com/Hery-R/projet_INFO901.git
cd projet_INFO901
```

### Exécution

#### Test complet du système

```bash
python main.py
```

#### Test du module Process seul

```bash
python Process.py
```

#### Utilisation programmatique

```python
from Com import Com
from Process import Process, create_processes

# Créer 3 processus
processes = create_processes(3)

# Laisser s'exécuter
import time
time.sleep(10)

# Arrêter proprement
from Process import stop_all_processes
stop_all_processes(processes)
```

## Scénarios de Test

### 1. Communication Basique

- Création de 3 processus (P0, P1, P2)
- Messages asynchrones et synchrones
- Vérification des acquittements

### 2. Synchronisation

- Barrière de synchronisation entre tous les processus
- Délais différents pour chaque processus
- Vérification que tous attendent le dernier

### 3. Section Critique

- Accès concurrent à une ressource partagée
- Vérification de l'exclusion mutuelle
- Test avec plusieurs itérations par processus

### 4. Diffusion (Broadcast)

- Un processus diffuse à tous les autres
- Réception par tous les destinataires
- Vérification de la cohérence

## Fonctionnalités Avancées

### Gestion d'Erreurs

- **Timeouts** sur les communications synchrones (5-10 secondes)
- **Messages différés** remis en file d'attente
- **Logging** détaillé des opérations

### Thread Safety

- Tous les accès partagés sont protégés par des verrous
- Conditions de synchronisation pour l'attente de messages
- Gestion propre des ressources

### Extensibilité

- Architecture modulaire facilement extensible
- Types de messages configurables
- Algorithmes d'exclusion mutuelle interchangeables

## Structure des Fichiers

```
projet_INFO901/
├── README.md              # Documentation du projet
├── main.py               # Tests et démonstrations
├── Com.py                # Communication distribuée
├── Message.py            # Encapsulation des messages
├── Mailbox.py            # Boîte aux lettres thread-safe
├── Process.py            # Processus distribués
├── Exemple.py            # Code original (référence)
└── sujet.pdf             # Énoncé du projet
```

## Exemple d'Exécution

```
=== SYSTÈME DE COMMUNICATION DISTRIBUÉ ===
Démarrage des tests...

=== TEST COMMUNICATION BASIQUE ===
Processus P0 créé avec ID 0
Processus P1 créé avec ID 1
Processus P2 créé avec ID 2
P0 -> P1: j'appelle 2 et je te recontacte après
P0 -sync-> P2: J'ai laissé un message...
P2 <-sync- P0: J'ai laissé un message...
P0 <-sync-ack- P2
...

=== TEST SYNCHRONISATION ===
P0 avant synchronisation - 1640995200.12
P1 avant synchronisation - 1640995200.62
P2 avant synchronisation - 1640995201.12
P0 synchronisé avec 3 processus
P1 synchronisé avec 3 processus
P2 synchronisé avec 3 processus
...
```
