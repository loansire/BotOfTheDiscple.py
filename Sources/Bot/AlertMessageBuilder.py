import json
import os


ALERTS_DIR = 'Ressources/AlertDatabase'


def load_alert_channels(alert_type):
    file_path = os.path.join(ALERTS_DIR, f"{alert_type}_alert_channels.json")
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return json.load(file)
    return {}


def save_alert_channels(alert_type, data):
    file_path = os.path.join(ALERTS_DIR, f"{alert_type}_alert_channels.json")
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)