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
