# Projet INFO901 - Systeme Distribue avec Middleware de Communication

## Auteurs

- RASOAMIARAMANANA Hery ny aina
- ROUSSEAU Maxime

## Vue d'ensemble

Ce projet implemente un systeme distribue complet avec middleware de communication. Le systeme utilise une architecture a base de bus d'evenements (PyBus) pour la communication asynchrone entre processus, avec gestion automatique de la synchronisation temporelle (horloges de Lamport) et exclusion mutuelle distribuee (algorithme en anneau avec jeton).

## Architecture Generale

```
Process (logique metier)
   ↓ delegue a
Com (middleware communication)
   ↓ utilise
PyBus (bus d'evenements)
   ↓
MessageDistributor (routage intelligent)
   ↓
Mailbox (stockage asynchrone)
   ↓
Process (consommation a son rythme)
```

### Separation des Responsabilites

Cette architecture respecte le principe de separation des responsabilites :

- **Process** : Logique metier et traitement des messages
- **Com** : Middleware de communication centralise
- **PyBus** : Transport global d'evenements
- **MessageDistributor** : Routage intelligent des messages
- **Mailbox** : Stockage asynchrone par processus

## Concepts du TP et leur Implementation

### 1. Horloges de Lamport

**Concept** : Synchronisation temporelle logique dans un systeme distribue sans horloge globale.

**Implementation** :

- Chaque processus maintient une horloge logique locale (`lamport_clock`)
- Incrementation avant chaque envoi de message (`incclock()`)
- Mise a jour a la reception selon la regle : `max(horloge_locale, horloge_message) + 1`
- Protection thread-safe avec mutex (`Lock`)

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

**Concept** : Echange de messages sans blocage des processus emetteurs.

**Implementation** :

- Bus d'evenements PyBus pour le transport global
- Boites aux lettres (Mailbox) pour chaque processus
- Communication non-bloquante pour l'emetteur

```python
# Envoi (non-bloquant)
def broadcast(self, payload):
    current_clock = self.incclock()
    msg = BroadcastMessage(current_clock, payload)
    PyBus.Instance().post(msg)  # Envoi asynchrone
```

### 3. PyBus et @subscribe : Architecture de Communication

**Pourquoi PyBus ?**
PyBus est un bus d'evenements qui permet :

- Communication decouplee entre composants
- Publication/abonnement (publish/subscribe) pattern
- Gestion automatique des threads
- Extensibilite pour nouveaux types de messages

**Implementation du pattern publish/subscribe** :

```python
# Dans MessageDistributor.py - Abonnement aux evenements
@subscribe(threadMode=Mode.PARALLEL, onEvent=BroadcastMessage)
def distribute_broadcast(self, event):
    # Reception automatique de tous les messages de diffusion
    for process_id, mailbox in self.mailboxes.items():
        mailbox.deposit_message(event)

@subscribe(threadMode=Mode.PARALLEL, onEvent=MessageTo)
def distribute_directed_message(self, event):
    # Reception automatique des messages diriges
    destination_id = event.getTo()
    if destination_id in self.mailboxes:
        self.mailboxes[destination_id].deposit_message(event)
```

**Publication sur le bus** :

```python
# Dans Com.py - Publication d'evenements
def broadcast(self, payload):
    msg = BroadcastMessage(current_clock, payload)
    PyBus.Instance().post(msg)  # Publication sur le bus

def sendTo(self, payload, destination_id):
    msg = MessageTo(current_clock, payload, destination_id)
    PyBus.Instance().post(msg)  # Publication sur le bus
```

**Avantages de cette architecture** :

- **Decouplage complet** : Emetteurs et recepteurs ne se connaissent pas
- **Extensibilite** : Ajout de nouveaux types de messages facile
- **Performance** : Traitement parallele des messages
- **Robustesse** : Un seul point d'ecoute (MessageDistributor)

### 4. Boites aux Lettres (Mailbox)

**Concept** : Stockage asynchrone des messages pour chaque processus.

**Implementation** :

- File FIFO thread-safe (`collections.deque`)
- Condition variables pour l'attente de messages
- Interface non-bloquante et bloquante

```python
def deposit_message(self, message):
    with self.condition:
        self.messages.append(message)
        self.condition.notify_all()  # Reveil des threads en attente

def wait_for_message(self, timeout=None):
    with self.condition:
        while len(self.messages) == 0:
            if not self.condition.wait(timeout):
                return None
        return self.messages.popleft()
```

### 5. Section Critique Distribuee

**Concept** : Exclusion mutuelle dans un systeme distribue.

**Implementation** : Algorithme en anneau avec jeton

- Un seul jeton circule dans l'anneau (P0 → P1 → P2 → P0)
- Possession du jeton = droit d'entrer en section critique
- Transmission automatique du jeton apres sortie

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

**Concept** : Barriere de synchronisation pour coordonner tous les processus.

**Implementation** : Variables de classe partagees avec condition

- Compteur global du nombre de processus synchronises
- Attente collective jusqu'a ce que tous arrivent a la barriere

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

### 7. Numerotation Automatique

**Concept** : Attribution automatique d'identifiants uniques sans variables de classe.

**Implementation** : Pattern Singleton avec variables d'instance

- Gestionnaire centralise (ProcessIDManager)
- Attribution sequentielle (0, 1, 2, ...)
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

## Communication Synchrone

Le systeme implemente egalement des methodes de communication synchrone utilisant la synchronisation globale :

```python
def broadcastSyncObject(self, payload, from_process_id):
    if self.process_id == from_process_id:
        self.broadcast(payload)
        self.synchronize()  # Attente que tous recoivent
    else:
        self.wait_for_message()
        self.synchronize()  # Confirmation de reception
```

## Structure des Fichiers

### Noyau du Systeme

- `Process.py` : Processus principal avec logique metier
- `Com.py` : Middleware de communication centralise
- `Launcher.py` : Point d'entree et orchestration

### Communication

- `PyBus` : Bus d'evenements (bibliotheque externe)
- `MessageDistributor.py` : Routage intelligent des messages
- `Mailbox.py` : Stockage asynchrone par processus

### Messages

- `LamportMessage.py` : Classe de base avec timestamp
- `BroadcastMessage.py` : Messages de diffusion generale
- `MessageTo.py` : Messages diriges vers un destinataire
- `CriticalSectionMessage.py` : Messages de jeton pour SC

### Gestion d'Etat

- `CriticalSectionState.py` : Etats des processus en section critique
- `ProcessIDManager.py` : Numerotation automatique des processus

## Execution et Tests

### Lancement

```bash
python Launcher.py
```

### Sortie Typique

```
Lancement de 3 processus pour 5 secondes...
ProcessIDManager initialized - Ready for automatic numbering
Assigned process ID: 0
Mailbox created for P0 (ID: 0)
P0 starts WITH the token
Com middleware initialized for P0 (ID: 0)
Processus P0 cree avec ID automatique: 0
[... tests de communication synchrone ...]
```
