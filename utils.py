import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logger(log_file="app.log"):
    logger = logging.getLogger("DriveDownloader")
    logger.setLevel(logging.DEBUG)
    
    # Previne adicionar múltiplos handlers se a função for chamada novamente
    if not logger.handlers:
        # File handler (10 MB max size, keep 3 backups)
        fh = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=3, encoding="utf-8")
        fh.setLevel(logging.INFO)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        logger.addHandler(fh)
        logger.addHandler(ch)
    
    return logger

logger = setup_logger()

def format_size(size_bytes):
    if not size_bytes: return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"

def format_time(seconds):
    if seconds < 0 or seconds == float('inf'):
        return "Calculando..."
    if seconds < 60:
        return f"{int(seconds)}s"
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    if minutes < 60:
        return f"{minutes}m {seconds}s"
    hours = int(minutes // 60)
    minutes = int(minutes % 60)
    return f"{hours}h {minutes}m"
