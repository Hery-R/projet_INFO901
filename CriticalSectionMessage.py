"""
CriticalSectionMessage.py - Messages pour l'algorithme en anneau avec jeton
Auteur: RASOAMIARAMANANA Hery ny aina
Auteur: ROUSSEAU Maxime

Cette classe gère la circulation du jeton dans l'algorithme en anneau
pour l'exclusion mutuelle en section critique.
"""

from LamportMessage import LamportMessage


class TokenMessage(LamportMessage):
    """
    Message représentant le jeton circulant dans l'anneau.

    Le jeton permet l'exclusion mutuelle : seul le processus possédant
    le jeton peut entrer en section critique. Le jeton circule dans
    l'ordre des IDs : P0 → P1 → P2 → ... → P0.
    """

    def __init__(self, timestamp, from_process_id, to_process_id):
        """
        Initialise un message de jeton.

        Args:
            timestamp (int): Horloge de Lamport du processus émetteur
            from_process_id (int): ID du processus qui envoie le jeton
            to_process_id (int): ID du processus destinataire du jeton
        """
        # Création du payload descriptif
        payload = f"TOKEN from P{from_process_id} to P{to_process_id}"

        # Appel du constructeur parent
        LamportMessage.__init__(self, timestamp, payload)

        # Stockage des IDs pour le routage
        self.from_process_id = from_process_id
        self.to_process_id = to_process_id

    def getFromProcessId(self):
        """
        Retourne l'ID du processus émetteur du jeton.

        Returns:
            int: ID du processus qui a envoyé le jeton
        """
        return self.from_process_id

    def getToProcessId(self):
        """
        Retourne l'ID du processus destinataire du jeton.

        Returns:
            int: ID du processus qui doit recevoir le jeton
        """
        return self.to_process_id
