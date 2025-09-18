"""
MessageTo.py - Message dirigé vers un processus spécifique
Auteur: RASOAMIARAMANANA Hery ny aina

Cette classe représente un message envoyé à un processus particulier
identifié par son ID dans le système distribué.
"""

from LamportMessage import LamportMessage

class MessageTo(LamportMessage):
    """
    Message dirigé vers un processus spécifique.
    
    Hérite de LamportMessage et ajoute la capacité d'adressage
    vers un processus particulier du système distribué.
    """
    
    def __init__(self, timestamp, payload, to):
        """
        Initialise un message dirigé.
        
        Args:
            timestamp (int): Horloge de Lamport du processus émetteur
            payload (str): Contenu du message
            to (int): ID du processus destinataire
        """
        # Appel du constructeur parent
        LamportMessage.__init__(self, timestamp, payload)
        self.to = to  # ID du processus destinataire
    
    def getTo(self):
        """
        Retourne l'ID du processus destinataire.
        
        Returns:
            int: ID du processus qui doit recevoir le message
        """
        return self.to
    
    def setTo(self, to):
        """
        Modifie le destinataire du message.
        
        Args:
            to (int): Nouvel ID du processus destinataire
        """
        self.to = to