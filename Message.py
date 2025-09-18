"""
Module Message pour la communication entre processus distribués.
Contient la classe Message pour encapsuler les données échangées.
"""

import time
from enum import Enum
from typing import Any, Optional


class MessageType(Enum):
    """Types de messages possibles dans le système."""
    NORMAL = "normal"
    SYNC_REQUEST = "sync_request"
    SYNC_ACK = "sync_ack"
    CS_REQUEST = "cs_request"  # Critical Section Request
    CS_REPLY = "cs_reply"     # Critical Section Reply
    CS_RELEASE = "cs_release"  # Critical Section Release
    BROADCAST = "broadcast"
    BARRIER = "barrier"


class Message:
    """
    Classe représentant un message dans le système distribué.

    Attributes:
        sender (int): ID du processus expéditeur
        receiver (int): ID du processus destinataire (-1 pour broadcast)
        content (Any): Contenu du message
        message_type (MessageType): Type du message
        timestamp (float): Horodatage du message (pour l'ordre des événements)
        message_id (str): Identifiant unique du message
    """

    def __init__(self, sender: int, receiver: int, content: Any,
                 message_type: MessageType = MessageType.NORMAL):
        """
        Initialise un nouveau message.

        Args:
            sender: ID du processus expéditeur
            receiver: ID du processus destinataire (-1 pour broadcast)
            content: Contenu du message
            message_type: Type du message
        """
        self.sender = sender
        self.receiver = receiver
        self.content = content
        self.message_type = message_type
        self.timestamp = time.time()
        self.message_id = f"{sender}_{receiver}_{self.timestamp}"

    def getSender(self) -> int:
        """Retourne l'ID de l'expéditeur du message."""
        return self.sender

    def getReceiver(self) -> int:
        """Retourne l'ID du destinataire du message."""
        return self.receiver

    def getContent(self) -> Any:
        """Retourne le contenu du message."""
        return self.content

    def getType(self) -> MessageType:
        """Retourne le type du message."""
        return self.message_type

    def getTimestamp(self) -> float:
        """Retourne l'horodatage du message."""
        return self.timestamp

    def getId(self) -> str:
        """Retourne l'identifiant unique du message."""
        return self.message_id

    def __str__(self) -> str:
        """Représentation en chaîne du message."""
        return f"Message[{self.sender}->{self.receiver}]: {self.content} ({self.message_type.value})"

    def __repr__(self) -> str:
        """Représentation détaillée du message."""
        return (f"Message(sender={self.sender}, receiver={self.receiver}, "
                f"content='{self.content}', type={self.message_type.value}, "
                f"timestamp={self.timestamp})")
