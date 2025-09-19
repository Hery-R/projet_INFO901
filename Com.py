"""
Com.py - Classe middleware pour la communication dans le système distribué
Auteur: RASOAMIARAMANANA Hery ny aina
Auteur: ROUSSEAU Maxime

Cette classe centralise toute la logique de communication qui était
précédemment dans Process.py, pour une meilleure séparation des responsabilités.
"""

from threading import Lock, Condition
from pyeventbus3.pyeventbus3 import *
from BroadcastMessage import BroadcastMessage
from MessageTo import MessageTo
from CriticalSectionMessage import TokenMessage
from CriticalSectionState import CriticalSectionState
from Mailbox import Mailbox
from MessageDistributor import get_message_distributor
from ProcessIDManager import get_process_id_manager


class Com:
    """
    Middleware de communication pour système distribué.

    Responsabilités :
    - Gestion de l'horloge logique de Lamport avec protection thread-safe
    - Services de communication (broadcast, messages dirigés)
    - Gestion des sections critiques distribuées
    - Synchronisation globale
    """

    def __init__(self, process_name=None, total_processes=None):
        """
        Initialise le middleware de communication avec numérotation automatique.

        Le processus reçoit automatiquement un numéro unique consécutif
        selon les spécifications du TP (numérotation commençant à 0).

        Args:
            process_name (str, optional): Nom du processus. Si None, généré automatiquement
            total_processes (int, optional): Nombre total de processus. Si None, déterminé dynamiquement
        """
        # === NUMÉROTATION AUTOMATIQUE CONSÉCUTIVE ===
        id_manager = get_process_id_manager()
        # Attribution automatique d'ID unique
        self.process_id = id_manager.get_next_id()

        # Configuration de base
        if process_name is None:
            # Génération automatique du nom
            self.process_name = f"P{self.process_id}"
        else:
            self.process_name = process_name

        # Peut être None si déterminé dynamiquement
        self.total_processes = total_processes
        self.process_alive = True  # Référence à l'état du processus

        # Horloge logique de Lamport avec protection thread-safe
        self.lamport_clock = 0
        self.lock = Lock()

        # === BOÎTE AUX LETTRES ===
        self.mailbox = Mailbox(self.process_id, self.process_name)

        # Enregistrer la mailbox au distributeur
        distributor = get_message_distributor()
        distributor.register_mailbox(self.process_id, self.mailbox)

        # === GESTION DE LA SECTION CRITIQUE ===
        self.cs_condition = Condition(self.lock)  # Pour bloquer requestSC()

        # === GESTION DE LA SECTION CRITIQUE ===
        # État initial : tous les processus sont au repos sauf P0
        self.cs_state = CriticalSectionState.IDLE
        self.has_token = (self.process_id == 0)  # P0 commence avec le jeton
        self.wants_cs = False               # Pas de demande de SC au début

        # Si ce processus a le jeton au démarrage, changer son état
        if self.has_token:
            self.cs_state = CriticalSectionState.HAS_TOKEN
            print(f"🎯 {self.process_name} starts WITH the token")

        # Note : Com ne s'enregistre PAS au bus d'événements
        # Seuls les Process doivent s'y enregistrer pour recevoir les messages

        print(
            f"🔧 Com middleware initialized for {self.process_name} (ID: {self.process_id})")

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
            self.lamport_clock = max(
                self.lamport_clock, received_timestamp) + 1
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

    # === MÉTHODES D'ACCÈS À LA BOÎTE AUX LETTRES ===

    def has_messages(self):
        """Vérifie si des messages sont en attente dans la boîte aux lettres."""
        return self.mailbox.has_messages()

    def get_message(self):
        """Récupère le prochain message de la boîte aux lettres (non-bloquant)."""
        return self.mailbox.get_message()

    def wait_for_message(self, timeout=None):
        """Attend l'arrivée d'un message (bloquant)."""
        return self.mailbox.wait_for_message(timeout)

    def get_message_count(self):
        """Retourne le nombre de messages en attente."""
        return self.mailbox.get_message_count()

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
        print(
            f"📢 {self.process_name} broadcast: {payload} with timestamp {current_clock}")
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
        print(
            f"{self.process_name} sendTo P{destination_id}: {payload} with timestamp {current_clock}")
        PyBus.Instance().post(msg)

    # === MÉTHODES DE SECTION CRITIQUE ===

    def requestSC(self):
        """
        Demande d'accès à la section critique (BLOQUANT).

        Cette méthode bloque jusqu'à ce que le processus obtienne
        effectivement l'accès à la section critique.
        """
        with self.cs_condition:
            self.wants_cs = True
            print(f"🙋 {self.process_name} wants to enter critical section")

            # Attendre jusqu'à pouvoir entrer en section critique
            while not (self.has_token and self.wants_cs and self.cs_state == CriticalSectionState.HAS_TOKEN) and self.process_alive():
                print(
                    f"⏳ {self.process_name} waiting for critical section access...")
                self.cs_condition.wait()  # Attendre le réveil

            # Si le processus n'est plus actif, abandonner
            if not self.process_alive():
                print(
                    f"🛑 {self.process_name} abandoning critical section request (process stopping)")
                self.wants_cs = False
                return False

            # Entrer en section critique
            self.cs_state = CriticalSectionState.IN_CS
            print(f"🔒 {self.process_name} ENTERS critical section")
            return True

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

    def _get_total_processes(self):
        """
        Obtient le nombre total de processus de manière dynamique.

        Returns:
            int: Nombre total de processus actuellement enregistrés
        """
        if self.total_processes is not None:
            return self.total_processes
        else:
            # Mode dynamique : obtenir depuis le gestionnaire d'IDs
            id_manager = get_process_id_manager()
            return id_manager.get_assigned_count()

    def _pass_token(self):
        """Passer le jeton au processus suivant dans l'anneau"""
        total_procs = self._get_total_processes()
        next_process_id = (self.process_id + 1) % total_procs

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

        with self.cs_condition:
            self.has_token = True
            self.cs_state = CriticalSectionState.HAS_TOKEN

            print(f"{self.process_name} received TOKEN from P{from_process_id}")

            # Notifier les threads en attente de la section critique
            self.cs_condition.notify_all()

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

    # === MÉTHODES DE SYNCHRONISATION ===

    # Variables globales pour la synchronisation
    _sync_counter = 0
    _sync_condition = Condition()
    _sync_total_processes = 0

    @classmethod
    def initialize_sync(cls, total_processes):
        """Initialise la synchronisation globale pour tous les processus."""
        with cls._sync_condition:
            cls._sync_total_processes = total_processes
            cls._sync_counter = 0

    def synchronize(self):
        """
        Barrière de synchronisation - attend que tous les processus l'invoquent.

        Cette méthode bloque jusqu'à ce que tous les processus du système
        aient appelé synchronize().
        """
        with Com._sync_condition:
            Com._sync_counter += 1
            print(
                f"🔄 {self.process_name} reached synchronization barrier ({Com._sync_counter}/{Com._sync_total_processes})")

            if Com._sync_counter >= Com._sync_total_processes:
                # Tous les processus sont arrivés, les débloquer tous
                print(f"✅ All processes synchronized! Releasing barrier...")
                Com._sync_counter = 0  # Reset pour la prochaine synchronisation
                Com._sync_condition.notify_all()
            else:
                # Attendre que les autres arrivent
                print(f"⏳ {self.process_name} waiting for other processes...")
                Com._sync_condition.wait()

    # === MÉTHODES DE COMMUNICATION SYNCHRONE ===

    def broadcastSyncObject(self, payload, from_process_id):
        """
        Broadcast synchrone avec barrière de synchronisation.

        - Si ce processus est l'émetteur (from_process_id), il envoie le broadcast puis synchronise
        - Sinon, il attend de recevoir le message puis synchronise

        Args:
            payload (str): Contenu à diffuser
            from_process_id (int): ID du processus émetteur
        """
        if self.process_id == from_process_id:
            # Ce processus est l'émetteur
            print(f"📢🔒 {self.process_name} starting synchronous broadcast")

            # Envoyer le broadcast asynchrone
            self.broadcast(payload)
            print(f"📢 {self.process_name} broadcast sent")

            # Synchroniser tous les processus
            self.synchronize()
            print(f"✅ {self.process_name} broadcast completed and synchronized!")
        else:
            # Ce processus doit recevoir
            print(
                f"👂 {self.process_name} waiting for broadcast from P{from_process_id}")

            # Attendre le message dans la mailbox
            while True:
                message = self.wait_for_message(timeout=1.0)
                if message and payload in message.getPayload():
                    print(
                        f"✅ {self.process_name} received broadcast from P{from_process_id}")
                    break

            # Synchroniser avec tous les autres processus
            self.synchronize()
            print(f"✅ {self.process_name} broadcast received and synchronized!")

    def sendToSyncObject(self, payload, destination_id):
        """
        Envoi synchrone avec barrière de synchronisation.

        Args:
            payload (str): Message à envoyer
            destination_id (int): ID du processus destinataire
        """
        print(f"📤🔒 {self.process_name} sending synchronously to P{destination_id}")

        # Envoyer le message asynchrone
        self.sendTo(payload, destination_id)
        print(f"📤 {self.process_name} message sent to P{destination_id}")

        # Synchroniser tous les processus
        self.synchronize()
        print(f"✅ {self.process_name} send completed and synchronized!")

    def recevFromSyncObject(self, from_process_id):
        """
        Réception synchrone avec barrière de synchronisation.

        Args:
            from_process_id (int): ID du processus émetteur attendu

        Returns:
            str: Le payload du message reçu
        """
        print(f"👂🔒 {self.process_name} waiting for message from P{from_process_id}")

        # Attendre spécifiquement un message de from_process_id
        while True:
            message = self.wait_for_message(timeout=1.0)
            if message:
                # Vérifier si le message vient du bon processus
                if hasattr(message, 'getFrom') and message.getFrom() == from_process_id:
                    payload = message.getPayload()
                    print(
                        f"✅ {self.process_name} received message from P{from_process_id}: {payload}")

                    # Synchroniser tous les processus
                    self.synchronize()
                    print(
                        f"✅ {self.process_name} message received and synchronized!")

                    return payload
                else:
                    # Pas le bon message, le remettre dans la mailbox
                    self.mailbox.deposit_message(message)
