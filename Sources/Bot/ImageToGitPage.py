import base64
import requests
import certifi
import Sources.Bot.ApiKey as APIKey
from Sources.LostSector.Html.HtmlDefines import OUTPUT_JPEG_PATH

# === CONFIGURATION ===
GITHUB_TOKEN = APIKey.git_api
REPO_OWNER = "loansire"
REPO_NAME = "Botofthedisciple.fr"
BRANCH = "main"
TARGET_PATH = "todaylostsector/Output.png"
LOCAL_IMAGE_PATH = OUTPUT_JPEG_PATH
COMMIT_MESSAGE = "Bot: mise à jour de l’image secteur oublié du jour"


def upload_image_to_github():
    print("📁 Lecture de l'image locale...")
    try:
        with open(LOCAL_IMAGE_PATH, "rb") as image_file:
            encoded_content = base64.b64encode(image_file.read()).decode("utf-8")
        print("✅ Image lue et encodée avec succès.")
    except Exception as e:
        print("❌ Erreur lecture image :", e)
        return

    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{TARGET_PATH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    print("🔍 Vérification de l'existence du fichier sur GitHub...")
    sha = None
    try:
        get_resp = requests.get(url, headers=headers, verify=certifi.where(), timeout=30)
        if get_resp.status_code == 200:
            sha = get_resp.json()["sha"]
            print("📝 Fichier déjà présent, SHA récupéré.")
        elif get_resp.status_code == 404:
            print("📄 Aucun fichier existant à ce chemin (création).")
        else:
            print(f"⚠️ Erreur {get_resp.status_code} lors de la vérification :", get_resp.text)
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur pendant la requête GET (délai ou autre) : {e}")
        return

    payload = {
        "message": COMMIT_MESSAGE,
        "content": encoded_content,
        "branch": BRANCH
    }
    if sha:
        payload["sha"] = sha

    print("🚀 Envoi de l'image sur GitHub...")

    try:
        put_resp = requests.put(url, headers=headers, json=payload, verify=certifi.where(), timeout=60)

        # Affichage de la progression
        total_size = len(encoded_content)
        for i in range(0, total_size, total_size // 10):  # 10 étapes
            print(f"⚡ Progression : {int((i / total_size) * 100)}%", end='\r')

        if put_resp.status_code in [200, 201]:
            print("\n✅ Image mise à jour sur GitHub avec succès.")
        else:
            print(f"❌ Erreur ({put_resp.status_code}) lors du PUT :", put_resp.json())
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur pendant la requête PUT (délai ou autre) : {e}")


if __name__ == "__main__":
    print("🚧 DÉMARRAGE DE L'UPLOAD IMAGE SUR GITHUB 🚧")
    upload_image_to_github()
    print("🏁 FIN DU SCRIPT")
