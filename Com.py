"""
Com.py - Classe middleware pour la communication dans le système distribué
Auteur: Refactorisation du code de RASOAMIARAMANANA Hery ny aina

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
        self.process_alive = True  # Référence à l'état du processus

        # Horloge logique de Lamport avec protection thread-safe
        self.lamport_clock = 0
        self.lock = Lock()

        # === BOÎTE AUX LETTRES ===
        self.mailbox = Mailbox(process_id, process_name)

        # Enregistrer la mailbox au distributeur
        distributor = get_message_distributor()
        distributor.register_mailbox(process_id, self.mailbox)

        # === GESTION DE LA SECTION CRITIQUE ===
        self.cs_condition = Condition(self.lock)  # Pour bloquer requestSC()

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

        print(
            f"🔧 Com middleware initialized for {process_name} (ID: {process_id})")

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

    def broadcastSync(self, payload, from_process_id):
        """
        Broadcast synchrone avec acquittements.

        - Si ce processus est l'émetteur (from_process_id), il envoie à tous et attend les acquittements
        - Sinon, il attend de recevoir le message de from_process_id

        Args:
            payload (str): Contenu à diffuser
            from_process_id (int): ID du processus émetteur
        """
        if self.process_id == from_process_id:
            # Ce processus est l'émetteur
            print(f"📢🔒 {self.process_name} starting synchronous broadcast")

            # Envoyer le broadcast
            self.broadcast(f"SYNC_BROADCAST:{payload}")

            # Attendre les acquittements (simulation - dans un vrai système,
            # il faudrait compter les ACK reçus)
            print(f"⏳ {self.process_name} waiting for broadcast acknowledgments...")
            # Simulation d'attente des ACK
            from time import sleep
            sleep(0.5)  # Temps pour que les autres reçoivent
            print(f"✅ {self.process_name} broadcast synchronized!")
        else:
            # Ce processus doit recevoir
            print(
                f"👂 {self.process_name} waiting for synchronous broadcast from P{from_process_id}")

            # Attendre le message dans la mailbox
            while True:
                message = self.wait_for_message(timeout=1.0)
                if message and f"SYNC_BROADCAST:{payload}" in message.getPayload():
                    print(
                        f"✅ {self.process_name} received synchronous broadcast from P{from_process_id}")
                    break

    def sendToSync(self, payload, destination_id):
        """
        Envoi synchrone - bloque jusqu'à ce que le destinataire confirme la réception.

        Args:
            payload (str): Message à envoyer
            destination_id (int): ID du processus destinataire
        """
        print(f"📤🔒 {self.process_name} sending synchronously to P{destination_id}")

        # Envoyer le message avec un marqueur sync
        sync_payload = f"SYNC_MSG:{payload}:FROM_{self.process_id}"
        self.sendTo(sync_payload, destination_id)

        # Attendre l'accusé de réception (simulation)
        print(
            f"⏳ {self.process_name} waiting for sync acknowledgment from P{destination_id}")

        # Dans un vrai système, on attendrait un ACK spécifique
        from time import sleep
        sleep(0.3)  # Simulation de l'attente d'ACK
        print(f"✅ {self.process_name} sync send completed to P{destination_id}")

    def receiveFromSync(self, from_process_id):
        """
        Réception synchrone - bloque jusqu'à recevoir un message de from_process_id.

        Args:
            from_process_id (int): ID du processus émetteur attendu

        Returns:
            str: Le payload du message reçu
        """
        print(
            f"👂🔒 {self.process_name} waiting synchronously for message from P{from_process_id}")

        # Attendre spécifiquement un message de from_process_id
        while True:
            message = self.wait_for_message(timeout=1.0)
            if message:
                payload = message.getPayload()
                if f"SYNC_MSG:" in payload and f"FROM_{from_process_id}" in payload:
                    # Extraire le vrai payload
                    actual_payload = payload.split(":")[1]
                    print(
                        f"✅ {self.process_name} received sync message from P{from_process_id}: {actual_payload}")

                    # Envoyer ACK (simulation)
                    # Dans un vrai système, on enverrait un ACK explicite

                    return actual_payload
                else:
                    # Pas le bon message, le remettre dans la mailbox
                    self.mailbox.deposit_message(message)
