from ui import AppUI
from utils import logger
import sys

def main():
    logger.info("Iniciando Google Drive Downloader Pro...")
    try:
        app = AppUI()
        app.mainloop()
    except Exception as e:
        logger.error(f"Erro fatal na aplicacao: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
