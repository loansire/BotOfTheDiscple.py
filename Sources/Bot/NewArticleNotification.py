import json
import os
from asyncio import tasks

from Sources.Bot.AlertMessageBuilder import publish_alerts
from Sources.Bot.BungieNewsRequest import get_latest_article_by_keyword


# Charger les alertes existantes
async def load_news_alerts():
    if os.path.exists('Ressources/AlertDatabase/News_Alert.json'):
        with open('Ressources/AlertDatabase/News_Alert.json', 'r') as file:
            return json.load(file)
    return {
        "UniqueIdentifier_twid": "",
        "UniqueIdentifier_destiny_2_update": ""
    }


# Sauvegarder les alertes mises à jour
async def save_news_alerts(news_alerts):
    with open('Ressources/AlertDatabase/news_alert.json', 'w') as file:
        json.dump(news_alerts, file, indent=4)


async def NewArticleTest():
    print("Début de la vérification récurrente.")
    try:
        # Récupérer les derniers articles TWID et Destiny 2 Update
        twid_item, _ = await get_latest_article_by_keyword('en', 'twid')
        update_item, _ = await get_latest_article_by_keyword('en', 'destiny_2_update')

        # Charger les données actuelles depuis le fichier JSON
        news_alerts = await load_news_alerts()

        # Vérifier et mettre à jour si nécessaire pour TWID
        if twid_item:
            latest_twid_id = twid_item.get('UniqueIdentifier', '')
            if latest_twid_id != news_alerts['UniqueIdentifier_twid']:
                print(f"Nouvel article TWID détecté : {latest_twid_id}")
                await publish_alerts('twid')
                print(f"Publié")
                news_alerts['UniqueIdentifier_twid'] = latest_twid_id

        # Vérifier et mettre à jour si nécessaire pour Destiny 2 Update
        if update_item:
            latest_update_id = update_item.get('UniqueIdentifier', '')
            if latest_update_id != news_alerts['UniqueIdentifier_destiny_2_update']:
                print(f"Nouvel article de mise à jour Destiny 2 détecté : {latest_update_id}")
                await publish_alerts('patch_note')
                print(f"Publié")
                news_alerts['UniqueIdentifier_destiny_2_update'] = latest_update_id

        # Sauvegarder les modifications dans le fichier JSON
        await save_news_alerts(news_alerts)
        print("Vérification récurrente terminée avec succès.")

    except Exception as e:
        print(f"Erreur lors de la vérification récurrente : {e}")