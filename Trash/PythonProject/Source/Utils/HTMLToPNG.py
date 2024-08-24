from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from PIL import Image
import io
import time

def html_to_png(html_path, output_path):
    # Configurer Selenium pour utiliser Chrome en mode headless
    options = Options()
    options.add_argument("start-maximized")
    options.add_argument('--headless')  # Mode headless pour ne pas afficher le navigateur

    # Initialiser le WebDriver pour Chrome
    driver = webdriver.Chrome(options=options)

    # Charger le fichier HTML
    driver.get(f"file:///{html_path}")

    # Définir explicitement la taille de la fenêtre à 1920x1080
    driver.set_window_size(1936, 1227)

    # Attendre un peu pour s'assurer que le contenu est chargé
    time.sleep(3)

    # Prendre une capture d'écran entière de la page
    screenshot = driver.get_screenshot_as_png()

    # Fermer le navigateur
    driver.quit()

    # Charger l'image avec Pillow et l'enregistrer
    image = Image.open(io.BytesIO(screenshot))
    image.save(output_path)

    print(f"Image PNG générée avec succès : {output_path}")