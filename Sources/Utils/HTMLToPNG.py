import requests

def html_to_png(html_path, output_path, css_path):
    # Lire le contenu des fichiers HTML et CSS
    with open(html_path, 'r', encoding='utf-8') as html_file:
        html_content = html_file.read()

    with open(css_path, 'r', encoding='utf-8') as css_file:
        css_content = css_file.read()

    # Informations sur l'API
    api_endpoint = "https://hcti.io/v1/image"
    api_user = "aadb32cf-e14c-47ea-8b0d-63ef95c0a546"
    api_key = "415c4e2b-5faf-489e-a607-e72c5fdaecef"

    data = {
        "html": html_content,
        "css": css_content,
        "viewport_width": 1880,
        "viewport_height": 960,
        "ms_delay": 3000,
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
            # Sauvegarder l'image dans output_path
            with open(output_path, 'wb') as image_file:
                image_file.write(image_response.content)
            print(f"Image PNG téléchargée et sauvegardée avec succès : {output_path}\n")
        else:
            print(f"Erreur lors du téléchargement de l'image : {image_response.status_code}\n")
    else:
        print(f"Erreur lors de la génération de l'image : {response.status_code}, {response.text}\n")