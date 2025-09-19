# Projet INFO901 - Système Distribué avec Middleware de Communication

## Auteurs

- RASOAMIARAMANANA Hery ny aina
- ROUSSEAU Maxime

## Vue d'ensemble

Ce projet implémente un système distribué complet avec middleware de communication, respectant les spécifications du TP INFO901. Le système utilise une architecture basée sur un bus d'événements (PyBus) pour la communication asynchrone entre processus, avec gestion automatique de la synchronisation temporelle (horloges de Lamport) et exclusion mutuelle distribuée (algorithme en anneau avec jeton).

## Architecture Générale

```text
Process (logique métier)
   ↓ délègue à
Com (middleware communication)
   ↓ utilise
PyBus (bus d'événements)
   ↓
MessageDistributor (routage intelligent)
   ↓
Mailbox (stockage asynchrone)
   ↓
Process (consommation à son rythme)
```

### Séparation des Responsabilités

Cette architecture respecte le principe de séparation des responsabilités :

- **Process** : Logique métier et traitement des messages
- **Com** : Middleware de communication centralisé
- **PyBus** : Transport global d'événements
- **MessageDistributor** : Routage intelligent des messages
- **Mailbox** : Stockage asynchrone par processus

## Composants Principaux Détaillés

### 1. Launcher.py

**Rôle** : Point d'entrée principal. Initialise et gère le cycle de vie des processus.

**Fonctionnalités** :

- Crée un nombre spécifié de processus (Process)
- Initialise le MessageDistributor et le gestionnaire d'IDs (ProcessIDManager)
- Initialise la synchronisation globale via Com.initialize_sync()
- Démarre tous les processus en tant que threads
- Attend une durée définie, puis arrête tous les processus proprement

### 2. Process.py

**Rôle** : Représente un processus logique dans le système distribué. Chaque instance de Process est un thread Python.

**Fonctionnalités** :

- Initialise une instance du middleware Com qui lui attribue un ID unique
- Contient la logique métier du processus (simulée par une boucle run)
- Délègue toutes les opérations de communication et de synchronisation à son instance Com
- Traite les messages reçus via une boîte aux lettres (Mailbox) gérée par Com
- Implémente la logique de demande et de libération de section critique en lançant un thread séparé pour requestSC() car cette méthode est bloquante
- Gère son propre cycle de vie (alive, stop, waitStopped)

### 3. Com.py (Middleware de Communication)

**Rôle** : Agit comme un middleware centralisé pour chaque Process, gérant la logique de communication, de synchronisation et de section critique.

**Fonctionnalités** :

- **Numérotation Automatique** : Utilise ProcessIDManager pour attribuer un ID unique et consécutif à chaque processus
- **Horloge de Lamport** : Gère une horloge logique de Lamport thread-safe (lamport_clock) avec des méthodes pour incrémenter (incclock) et mettre à jour à la réception de messages (update_clock_on_receive)
- **Boîte aux Lettres (Mailbox)** : Chaque instance de Com possède une Mailbox pour son processus associé, où les messages asynchrones sont déposés
- **Communication Asynchrone** : Fournit des méthodes broadcast et sendTo qui utilisent PyBus pour envoyer des messages
- **Section Critique Distribuée** : Implémente un algorithme en anneau avec jeton
  - requestSC() : Bloque le processus jusqu'à l'obtention du jeton et l'entrée en section critique
  - releaseSC() : Libère la section critique et passe le jeton au processus suivant
  - Utilise un Condition (cs_condition) pour la synchronisation des threads attendant la SC
  - P0 démarre avec le jeton
- **Synchronisation Globale** : Implémente une barrière de synchronisation (synchronize()) qui bloque tous les processus jusqu'à ce qu'ils l'aient tous invoquée
- **Communication Synchrone** : Fournit des méthodes broadcastSyncObject, sendToSyncObject, recevFromSyncObject qui combinent l'envoi/réception de messages avec la barrière de synchronisation globale

### 4. MessageDistributor.py

**Rôle** : Un singleton qui s'enregistre au PyBus global et route les messages vers les Mailbox appropriées.

**Fonctionnalités** :

- S'abonne à différents types de messages (BroadcastMessage, MessageTo, TokenMessage) via PyBus
- Distribue les messages reçus à la Mailbox du processus destinataire (pour MessageTo et TokenMessage) ou à toutes les Mailbox (pour BroadcastMessage)
- Utilise des threads parallèles (Mode.PARALLEL) pour la distribution des messages

### 5. Mailbox.py

**Rôle** : Fournit une file d'attente thread-safe pour les messages asynchrones destinés à un processus spécifique.

**Fonctionnalités** :

- deposit_message() : Ajoute un message à la file d'attente et notifie les threads en attente
- get_message() : Récupère un message sans bloquer
- wait_for_message() : Bloque jusqu'à ce qu'un message soit disponible ou qu'un timeout expire
- Utilise deque pour la file d'attente et Lock/Condition pour la thread-safety

### 6. ProcessIDManager.py

