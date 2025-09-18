from threading import Thread
from time import sleep
from typing import Optional
from Com import Com
from Message import Message


class Process(Thread):
    """
    Classe représentant un processus dans le système distribué.

    Cette classe hérite de Thread et implémente la logique de communication
    et de synchronisation entre processus distribués.

    Attributes:
        com (Com): Instance de communication pour ce processus
        alive (bool): Indicateur si le processus est actif
        myId (int): Identifiant unique de ce processus
        nbProcess (int): Nombre total de processus dans le système
    """

    def __init__(self, name: str):
        """
        Initialise un nouveau processus.

        Args:
            name: Nom du processus (ex: "P0", "P1", etc.)
        """
        Thread.__init__(self)

        self.com = Com()
        self.nbProcess = self.com.getNbProcess()
        self.myId = self.com.getMyId()
        self.setName(name)

        self.alive = True
        print(f"Processus {name} créé avec ID {self.myId}")
        self.start()

    def run(self):
        """
        Méthode principale du processus (version corrigée de l'exemple).

        Implémente le scénario de communication et synchronisation
        entre trois processus (P0, P1, P2).
        """
        loop = 0

        try:
            while self.alive and loop < 3:  # Limiter le nombre de boucles pour les tests
                print(f"{self.name} Loop: {loop}")
                sleep(0.5)

                if self.name == "P0":
                    self._process_p0_logic()
                elif self.name == "P1":
                    self._process_p1_logic()
                elif self.name == "P2":
                    self._process_p2_logic()

                loop += 1
                sleep(1)  # Pause entre les boucles

        except Exception as e:
            print(f"Erreur dans {self.name}: {e}")
        finally:
            print(f"{self.name} stopped")

    def _process_p0_logic(self):
        """Logique spécifique au processus P0."""
        try:
            # P0 envoie un message asynchrone à P1
            self.com.sendTo("j'appelle 2 et je te recontacte après", 1)

            # P0 envoie un message synchrone à P2
            success = self.com.sendToSync(
                "J'ai laissé un message à 2, je le rappellerai après, on se synchronise tous et on attaque la partie ?",
                2
            )

            if success:
                # P0 reçoit la réponse synchrone de P2
                response = self.com.recevFromSync(2)
                if response:
                    print(f"P0 reçoit de P2: {response.getContent()}")

                # P0 informe P1 que P2 est d'accord
                self.com.sendToSync(
                    "2 est OK pour jouer, on se synchronise et c'est parti!", 1)

                # Synchronisation avec tous les processus
                print("P0 se synchronise...")
                self.com.synchronize()

                # Test de section critique
                self._test_critical_section("P0")

        except Exception as e:
            print(f"Erreur dans la logique P0: {e}")

    def _process_p1_logic(self):
        """Logique spécifique au processus P1."""
        try:
            # P1 vérifie s'il a des messages
            if not self.com.mailbox.isEmpty():
                message = self.com.mailbox.getMessage()
                if message:
                    print(
                        f"P1 reçoit: {message.getContent()} de P{message.getSender()}")

                # P1 attend le message synchrone de P0
                sync_msg = self.com.recevFromSync(0)
                if sync_msg:
                    print(
                        f"P1 reçoit message sync de P0: {sync_msg.getContent()}")

                # Synchronisation avec tous les processus
                print("P1 se synchronise...")
                self.com.synchronize()

                # Test de section critique
                self._test_critical_section("P1")

        except Exception as e:
            print(f"Erreur dans la logique P1: {e}")

    def _process_p2_logic(self):
        """Logique spécifique au processus P2."""
        try:
            # P2 attend le message synchrone de P0
            sync_msg = self.com.recevFromSync(0)
            if sync_msg:
                print(f"P2 reçoit message sync de P0: {sync_msg.getContent()}")

                # P2 répond à P0
                self.com.sendToSync("OK, je suis prêt pour jouer!", 0)

            # Synchronisation avec tous les processus
            print("P2 se synchronise...")
            self.com.synchronize()

            # Test de section critique
            self._test_critical_section("P2")

        except Exception as e:
            print(f"Erreur dans la logique P2: {e}")

    def _test_critical_section(self, process_name: str):
        """
        Test de la section critique pour ce processus.

        Args:
            process_name: Nom du processus pour les messages
        """
        try:
            print(f"{process_name} demande l'accès à la section critique")
            self.com.requestSC()

            # Vérifier si on a gagné (boîte aux lettres vide = premier à entrer)
            if self.com.mailbox.isEmpty():
                print(
                    f"{process_name} Catched ! J'ai eu la section critique en premier !")
                self.com.broadcast(f"{process_name} a gagné !!!")
            else:
                # Vérifier s'il y a des messages de victoire
                message = self.com.mailbox.getMsg()
                if message:
                    print(
                        f"{process_name}: P{message.getSender()} a eu le jeton en premier")

            # Simuler du travail en section critique
            sleep(0.5)

            self.com.releaseSC()
            print(f"{process_name} libère la section critique")

        except Exception as e:
            print(f"Erreur dans la section critique de {process_name}: {e}")

    def stop(self):
        """Arrête proprement le processus."""
        print(f"Arrêt de {self.name}...")
        self.alive = False

        # Attendre que le thread se termine
        if self.is_alive():
            self.join(timeout=2.0)

        print(f"{self.name} arrêté")

    def get_process_info(self) -> dict:
        """
        Retourne les informations sur ce processus.

        Returns:
            Dictionnaire contenant les informations du processus
        """
        return {
            "name": self.name,
            "id": self.myId,
            "alive": self.alive,
            "nb_processes": self.nbProcess,
            "mailbox_size": len(self.com.mailbox)
        }


# Fonction utilitaire pour créer et gérer plusieurs processus
def create_processes(num_processes: int = 3) -> list[Process]:
    """
    Crée et démarre plusieurs processus.

    Args:
        num_processes: Nombre de processus à créer (défaut: 3)

    Returns:
        Liste des processus créés
    """
    # Configurer le système avec le nombre total de processus
    Com.setTotalProcesses(num_processes)

    processes = []
    for i in range(num_processes):
        process_name = f"P{i}"
        process = Process(process_name)
        processes.append(process)
        sleep(0.1)  # Petit délai pour éviter les conflits

    return processes


def stop_all_processes(processes: list[Process]):
    """
    Arrête tous les processus de manière propre.

    Args:
        processes: Liste des processus à arrêter
    """
    print("Arrêt de tous les processus...")

    for process in processes:
        process.stop()

    print("Tous les processus ont été arrêtés")


if __name__ == "__main__":
    """Test rapide du module Process."""
    print("=== Test du module Process ===")

    try:
        # Créer 3 processus
        processes = create_processes(3)

        # Laisser les processus s'exécuter
        sleep(10)

        # Afficher les informations des processus
        for process in processes:
            info = process.get_process_info()
            print(
                f"Processus {info['name']}: ID={info['id']}, Alive={info['alive']}")

        # Arrêter tous les processus
        stop_all_processes(processes)

    except KeyboardInterrupt:
        print("\nInterruption par l'utilisateur")
        if 'processes' in locals():
            stop_all_processes(processes)
    except Exception as e:
        print(f"Erreur: {e}")
        if 'processes' in locals():
            stop_all_processes(processes)
