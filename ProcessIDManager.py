"""
ProcessIDManager.py - Gestionnaire de numérotation automatique des processus
Auteur: RASOAMIARAMANANA Hery ny aina
Auteur: ROUSSEAU Maxime

Cette classe gère la numérotation automatique et consécutive des processus
sans utiliser de variables de classe, conformément aux spécifications du TP.
"""

import threading


class ProcessIDManager:
    """
    Gestionnaire centralisé pour l'attribution d'IDs uniques aux processus.

    Fournit une numérotation automatique et consécutive commençant à 0,
    sans utiliser de variables de classe comme interdit par les spécifications.
    """

    def __init__(self):
        """Initialise le gestionnaire d'IDs."""
        self._next_id = 0
        self._lock = threading.Lock()
        self._assigned_ids = []  # Liste des IDs attribués pour vérification
        print("🔢 ProcessIDManager initialized - Ready for automatic numbering")

    def get_next_id(self):
        """
        Attribue le prochain ID unique de manière thread-safe.

        Returns:
            int: ID unique consécutif (0, 1, 2, ...)
        """
        with self._lock:
            assigned_id = self._next_id
            self._next_id += 1
            self._assigned_ids.append(assigned_id)
            print(f"🔢➡️ Assigned process ID: {assigned_id}")
            return assigned_id

    def get_assigned_count(self):
        """
        Retourne le nombre de processus déjà enregistrés.

        Returns:
            int: Nombre de processus avec un ID attribué
        """
        with self._lock:
            return len(self._assigned_ids)

    def reset(self):
        """
        Remet à zéro le compteur (pour les tests).
        ⚠️ À utiliser avec précaution en production.
        """
        with self._lock:
            self._next_id = 0
            self._assigned_ids.clear()
            print("🔢🔄 ProcessIDManager reset to 0")


# Instance globale singleton du gestionnaire d'IDs
_id_manager = None
_manager_lock = threading.Lock()


def get_process_id_manager():
    """
    Retourne l'instance singleton du gestionnaire d'IDs.

    Returns:
        ProcessIDManager: Instance du gestionnaire
    """
    global _id_manager
    if _id_manager is None:
        with _manager_lock:
            if _id_manager is None:
                _id_manager = ProcessIDManager()
    return _id_manager


def reset_process_id_manager():
    """
    Remet à zéro le gestionnaire d'IDs (pour les tests).
    """
    global _id_manager
    if _id_manager is not None:
        _id_manager.reset()
    else:
        # Créer et reset immédiatement
        get_process_id_manager().reset()
