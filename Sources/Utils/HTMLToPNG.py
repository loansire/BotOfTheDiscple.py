from PIL import Image
import requests
import io
import Sources.Bot.ApiKey as APIKey

def html_to_png(html_path, output_path, css_path):
    # Lire le contenu des fichiers HTML et CSS
    with open(html_path, 'r', encoding='utf-8') as html_file:
        html_content = html_file.read()

    with open(css_path, 'r', encoding='utf-8') as css_file:
        css_content = css_file.read()

    # Informations sur l'API
    api_endpoint = "https://hcti.io/v1/image"
    api_user = APIKey.html_to_png_api_user
    api_key = APIKey.html_to_png_api_key

    data = {
        "html": html_content,
        "css": css_content,
        "viewport_width": 1880,  # Largeur souhaitée pour le rendu
        "viewport_height": 960,  # Hauteur souhaitée pour le rendu
        "ms_delay": 3000,        # Délai pour s'assurer que la page soit rendue
    }

    # Envoyer la requête POST à l'API
    response = requests.post(url=api_endpoint, data=data, auth=(api_user, api_key))

    if response.status_code == 200:
        # Récupérer l'URL de l'image générée
        image_url = response.json()['url']
        print(f"Votre URL d'image est : {image_url}")

        # Télécharger l'image depuis l'URL
        image_response = requests.get(image_url)
        if image_response.status_code == 200:
            # Ouvrir l'image à l'aide de Pillow
            image = Image.open(io.BytesIO(image_response.content))

            # Redimensionner l'image en 1920x1080
            image_resized = image.resize((1920, 1080), Image.ANTIALIAS)

            # Sauvegarder l'image redimensionnée dans output_path
            image_resized.save(output_path, format='PNG')
            print(f"Image PNG redimensionnée et sauvegardée avec succès : {output_path}\n")
        else:
            print(f"Erreur lors du téléchargement de l'image : {image_response.status_code}\n")
    else:
        print(f"Erreur lors de la génération de l'image : {response.status_code}, {response.text}\n")
