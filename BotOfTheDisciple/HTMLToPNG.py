from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from PIL import Image
import io
import time  # Importer la bibliothèque time pour utiliser sleep

def html_to_png(html_path, output_path):
    # Configurer Selenium pour utiliser Chrome en mode headless
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920x1080')  # Vous pouvez ajuster la taille de la fenêtre

    # Initialiser le WebDriver (vous pouvez changer de driver si nécessaire)
    driver = webdriver.Chrome(options=options)

    # Charger le fichier HTML
    driver.get(f"file:///{html_path}")

    # Attendre 3 secondes pour laisser toutes les animations CSS se terminer
    time.sleep(3)

    # Prendre une capture d'écran entière de la page
    screenshot = driver.get_screenshot_as_png()

    # Fermer le navigateur
    driver.quit()

    # Charger l'image avec Pillow et l'enregistrer
    image = Image.open(io.BytesIO(screenshot))
    image.save(output_path)

    print(f"Image PNG générée avec succès : {output_path}")

# Exemple d'utilisation avec des backslashes dans les chemins
html_path = 'D:\\PC-Loan\\Desktop\\Destiny\\Destiny2LostSector_FR\\PythonProject\\Ressources\\Output.html'
output_path = 'D:\\PC-Loan\\Desktop\\Destiny\\Destiny2LostSector_FR\\BotOfTheDisciple\\CurrentLostSector.png'

html_to_png(html_path, output_path)