**Rôle** : Un singleton qui attribue des IDs uniques et consécutifs aux processus.

**Fonctionnalités** :

- get_next_id() : Retourne le prochain ID disponible de manière thread-safe
- reset() : Réinitialise le compteur d'IDs (utilisé pour les tests)

### 7. Classes de Messages

**Rôle** : Définissent la structure des différents types de messages échangés dans le système.

- **LamportMessage** : Classe de base pour tous les messages, incluant un timestamp de Lamport et un payload
- **BroadcastMessage** : Message destiné à tous les processus
- **MessageTo** : Message destiné à un processus spécifique
- **TokenMessage** : Message spécial représentant le jeton pour l'algorithme de section critique

### 8. CriticalSectionState.py

**Rôle** : Énumération définissant les états possibles d'un processus par rapport à la section critique (IDLE, HAS_TOKEN, IN_CS).

## Concepts du TP et leur Implémentation

### 1. Horloges de Lamport

**Concept** : Synchronisation temporelle logique dans un système distribué sans horloge globale.

**Implémentation** :

- Chaque processus maintient une horloge logique locale (lamport_clock)
- Incrémentation avant chaque envoi de message (incclock())
- Mise à jour à la réception selon la règle : max(horloge_locale, horloge_message) + 1
- Protection thread-safe avec mutex (Lock)

```python
def incclock(self):
    with self.lock:
        self.lamport_clock += 1
        return self.lamport_clock

def update_clock_on_receive(self, received_timestamp):
    with self.lock:
        old_clock = self.lamport_clock
        self.lamport_clock = max(self.lamport_clock, received_timestamp) + 1
        return (old_clock, self.lamport_clock)
```

### 2. Communication Asynchrone

**Concept** : Échange de messages sans blocage des processus émetteurs.

**Implémentation** :

- Bus d'événements PyBus pour le transport global
- Boîtes aux lettres (Mailbox) pour chaque processus
- Communication non-bloquante pour l'émetteur

```python
# Envoi (non-bloquant)
def broadcast(self, payload):
    current_clock = self.incclock()
    msg = BroadcastMessage(current_clock, payload)
    PyBus.Instance().post(msg)  # Envoi asynchrone
```

### 3. PyBus et @subscribe : Architecture de Communication

**Pourquoi PyBus ?**
PyBus est un bus d'événements qui permet :

- Communication découplée entre composants
- Publication/abonnement (publish/subscribe) pattern
- Gestion automatique des threads
- Extensibilité pour nouveaux types de messages

**Implémentation du pattern publish/subscribe** :

```python
# Dans MessageDistributor.py - Abonnement aux événements
@subscribe(threadMode=Mode.PARALLEL, onEvent=BroadcastMessage)
def distribute_broadcast(self, event):
    # Réception automatique de tous les messages de diffusion
    for process_id, mailbox in self.mailboxes.items():
        mailbox.deposit_message(event)

@subscribe(threadMode=Mode.PARALLEL, onEvent=MessageTo)
def distribute_directed_message(self, event):
    # Réception automatique des messages dirigés
    destination_id = event.getTo()
    if destination_id in self.mailboxes:
        mailbox.deposit_message(event)
```

**Publication sur le bus** :

```python
# Dans Com.py - Publication d'événements
def broadcast(self, payload):
    msg = BroadcastMessage(current_clock, payload)
    PyBus.Instance().post(msg)  # Publication sur le bus

def sendTo(self, payload, destination_id):
    msg = MessageTo(current_clock, payload, destination_id)
    PyBus.Instance().post(msg)  # Publication sur le bus
```

**Avantages de cette architecture** :

- **Découplage complet** : Émetteurs et recepteurs ne se connaissent pas
- **Extensibilité** : Ajout de nouveaux types de messages facile
- **Performance** : Traitement parallèle des messages
- **Robustesse** : Un seul point d'écoute (MessageDistributor)

### 4. Boîtes aux Lettres (Mailbox)

**Concept** : Stockage asynchrone des messages pour chaque processus.

**Implémentation** :

- File FIFO thread-safe (collections.deque)
- Condition variables pour l'attente de messages
- Interface non-bloquante et bloquante

```python
def deposit_message(self, message):
    with self.condition:
        self.messages.append(message)
        self.condition.notify_all()  # Réveil des threads en attente

def wait_for_message(self, timeout=None):
    with self.condition:
        while len(self.messages) == 0:
            if not self.condition.wait(timeout):
                return None
        return self.messages.popleft()
```

### 5. Section Critique Distribuée

**Concept** : Exclusion mutuelle dans un système distribué.

**Implémentation** : Algorithme en anneau avec jeton

- Un seul jeton circule dans l'anneau (P0 → P1 → P2 → P0)
- Possession du jeton = droit d'entrer en section critique
- Transmission automatique du jeton après sortie

```python
def requestSC(self):
    with self.cs_condition:
        self.wants_cs = True
        while not (self.has_token and self.wants_cs):
            self.cs_condition.wait()  # Attente bloquante
        self.cs_state = CriticalSectionState.IN_CS

def releaseSC(self):
    self.wants_cs = False
    self._pass_token()  # Transmission du jeton
```

