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
        
        # === ALGORITHME EN ANNEAU AVEC JETON ===
        # État initial : tous les processus sont au repos sauf P0
        self.cs_state = CriticalSectionState.IDLE
        self.has_token = (self.myId == 0)           # P0 commence avec le jeton
        self.wants_cs = False                       # Pas de demande de SC au début
        
        # Si ce processus a le jeton au démarrage, changer son état
        if self.has_token:
            self.cs_state = CriticalSectionState.HAS_TOKEN
            print(f"🎯 {self.getName()} starts WITH the token")
        
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
        """
        Demande d'accès à la section critique.
        
        Dans l'algorithme en anneau, il suffit de marquer son intention.
        Le processus devra attendre de recevoir le jeton pour y accéder.
        """
        self.wants_cs = True  # Marquer l'intention d'entrer en SC
        print(f"🙋 {self.getName()} wants to enter critical section")
    
    def enter_critical_section(self):
        """
        Tentative d'entrée en section critique.
        
        Conditions requises :
        1. Posséder le jeton (has_token = True)
        2. Vouloir entrer en SC (wants_cs = True)  
        3. Être dans l'état HAS_TOKEN
        
        Returns:
            bool: True si l'entrée a réussi, False sinon
        """
        # Vérifier toutes les conditions d'entrée (pas besoin de lock pour la lecture)
        if self.has_token and self.wants_cs and self.cs_state == CriticalSectionState.HAS_TOKEN:
            self.cs_state = CriticalSectionState.IN_CS
            print(f"🔒 {self.getName()} ENTERS critical section with TOKEN")
            return True
        return False
    
    def exit_critical_section(self):
        """
        Sortie de la section critique et transmission du jeton.
        
        Actions :
        1. Vérifier qu'on est bien en section critique
        2. Marquer qu'on ne veut plus la SC
        3. Transmettre le jeton au processus suivant
        """
        # Vérifier qu'on est bien en section critique
        if self.cs_state != CriticalSectionState.IN_CS:
            return
        
        print(f"🔓 {self.getName()} EXITS critical section")
        self.wants_cs = False  # Plus besoin de la SC
        
        # Transmettre directement le jeton (qui mettra l'état à IDLE)
        self._pass_token()
    
    def _pass_token(self):
        """Passer le jeton au processus suivant dans l'anneau"""
        if not self.alive:  # Ne pas passer le jeton si le processus s'arrête
            return
            
        next_process_id = (self.myId + 1) % self.npProcess
        
        # Utilisation du middleware Com pour incrémenter l'horloge
        current_clock = self.com.incclock()
        self.has_token = False
        self.cs_state = CriticalSectionState.IDLE
        
        # Envoyer le jeton
        msg = TokenMessage(current_clock, self.myId, next_process_id)
        print(f"{self.getName()} passes TOKEN to P{next_process_id}")
        PyBus.Instance().post(msg)
    
    @subscribe(threadMode=Mode.PARALLEL, onEvent=TokenMessage)
    def onTokenMessage(self, event):
        # Vérifier si le jeton est pour ce processus et si le processus est encore vivant
        if event.getToProcessId() == self.myId and self.alive:
            # Utilisation du middleware Com pour la mise à jour de l'horloge
            old_clock, new_clock = self.com.update_clock_on_receive(event.getTimestamp())
            self.has_token = True
            self.cs_state = CriticalSectionState.HAS_TOKEN
            
            print(f"{self.getName()} received TOKEN from P{event.getFromProcessId()}")
            
            # Si on ne veut pas la section critique, passer le jeton immédiatement
            if not self.wants_cs and self.alive:
                sleep(0.1)  # Petite pause pour éviter la circulation trop rapide
                self._pass_token()
    
    def run(self):
        loop = 0
        while self.alive:
            # Utilisation du middleware Com pour incrémenter l'horloge
            current_clock = self.com.incclock()
            token_status = "WITH_TOKEN" if self.has_token else "NO_TOKEN"
            wants_status = "WANTS_CS" if self.wants_cs else "NO_REQUEST"

            print(f"{self.getName()} Loop: {loop} (clock {current_clock}) - State: {self.cs_state.value} - {token_status} - {wants_status}")

            # Test de la section critique avec jeton : demander périodiquement
            if loop % 5 == self.myId and not self.wants_cs:  # Décalage pour éviter les demandes simultanées
                self.request_critical_section()
            
            # Si on a le jeton et qu'on veut la section critique, y entrer
            if self.cs_state == CriticalSectionState.HAS_TOKEN and self.wants_cs:
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
