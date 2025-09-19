"""
Mailbox.py - Boîte aux lettres pour messages asynchrones
Auteur: RASOAMIARAMANANA Hery ny aina
Auteur: ROUSSEAU Maxime

Cette classe implémente une boîte aux lettres thread-safe permettant
aux processus de récupérer leurs messages à leur rythme.
"""

from threading import Lock, Condition
from collections import deque


class Mailbox:
    """
    Boîte aux lettres thread-safe pour la communication asynchrone.

    Permet aux processus de :
    - Déposer des messages de manière thread-safe
    - Récupérer des messages sans attente active
    - Attendre l'arrivée de nouveaux messages
    """

    def __init__(self, owner_process_id, owner_process_name):
        """
        Initialise une boîte aux lettres pour un processus.

        Args:
            owner_process_id (int): ID du processus propriétaire
            owner_process_name (str): Nom du processus propriétaire
        """
        self.owner_id = owner_process_id
        self.owner_name = owner_process_name

        # File d'attente des messages (FIFO)
        self.messages = deque()

        # Synchronisation thread-safe
        self.lock = Lock()
        self.condition = Condition(self.lock)

        print(
            f"📬 Mailbox created for {owner_process_name} (ID: {owner_process_id})")

    def deposit_message(self, message):
        """
        Dépose un message dans la boîte aux lettres.

        Cette méthode est appelée par le middleware Com quand un message
        arrive pour ce processus.

        Args:
            message (LamportMessage): Message à déposer
        """
        with self.condition:
            self.messages.append(message)
            print(
                f"📬➡️ Message deposited in {self.owner_name}'s mailbox: {message.getPayload()[:50]}...")
            # Réveiller les threads en attente de messages
            self.condition.notify_all()

    def has_messages(self):
        """
        Vérifie s'il y a des messages en attente.

        Returns:
            bool: True si au moins un message est disponible
        """
        with self.lock:
            return len(self.messages) > 0

    def get_message(self):
        """
        Récupère le prochain message sans attendre.

        Returns:
            LamportMessage | None: Le prochain message ou None si aucun disponible
        """
        with self.lock:
            if len(self.messages) > 0:
                message = self.messages.popleft()
                print(
                    f"📬⬅️ {self.owner_name} retrieved message: {message.getPayload()[:50]}...")
                return message
            return None

    def wait_for_message(self, timeout=None):
        """
        Attend l'arrivée d'un nouveau message (bloquant).

        Args:
            timeout (float, optional): Timeout en secondes. None = attente infinie

        Returns:
            LamportMessage | None: Message reçu ou None si timeout
        """
        with self.condition:
            # Attendre qu'un message arrive
            while len(self.messages) == 0:
                if not self.condition.wait(timeout):
                    # Timeout expiré
                    return None

            # Un message est arrivé, le récupérer
            message = self.messages.popleft()
            print(
                f"📬⏰ {self.owner_name} waited and got message: {message.getPayload()[:50]}...")
            return message

    def get_message_count(self):
        """
        Retourne le nombre de messages en attente.

        Returns:
            int: Nombre de messages dans la boîte
        """
        with self.lock:
            return len(self.messages)
