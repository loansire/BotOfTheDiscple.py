import aiohttp
import json
import asyncio


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


async def get_latest_twid_article(api_key, language):
    articles = await get_bungie_rss_articles(api_key, language=language, page_token='0')

    if articles and 'Response' in articles and 'NewsArticles' in articles['Response']:
        for item in articles['Response']['NewsArticles']:
            title = item.get('Title', '')
            if language == "en" and title.startswith("This Week In Destiny"):
                return item
            if language == "fr" and title.startswith("Cette semaine dans Destiny"):
                return item
    return None


def pretty_print_json(data):
    print(json.dumps(data, indent=4, ensure_ascii=False))


# Exemple d'utilisation
async def main():
    API_KEY = '95d66cb52e4d443ea72e729779de4263'
    LANGUAGE = 'fr'  # Langue souhaitée (par exemple 'fr' pour français, 'en' pour anglais)

    latest_twid = await get_latest_twid_article(API_KEY, language=LANGUAGE)

    if latest_twid:
        print("Dernier article TWID trouvé :")
        pretty_print_json(latest_twid)
    else:
        print("Aucun article TWID trouvé.")


if __name__ == "__main__":
    asyncio.run(main())
