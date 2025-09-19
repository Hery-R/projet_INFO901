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

        # Note : Process ne s'enregistre plus au PyBus
        # Les messages sont maintenant gérés via la mailbox dans Com

        # État du processus
        self.alive = True                            # Contrôle de la boucle principale
        # Liste des threads de section critique actifs
        self.active_cs_threads = []

        # Middleware de communication
        self.com = Com(self.myId, self.myProcessName, self.npProcess)
        # Partager l'état du processus avec Com
        # Démarrer le thread du processus
        self.com.process_alive = lambda: self.alive
        self.start()

    # === TRAITEMENT DES MESSAGES VIA MAILBOX ===

    def process_mailbox_messages(self):
        """
        Traite les messages disponibles dans la mailbox.

        Cette méthode remplace les anciens handlers PyBus.
        Elle récupère les messages de la boîte aux lettres et les traite.
        """
        while self.com.has_messages():
            message = self.com.get_message()
            if message:
                self._handle_message(message)

    def _handle_message(self, message):
        """
        Traite un message spécifique selon son type.

        Args:
            message (LamportMessage): Message à traiter
        """
        # Mise à jour de l'horloge de Lamport
        old_clock, new_clock = self.com.update_clock_on_receive(
            message.getTimestamp())

        if isinstance(message, TokenMessage):
            self._handle_token_message(message)
        elif isinstance(message, BroadcastMessage):
            self._handle_broadcast_message(message)
        elif isinstance(message, MessageTo):
            self._handle_directed_message(message)
        else:
            # Message générique
            print(
                f"{self.getName()} processed generic message: {message.getPayload()} (clock: {old_clock} → {new_clock})")

    def _handle_token_message(self, message):
        """Traite un message de jeton."""
        if message.getToProcessId() == self.myId and self.alive:
            should_pass_immediately = self.com.receive_token(
                message.getFromProcessId(),
                message.getTimestamp()
            )

            if should_pass_immediately and self.alive:
                from time import sleep
                sleep(0.1)  # Petit délai avant de passer le jeton

    def _handle_broadcast_message(self, message):
        """Traite un message de diffusion."""
        old_clock, new_clock = self.com.update_clock_on_receive(
            message.getTimestamp())
        print(
            f"{self.getName()} received broadcast: {message.getPayload()} (local clock: {new_clock})")

    def _handle_directed_message(self, message):
        """Traite un message dirigé."""
        if message.getTo() == self.myId:
            old_clock, new_clock = self.com.update_clock_on_receive(
                message.getTimestamp())
            print(
                f"{self.getName()} received directed message: {message.getPayload()} (clock: {new_clock})")

    def broadcast(self, payload):
        """
        Diffuse un message à tous les processus du système.

        Args:
            payload (str): Contenu à diffuser
        """
        # Déléguer au middleware Com
        self.com.broadcast(payload)

    def sendTo(self, payload, to):
        """
        Envoie un message à un processus spécifique.

        Args:
            payload (str): Contenu du message
            to (int): ID du processus destinataire
        """
        # Déléguer au middleware Com
        self.com.sendTo(payload, to)

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

    # === NOUVELLES MÉTHODES DU TP ===

    def synchronize(self):
        """Synchronisation avec tous les autres processus"""
        self.com.synchronize()

    def broadcast_sync(self, payload):
        """Broadcast synchrone - ce processus est l'émetteur"""
        self.com.broadcastSync(payload, self.myId)

    def wait_broadcast_sync(self, from_process_id, payload):
        """Attendre un broadcast synchrone d'un processus spécifique"""
        self.com.broadcastSync(payload, from_process_id)

    def send_to_sync(self, payload, destination_id):
        """Envoi synchrone à un processus"""
        self.com.sendToSync(payload, destination_id)

    def receive_from_sync(self, from_process_id):
        """Réception synchrone depuis un processus"""
        return self.com.receiveFromSync(from_process_id)

    # Les handlers PyBus ont été remplacés par le traitement via mailbox

    def process_mailbox_messages(self):
        """Traite tous les messages en attente dans la mailbox"""
        while self.com.has_messages() and self.alive:
            message = self.com.get_message()
            if message:
                self.handle_message(message)

    def handle_message(self, message):
        """Traite un message spécifique selon son type"""
        from BroadcastMessage import BroadcastMessage
        from MessageTo import MessageTo
        from CriticalSectionMessage import TokenMessage

        # Mettre à jour l'horloge de Lamport
        old_clock, new_clock = self.com.update_clock_on_receive(
            message.getTimestamp())

        if isinstance(message, TokenMessage):
            # Traitement des jetons
            if message.getToProcessId() == self.myId:
                should_pass_immediately = self.com.receive_token(
                    message.getFromProcessId(),
                    message.getTimestamp()
                )

                # Si on ne veut pas la section critique, passer le jeton immédiatement
                if should_pass_immediately and self.alive:
                    from time import sleep
                    sleep(0.1)
                    self.com._pass_token()

        elif isinstance(message, BroadcastMessage):
            # Traitement des broadcasts
            print(
                f"{self.getName()} received broadcast: {message.getPayload()} (clock: {new_clock})")

        elif isinstance(message, MessageTo):
            # Traitement des messages dirigés
            if message.getTo() == self.myId:
                print(
                    f"{self.getName()} received directed message: {message.getPayload()} (clock: {new_clock})")

    def run(self):
        loop = 0
        while self.alive:
            # Traiter les messages en attente dans la mailbox
            self.process_mailbox_messages()

            # Utilisation du middleware Com pour incrémenter l'horloge
            current_clock = self.com.incclock()

            # Récupérer l'état de la section critique depuis Com
            cs_status = self.com.get_cs_status()
            token_status = "WITH_TOKEN" if cs_status['has_token'] else "NO_TOKEN"
            wants_status = "WANTS_CS" if cs_status['wants_cs'] else "NO_REQUEST"

            print(
                f"{self.getName()} Loop: {loop} (clock {current_clock}) - State: {cs_status['state'].value} - {token_status} - {wants_status}")

            # Test de la section critique avec jeton : demander périodiquement
            # Décalage pour éviter les demandes simultanées
            if loop % 7 == self.myId and not cs_status['wants_cs']:
                print(f"🎯 {self.getName()} requesting critical section...")
                # Attention: requestSC() est maintenant BLOQUANT selon les spécifications
                # Il faudra le lancer dans un thread séparé pour éviter de bloquer la boucle principale
                import threading

                def request_cs():
                    try:
                        if not self.alive:  # Vérifier si le processus est encore actif
                            return
                        self.request_critical_section()  # BLOQUANT jusqu'à obtention
                        if not self.alive:  # Vérifier à nouveau après l'attente
                            return
                        # Simuler du travail en section critique
                        print(
                            f"{self.getName()} *** WORKING IN CRITICAL SECTION ***")
                        sleep(1.0)  # Travail en section critique
                        self.exit_critical_section()
                    except Exception as e:
                        print(
                            f"❌ {self.getName()} error in critical section: {e}")

                cs_thread = threading.Thread(
                    target=request_cs, name=f"CS-{self.getName()}")
                cs_thread.daemon = True  # Thread daemon s'arrête avec le programme principal
                cs_thread.start()
                self.active_cs_threads.append(cs_thread)

            sleep(0.8)
            loop += 1
        print(f"{self.getName()} stopped")

    def stop(self):
        self.alive = False
        # Notifier tous les threads en attente de section critique pour qu'ils se terminent
        with self.com.cs_condition:
            self.com.cs_condition.notify_all()

    def waitStopped(self):
        self.join()
        # Attendre que tous les threads de section critique se terminent
        for thread in self.active_cs_threads:
            if thread.is_alive():
                # Timeout pour éviter d'attendre indéfiniment
                thread.join(timeout=1.0)
