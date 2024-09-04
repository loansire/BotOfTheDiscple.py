import requests

def html_to_png(html_path, output_path, css_path):
    # Lire le contenu des fichiers HTML et CSS
    with open(html_path, 'r', encoding='utf-8') as html_file:
        html_content = html_file.read()

    with open(css_path, 'r', encoding='utf-8') as css_file:
        css_content = css_file.read()

    # Informations sur l'API
    api_endpoint = "https://hcti.io/v1/image"
    api_user = "3b28f166-11d3-48c1-bf53-8ea33d688dac"
    api_key = "aec9b06a-ab3a-4224-8c82-fb64bc26feb7"

    data = {
        "html": html_content,
        "css": css_content,
        "viewport_width": 1880,
        "viewport_height": 960,
        "device_scale": 1,
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
            print(f"Image PNG téléchargée et sauvegardée avec succès : {output_path}")
        else:
            print(f"Erreur lors du téléchargement de l'image : {image_response.status_code}")
    else:
        print(f"Erreur lors de la génération de l'image : {response.status_code}, {response.text}")

def main():
    html_path = "../../Output/Output.html"
    output_path = "../../Output/Output.png"
    css_path = "../../Output/styles.css"

    html_to_png(html_path, output_path, css_path)

if __name__ == "__main__":
    main()