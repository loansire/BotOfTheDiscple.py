#import extern
import logging

#import intern
import Config
import Download


def main():
    # Configuration de la journalisation
    logging.basicConfig(filename='manifest_download.log', level=logging.ERROR,
                    format='%(asctime)s:%(levelname)s:%(message)s')

    Download.download_manifest(Config.MAIN_MANIFEST_URL, Config.MAIN_MANIFEST_OUTPUT_FILE, 3, 1, True);







if __name__ == "__main__":
    main()