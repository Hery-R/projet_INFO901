"""
Launcher.py - Point d'entrée principal du système distribué
Auteur: RASOAMIARAMANANA Hery ny aina

Ce module lance et coordonne l'exécution de plusieurs processus
dans un système distribué simulé avec horloges de Lamport.
"""

from time import sleep
from Process import Process

def launch(nbProcess, runningTime=5):
    """
    Lance un système distribué avec plusieurs processus.
    
    Args:
        nbProcess (int): Nombre de processus à créer (ex: 3 pour P0, P1, P2)
        runningTime (int): Durée d'exécution en secondes
    """
    print(f"🚀 Lancement de {nbProcess} processus pour {runningTime} secondes...")
    
    # Création et démarrage de tous les processus
    processes = []
    for i in range(nbProcess):
        process_name = "P" + str(i)
        processes.append(Process(process_name, nbProcess))
        print(f"✅ Processus {process_name} créé (ID: {i})")
    
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
    
    print("✅ Tous les processus sont arrêtés")

if __name__ == '__main__':
    # Configuration par défaut : 3 processus pendant 5 secondes
    launch(nbProcess=3, runningTime=5)
