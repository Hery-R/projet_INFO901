"""
Process.py - Processus principal du système distribué refactorisé
Auteur: RASOAMIARAMANANA Hery ny aina (refactorisé)

Ce module implémente un processus dans un système distribué avec :
- Délégation de la communication au middleware Com
- Algorithme en anneau avec jeton pour la section critique
- Logique métier séparée de la communication
"""

from threading import Thread
from time import sleep
import threading

from LamportMessage import LamportMessage
from BroadcastMessage import BroadcastMessage
from MessageTo import MessageTo
from CriticalSectionMessage import TokenMessage
from CriticalSectionState import CriticalSectionState
from Com import Com
from pyeventbus3.pyeventbus3 import *

class Process(Thread):
    """
    Processus dans un système distribué refactorisé.
    
    Responsabilités :
    - Logique métier du processus
    - Gestion de l'état de la section critique
    - Délégation de la communication au middleware Com
    """

    # Compteur global pour assigner des IDs uniques aux processus
    nbProcessCreated = 0

    def __init__(self, name, npProcess):
        """
        Initialise un nouveau processus dans le système distribué.
        
        Args:
            name (str): Nom du processus (ex: "P0", "P1", "P2")
            npProcess (int): Nombre total de processus dans le système
        """
        Thread.__init__(self)
        
        # Configuration de base du processus
        self.npProcess = npProcess                    # Nombre total de processus
        self.myId = Process.nbProcessCreated          # ID unique de ce processus
        Process.nbProcessCreated += 1                 # Incrémenter le compteur global
        self.myProcessName = name                     # Nom lisible du processus
        self.setName("MainThread-" + name)           # Nom du thread
        
        # Inscription au bus d'événements pour recevoir les messages
        PyBus.Instance().register(self, self)
        
        # État du processus
        self.alive = True                            # Contrôle de la boucle principale
        
        # Middleware de communication
        self.com = Com(self.myId, self.myProcessName, self.npProcess)
        
        # Démarrer le thread du processus
        self.start()

    # === GESTION DES MESSAGES LAMPORT ===
    
    @subscribe(threadMode=Mode.PARALLEL, onEvent=LamportMessage)
    def process(self, event):
        """
        Handler pour tous les messages de base avec horloge de Lamport.
        
        Applique les règles de synchronisation de Lamport :
        - Réception : clock = max(clock_local, clock_message) + 1
        """
        # Utilisation du middleware Com pour la mise à jour de l'horloge
        old_clock, new_clock = self.com.update_clock_on_receive(event.getTimestamp())

        print(f"{threading.current_thread().name} Processes event with timestamp {event.getTimestamp()}: {event.getPayload()} (local clock: {old_clock} → {new_clock})")

    def broadcast(self, payload):
        """
        Diffuse un message à tous les processus du système.
        
        Args:
            payload (str): Contenu à diffuser
        """
        # Déléguer au middleware Com
        self.com.broadcast(payload)

    @subscribe(threadMode=Mode.PARALLEL, onEvent=BroadcastMessage)
    def onBroadcast(self, event):
        # Utilisation du middleware Com pour la mise à jour de l'horloge
        old_clock, new_clock = self.com.update_clock_on_receive(event.getTimestamp())
        print(f"{self.getName()} received broadcast: {event.getPayload()} (local clock: {new_clock})")
        
    
    def sendTo(self, payload, to):
        """
        Envoie un message à un processus spécifique.
        
        Args:
            payload (str): Contenu du message
            to (int): ID du processus destinataire
        """
        # Déléguer au middleware Com
        self.com.sendTo(payload, to)

    @subscribe(threadMode=Mode.PARALLEL, onEvent=MessageTo)
    def onReceive(self, event):
        if event.getTo() == self.myId:
            # Utilisation du middleware Com pour la mise à jour de l'horloge
            old_clock, new_clock = self.com.update_clock_on_receive(event.getTimestamp())
            print(f"{self.getName()} received message for me: {event.getPayload()} (clock: {new_clock})")
        else:
            # Message pas pour ce process, on ignore
            pass
    
    # === ALGORITHME EN ANNEAU AVEC JETON POUR SECTION CRITIQUE ===
    
    def request_critical_section(self):
        """Demande d'accès à la section critique via Com"""
        self.com.requestSC()
    
    def enter_critical_section(self):
        """Tentative d'entrée en section critique via Com"""
        return self.com.trySC()
    
    def exit_critical_section(self):
        """Sortie de la section critique via Com"""
        self.com.releaseSC()
    
    @subscribe(threadMode=Mode.PARALLEL, onEvent=TokenMessage)
    def onTokenMessage(self, event):
        # Vérifier si le jeton est pour ce processus et si le processus est encore vivant
        if event.getToProcessId() == self.myId and self.alive:
            # Déléguer la réception du jeton au middleware Com
            should_pass_immediately = self.com.receive_token(
                event.getFromProcessId(), 
                event.getTimestamp()
            )
            
            # Si on ne veut pas la section critique, passer le jeton immédiatement
            if should_pass_immediately and self.alive:
                sleep(0.1)  # Petite pause pour éviter la circulation trop rapide
                self.com._pass_token()
    
    def run(self):
        loop = 0
        while self.alive:
            # Utilisation du middleware Com pour incrémenter l'horloge
            current_clock = self.com.incclock()
            
            # Récupérer l'état de la section critique depuis Com
            cs_status = self.com.get_cs_status()
            token_status = "WITH_TOKEN" if cs_status['has_token'] else "NO_TOKEN"
            wants_status = "WANTS_CS" if cs_status['wants_cs'] else "NO_REQUEST"

            print(f"{self.getName()} Loop: {loop} (clock {current_clock}) - State: {cs_status['state'].value} - {token_status} - {wants_status}")

            # Test de la section critique avec jeton : demander périodiquement
            if loop % 5 == self.myId and not cs_status['wants_cs']:  # Décalage pour éviter les demandes simultanées
                self.request_critical_section()
            
            # Si on a le jeton et qu'on veut la section critique, y entrer
            if cs_status['state'] == CriticalSectionState.HAS_TOKEN and cs_status['wants_cs']:
                if self.enter_critical_section():
                    # Simuler du travail en section critique
                    print(f"{self.getName()} *** WORKING IN CRITICAL SECTION ***")
                    sleep(1.0)  # Travail en section critique
                    self.exit_critical_section()

            sleep(0.8)
            loop += 1
        print(f"{self.getName()} stopped")


    def stop(self):
        self.alive = False

    def waitStopped(self):
        self.join()
