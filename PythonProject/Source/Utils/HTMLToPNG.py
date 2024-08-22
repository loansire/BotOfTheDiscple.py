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

    # Fixer la taille de la fenêtre à 1920x1080 pixels
    driver.set_window_size(1920, 1080)
    # Fixer la position de la fenêtre à (0, 0)
    driver.set_window_position(0, 0)

    # Attendre 3 secondes pour laisser toutes les animations CSS se terminer
    time.sleep(3)

    # Obtenir les dimensions et la position de la fenêtre
    window_rect = driver.get_window_rect()
    print(f"Largeur de la fenêtre: {window_rect['width']} pixels")
    print(f"Hauteur de la fenêtre: {window_rect['height']} pixels")
    print(f"Position X de la fenêtre: {window_rect['x']} pixels")
    print(f"Position Y de la fenêtre: {window_rect['y']} pixels")

    # Prendre une capture d'écran entière de la page
    screenshot = driver.get_screenshot_as_png()

    # Fermer le navigateur
    driver.quit()

    # Charger l'image avec Pillow et l'enregistrer
    image = Image.open(io.BytesIO(screenshot))
    image.save(output_path)

    print(f"Image PNG générée avec succès : {output_path}")