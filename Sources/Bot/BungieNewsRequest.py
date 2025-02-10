from datetime import datetime
import re
import aiohttp
import json
import asyncio
import Sources.Bot.ApiKey as APIKey

from langdetect import detect

api_key = APIKey.bungie_api


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

async def get_bungie_rss_articles(language, page_token='0', includebody=False):
    url = f"https://www.bungie.net/Platform/Content/Rss/NewsArticles/{page_token}/"

    headers = {
        "X-API-Key": api_key
    }

    params = {
        "lc": language,
        "includebody": 'true' if includebody else 'false'
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            if response.status == 200:
                return await response.json()
            else:
                return None

async def get_latest_article_by_keyword(language, keyword):
    print(f"Le keyword est {keyword}")
    # Récupérer tous les articles
    articles = await get_bungie_rss_articles(language=language, page_token='0', includebody='true')

    french_articles = await get_bungie_rss_articles(language='fr', page_token='0', includebody='true')
    is_translation_available = False

    # Vérifier si le contenu HTML des articles en français est bien en français
    if french_articles and 'Response' in french_articles and 'NewsArticles' in french_articles['Response']:
        for item in french_articles['Response']['NewsArticles']:
            link = item.get('Link', '')
            if keyword in link:
                html_content = item.get('HtmlContent', '')
                detected_language = detect(html_content)
                if detected_language == 'fr':
                    is_translation_available = True
                break

    if articles and 'Response' in articles and 'NewsArticles' in articles['Response']:
        for item in articles['Response']['NewsArticles']:
            link = item.get('Link', '')

            await reformat_pubdate(item)

            # Vérifier la présence du mot-clé dans le lien
            if keyword in link:
                return item, is_translation_available

    return None, False


# Exemple d'utilisation
async def main():
    LANGUAGE = 'en'  # Langue souhaitée (par exemple 'fr' pour français, 'en' pour anglais)
    keyword_twid = 'twid'
    keyword_destiny_2_update = 'destiny_update'

    twid, is_french_available_twid = await get_latest_article_by_keyword(language=LANGUAGE, keyword=keyword_twid)
    destiny_2_update, is_french_available_destiny_2_update = await get_latest_article_by_keyword(language=LANGUAGE, keyword=keyword_destiny_2_update)

    if twid:
        if is_french_available_twid:
            print("L'article en français est disponible.")
        else:
            print("L'article en français n'est pas disponible, voici l'article en anglais.")
        await pretty_print_json(twid)
    else:
        print("Aucun article trouvé.")

    if destiny_2_update:
        if is_french_available_destiny_2_update:
            print("L'article en français est disponible.")
        else:
            print("L'article en français n'est pas disponible, voici l'article en anglais.")
        await pretty_print_json(destiny_2_update)
    else:
        print("Aucun article trouvé.")


if __name__ == "__main__":
    asyncio.run(main())