### 6. Synchronisation Globale

**Concept** : Barrière de synchronisation pour coordonner tous les processus.

**Implémentation** : Variables de classe partagées avec condition

- Compteur global du nombre de processus synchronisés
- Attente collective jusqu'à ce que tous arrivent à la barrière

```python
def synchronize(self):
    with Com._sync_condition:
        Com._sync_counter += 1
        if Com._sync_counter >= Com._sync_total_processes:
            Com._sync_counter = 0
            Com._sync_condition.notify_all()
        else:
            Com._sync_condition.wait()
```

### 7. Numérotation Automatique

**Concept** : Attribution automatique d'identifiants uniques sans variables de classe.

**Implémentation** : Pattern Singleton avec variables d'instance

- Gestionnaire centralisé (ProcessIDManager)
- Attribution séquentielle (0, 1, 2, ...)
- Thread-safe avec mutex

```python
class ProcessIDManager:
    def __init__(self):
        self._next_id = 0  # Variable d'instance, pas de classe
        self._lock = threading.Lock()

    def get_next_id(self):
        with self._lock:
            assigned_id = self._next_id
            self._next_id += 1
            return assigned_id
```

## Flux de Communication et de Synchronisation

### Démarrage

Launcher crée les Process. Chaque Process initialise son Com qui obtient un ID via ProcessIDManager et enregistre sa Mailbox auprès du MessageDistributor.

### Envoi de Message

Un Process appelle une méthode de communication sur son Com (ex: broadcast, sendTo).

### Horloge de Lamport

Com incrémente son horloge de Lamport et l'inclut dans le message.

### Publication sur PyBus

Com publie le message sur le PyBus global.

### Distribution

MessageDistributor intercepte le message et le dépose dans la Mailbox du ou des processus destinataires.

### Réception de Message

Le Process (dans sa boucle run) récupère les messages de sa Mailbox via Com.get_message().

### Mise à jour Horloge

Lors de la réception, Com met à jour l'horloge de Lamport du processus en fonction du timestamp du message reçu.

### Section Critique

- Un Process demande la SC via com.requestSC(). Cette méthode est bloquante et est exécutée dans un thread séparé pour ne pas bloquer la boucle principale du Process
- Com gère l'état du jeton (has_token, wants_cs, cs_state) et utilise une Condition pour bloquer/débloquer les threads
- Le jeton (TokenMessage) circule via PyBus et est distribué par MessageDistributor

### Synchronisation

Les méthodes synchrones (broadcastSyncObject, sendToSyncObject, recevFromSyncObject) utilisent une barrière de synchronisation globale (Com.\_sync_condition) pour s'assurer que tous les processus atteignent un certain point avant de continuer.

## Communication Synchrone

Le système implémente également des méthodes de communication synchrone utilisant la synchronisation globale :

```python
def broadcastSyncObject(self, payload, from_process_id):
    if self.process_id == from_process_id:
        self.broadcast(payload)
        self.synchronize()  # Attente que tous recoivent
    else:
        self.wait_for_message()
        self.synchronize()  # Confirmation de réception
```

## Gestion des Threads

- Chaque Process est un Thread Python
- La méthode run() de Process contient la boucle principale du processus
- Les demandes de section critique (requestSC()) sont lancées dans des threads séparés (CS-Thread) pour éviter de bloquer le thread principal du Process
- Le MessageDistributor utilise Mode.PARALLEL pour ses abonnements PyBus, ce qui signifie que la distribution des messages se fait dans des threads séparés
- Des Lock et Condition sont utilisés dans Com et Mailbox pour assurer la thread-safety des ressources partagées (horloge de Lamport, mailbox, état de la section critique, barrière de synchronisation)

## Structure des Fichiers

### Noyau du Système

- `Process.py` : Processus principal avec logique métier
- `Com.py` : Middleware de communication centralisé
- `Launcher.py` : Point d'entrée et orchestration

### Communication

- `PyBus` : Bus d'événements (bibliothèque externe)
- `MessageDistributor.py` : Routage intelligent des messages
- `Mailbox.py` : Stockage asynchrone par processus

### Messages

- `LamportMessage.py` : Classe de base avec timestamp
- `BroadcastMessage.py` : Messages de diffusion générale
- `MessageTo.py` : Messages dirigés vers un destinataire
- `CriticalSectionMessage.py` : Messages de jeton pour SC

### Gestion d'État

- `CriticalSectionState.py` : États des processus en section critique
- `ProcessIDManager.py` : Numérotation automatique des processus

## Exécution et Tests

### Lancement

```bash
python Launcher.py
```

### Sortie Typique

```text
Lancement de 3 processus pour 5 secondes...
ProcessIDManager initialized - Ready for automatic numbering
Assigned process ID: 0
Mailbox created for P0 (ID: 0)
P0 starts WITH the token
Com middleware initialized for P0 (ID: 0)
Processus P0 créé avec ID automatique: 0
[... tests de communication synchrone ...]
```
