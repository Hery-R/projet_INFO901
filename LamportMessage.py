"""
LamportMessage.py - Classe de base pour tous les messages avec horloge de Lamport
Auteur: RASOAMIARAMANANA Hery ny aina
Auteur: ROUSSEAU Maxime

Cette classe encapsule un message avec un timestamp de Lamport pour
ordonner les événements dans un système distribué.
"""


class LamportMessage:
    """
    Message de base avec estampillage temporel de Lamport.

    L'horloge de Lamport permet d'établir un ordre partiel des événements
    dans un système distribué sans horloge globale synchronisée.
    """

    def __init__(self, timestamp, payload):
        """
        Initialise un message avec horloge de Lamport.

        Args:
            timestamp (int): Valeur de l'horloge logique de Lamport
            payload (str): Contenu du message
        """
        self.timestamp = timestamp
        self.payload = payload

    def getTimestamp(self):
        """
        Retourne l'estampille temporelle de Lamport.

        Returns:
            int: Valeur de l'horloge logique au moment de création du message
        """
        return self.timestamp

    def getPayload(self):
        """
        Retourne le contenu du message.

        Returns:
            str: Données transportées par le message
        """
        return self.payload
