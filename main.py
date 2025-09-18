"""
Fichier principal pour tester le système de communication distribué.
Démontre l'utilisation des différentes fonctionnalités : communication,
synchronisation, exclusion mutuelle et diffusion.
"""

import time
import threading
from typing import List
from Com import Com
from Process import Process


def test_basic_communication():
    """Test basique de communication entre processus."""
    print("\n=== TEST COMMUNICATION BASIQUE ===")

    # Configuration du système avec 3 processus
    Com.setTotalProcesses(3)

    # Création des processus
    processes = []
    for i in range(3):
        process = Process(f"P{i}")
        processes.append(process)
        time.sleep(0.1)  # Petit délai pour éviter les conflits

    # Test de communication
    time.sleep(1)

    # Arrêt des processus
    for process in processes:
        process.stop()

    print("Test de communication terminé\n")


def test_synchronization():
    """Test de synchronisation entre processus."""
    print("\n=== TEST SYNCHRONISATION ===")

    # Réinitialiser le système
    Com._all_processes.clear()
    Com._next_id = 0
    Com.setTotalProcesses(3)

    # Créer 3 processus qui vont se synchroniser
    coms = [Com() for _ in range(3)]

    def synchronized_task(com_instance, process_id):
        """Tâche qui se synchronise avec les autres."""
        print(f"P{process_id} avant synchronisation - {time.time():.2f}")
        time.sleep(process_id * 0.5)  # Délais différents pour chaque processus

        com_instance.synchronize()

        print(f"P{process_id} après synchronisation - {time.time():.2f}")

    # Lancer les tâches en parallèle
    threads = []
    for i, com in enumerate(coms):
        thread = threading.Thread(target=synchronized_task, args=(com, i))
        threads.append(thread)
        thread.start()

    # Attendre que tous les threads se terminent
    for thread in threads:
        thread.join()

    print("Test de synchronisation terminé\n")


def test_critical_section():
    """Test de section critique avec exclusion mutuelle."""
    print("\n=== TEST SECTION CRITIQUE ===")

    # Réinitialiser le système
    Com._all_processes.clear()
    Com._next_id = 0
    Com.setTotalProcesses(3)

    # Variable partagée simulée
    shared_resource = {"value": 0, "access_log": []}
    access_lock = threading.Lock()

    # Créer 3 processus
    coms = [Com() for _ in range(3)]

    def critical_section_task(com_instance, process_id):
        """Tâche qui accède à une ressource partagée."""
        for iteration in range(2):
            print(f"P{process_id} demande l'accès à la SC (itération {iteration})")

            # Demander l'accès à la section critique
            com_instance.requestSC()

            # Simulation d'accès à une ressource partagée
            print(f"P{process_id} entre en section critique")
            with access_lock:
                old_value = shared_resource["value"]
                time.sleep(0.1)  # Simulation de traitement
                shared_resource["value"] = old_value + 1
                shared_resource["access_log"].append(f"P{process_id}")
                print(
                    f"P{process_id} modifie la ressource: {old_value} -> {shared_resource['value']}")

            # Libérer la section critique
            com_instance.releaseSC()
            print(f"P{process_id} sort de la section critique")

            time.sleep(0.2)  # Pause entre les itérations

    # Lancer les tâches en parallèle
    threads = []
    for i, com in enumerate(coms):
        thread = threading.Thread(target=critical_section_task, args=(com, i))
        threads.append(thread)
        thread.start()

    # Attendre que tous les threads se terminent
    for thread in threads:
        thread.join()

    print(
        f"Valeur finale de la ressource partagée: {shared_resource['value']}")
    print(f"Ordre d'accès: {shared_resource['access_log']}")
    print("Test de section critique terminé\n")


def test_broadcast():
    """Test de diffusion de messages."""
    print("\n=== TEST BROADCAST ===")

    # Réinitialiser le système
    Com._all_processes.clear()
    Com._next_id = 0
    Com.setTotalProcesses(3)

    # Créer 3 processus
    coms = [Com() for _ in range(3)]

    def broadcast_receiver(com_instance, process_id):
        """Processus qui écoute les messages de diffusion."""
        print(f"P{process_id} écoute les messages...")

        for _ in range(2):  # Attendre 2 messages de broadcast
            message = com_instance.mailbox.waitForMessage(timeout=5.0)
            if message and message.getType().value == "broadcast":
                print(
                    f"P{process_id} reçoit broadcast de P{message.getSender()}: {message.getContent()}")

    def broadcast_sender(com_instance, process_id):
        """Processus qui envoie des messages de diffusion."""
        time.sleep(1)  # Attendre que les autres soient prêts à écouter

        message = f"Hello from P{process_id}!"
        print(f"P{process_id} diffuse: {message}")
        com_instance.broadcast(message)

    # Lancer les processus récepteurs
    threads = []
    for i in range(2):  # P0 et P1 écoutent
        thread = threading.Thread(target=broadcast_receiver, args=(coms[i], i))
        threads.append(thread)
        thread.start()

    # Lancer le processus diffuseur
    sender_thread = threading.Thread(
        target=broadcast_sender, args=(coms[2], 2))
    threads.append(sender_thread)
    sender_thread.start()

    # Attendre que tous les threads se terminent
    for thread in threads:
        thread.join(timeout=10)

    print("Test de broadcast terminé\n")


def main():
    """Fonction principale pour exécuter tous les tests."""
    print("=== SYSTÈME DE COMMUNICATION DISTRIBUÉ ===")
    print("Démarrage des tests...\n")

    try:
        # Exécuter les différents tests
        test_basic_communication()
        test_synchronization()
        test_critical_section()
        test_broadcast()

        print("=== TOUS LES TESTS TERMINÉS ===")

    except KeyboardInterrupt:
        print("\n\nInterruption par l'utilisateur")
    except Exception as e:
        print(f"\nErreur lors des tests: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
