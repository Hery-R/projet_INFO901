# Projet INFO901 - Refactorisation Bus Asynchrone

## Auteur
**RASOAMIARAMANANA Hery ny aina**

## État Actuel - Étape 1 Complétée ✅

Ce projet est en cours de refactorisation pour séparer la logique métier de la communication.

### Architecture Refactorisée

```
Process (logique métier)
   ↓ délègue à
Com (middleware communication)
   ↓ utilise
PyBus (bus d'événements)
```

### Composants

#### 1. **`Com.py`** - Middleware de Communication
- Gestion centralisée de l'horloge de Lamport
- Méthodes thread-safe : `incclock()`, `getclock()`, `update_clock_on_receive()`
- Services de communication : `broadcast()`, `sendTo()`
- Protection par mutex pour la concurrence

#### 2. **`Process.py`** - Processus Métier Refactorisé
- Logique métier du processus
- Gestion de l'état de la section critique
- Délégation de la communication au middleware `Com`
- Test de section critique avec jeton en anneau

#### 3. **Modules de Messages**
- `LamportMessage.py` - Message de base avec timestamp
- `BroadcastMessage.py` - Message de diffusion
- `MessageTo.py` - Message dirigé
- `CriticalSectionMessage.py` - Message de jeton
- `CriticalSectionState.py` - États de section critique

#### 4. **`Launcher.py`** - Point d'Entrée
- Lance et coordonne plusieurs processus
- Configuration par défaut : 3 processus, 5 secondes

## Installation et Utilisation

### Prérequis
```bash
# Activer l'environnement virtuel
.venv\Scripts\activate

# Installer les dépendances
pip install pyeventbus3
```

### Exécution
```bash
python Launcher.py
```

## Fonctionnalités Validées ✅

1. **Horloge de Lamport** : Gérée par `Com` avec protection thread-safe
2. **Communication** : `broadcast()` et `sendTo()` via `Com`
3. **Section Critique** : Algorithme en anneau avec jeton fonctionnel
4. **Séparation des responsabilités** : Process ↔ Com

## Prochaines Étapes 🚀

- **Étape 2** : Transférer la gestion de la section critique vers `Com`
- **Étape 3** : Implémenter les services bloquants/non-bloquants
- **Étape 4** : Ajouter la synchronisation globale
- **Étape 5** : Gestion automatique de la numérotation des processus

## Tests

Le système utilise actuellement le test de **section critique avec jeton** pour valider :
- L'exclusion mutuelle distribuée
- La circulation correcte du jeton (P0 → P1 → P2 → P0)
- Le respect des horloges de Lamport
- La séparation Process/Com

## Structure du Projet

```
projet_INFO901/
├── Process.py          # Processus métier refactorisé
├── Com.py             # Middleware de communication
├── Launcher.py        # Point d'entrée
├── LamportMessage.py  # Message de base
├── BroadcastMessage.py # Message diffusion
├── MessageTo.py       # Message dirigé
├── CriticalSectionMessage.py # Message jeton
├── CriticalSectionState.py   # États SC
├── TODO.txt          # Plan de refactorisation
└── README.md         # Ce fichier
```