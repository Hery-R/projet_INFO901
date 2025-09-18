"""
Module Mailbox pour la gestion des messages reçus par un processus.
Contient la classe Mailbox qui sert de boîte aux lettres thread-safe.
"""

import threading
from collections import deque
from typing import Optional, List
from Message import Message, MessageType


class Mailbox:
    """
    Boîte aux lettres thread-safe pour stocker les messages reçus par un processus.

    Cette classe gère la réception, le stockage et la récupération des messages
    de manière sécurisée dans un environnement multi-threadé.

    Attributes:
        _messages (deque): File des messages reçus
        _lock (threading.Lock): Verrou pour la synchronisation thread-safe
        _condition (threading.Condition): Condition pour attendre des messages
    """

    def __init__(self):
        """Initialise une nouvelle boîte aux lettres vide."""
        self._messages: deque[Message] = deque()
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)

    def isEmpty(self) -> bool:
        """
        Vérifie si la boîte aux lettres est vide.

        Returns:
            True si aucun message n'est présent, False sinon
        """
        with self._lock:
            return len(self._messages) == 0

    def size(self) -> int:
        """
        Retourne le nombre de messages dans la boîte aux lettres.

        Returns:
            Nombre de messages en attente
        """
        with self._lock:
            return len(self._messages)

    def putMessage(self, message: Message) -> None:
        """
        Ajoute un message à la boîte aux lettres.

        Args:
            message: Le message à ajouter
        """
        with self._condition:
            self._messages.append(message)
            self._condition.notify_all()  # Réveille tous les threads en attente

    def getMsg(self) -> Optional[Message]:
        """
        Récupère et supprime le premier message de la boîte aux lettres.

        Returns:
            Le premier message ou None si la boîte est vide
        """
        with self._lock:
            if self._messages:
                return self._messages.popleft()
            return None

    def getMessage(self) -> Optional[Message]:
        """
        Alias pour getMsg() pour compatibilité avec l'exemple existant.

        Returns:
            Le premier message ou None si la boîte est vide
        """
        return self.getMsg()

    def peekMessage(self) -> Optional[Message]:
        """
        Consulte le premier message sans le supprimer.

        Returns:
            Le premier message ou None si la boîte est vide
        """
        with self._lock:
            if self._messages:
                return self._messages[0]
            return None

    def waitForMessage(self, timeout: Optional[float] = None) -> Optional[Message]:
        """
        Attend qu'un message arrive et le retourne.

        Args:
            timeout: Temps d'attente maximum en secondes (None = infini)

        Returns:
            Le premier message reçu ou None si timeout
        """
        with self._condition:
            while len(self._messages) == 0:
                if not self._condition.wait(timeout):
                    return None  # Timeout
            return self._messages.popleft()

    def getMessageFromSender(self, sender_id: int) -> Optional[Message]:
        """
        Récupère le premier message provenant d'un expéditeur spécifique.

        Args:
            sender_id: ID de l'expéditeur recherché

        Returns:
            Le premier message du sender ou None si aucun trouvé
        """
        with self._lock:
            for i, message in enumerate(self._messages):
                if message.getSender() == sender_id:
                    del self._messages[i]
                    return message
            return None

    def getMessagesByType(self, message_type: MessageType) -> List[Message]:
        """
        Récupère tous les messages d'un type spécifique.

        Args:
            message_type: Type de message recherché

        Returns:
            Liste des messages du type spécifié
        """
        with self._lock:
            matching_messages = []
            remaining_messages = deque()

            while self._messages:
                message = self._messages.popleft()
                if message.getType() == message_type:
                    matching_messages.append(message)
                else:
                    remaining_messages.append(message)

            self._messages = remaining_messages
            return matching_messages

    def hasMessageFromSender(self, sender_id: int) -> bool:
        """
        Vérifie s'il y a un message provenant d'un expéditeur spécifique.

        Args:
            sender_id: ID de l'expéditeur recherché

        Returns:
            True si un message du sender existe, False sinon
        """
        with self._lock:
            return any(msg.getSender() == sender_id for msg in self._messages)

    def clear(self) -> None:
        """Vide complètement la boîte aux lettres."""
        with self._condition:
            self._messages.clear()
            self._condition.notify_all()

    def getAllMessages(self) -> List[Message]:
        """
        Récupère tous les messages et vide la boîte aux lettres.

        Returns:
            Liste de tous les messages
        """
        with self._lock:
            all_messages = list(self._messages)
            self._messages.clear()
            return all_messages

    def __len__(self) -> int:
        """Retourne le nombre de messages (utilisable avec len())."""
        return self.size()

    def __str__(self) -> str:
        """Représentation en chaîne de la boîte aux lettres."""
        with self._lock:
            return f"Mailbox({len(self._messages)} messages)"

    def __repr__(self) -> str:
        """Représentation détaillée de la boîte aux lettres."""
        with self._lock:
            messages_info = [str(msg) for msg in self._messages]
            return f"Mailbox(messages={messages_info})"
