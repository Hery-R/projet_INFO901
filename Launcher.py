"""
Launcher.py - Point d'entrée principal du système distribué
Auteur: RASOAMIARAMANANA Hery ny aina

Ce module lance et coordonne l'exécution de plusieurs processus
dans un système distribué simulé avec horloges de Lamport.
"""

from time import sleep
from Process import Process
from Com import Com
from MessageDistributor import get_message_distributor, shutdown_message_distributor
from ProcessIDManager import reset_process_id_manager


def launch(nbProcess, runningTime=5):
    """
    Lance un système distribué avec plusieurs processus.

    Args:
        nbProcess (int): Nombre de processus à créer (ex: 3 pour P0, P1, P2)
        runningTime (int): Durée d'exécution en secondes
    """
    print(
        f"🚀 Lancement de {nbProcess} processus pour {runningTime} secondes...")

    # Reset de la numérotation pour garantir que ça commence à 0
    reset_process_id_manager()

    # Initialiser la synchronisation globale
    Com.initialize_sync(nbProcess)

    # Initialiser le distributeur de messages
    distributor = get_message_distributor()

    # Création et démarrage de tous les processus avec numérotation automatique
    processes = []
    for i in range(nbProcess):
        # Les processus reçoivent automatiquement leur numéro (0, 1, 2...)
        # Plus besoin de spécifier l'ID manuellement - numérotation automatique !
        # Numérotation automatique consécutive
        process = Process(npProcess=nbProcess)
        processes.append(process)
        print(
            f"✅ Processus {process.myProcessName} créé avec ID automatique: {process.myId}")

    print(f"⏱️  Simulation en cours pendant {runningTime} secondes...\n")

    # Attendre la durée spécifiée
    sleep(runningTime)

    print(f"\n🛑 Arrêt programmé après {runningTime} secondes")

    # Arrêter tous les processus
    for p in processes:
        p.stop()

    # Attendre que tous les threads se terminent proprement
    for p in processes:
        p.waitStopped()

    # Arrêter le distributeur de messages
    shutdown_message_distributor()

    print("✅ Tous les processus sont arrêtés")


if __name__ == '__main__':
    # Configuration par défaut : 3 processus pendant 5 secondes
    launch(nbProcess=3, runningTime=5)
