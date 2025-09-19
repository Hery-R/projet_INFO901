"""
MessageDistributor.py - Distributeur central de messages
Auteur: RASOAMIARAMANANA Hery ny aina

Cette classe s'enregistre au bus PyBus et distribue automatiquement
les messages vers les bonnes boîtes aux lettres selon leur destination.
"""

import threading
from pyeventbus3.pyeventbus3 import *
from LamportMessage import LamportMessage
from BroadcastMessage import BroadcastMessage
from MessageTo import MessageTo
from CriticalSectionMessage import TokenMessage


class MessageDistributor:
    """
    Distributeur central qui route les messages vers les mailboxes appropriées.

    Cette classe fait le lien entre le bus PyBus global et les boîtes aux lettres
    individuelles des processus, conformément aux spécifications du TP.
    """

    def __init__(self):
        """Initialise le distributeur de messages."""
        self.mailboxes = {}  # {process_id: mailbox}
        self.lock = threading.Lock()

        # S'enregistrer au bus pour tous les types de messages
        PyBus.Instance().register(self, self)
        print("📡 MessageDistributor initialized and registered to PyBus")

    def register_mailbox(self, process_id, mailbox):
        """
        Enregistre une boîte aux lettres pour un processus.

        Args:
            process_id (int): ID du processus
            mailbox (Mailbox): Boîte aux lettres du processus
        """
        with self.lock:
            self.mailboxes[process_id] = mailbox
            print(f"📡➡️ Mailbox registered for process P{process_id}")

    def unregister_mailbox(self, process_id):
        """
        Désenregistre une boîte aux lettres.

        Args:
            process_id (int): ID du processus
        """
        with self.lock:
            if process_id in self.mailboxes:
                del self.mailboxes[process_id]
                print(f"📡❌ Mailbox unregistered for process P{process_id}")

    @subscribe(threadMode=Mode.PARALLEL, onEvent=BroadcastMessage)
    def distribute_broadcast(self, event):
        """
        Distribue un message de diffusion à toutes les mailboxes.

        Args:
            event (BroadcastMessage): Message de diffusion à distribuer
        """
        with self.lock:
            mailboxes_copy = dict(self.mailboxes)

        print(
            f"📡📢 Distributing broadcast to {len(mailboxes_copy)} mailboxes: {event.getPayload()[:50]}...")

        for process_id, mailbox in mailboxes_copy.items():
            mailbox.deposit_message(event)

    @subscribe(threadMode=Mode.PARALLEL, onEvent=MessageTo)
    def distribute_directed_message(self, event):
        """
        Distribue un message dirigé vers la mailbox appropriée.

        Args:
            event (MessageTo): Message dirigé à distribuer
        """
        destination_id = event.getTo()

        with self.lock:
            if destination_id in self.mailboxes:
                mailbox = self.mailboxes[destination_id]
                mailbox.deposit_message(event)
                print(
                    f"📡➡️ Directed message delivered to P{destination_id}: {event.getPayload()[:50]}...")
            else:
                print(
                    f"📡❌ No mailbox found for P{destination_id}, message lost: {event.getPayload()[:50]}...")

    @subscribe(threadMode=Mode.PARALLEL, onEvent=TokenMessage)
    def distribute_token_message(self, event):
        """
        Distribue un message de jeton vers le processus destinataire.

        Args:
            event (TokenMessage): Message de jeton à distribuer
        """
        destination_id = event.getToProcessId()

        with self.lock:
            if destination_id in self.mailboxes:
                mailbox = self.mailboxes[destination_id]
                mailbox.deposit_message(event)
                print(f"📡🎯 Token delivered to P{destination_id}")
            else:
                print(
                    f"📡❌ No mailbox found for token recipient P{destination_id}")

    def get_registered_processes(self):
        """
        Retourne la liste des processus enregistrés.

        Returns:
            list: Liste des IDs de processus enregistrés
        """
        with self.lock:
            return list(self.mailboxes.keys())

    def shutdown(self):
        """Arrêt propre du distributeur."""
        try:
            PyBus.Instance().unregister(self, self)
            print("📡🛑 MessageDistributor unregistered from PyBus")
        except AttributeError:
            # PyBus n'a pas de méthode unregister dans cette version
            print("📡🛑 MessageDistributor shutdown (unregister not available)")
        except Exception as e:
            print(f"📡⚠️ MessageDistributor shutdown error: {e}")


# Instance globale singleton du distributeur
_message_distributor = None
_distributor_lock = threading.Lock()


def get_message_distributor():
    """
    Retourne l'instance singleton du distributeur de messages.

    Returns:
        MessageDistributor: Instance du distributeur
    """
    global _message_distributor
    if _message_distributor is None:
        with _distributor_lock:
            if _message_distributor is None:
                _message_distributor = MessageDistributor()
    return _message_distributor


def shutdown_message_distributor():
    """Arrêt du distributeur singleton."""
    global _message_distributor
    if _message_distributor is not None:
        _message_distributor.shutdown()
        _message_distributor = None
