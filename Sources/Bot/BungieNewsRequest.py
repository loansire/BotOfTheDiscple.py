from datetime import datetime
import re
import aiohttp
import json
import asyncio


api_key = '95d66cb52e4d443ea72e729779de4263'


async def extract_version_from_title(title):
    # Expression régulière pour extraire la version du titre
    match = re.search(r"Mise à jour (\d+\.\d+\.\d+\.\d+) de Destiny 2", title)
    if match:
        return match.group(1)
    return None


async def reformat_pubdate(item):
    try:
        # Récupérer la valeur de PubDate à partir de l'objet JSON
        pubdate = item.get('PubDate', '')

        # Parse the date from the given format
        dt = datetime.strptime(pubdate, "%Y-%m-%dT%H:%M:%SZ")

        # Format the date to the desired output format
        formatted_date = dt.strftime("%Y-%m-%d | %H:%M:%S")

        # Modifier directement l'objet JSON
        item['PubDate'] = formatted_date

    except ValueError:
        # Handle the case where the input format is incorrect
        print(f"Invalid date format: {pubdate}")


async def pretty_print_json(data):
    print(json.dumps(data, indent=4, ensure_ascii=False))

async def get_bungie_rss_articles(language, page_token='0'):
    url = f"https://www.bungie.net/Platform/Content/Rss/NewsArticles/{page_token}/"

    headers = {
        "X-API-Key": api_key
    }

    params = {
        "lc": language
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            if response.status == 200:
                return await response.json()
            else:
                return None


async def get_latest_article_by_keyword(language, keyword):
    # Récupérer tous les articles en anglais et en français
    english_articles = await get_bungie_rss_articles(api_key, language='en', page_token='0')
    french_articles = await get_bungie_rss_articles(api_key, language='fr', page_token='0')

    if english_articles and 'Response' in english_articles and 'NewsArticles' in english_articles['Response']:
        for item in english_articles['Response']['NewsArticles']:
            link = item.get('Link', '')

            await reformat_pubdate(item)

            # Vérifier la présence du mot-clé dans le lien
            if keyword in link:
                unique_id = item.get('UniqueIdentifier', None)

                if language == 'en':
                    # Vérifier si une version française existe
                    has_french_version = False
                    if unique_id and french_articles and 'Response' in french_articles and 'NewsArticles' in \
                            french_articles['Response']:
                        for french_item in french_articles['Response']['NewsArticles']:
                            if french_item.get('UniqueIdentifier') == unique_id:
                                has_french_version = True
                                break
                    return item, has_french_version

                elif language == 'fr':
                    # Essayer de trouver la version française
                    if unique_id and french_articles and 'Response' in french_articles and 'NewsArticles' in \
                            french_articles['Response']:
                        for french_item in french_articles['Response']['NewsArticles']:
                            if french_item.get('UniqueIdentifier') == unique_id:
                                await reformat_pubdate(french_item)
                                return french_item, True

                    # Si la version française n'est pas trouvée, retourner l'article en anglais
                    return item, False

                # Retourner l'article en anglais si aucune version française n'est trouvée
                return item

    # Si aucun article trouvé, retourner None
    return None, False


# Exemple d'utilisation
async def main():
    API_KEY = '95d66cb52e4d443ea72e729779de4263'
    LANGUAGE = 'en'  # Langue souhaitée (par exemple 'fr' pour français, 'en' pour anglais)
    keyword_twid = 'twid'
    keyword_destiny_2_update = 'destiny_2_update'

    twid, is_french_available = await get_latest_article_by_keyword(API_KEY, language=LANGUAGE, keyword=keyword_twid)
    destiny_2_update, is_french_available = await get_latest_article_by_keyword(API_KEY, language=LANGUAGE, keyword=keyword_destiny_2_update)

    if twid:
        if is_french_available:
            print("L'article en français est disponible.")
        else:
            print("L'article en français n'est pas disponible, voici l'article en anglais.")
        await pretty_print_json(twid)
    else:
        print("Aucun article trouvé.")

    if destiny_2_update:
        if is_french_available:
            print("L'article en français est disponible.")
        else:
            print("L'article en français n'est pas disponible, voici l'article en anglais.")
        await pretty_print_json(destiny_2_update)
    else:
        print("Aucun article trouvé.")


if __name__ == "__main__":
    asyncio.run(main())