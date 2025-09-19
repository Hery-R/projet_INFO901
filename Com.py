"""
Com.py - Classe middleware pour la communication dans le système distribué
Auteur: Refactorisation du code de RASOAMIARAMANANA Hery ny aina

Cette classe centralise toute la logique de communication qui était
précédemment dans Process.py, pour une meilleure séparation des responsabilités.
"""

from threading import Lock
from pyeventbus3.pyeventbus3 import *
from BroadcastMessage import BroadcastMessage
from MessageTo import MessageTo
from CriticalSectionMessage import TokenMessage
from CriticalSectionState import CriticalSectionState

class Com:
    """
    Middleware de communication pour système distribué.
    
    Responsabilités :
    - Gestion de l'horloge logique de Lamport avec protection thread-safe
    - Services de communication (broadcast, messages dirigés)
    - Gestion des sections critiques distribuées
    - Synchronisation globale
    """
    
    def __init__(self, process_id, process_name, total_processes):
        """
        Initialise le middleware de communication.
        
        Args:
            process_id (int): ID unique du processus propriétaire
            process_name (str): Nom lisible du processus (ex: "P0", "P1")
            total_processes (int): Nombre total de processus dans le système
        """
        # Configuration de base
        self.process_id = process_id
        self.process_name = process_name
        self.total_processes = total_processes
        
        # Horloge logique de Lamport avec protection thread-safe
        self.lamport_clock = 0
        self.lock = Lock()
        
        # === GESTION DE LA SECTION CRITIQUE ===
        # État initial : tous les processus sont au repos sauf P0
        self.cs_state = CriticalSectionState.IDLE
        self.has_token = (process_id == 0)  # P0 commence avec le jeton
        self.wants_cs = False               # Pas de demande de SC au début
        
        # Si ce processus a le jeton au démarrage, changer son état
        if self.has_token:
            self.cs_state = CriticalSectionState.HAS_TOKEN
            print(f"🎯 {process_name} starts WITH the token")
        
        # Note : Com ne s'enregistre PAS au bus d'événements
        # Seuls les Process doivent s'y enregistrer pour recevoir les messages
        
        print(f"🔧 Com middleware initialized for {process_name} (ID: {process_id})")
    
    def incclock(self):
        """
        Incrémente l'horloge de Lamport pour un événement local.
        
        Cette méthode doit être appelée par Process avant chaque action locale
        qui génère un message (envoi, broadcast, etc.).
        
        Returns:
            int: Nouvelle valeur de l'horloge après incrémentation
        """
        with self.lock:
            self.lamport_clock += 1
            return self.lamport_clock
    
    def getclock(self):
        """
        Retourne la valeur actuelle de l'horloge de Lamport.
        
        Returns:
            int: Valeur actuelle de l'horloge logique
        """
        with self.lock:
            return self.lamport_clock
    
    def update_clock_on_receive(self, received_timestamp):
        """
        Met à jour l'horloge selon les règles de Lamport à la réception d'un message.
        
        Règle : clock = max(clock_local, clock_message) + 1
        
        Args:
            received_timestamp (int): Timestamp du message reçu
            
        Returns:
            tuple: (ancienne_horloge, nouvelle_horloge)
        """
        with self.lock:
            old_clock = self.lamport_clock
            self.lamport_clock = max(self.lamport_clock, received_timestamp) + 1
            return (old_clock, self.lamport_clock)
    
    def get_process_info(self):
        """
        Retourne les informations du processus propriétaire.
        
        Returns:
            dict: Informations du processus (id, name, total)
        """
        return {
            'id': self.process_id,
            'name': self.process_name,
            'total_processes': self.total_processes
        }
    
    # === MÉTHODES DE COMMUNICATION ===
    
    def broadcast(self, payload):
        """
        Diffuse un message à tous les processus du système.
        
        Cette méthode encapsule l'envoi de messages de diffusion en gérant
        automatiquement l'incrémentation de l'horloge de Lamport.
        
        Args:
            payload (str): Contenu à diffuser à tous les processus
        """
        # Incrémenter l'horloge pour cet événement local d'envoi
        current_clock = self.incclock()
        
        # Créer et envoyer le message de diffusion
        msg = BroadcastMessage(current_clock, payload)
        print(f"📢 {self.process_name} broadcast: {payload} with timestamp {current_clock}")
        PyBus.Instance().post(msg)
    
    def sendTo(self, payload, destination_id):
        """
        Envoie un message à un processus spécifique.
        
        Cette méthode encapsule l'envoi de messages dirigés en gérant
        automatiquement l'incrémentation de l'horloge de Lamport.
        
        Args:
            payload (str): Contenu du message
            destination_id (int): ID du processus destinataire
        """
        # Incrémenter l'horloge pour cet événement local d'envoi
        current_clock = self.incclock()
        
        # Créer et envoyer le message dirigé
        msg = MessageTo(current_clock, payload, destination_id)
        print(f"{self.process_name} sendTo P{destination_id}: {payload} with timestamp {current_clock}")
        PyBus.Instance().post(msg)
    
    # === MÉTHODES DE SECTION CRITIQUE ===
    
    def requestSC(self):
        """
        Demande d'accès à la section critique.
        
        Dans l'algorithme en anneau, il suffit de marquer son intention.
        Le processus devra attendre de recevoir le jeton pour y accéder.
        """
        self.wants_cs = True
        print(f"🙋 {self.process_name} wants to enter critical section")
    
    def trySC(self):
        """
        Tentative d'entrée en section critique.
        
        Returns:
            bool: True si l'entrée a réussi, False sinon
        """
        # Vérifier toutes les conditions d'entrée
        if self.has_token and self.wants_cs and self.cs_state == CriticalSectionState.HAS_TOKEN:
            self.cs_state = CriticalSectionState.IN_CS
            print(f"🔒 {self.process_name} ENTERS critical section with TOKEN")
            return True
        return False
    
    def releaseSC(self):
        """
        Sortie de la section critique et transmission du jeton.
        """
        # Vérifier qu'on est bien en section critique
        if self.cs_state != CriticalSectionState.IN_CS:
            return
        
        print(f"🔓 {self.process_name} EXITS critical section")
        self.wants_cs = False  # Plus besoin de la SC
        
        # Transmettre le jeton au processus suivant
        self._pass_token()
    
    def _pass_token(self):
        """Passer le jeton au processus suivant dans l'anneau"""
        next_process_id = (self.process_id + 1) % self.total_processes
        
        # Incrémenter l'horloge pour cet événement local d'envoi
        current_clock = self.incclock()
        self.has_token = False
        self.cs_state = CriticalSectionState.IDLE
        
        # Envoyer le jeton
        msg = TokenMessage(current_clock, self.process_id, next_process_id)
        print(f"{self.process_name} passes TOKEN to P{next_process_id}")
        PyBus.Instance().post(msg)
    
    def receive_token(self, from_process_id, timestamp):
        """
        Réception du jeton depuis un autre processus.
        
        Args:
            from_process_id (int): ID du processus qui envoie le jeton
            timestamp (int): Timestamp du message de jeton
        """
        # Mise à jour de l'horloge de Lamport
        old_clock, new_clock = self.update_clock_on_receive(timestamp)
        self.has_token = True
        self.cs_state = CriticalSectionState.HAS_TOKEN
        
        print(f"{self.process_name} received TOKEN from P{from_process_id}")
        
        return not self.wants_cs  # Retourne True si on doit passer le jeton immédiatement
    
    def get_cs_status(self):
        """
        Retourne l'état actuel de la section critique.
        
        Returns:
            dict: État complet de la section critique
        """
        return {
            'state': self.cs_state,
            'has_token': self.has_token,
            'wants_cs': self.wants_cs
        }
