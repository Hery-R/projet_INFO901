"""
BroadcastMessage.py - Message de diffusion générale
Auteur: RASOAMIARAMANANA Hery ny aina

Cette classe représente un message diffusé à tous les processus
du système distribué.
"""

from LamportMessage import LamportMessage

class BroadcastMessage(LamportMessage):
    """
    Message de diffusion envoyé à tous les processus.
    
    Hérite de LamportMessage et ajoute la capacité de diffusion
    générale vers tous les participants du système distribué.
    """
    
    def __init__(self, timestamp, payload):
        """
        Initialise un message de diffusion.
        
        Args:
            timestamp (int): Horloge de Lamport du processus émetteur
            payload (str): Contenu à diffuser à tous les processus
        """
        # Appel du constructeur parent
        LamportMessage.__init__(self, timestamp, payload)
        self.broadcast = True  # Marqueur de diffusion

    def isBroadcast(self):
        """
        Vérifie si le message est un broadcast.
        
        Returns:
            bool: True car c'est toujours un message de diffusion
        """
        return self.broadcast