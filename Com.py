"""
Module Com pour la communication distribué entre processus.
Contient la classe Com qui gère toutes les communications, synchronisations
et l'exclusion mutuelle distribué.
"""

import threading
import time
from typing import Dict, List, Optional, Set
from Mailbox import Mailbox
from Message import Message, MessageType


class Com:
    """
    Classe principale de communication pour un système distribué.

    Cette classe gère:
    - La communication point-à-point et en diffusion
    - La synchronisation entre processus (barrières)
    - L'exclusion mutuelle distribuée (section critique)
    - La gestion des identifiants de processus

    Attributes:
        _nb_process (int): Nombre total de processus dans le système
        _my_id (int): Identifiant de ce processus
        _processes (Dict[int, Com]): Références vers tous les processus
        mailbox (Mailbox): Boîte aux lettres pour recevoir les messages
        _sync_barrier (threading.Barrier): Barrière de synchronisation
        _cs_lock (threading.Lock): Verrou pour la gestion de la section critique
        _cs_requests (List): Files d'attente des demandes de section critique
        _cs_replies (Set): Ensemble des réponses reçues pour la section critique
        _logical_clock (int): Horloge logique de Lamport
    """

    # Variables partagées entre toutes les instances
    _all_processes: Dict[int, 'Com'] = {}
    _total_processes = 0
    _next_id = 0
    _global_lock = threading.Lock()

    def __init__(self):
        """Initialise une nouvelle instance de communication."""
        with Com._global_lock:
            self._my_id = Com._next_id
            Com._next_id += 1
            Com._total_processes += 1
            Com._all_processes[self._my_id] = self

        self._nb_process = 0  # Sera mis à jour quand tous les processus sont créés
        self.mailbox = Mailbox()

        # Variables pour la synchronisation
        self._sync_counter = 0
        self._sync_lock = threading.Lock()
        self._sync_condition = threading.Condition(self._sync_lock)

        # Variables pour l'exclusion mutuelle (algorithme de Ricart-Agrawala)
        self._cs_requesting = False
        self._cs_in_critical_section = False
        self._cs_request_timestamp = 0
        self._cs_replies_received = set()
        self._cs_deferred_replies = []
        self._cs_lock = threading.Lock()
        self._cs_condition = threading.Condition(self._cs_lock)

        # Horloge logique de Lamport
        self._logical_clock = 0
        self._clock_lock = threading.Lock()

    @classmethod
    def setTotalProcesses(cls, total: int) -> None:
        """
        Définit le nombre total de processus dans le système.

        Args:
            total: Nombre total de processus
        """
        with cls._global_lock:
            cls._total_processes = total
            for process in cls._all_processes.values():
                process._nb_process = total

    def getNbProcess(self) -> int:
        """
        Retourne le nombre total de processus dans le système.

        Returns:
            Nombre de processus
        """
        return self._nb_process if self._nb_process > 0 else Com._total_processes

    def getMyId(self) -> int:
        """
        Retourne l'identifiant de ce processus.

        Returns:
            ID du processus
        """
        return self._my_id

    def _increment_clock(self) -> int:
        """Incrémente et retourne l'horloge logique."""
        with self._clock_lock:
            self._logical_clock += 1
            return self._logical_clock

    def _update_clock(self, received_timestamp: int) -> None:
        """Met à jour l'horloge logique avec un timestamp reçu."""
        with self._clock_lock:
            self._logical_clock = max(
                self._logical_clock, received_timestamp) + 1

    def sendTo(self, content: str, destination_id: int) -> bool:
        """
        Envoie un message asynchrone à un processus spécifique.

        Args:
            content: Contenu du message
            destination_id: ID du processus destinataire

        Returns:
            True si le message a été envoyé avec succès
        """
        if destination_id not in Com._all_processes:
            print(f"Erreur: Processus {destination_id} n'existe pas")
            return False

        timestamp = self._increment_clock()
        message = Message(
            sender=self._my_id,
            receiver=destination_id,
            content=content,
            message_type=MessageType.NORMAL
        )
        message.timestamp = timestamp

        target_process = Com._all_processes[destination_id]
        target_process.mailbox.putMessage(message)

        print(f"P{self._my_id} -> P{destination_id}: {content}")
        return True

    def sendToSync(self, content: str, destination_id: int) -> bool:
        """
        Envoie un message synchrone et attend une réponse.

        Args:
            content: Contenu du message
            destination_id: ID du processus destinataire

        Returns:
            True si le message a été envoyé et acquitté
        """
        if destination_id not in Com._all_processes:
            print(f"Erreur: Processus {destination_id} n'existe pas")
            return False

        timestamp = self._increment_clock()
        message = Message(
            sender=self._my_id,
            receiver=destination_id,
            content=content,
            message_type=MessageType.SYNC_REQUEST
        )
        message.timestamp = timestamp

        target_process = Com._all_processes[destination_id]
        target_process.mailbox.putMessage(message)

        print(f"P{self._my_id} -sync-> P{destination_id}: {content}")

        # Attendre la réponse de synchronisation
        while True:
            ack_msg = self.mailbox.waitForMessage(timeout=5.0)
            if ack_msg is None:
                print(f"Timeout: Pas de réponse de P{destination_id}")
                return False

            if (ack_msg.getSender() == destination_id and
                    ack_msg.getType() == MessageType.SYNC_ACK):
                self._update_clock(ack_msg.timestamp)
                print(f"P{self._my_id} <-sync-ack- P{destination_id}")
                return True
            else:
                # Remettre le message dans la mailbox s'il ne s'agit pas de l'ACK attendu
                self.mailbox.putMessage(ack_msg)

    def recevFromSync(self, expected_sender: int) -> Optional[Message]:
        """
        Reçoit un message synchrone et envoie automatiquement un acquittement.

        Args:
            expected_sender: ID de l'expéditeur attendu

        Returns:
            Le message reçu ou None si timeout
        """
        while True:
            message = self.mailbox.waitForMessage(timeout=10.0)
            if message is None:
                print(f"Timeout: Aucun message reçu de P{expected_sender}")
                return None

            if (message.getSender() == expected_sender and
                    message.getType() == MessageType.SYNC_REQUEST):

                self._update_clock(message.timestamp)

                # Envoyer l'acquittement
                ack_timestamp = self._increment_clock()
                ack_message = Message(
                    sender=self._my_id,
                    receiver=expected_sender,
                    content="ACK",
                    message_type=MessageType.SYNC_ACK
                )
                ack_message.timestamp = ack_timestamp

                sender_process = Com._all_processes[expected_sender]
                sender_process.mailbox.putMessage(ack_message)

                print(
                    f"P{self._my_id} <-sync- P{expected_sender}: {message.getContent()}")
                return message
            else:
                # Remettre le message dans la mailbox s'il ne vient pas du bon expéditeur
                self.mailbox.putMessage(message)

    def broadcast(self, content: str) -> None:
        """
        Diffuse un message à tous les autres processus.

        Args:
            content: Contenu du message à diffuser
        """
        timestamp = self._increment_clock()

        for process_id in Com._all_processes:
            if process_id != self._my_id:
                message = Message(
                    sender=self._my_id,
                    receiver=process_id,
                    content=content,
                    message_type=MessageType.BROADCAST
                )
                message.timestamp = timestamp

                target_process = Com._all_processes[process_id]
                target_process.mailbox.putMessage(message)

        print(f"P{self._my_id} broadcast: {content}")

    def synchronize(self) -> None:
        """
        Synchronise ce processus avec tous les autres (barrière de synchronisation).
        Implémentation simple par comptage.
        """
        expected_processes = self.getNbProcess()

        # Envoyer un signal de synchronisation à tous les autres processus
        for process_id in Com._all_processes:
            if process_id != self._my_id:
                sync_msg = Message(
                    sender=self._my_id,
                    receiver=process_id,
                    content="SYNC_BARRIER",
                    message_type=MessageType.BARRIER
                )
                sync_msg.timestamp = self._increment_clock()
                Com._all_processes[process_id].mailbox.putMessage(sync_msg)

        # Attendre les signaux de synchronisation de tous les autres processus
        received_sync_signals = set()
        received_sync_signals.add(self._my_id)  # On se compte nous-même

        while len(received_sync_signals) < expected_processes:
            message = self.mailbox.waitForMessage(timeout=10.0)
            if message is None:
                print(
                    f"Timeout lors de la synchronisation pour P{self._my_id}")
                break

            if message.getType() == MessageType.BARRIER:
                received_sync_signals.add(message.getSender())
                self._update_clock(message.timestamp)
            else:
                # Remettre les messages non-sync dans la mailbox
                self.mailbox.putMessage(message)

        print(
            f"P{self._my_id} synchronisé avec {len(received_sync_signals)} processus")

    def requestSC(self) -> None:
        """
        Demande l'accès à la section critique (algorithme de Ricart-Agrawala).
        """
        with self._cs_lock:
            if self._cs_requesting or self._cs_in_critical_section:
                return  # Déjà en cours de demande ou dans la SC

            self._cs_requesting = True
            self._cs_request_timestamp = self._increment_clock()
            self._cs_replies_received.clear()

        # Envoyer des demandes à tous les autres processus
        for process_id in Com._all_processes:
            if process_id != self._my_id:
                request_msg = Message(
                    sender=self._my_id,
                    receiver=process_id,
                    content=f"CS_REQUEST:{self._cs_request_timestamp}",
                    message_type=MessageType.CS_REQUEST
                )
                request_msg.timestamp = self._cs_request_timestamp
                Com._all_processes[process_id].mailbox.putMessage(request_msg)

        # Attendre les réponses de tous les autres processus
        expected_replies = self.getNbProcess() - 1

        while len(self._cs_replies_received) < expected_replies:
            message = self.mailbox.waitForMessage(timeout=10.0)
            if message is None:
                print(f"Timeout lors de la demande SC pour P{self._my_id}")
                break

            if message.getType() == MessageType.CS_REPLY:
                with self._cs_lock:
                    self._cs_replies_received.add(message.getSender())
                    self._update_clock(message.timestamp)
            elif message.getType() == MessageType.CS_REQUEST:
                # Traiter les demandes concurrentes
                self._handle_cs_request(message)
            else:
                # Remettre les autres messages dans la mailbox
                self.mailbox.putMessage(message)

        with self._cs_lock:
            self._cs_requesting = False
            self._cs_in_critical_section = True

        print(f"P{self._my_id} entre en section critique")

    def releaseSC(self) -> None:
        """
        Libère la section critique.
        """
        with self._cs_lock:
            if not self._cs_in_critical_section:
                return

            self._cs_in_critical_section = False

            # Envoyer les réponses différées
            for deferred_sender in self._cs_deferred_replies:
                reply_msg = Message(
                    sender=self._my_id,
                    receiver=deferred_sender,
                    content="CS_REPLY",
                    message_type=MessageType.CS_REPLY
                )
                reply_msg.timestamp = self._increment_clock()
                Com._all_processes[deferred_sender].mailbox.putMessage(
                    reply_msg)

            self._cs_deferred_replies.clear()

        print(f"P{self._my_id} sort de la section critique")

    def _handle_cs_request(self, request_msg: Message) -> None:
        """
        Traite une demande de section critique reçue.

        Args:
            request_msg: Message de demande de section critique
        """
        sender_id = request_msg.getSender()
        request_timestamp = request_msg.timestamp

        with self._cs_lock:
            # Si on n'est pas intéressé par la SC, on répond immédiatement
            if not self._cs_requesting and not self._cs_in_critical_section:
                reply_msg = Message(
                    sender=self._my_id,
                    receiver=sender_id,
                    content="CS_REPLY",
                    message_type=MessageType.CS_REPLY
                )
                reply_msg.timestamp = self._increment_clock()
                Com._all_processes[sender_id].mailbox.putMessage(reply_msg)

            # Si on est en SC, on diffère la réponse
            elif self._cs_in_critical_section:
                self._cs_deferred_replies.append(sender_id)

            # Si on demande aussi la SC, on compare les timestamps
            elif self._cs_requesting:
                # Priorité basée sur le timestamp, puis sur l'ID en cas d'égalité
                if (request_timestamp < self._cs_request_timestamp or
                        (request_timestamp == self._cs_request_timestamp and sender_id < self._my_id)):
                    # L'autre processus a la priorité
                    reply_msg = Message(
                        sender=self._my_id,
                        receiver=sender_id,
                        content="CS_REPLY",
                        message_type=MessageType.CS_REPLY
                    )
                    reply_msg.timestamp = self._increment_clock()
                    Com._all_processes[sender_id].mailbox.putMessage(reply_msg)
                else:
                    # On a la priorité, on diffère la réponse
                    self._cs_deferred_replies.append(sender_id)
