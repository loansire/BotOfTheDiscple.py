from Sources.Bot.CurrentActivity.CharacterActivityRequest import get_bungie_character_data

if __name__ == "__main__":
    # Récupère la liste des activités selectionnables en jeu
    MainJson = get_bungie_character_data()

    #récupère uniquement les activitées posédant un challenge + clean le résultat
    MainJson = get_only_challenges_activities(MainJson)

    # Afficher les données filtrées
    print(MainJson)