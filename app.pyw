import sys
import os
import psutil
import multiprocessing
from ui import AppUI
from utils import setup_logger

logger = setup_logger()


def kill_previous_instances():
    """
    Verifica se já existe uma instância deste aplicativo rodando.
    Se existir, encerra a instância antiga para que a nova possa iniciar.
    """
    current_pid = os.getpid()
    try:
        if getattr(sys, 'frozen', False):
            # Executável compilado
            executable_path = sys.executable.lower()
            for proc in psutil.process_iter(['pid', 'exe', 'cmdline']):
                try:
                    if proc.info['pid'] == current_pid:
                        continue
                    # Ignorar processos filhos (multiprocessing)
                    if proc.info['cmdline'] and any('--multiprocessing-fork' in arg for arg in proc.info['cmdline']):
                        continue
                        
                    if proc.info['exe'] and proc.info['exe'].lower() == executable_path:
                        proc.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        else:
            # Script Python
            script_path = os.path.abspath(sys.argv[0]).lower()
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['pid'] == current_pid:
                        continue
                        
                    cmdline = proc.info['cmdline']
                    # Ignorar processos filhos (multiprocessing)
                    if cmdline and any('--multiprocessing-fork' in arg for arg in cmdline):
                        continue
                        
                    name = proc.info['name']
                    if name and ('python' in name.lower() or 'pythonw' in name.lower()):
                        if cmdline:
                            for arg in cmdline:
                                if arg.endswith('.py') or arg.endswith('.pyw'):
                                    if os.path.abspath(arg).lower() == script_path:
                                        proc.terminate()
                                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
    except Exception as e:
        logger.error(f"Erro ao tentar fechar instancias anteriores: {e}")

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.error("Erro Não Tratado (Crash Global):", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = handle_exception

def main():
    multiprocessing.freeze_support()
    kill_previous_instances()
    logger.info("Iniciando Google Drive Downloader Pro...")
    try:
        app = AppUI()
        app.mainloop()
    except Exception as e:
        logger.error(f"Erro fatal na aplicacao: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

