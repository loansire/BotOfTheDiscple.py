from Sources.Bot.CurrentActivity.BungieRequest import get_bungie_character_data
from Sources.Bot.CurrentActivity.JsonFilter import get_only_challenges_activities

if __name__ == "__main__":
    print("Starting request for Weekly activities ...")
    # Récupère la liste des activités selectionnables en jeu
    MainJson = get_bungie_character_data()

    # Récupère uniquement les activitées posédant un challenge + clean le résultat
    MainJson = get_only_challenges_activities(MainJson)

    # Traduit les hash et les artibuts du json en données lisible
    MainJson = translate_to_readable_data(MainJson)

    # Afficher les données filtrées
    print(MainJson)