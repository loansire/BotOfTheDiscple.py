import json
import os

from api.BungieAPI import BungieAPI
from enrichers.ActivityService import ActivityService
from enrichers.InteractableService import InteractableService

if __name__ == "__main__":
    # Paramètres de contrôle
    LIMIT = 1       # nombre maximum d'éléments à sauvegarder
    OFFSET = 28       # décalage à partir du début

    # 1. Charger les données depuis BungieAPI
    currentActivities = BungieAPI(lang="fr").get_character_profile()

    # Services
    activity_service = ActivityService(currentActivities)
    interactable_service = InteractableService(currentActivities)

    # Enrichissement
    enriched_activities = activity_service.enrich()
    enriched_interactables = interactable_service.enrich()

    # Appliquer offset et limit
    enriched_activities = enriched_activities[OFFSET:OFFSET + LIMIT]
    enriched_interactables = enriched_interactables[OFFSET:OFFSET + LIMIT]

    # Créer le dossier de sortie si nécessaire
    os.makedirs("data/temp", exist_ok=True)

    # Sauvegarde des résultats
    with open("data/temp/enriched_activities.json", "w", encoding="utf-8") as f:
        json.dump(enriched_activities, f, indent=2, ensure_ascii=False)

    with open("data/temp/enriched_interactables.json", "w", encoding="utf-8") as f:
        json.dump(enriched_interactables, f, indent=2, ensure_ascii=False)

    print(f"[OK] Données enrichies sauvegardées dans data/temp/ (limit={LIMIT}, offset={OFFSET})")