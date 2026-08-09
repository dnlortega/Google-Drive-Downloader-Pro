from ui import AppUI
from utils import logger
import sys

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.error("Erro Não Tratado (Crash Global):", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = handle_exception

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
