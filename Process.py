"""
Process.py - Processus principal du système distribué refactorisé
Auteur: RASOAMIARAMANANA Hery ny aina
Auteur: ROUSSEAU Maxime

Ce module implémente un processus dans un système distribué avec :
- Délégation de la communication au middleware Com
- Algorithme en anneau avec jeton pour la section critique
- Logique métier séparée de la communication
"""

from threading import Thread
from time import sleep

from BroadcastMessage import BroadcastMessage
from MessageTo import MessageTo
from CriticalSectionMessage import TokenMessage
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

    def __init__(self, name=None, npProcess=None):
        """
        Initialise un nouveau processus avec numérotation automatique.

        Le processus se connecte au communicateur qui lui attribue
        automatiquement un numéro unique consécutif.

        Args:
            name (str, optional): Nom du processus. Si None, généré automatiquement
            npProcess (int, optional): Nombre total de processus. Si None, déterminé dynamiquement
        """
        Thread.__init__(self)

        # === CONNEXION ET NUMÉROTATION AUTOMATIQUE ===
        # Le middleware Com attribue automatiquement un ID unique et consécutif
        self.com = Com(process_name=name, total_processes=npProcess)

        # Configuration de base du processus (récupérée depuis Com)
        self.npProcess = npProcess if npProcess is not None else self.com._get_total_processes()
        # ID attribué automatiquement par Com
        self.myId = self.com.process_id
        # Nom du processus (généré si nécessaire)
        self.myProcessName = self.com.process_name
        self.setName("MainThread-" + self.myProcessName)  # Nom du thread

        # Note : Process ne s'enregistre plus au PyBus
        # Les messages sont maintenant gérés via la mailbox dans Com

        # État du processus
        self.alive = True                            # Contrôle de la boucle principale
        # Liste des threads de section critique actifs
        self.active_cs_threads = []

        # Partager l'état du processus avec Com (déjà créé plus haut)
        self.com.process_alive = lambda: self.alive

        # Démarrer le thread du processus
        self.start()

    # === TRAITEMENT DES MESSAGES VIA MAILBOX ===

    def process_mailbox_messages(self):
        """
        Traite les messages disponibles dans la mailbox.

        Cette méthode remplace les anciens handlers PyBus.
        Elle récupère les messages de la boîte aux lettres et les traite.
        """
        while self.com.has_messages() and self.alive:
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
                f"{self.name} processed generic message: {message.getPayload()} (clock: {old_clock} → {new_clock})")

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
            f"{self.name} received broadcast: {message.getPayload()} (local clock: {new_clock})")

    def _handle_directed_message(self, message):
        """Traite un message dirigé."""
        if message.getTo() == self.myId:
            old_clock, new_clock = self.com.update_clock_on_receive(
                message.getTimestamp())
            print(
                f"{self.name} received directed message: {message.getPayload()} (clock: {new_clock})")

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

    def exit_critical_section(self):
        """Sortie de la section critique via Com"""
        self.com.releaseSC()

    # === NOUVELLES MÉTHODES DU TP ===

    def synchronize(self):
        """Synchronisation avec tous les autres processus"""
        self.com.synchronize()

    def broadcast_sync(self, payload):
        """Broadcast synchrone - ce processus est l'émetteur"""
        self.com.broadcastSyncObject(payload, self.myId)

    def wait_broadcast_sync(self, from_process_id, payload):
        """Attendre un broadcast synchrone d'un processus spécifique"""
        self.com.broadcastSyncObject(payload, from_process_id)

    def send_to_sync(self, payload, destination_id):
        """Envoi synchrone à un processus"""
        self.com.sendToSyncObject(payload, destination_id)

    def receive_from_sync(self, from_process_id):
        """Réception synchrone depuis un processus"""
        return self.com.recevFromSyncObject(from_process_id)

    # Les handlers PyBus ont été remplacés par le traitement via mailbox

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
                f"{self.name} Loop: {loop} (clock {current_clock}) - State: {cs_status['state'].value} - {token_status} - {wants_status}")

            # Test des méthodes de communication synchrone avec barrière
            if loop == 2:
                print(f"🧪 {self.name} testing synchronous communication...")
                if self.myId == 0:  # P0 est l'émetteur
                    print(f"📢 {self.name} testing broadcast sync")
                    self.broadcast_sync("Test broadcast message")
                else:  # P1 et P2 participent au broadcast sync
                    print(f"👂 {self.name} participating in broadcast sync test")
                    # P1 et P2 attendent de recevoir le broadcast de P0
                    self.wait_broadcast_sync(0, "Test broadcast message")

            # Test de la section critique avec jeton : demander périodiquement
            # Décalage pour éviter les demandes simultanées
            if loop % 7 == self.myId and not cs_status['wants_cs']:
                print(f"🎯 {self.name} requesting critical section...")
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
                            f"{self.name} *** WORKING IN CRITICAL SECTION ***")
                        sleep(1.0)  # Travail en section critique
                        self.exit_critical_section()
                    except Exception as e:
                        print(
                            f"❌ {self.name} error in critical section: {e}")

                cs_thread = threading.Thread(
                    target=request_cs, name=f"CS-{self.name}")
                cs_thread.daemon = True  # Thread daemon s'arrête avec le programme principal
                cs_thread.start()
                self.active_cs_threads.append(cs_thread)

            sleep(0.8)
            loop += 1
        print(f"{self.name} stopped")

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
