from datetime import datetime
import re
import aiohttp
import json
import asyncio


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


async def get_bungie_rss_articles(api_key, language, page_token='0'):
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


async def pretty_print_json(data):
    print(json.dumps(data, indent=4, ensure_ascii=False))


async def get_latest_twid_article(api_key, language):
    articles = await get_bungie_rss_articles(api_key, language=language, page_token='0')

    if articles and 'Response' in articles and 'NewsArticles' in articles['Response']:
        for item in articles['Response']['NewsArticles']:
            title = item.get('Title', '')

            await reformat_pubdate(item)

            if language == "en" and title.startswith("This Week In Destiny"):
                return item
            if language == "fr" and title.startswith("Cette semaine dans Destiny"):
                return item
    return None


async def get_latest_patch_note_article(api_key, language):
    articles = await get_bungie_rss_articles(api_key, language=language, page_token='0')

    if articles and 'Response' in articles and 'NewsArticles' in articles['Response']:
        for item in articles['Response']['NewsArticles']:
            title = item.get('Title', '')

            await reformat_pubdate(item)

            if language == "en":
                # Pour l'anglais, vous vérifiez directement la chaîne exacte
                if title.startswith("Destiny 2 Update"):
                    return item
            elif language == "fr":
                # Pour le français, vous extrayez la version et construisez la chaîne de recherche
                version = await extract_version_from_title(title)
                if version and title.startswith(f"Mise à jour {version} de Destiny 2"):
                    return item
    return None


# Exemple d'utilisation
async def main():
    API_KEY = '95d66cb52e4d443ea72e729779de4263'
    LANGUAGE = 'en'  # Langue souhaitée (par exemple 'fr' pour français, 'en' pour anglais)

    latest_twid = await get_latest_patch_note_article(API_KEY, language=LANGUAGE)

    if latest_twid:
        print("Dernier article TWID trouvé :")
        await pretty_print_json(latest_twid)
    else:
        print("Aucun article TWID trouvé.")


if __name__ == "__main__":
    asyncio.run(main())
