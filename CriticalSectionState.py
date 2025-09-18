"""
CriticalSectionState.py - États des processus dans l'algorithme en anneau
Auteur: RASOAMIARAMANANA Hery ny aina

Cette énumération définit les différents états possibles d'un processus
dans l'algorithme en anneau avec jeton pour la section critique.
"""

from enum import Enum

class CriticalSectionState(Enum):
    """
    États possibles d'un processus dans l'algorithme en anneau avec jeton.
    
    Transitions possibles :
    IDLE → HAS_TOKEN (réception du jeton)
    HAS_TOKEN → IN_CS (entrée en section critique)
    IN_CS → IDLE (sortie de section critique et transmission du jeton)
    """
    
    IDLE = "idle"           # Processus au repos, sans jeton
    HAS_TOKEN = "has_token" # Processus possède le jeton (peut entrer en SC)
    IN_CS = "in_cs"         # Processus en section critique
