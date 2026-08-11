from CTkMessagebox import CTkMessagebox
from PIL import Image
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from logging.handlers import RotatingFileHandler
from plyer import notification
from pystray import MenuItem as item
from tkinter import filedialog, ttk
import concurrent.futures
import customtkinter as ctk
import gdown
import io
import json
import logging
import multiprocessing
import os
import os.path
import psutil
import pystray
import shutil
import sqlite3
import sys
import threading
import time
import tkinter as tk
import winsound
import zipfile


# --- START OF utils.py ---

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

# --- END OF utils.py ---

# --- START OF database.py ---

DB_FILE = "downloads_db.sqlite3"
OLD_HISTORY_FILE = "history.json"

def get_connection():
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT,
            file_name TEXT,
            file_path TEXT,
            status TEXT,
            file_size TEXT,
            download_date DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    migrate_old_history()

def migrate_old_history():
    # Only migrate old URLs that were stored in history.json
    if os.path.exists(OLD_HISTORY_FILE):
        try:
            with open(OLD_HISTORY_FILE, "r") as f:
                historico = json.load(f)
            
            conn = get_connection()
            cursor = conn.cursor()
            for url in historico:
                # Check if it exists to avoid duplicates during migration
                cursor.execute("SELECT id FROM history WHERE url = ?", (url,))
                if not cursor.fetchone():
                    cursor.execute("INSERT INTO history (url, file_name, file_path, status, file_size) VALUES (?, ?, ?, ?, ?)", (url, "Desconhecido", "", "Migrado", "0 B"))
            conn.commit()
            conn.close()
            os.remove(OLD_HISTORY_FILE) # Remove after migration
        except Exception as e:
            print(f"Erro ao migrar historico: {e}")

def add_to_history(url, file_name, file_path, status, file_size):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO history (url, file_name, file_path, status, file_size)
            VALUES (?, ?, ?, ?, ?)
        ''', (url, file_name, file_path, status, file_size))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Erro ao salvar historico: {e}")

def get_recent_urls(limit=5):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT url FROM history 
            ORDER BY download_date DESC 
            LIMIT ?
        ''', (limit,))
        urls = [row[0] for row in cursor.fetchall() if row[0]]
        conn.close()
        return urls
    except Exception as e:
        print(f"Erro ao buscar URLs: {e}")
        return []

def get_full_history():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT url, file_name, file_path, status, file_size, download_date 
            FROM history 
            ORDER BY download_date DESC
        ''')
        records = cursor.fetchall()
        conn.close()
        return records
    except Exception as e:
        print(f"Erro ao buscar historico completo: {e}")
        return []

# --- END OF database.py ---

# --- START OF downloader.py ---

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def get_drive_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif os.path.exists('credentials.json'):
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        else:
            return None
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('drive', 'v3', credentials=creds)

def _extrair_zip_proc(filepath, extract_path):
    with zipfile.ZipFile(filepath, 'r') as zip_ref:
        zip_ref.extractall(extract_path)

class SingleFile:
    def __init__(self, f_id, path):
        self.id = f_id
        self.local_path = path

class DownloaderCore:
    def __init__(self, callbacks):
        """
        callbacks: dict de funções de atualização da UI. Ex:
        - update_status(file_id, status_text, color, frame_color, is_highlighted, is_completed, is_failed, is_existing, progresso)
        - bulk_add(items, target_tree)
        - on_analyze_finish(arquivos_para_baixar, msg, color, has_files)
        - on_download_progress(archived_count, total)
        - on_download_finish(is_paused)
        """
        self.callbacks = callbacks
        self.cancel_event = threading.Event()
        self.lock = threading.Lock()
        
        self.arquivos_para_baixar = []
        self.archived_count = 0
        self.total_bytes_downloaded = 0
        self.log_entries = []
        self.completed_ids = set()
        
        self.is_downloading = False
        self.max_workers = 1
        self.extrair_zip = False
        self.pasta_destino = ""
        self.drive_service = None

    def auth_google(self):
        try:
            self.drive_service = get_drive_service()
            return self.drive_service is not None
        except Exception as e:
            logger.error(f"Erro na autenticacao do google: {e}")
            return False

    def config(self, max_workers, extrair_zip, pasta_destino):
        self.max_workers = max_workers
        self.extrair_zip = extrair_zip
        self.pasta_destino = pasta_destino

    def start_analysis(self, url, filtro, ordem):
        thread = threading.Thread(target=self._analyze_link_thread, args=(url, filtro, ordem))
        thread.start()

    def _filtrar_arquivos(self, arquivos, filtro):
        if filtro == "Todos":
            return arquivos
        ext_imagens = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'}
        ext_videos = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm'}
        ext_docs = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt'}
        filtrados = []
        for a in arquivos:
            ext = os.path.splitext(a.local_path)[1].lower() if hasattr(a, 'local_path') and a.local_path else ""
            if filtro == "Imagens" and ext in ext_imagens:
                filtrados.append(a)
            elif filtro == "Vídeos" and ext in ext_videos:
                filtrados.append(a)
            elif filtro == "Documentos" and ext in ext_docs:
                filtrados.append(a)
        return filtrados

    def _format_size(self, size_bytes):
        if not size_bytes: return "0 B"
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"

    def _analyze_link_thread(self, url, filtro, ordem):
        logger.info(f"Iniciando analise de link: {url}")
        os.makedirs(self.pasta_destino, exist_ok=True)
        try:
            url_lower = url.lower()
            file_id = url.split("id=")[1].split("&")[0] if "id=" in url else url.split("/d/")[1].split("/")[0] if "/d/" in url else url
            arquivos_brutos = []

            # Se o usuario estiver logado, tenta pegar os dados oficiais pela API
            if self.drive_service:
                try:
                    file_metadata = self.drive_service.files().get(fileId=file_id, fields="id, name, mimeType").execute()
                    if file_metadata['mimeType'] == 'application/vnd.google-apps.folder':
                        # Simplificação: listar arquivos da pasta via API não implementada por completo, falha graciosa pro gdown
                        logger.info("Pasta privada via API requer mais lógica. Tentando listar via gdown...")
                        arquivos_brutos = gdown.download_folder(url, output=self.pasta_destino, quiet=True, skip_download=True)
                    else:
                        local_path = os.path.join(self.pasta_destino, file_metadata['name'])
                        arquivos_brutos = [SingleFile(file_metadata['id'], local_path)]
                except Exception as api_e:
                    logger.warning(f"Falha ao ler via API (talvez falta de permissão ou id inválido): {api_e}")
            
            # Fallback para gdown se a API nao encontrou
            if not arquivos_brutos:
                if "folder" in url_lower or "drive.google.com/drive/folders/" in url_lower:
                    arquivos_brutos = gdown.download_folder(url, output=self.pasta_destino, quiet=True, skip_download=True)
                else:
                    res = gdown.download(url, output=self.pasta_destino, quiet=True, skip_download=True)
                    arquivos_brutos = [SingleFile(file_id, getattr(res, 'path', str(res) if res else None))] if res else []
                
            filtrados = self._filtrar_arquivos(arquivos_brutos, filtro)
            
            if not filtrados:
                self.callbacks.get('on_analyze_finish', lambda *args: None)([], "⚠️ Nenhum arquivo encontrado com esse filtro.", "#ffc107", False)
                return
                
            if ordem == "Nome (A-Z)":
                filtrados.sort(key=lambda x: getattr(x, 'path', getattr(x, 'local_path', '')).lower())
            elif ordem == "Nome (Z-A)":
                filtrados.sort(key=lambda x: getattr(x, 'path', getattr(x, 'local_path', '')).lower(), reverse=True)
            
            arquivos_pendentes = []
            inserir_exists = []
            inserir_queue = []
            count_exists = 0
            
            # Rastrear todos os nomes de arquivos já baixados na pasta destino (ignorando subpastas originais)
            nomes_existentes = set()
            if os.path.exists(self.pasta_destino):
                for root, _, files in os.walk(self.pasta_destino):
                    for f in files:
                        nomes_existentes.add(f.lower())
            
            for i, arquivo in enumerate(filtrados):
                nome_arquivo = os.path.basename(arquivo.local_path) if getattr(arquivo, 'local_path', None) else f"Arquivo_{i}"
                tamanho = self._format_size(os.path.getsize(arquivo.local_path)) if os.path.exists(arquivo.local_path) else "Desconhecido"
                
                # Verifica apenas pelo NOME do arquivo, independentemente de onde ele esteja salvo
                if nome_arquivo.lower() in nomes_existentes:
                    inserir_exists.append((arquivo.id, nome_arquivo, arquivo.local_path, "✅ Já existe", tamanho))
                    count_exists += 1
                else:
                    arquivos_pendentes.append(arquivo)
                    inserir_queue.append((arquivo.id, nome_arquivo, arquivo.local_path, "⏳ Aguardando", tamanho))
                    
            if inserir_exists:
                self.callbacks.get('bulk_add', lambda *args: None)(inserir_exists, "exists")
            if inserir_queue:
                self.callbacks.get('bulk_add', lambda *args: None)(inserir_queue, "queue")
                
            self.arquivos_para_baixar = arquivos_pendentes
            total_encontrados = len(arquivos_brutos) if arquivos_brutos else len(self.arquivos_para_baixar) + count_exists
            msg = f"✅ Análise Concluída! Total: {total_encontrados} | Pendentes: {len(self.arquivos_para_baixar)} | Já Baixados: {count_exists}"
            
            logger.info(msg)
            self.callbacks.get('on_analyze_finish', lambda *args: None)(self.arquivos_para_baixar, msg, "#28a745", True)
                
        except Exception as e:
            logger.error(f"Erro na análise: {e}")
            self.callbacks.get('on_analyze_finish', lambda *args: None)([], f"❌ Erro na análise:\n{e}", "#dc3545", False)

    def update_queue_order(self, ordered_ids):
        with self.lock:
            id_to_file = {f.id: f for f in self.arquivos_para_baixar}
            nova_lista = []
            for f_id in ordered_ids:
                if f_id in id_to_file:
                    nova_lista.append(id_to_file.pop(f_id))
            for f in id_to_file.values():
                nova_lista.append(f)
            self.arquivos_para_baixar = nova_lista

    def remove_from_queue(self, ids_to_remove):
        with self.lock:
            ids_set = set(ids_to_remove)
            self.arquivos_para_baixar = [f for f in self.arquivos_para_baixar if f.id not in ids_set]

    def retry_failed(self):
        with self.lock:
            # Mantém apenas os arquivos que ainda não foram concluídos
            self.arquivos_para_baixar = [f for f in self.arquivos_para_baixar if f.id not in self.completed_ids]
            self.archived_count = 0
            self.log_entries = []

    def start_download(self):
        self.is_downloading = True
        self.cancel_event.clear()
        
        if self.archived_count == 0 or self.archived_count == len(self.arquivos_para_baixar):
            self.log_entries = []
            self.archived_count = 0
            
        logger.info("Iniciando fila de downloads.")
        thread = threading.Thread(target=self._download_files_thread)
        thread.start()

    def pause_download(self):
        logger.info("Solicitado pause de download.")
        self.cancel_event.set()

    def _download_worker(self, arquivo):
        nome_arquivo = os.path.basename(arquivo.local_path) if getattr(arquivo, 'local_path', None) else arquivo.id
        
        if self.cancel_event.is_set():
            self.callbacks.get('update_status')(arquivo.id, "⏸️ Pausado", "#ffc107", "#242424", False, False, False, False, "")
            return
            
        if arquivo.id in self.completed_ids:
            return
            
        if os.path.exists(arquivo.local_path) and os.path.getsize(arquivo.local_path) > 0 and not self.cancel_event.is_set():
            self.callbacks.get('update_status')(arquivo.id, "✅ Já existe", "#28a745", "#242424", False, False, False, True, "")
            self.log_entries.append(f"JÁ EXISTE: {nome_arquivo}")
            self.completed_ids.add(arquivo.id)
            with self.lock:
                self.archived_count += 1
                self.callbacks.get('on_download_progress')(self.archived_count, len(self.arquivos_para_baixar))
            return

        local_state = {'last_time': time.time(), 'last_bytes': 0, 'last_speed_bytes': 0}
        
        def custom_progress(bytes_so_far, bytes_total):
            if self.cancel_event.is_set():
                raise Exception("Pausado pelo usuário")
                
            chunk = bytes_so_far - local_state['last_bytes']
            if chunk > 0:
                with self.lock:
                    self.total_bytes_downloaded += chunk
                local_state['last_bytes'] = bytes_so_far

            current_time = time.time()
            elapsed = current_time - local_state['last_time']
            
            if elapsed > 1.0:
                speed = (bytes_so_far - local_state['last_speed_bytes']) / elapsed if elapsed > 0 else 0
                local_state['last_speed_bytes'] = bytes_so_far
                local_state['last_time'] = current_time
                
                speed_str = f"{speed / (1024 * 1024):.1f} MB/s" if speed > 1024 * 1024 else f"{speed / 1024:.1f} KB/s"
                percentage = (bytes_so_far / bytes_total * 100) if bytes_total else 0
                baixado_str = self._format_size(bytes_so_far)
                total_str = self._format_size(bytes_total) if bytes_total else "?"
                prog_text = f"{baixado_str} / {total_str} ({percentage:.0f}%) | {speed_str}" if percentage > 0 else f"{baixado_str} | {speed_str}"
                
                self.callbacks.get('update_status')(arquivo.id, "🔄 Baixando...", "#00ffff", "#1f538d", True, False, False, False, prog_text)
        
        max_retries = 3
        sucesso = False
        ultimo_erro = "Desconhecido"
        
        for tentativa in range(max_retries):
            if self.cancel_event.is_set(): break
            try:
                if tentativa > 0:
                    logger.warning(f"Tentativa {tentativa+1} para {nome_arquivo}")
                    self.callbacks.get('update_status')(arquivo.id, f"⚠️ Tentando ({tentativa+1}/3)", "#ffc107", "#1f538d", True, False, False, False, "")
                    time.sleep(3) 
                    
                self.callbacks.get('update_status')(arquivo.id, "🔄 Baixando...", "#00ffff", "#1f538d", True, False, False, False, "")
                
                # Tenta baixar pela API oficial primeiro se disponivel
                baixou_pela_api = False
                if self.drive_service:
                    try:
                        request = self.drive_service.files().get_media(fileId=arquivo.id)
                        fh = io.FileIO(arquivo.local_path, 'wb')
                        downloader = MediaIoBaseDownload(fh, request)
                        done = False
                        while done is False:
                            status, done = downloader.next_chunk()
                            if status:
                                custom_progress(status.resumable_progress, status.total_size)
                        baixou_pela_api = True
                    except Exception as api_e:
                        logger.warning(f"Download via API falhou, caindo para gdown: {api_e}")
                        baixou_pela_api = False
                        
                if not baixou_pela_api:
                    gdown.download(id=arquivo.id, url=arquivo.id if "http" in arquivo.id else None, output=arquivo.local_path, quiet=True, progress=custom_progress, resume=True)
                
                self.callbacks.get('update_status')(arquivo.id, "✅ Concluído", "#28a745", "#242424", False, True, False, False, "")
                self.log_entries.append(f"SUCESSO: {nome_arquivo}")
                self.completed_ids.add(arquivo.id)
                sucesso = True
                
                if self.extrair_zip and arquivo.local_path.lower().endswith('.zip'):
                    self.callbacks.get('update_status')(arquivo.id, "📦 Extraindo ZIP...", "#17a2b8", "#1f538d", True, False, False, False, "")
                    try:
                        extract_path = os.path.splitext(arquivo.local_path)[0]
                        with concurrent.futures.ProcessPoolExecutor(max_workers=1) as proc_exec:
                            proc_exec.submit(_extrair_zip_proc, arquivo.local_path, extract_path).result()
                        self.callbacks.get('update_status')(arquivo.id, "✅ Extraído", "#28a745", "#242424", False, True, False, False, "")
                    except Exception as e:
                        logger.error(f"Erro ao extrair zip {nome_arquivo}: {e}")
                        self.callbacks.get('update_status')(arquivo.id, "⚠️ Erro no ZIP", "#ffc107", "#242424", False, True, False, False, "")
                break
            except Exception as e:
                if "Pausado" in str(e):
                    break
                ultimo_erro = str(e).replace('\n', ' ')
                continue 
                
        if not sucesso:
            if self.cancel_event.is_set():
                self.callbacks.get('update_status')(arquivo.id, "⏸️ Pausado", "#ffc107", "#242424", False, False, False, False, "")
                self.log_entries.append(f"PAUSADO: {nome_arquivo}")
            elif os.path.exists(arquivo.local_path) and os.path.getsize(arquivo.local_path) > 0:
                self.callbacks.get('update_status')(arquivo.id, "✅ Já existe", "#28a745", "#242424", False, False, False, True, "")
                self.log_entries.append(f"JÁ EXISTE: {nome_arquivo}")
                sucesso = True
            else:
                erro_curto = ultimo_erro[:30] + "..." if len(ultimo_erro) > 30 else ultimo_erro
                logger.error(f"Falha no download {nome_arquivo}: {ultimo_erro}")
                self.callbacks.get('update_status')(arquivo.id, f"❌ Erro: {erro_curto}", "#dc3545", "#242424", False, False, True, False, "")
                self.log_entries.append(f"FALHA [Motivo: {ultimo_erro}]: {nome_arquivo}")

        if sucesso or (not sucesso and not self.cancel_event.is_set()):
            with self.lock:
                self.archived_count += 1
                self.callbacks.get('on_download_progress')(self.archived_count, len(self.arquivos_para_baixar))

    def _download_files_thread(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self._download_worker, arg) for arg in self.arquivos_para_baixar]
            concurrent.futures.wait(futures)
            
        self.is_downloading = False
        is_paused = self.cancel_event.is_set()
        if is_paused:
            logger.info("Downloads pausados com sucesso.")
        else:
            logger.info("Fila de downloads finalizada.")
            self.archived_count = 0
            
        self.callbacks.get('on_download_finish')(is_paused, self.log_entries)

# --- END OF downloader.py ---

# --- START OF ui.py ---


ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

ctk.set_default_color_theme("blue")

# Inicializa banco de dados e migra se necessario
database.init_db()

class AppUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Redireciona qualquer crash da interface (Tkinter) direto para o log
        self.report_callback_exception = self.show_error

        self.title("Google Drive Downloader Pro")
        self.geometry("900x850")
        self.resizable(True, True)
        
        self.protocol('WM_DELETE_WINDOW', self.hide_window)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(7, weight=1)

        self.title_label = ctk.CTkLabel(self, text="Google Drive Downloader Pro", font=ctk.CTkFont(size=26, weight="bold"))
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 5))
        
        self.subtitle_label = ctk.CTkLabel(self, text="Filtros, Auto-retry, e Gerenciamento Inteligente.", font=ctk.CTkFont(size=13, slant="italic"), text_color="gray")
        self.subtitle_label.grid(row=1, column=0, padx=20, pady=(0, 15))

        self.folder_frame = ctk.CTkFrame(self, fg_color="#2b2b2b", corner_radius=12)
        self.folder_frame.grid(row=2, column=0, padx=25, pady=(5, 10), sticky="ew")
        self.folder_frame.grid_columnconfigure(1, weight=1)

        self.pasta_destino = os.path.expanduser("~/Downloads/Fotos_Drive")
        
        self.folder_label = ctk.CTkLabel(self.folder_frame, text="Destino:", font=ctk.CTkFont(weight="bold", size=14))
        self.folder_label.grid(row=0, column=0, padx=(15, 5), pady=15, sticky="w")
        
        self.folder_path_var = ctk.StringVar(value=self.pasta_destino)
        self.folder_path_label = ctk.CTkLabel(self.folder_frame, textvariable=self.folder_path_var, text_color="gray", anchor="w")
        self.folder_path_label.grid(row=0, column=1, padx=5, sticky="ew")
        
        self.folder_btn = ctk.CTkButton(self.folder_frame, text="📂", command=self.escolher_pasta, width=40, fg_color="#3b82f6", hover_color="#2563eb", font=ctk.CTkFont(size=18))
        self.folder_btn.grid(row=0, column=2, padx=5, pady=15)
        
        self.settings_btn = ctk.CTkButton(self.folder_frame, text="⚙️", command=self.abrir_configuracoes, width=40, fg_color="#4b5563", hover_color="#374151", font=ctk.CTkFont(size=18))
        self.settings_btn.grid(row=0, column=3, padx=5, pady=15)
        
        self.login_btn = ctk.CTkButton(self.folder_frame, text="Google Login", command=self.login_google, width=120, fg_color="#ea4335", hover_color="#d33426", font=ctk.CTkFont(weight="bold"))
        self.login_btn.grid(row=0, column=4, padx=(5, 15), pady=15)

        self.input_frame = ctk.CTkFrame(self, fg_color="#2b2b2b", corner_radius=12)
        self.input_frame.grid(row=3, column=0, padx=25, pady=(0, 10), sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)
        
        self.historico = self.carregar_historico()
        self.url_entry = ctk.CTkComboBox(self.input_frame, values=self.historico, height=40)
        self.url_entry.grid(row=0, column=0, padx=(15, 10), pady=15, sticky="ew")
        self.url_entry.set(self.historico[0] if self.historico else "")

        self.analyze_btn = ctk.CTkButton(self.input_frame, text="🔍", command=self.handle_analyze_only, height=40, width=50, fg_color="#3b82f6", hover_color="#2563eb", font=ctk.CTkFont(size=20))
        self.analyze_btn.grid(row=0, column=1, padx=5, pady=15, sticky="ew")

        self.action_button = ctk.CTkButton(self.input_frame, text="⬇️", command=self.handle_action, height=40, width=50, fg_color="#10b981", hover_color="#059669", font=ctk.CTkFont(size=20))
        self.action_button.grid(row=0, column=2, padx=(5, 15), pady=15, sticky="ew")
        
        self.filters_frame = ctk.CTkFrame(self, fg_color="#2b2b2b", corner_radius=12)
        self.filters_frame.grid(row=4, column=0, padx=25, pady=(0, 15), sticky="ew")
        
        ctk.CTkLabel(self.filters_frame, text="Filtro de Tipo:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(15, 5), pady=10)
        self.filtro_var = ctk.StringVar(value="Todos")
        self.filtro_combo = ctk.CTkComboBox(self.filters_frame, values=["Todos", "Imagens", "Vídeos", "Documentos"], variable=self.filtro_var, width=130)
        self.filtro_combo.pack(side="left", padx=(0, 20), pady=10)

        ctk.CTkLabel(self.filters_frame, text="Ordenar por:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(0, 5), pady=10)
        self.ordem_var = ctk.StringVar(value="Nome (A-Z)")
        self.ordem_combo = ctk.CTkComboBox(self.filters_frame, values=["Nome (A-Z)", "Nome (Z-A)", "Padrão (Drive)"], variable=self.ordem_var, width=150)
        self.ordem_combo.pack(side="left", padx=(0, 15), pady=10)

        self.info_label = ctk.CTkLabel(self, text="Bem-vindo! Selecione o destino, um filtro e cole o link para começar.", font=ctk.CTkFont(size=14))
        self.info_label.grid(row=5, column=0, padx=20, pady=10)

        self.actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.actions_frame.grid(row=6, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        self.open_folder_btn = ctk.CTkButton(self.actions_frame, text="📂", command=self.abrir_pasta, fg_color="#6c757d", hover_color="#5a6268", width=40, font=ctk.CTkFont(size=18))
        self.open_folder_btn.grid(row=0, column=0, padx=10)
        
        self.clear_folder_btn = ctk.CTkButton(self.actions_frame, text="🗑️", command=self.limpar_pasta, fg_color="#dc3545", hover_color="#c82333", width=40, font=ctk.CTkFont(size=18))
        self.clear_folder_btn.grid(row=0, column=1, padx=10)

        self.restart_failed_btn = ctk.CTkButton(self.actions_frame, text="🔄", command=self.reiniciar_falhas, fg_color="#ffc107", hover_color="#e0a800", width=40, text_color="black", font=ctk.CTkFont(size=18))
        self.restart_failed_btn.grid(row=0, column=2, padx=10)

        # Dados da Fila Virtual
        self.queue_data = [] # Lista de (file_id, filename, filepath, status, size, progresso)
        self.queue_page = 0
        self.queue_page_size = 100
        
        self.tab_names = {"queue": "Fila de Download", "completed": "Concluídos", "exists": "Já Existentes", "failed": "Falhas"}
        self.counts = {"queue": 0, "completed": 0, "exists": 0, "failed": 0}
        
        self.tabview = ctk.CTkTabview(self, height=280)
        self.tabview.grid(row=7, column=0, padx=20, pady=(0, 5), sticky="nsew")
        
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("Treeview", background="#2b2b2b", foreground="white", rowheight=30, fieldbackground="#2b2b2b", borderwidth=0)
        style.map('Treeview', background=[('selected', '#22559b')])
        style.configure("Treeview.Heading", background="#565b5e", foreground="white", relief="flat", font=("Inter", 12, "bold"))
        style.map("Treeview.Heading", background=[('active', '#3484F0')])

        self.trees = {}
        for key in ["queue", "completed", "exists", "failed"]:
            self.tabview.add(self.tab_names[key])
            tab_frame = self.tabview.tab(self.tab_names[key])
            tree_frame = ctk.CTkFrame(tab_frame, fg_color="transparent")
            tree_frame.pack(fill="both", expand=True)
            
            tree = ttk.Treeview(tree_frame, columns=("ID", "Nome", "Tamanho", "Status", "Progresso"), show="headings", selectmode="extended")
            tree.heading("ID", text="ID")
            tree.heading("Nome", text="Nome do Arquivo")
            tree.heading("Tamanho", text="Tamanho")
            tree.heading("Status", text="Status")
            tree.heading("Progresso", text="Progresso")
            
            tree.column("ID", width=0, stretch=False)
            tree.column("Nome", width=400, anchor="w")
            tree.column("Tamanho", width=100, anchor="center")
            tree.column("Status", width=120, anchor="center")
            tree.column("Progresso", width=150, anchor="center")
            
            scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            
            tree.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            tree.bind("<Double-1>", self.on_tree_double_click)
            self.trees[key] = tree
            
            if key == "queue":
                self.queue_menu = tk.Menu(self, tearoff=0, bg="#2b2b2b", fg="white", activebackground="#3484F0")
                self.queue_menu.add_command(label="Mover para o Topo", command=lambda: self.reordenar_fila("topo"))
                self.queue_menu.add_command(label="Mover para Cima", command=lambda: self.reordenar_fila("cima"))
                self.queue_menu.add_command(label="Mover para Baixo", command=lambda: self.reordenar_fila("baixo"))
                self.queue_menu.add_command(label="Mover para o Fim", command=lambda: self.reordenar_fila("fim"))
                self.queue_menu.add_separator()
                self.queue_menu.add_command(label="Excluir Selecionados", command=self.excluir_da_fila)
                tree.bind("<Button-3>", self.mostrar_menu_fila)
            
        # Paginacao para a fila
        self.pagination_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.pagination_frame.grid(row=8, column=0, pady=5)
        self.btn_prev = ctk.CTkButton(self.pagination_frame, text="◀", width=40, command=self.prev_page, font=ctk.CTkFont(size=16))
        self.btn_prev.pack(side="left", padx=5)
        self.lbl_page = ctk.CTkLabel(self.pagination_frame, text="Pág 1")
        self.lbl_page.pack(side="left", padx=10)
        self.btn_next = ctk.CTkButton(self.pagination_frame, text="▶", width=40, command=self.next_page, font=ctk.CTkFont(size=16))
        self.btn_next.pack(side="left", padx=5)

        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_frame.grid(row=9, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.progress_frame.grid_columnconfigure(0, weight=1)

        self.progress_label = ctk.CTkLabel(self.progress_frame, text="Progresso Total: 0%", font=ctk.CTkFont(size=13, weight="bold"))
        self.progress_label.grid(row=0, column=0, pady=(0, 5), sticky="w")
        
        self.global_stats_label = ctk.CTkLabel(self.progress_frame, text="Baixado: 0.0 MB | ETA: --", font=ctk.CTkFont(size=13, weight="bold"), text_color="#00ffff")
        self.global_stats_label.grid(row=0, column=1, pady=(0, 5), sticky="e")

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, height=14)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=1, column=0, columnspan=2, pady=(0, 5), sticky="ew")
        self.progress_frame.grid_remove()
        
        self.file_labels = {} 
        self.gerar_relatorio_ativo = ctk.BooleanVar(value=False)
        self.extrair_zip_var = ctk.BooleanVar(value=False)
        self.max_workers = 1
        self.settings_window = None
        
        # Init Core
        self.safe_analyze_finish = lambda *args: self.after(0, self.on_analyze_finish, *args)
        
        callbacks = {
            'update_status': lambda *args: self.after(0, self.atualizar_status, *args),
            'bulk_add': lambda *args: self.after(0, self.bulk_add_rows, *args),
            'on_analyze_finish': self.safe_analyze_finish,
            'on_download_progress': lambda *args: self.after(0, self.on_download_progress, *args),
            'on_download_finish': lambda *args: self.after(0, self.on_download_finish, *args)
        }
        self.core = DownloaderCore(callbacks)
        self.core.config(self.max_workers, self.extrair_zip_var.get(), self.pasta_destino)
        
        self.global_updater_running = False
        self.last_global_time = 0
        self.last_global_bytes = 0
        
        # Monitor do Sistema (Rodapé)
        self.actions_frame.grid_columnconfigure(3, weight=1)
        
        self.lbl_gpu = ctk.CTkLabel(self.actions_frame, text="App GPU: --%", font=ctk.CTkFont(size=11), text_color="gray")
        self.lbl_gpu.grid(row=0, column=6, padx=10, sticky="e")

        self.lbl_cpu = ctk.CTkLabel(self.actions_frame, text="App CPU: --%", font=ctk.CTkFont(size=11), text_color="gray")
        self.lbl_cpu.grid(row=0, column=5, padx=10, sticky="e")
        
        self.lbl_ram = ctk.CTkLabel(self.actions_frame, text="App RAM: -- MB", font=ctk.CTkFont(size=11), text_color="gray")
        self.lbl_ram.grid(row=0, column=4, padx=10, sticky="e")
        
        self.current_process = psutil.Process(os.getpid())
        self.current_process.cpu_percent() # Primeira chamada para calibrar o psutil
        
        self.update_sys_monitor()
        
        self.tray_icon = None

    def update_sys_monitor(self):
        try:
            # Consumo exclusivo deste programa
            cores = psutil.cpu_count() or 1
            cpu = self.current_process.cpu_percent() / cores
            ram_mb = self.current_process.memory_info().rss / (1024 * 1024)
            
            self.lbl_cpu.configure(text=f"App CPU: {cpu:.1f}%")
            self.lbl_ram.configure(text=f"App RAM: {ram_mb:.1f} MB")
            self.lbl_gpu.configure(text="App GPU: 0%") # Tkinter não possui renderização por GPU
        except Exception as e:
            logger.error(f"Erro no monitor de sistema: {e}")
        self.after(2000, self.update_sys_monitor)

    def hide_window(self):
        self.withdraw()
        image = Image.new('RGB', (64, 64), color = (73, 109, 137))
        menu = (item('Restaurar', self.show_window), item('Sair', self.quit_window))
        self.tray_icon = pystray.Icon("name", image, "DriveDownloader", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def show_window(self, icon, item):
        self.tray_icon.stop()
        self.after(0, self.deiconify)

    def quit_window(self, icon, item):
        self.tray_icon.stop()
        self.quit()

    def show_error(self, exc, val, tb):
        logger.error("Erro na Interface (Tkinter Crash):", exc_info=(exc, val, tb))
        import traceback
        erro_msg = "".join(traceback.format_exception(exc, val, tb))
        # Tentativa segura de mostrar caixa de erro sem travar o loop principal
        try:
            CTkMessagebox(title="Erro Fatal na Interface", message=f"Ocorreu um erro interno.\nConsulte o arquivo app.log para mais detalhes.\n\nResumo:\n{str(val)}", icon="cancel")
        except:
            pass

    def prev_page(self):
        if self.queue_page > 0:
            self.queue_page -= 1
            self.render_queue_page()

    def next_page(self):
        max_page = len(self.queue_data) // self.queue_page_size
        if self.queue_page < max_page:
            self.queue_page += 1
            self.render_queue_page()
            
    def render_queue_page(self):
        tree = self.trees["queue"]
        for item in tree.get_children():
            tree.delete(item)
            
        start = self.queue_page * self.queue_page_size
        end = min(start + self.queue_page_size, len(self.queue_data))
        
        for file_id, filename, filepath, status, tamanho, progresso in self.queue_data[start:end]:
            iid = tree.insert("", "end", values=(file_id, filename, tamanho, status, progresso))
            self.file_labels[file_id] = {"tree": "queue", "iid": iid, "filepath": filepath}
            
        self.lbl_page.configure(text=f"Pág {self.queue_page + 1}")

    def on_analyze_finish(self, arquivos_para_baixar, msg, color, has_files):
        self.info_label.configure(text=msg, text_color=color)
        if has_files:
            self.action_button.configure(state="normal", text="📥", fg_color="#10b981", hover_color="#059669")
        else:
            self.action_button.configure(state="disabled", text="✔️")
        self.analyze_btn.configure(state="normal", text="🔍")

    def on_download_progress(self, count, total):
        self.progress_bar.set(count / total if total else 0)
        self.progress_label.configure(text=f"Progresso Total: {count} / {total}")

    def on_download_finish(self, is_paused, log_entries):
        self.global_updater_running = False
        if is_paused:
            self.action_button.configure(state="normal", text="▶️", fg_color="#28a745", hover_color="#218838")
            self.info_label.configure(text="Processo Pausado.", text_color="#ffc107")
        else:
            if self.gerar_relatorio_ativo.get():
                try:
                    with open(os.path.join(self.pasta_destino, "relatorio_downloads.txt"), "w") as f:
                        f.write("\n".join(log_entries))
                except: pass
            self.action_button.configure(state="normal", text="⬇️", fg_color="#10b981")
            self.info_label.configure(text="Todos os downloads concluídos!", text_color="#28a745")
            try: winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS)
            except: pass
            try: notification.notify(title="Concluído", message="Downloads finalizados.", timeout=5)
            except: pass
            
        self.url_entry.configure(state="normal")
        self.filtro_combo.configure(state="normal")
        self.ordem_combo.configure(state="normal")
        self.folder_btn.configure(state="normal")
        self.clear_folder_btn.configure(state="normal")

    def update_global_stats(self):
        if not self.global_updater_running: return
        current_time = time.time()
        elapsed = current_time - self.last_global_time
        if elapsed >= 1.0:
            with self.core.lock:
                bytes_diff = self.core.total_bytes_downloaded - self.last_global_bytes
                speed = bytes_diff / elapsed if elapsed > 0 else 0
                self.last_global_bytes = self.core.total_bytes_downloaded
                self.last_global_time = current_time
                
                downloaded_mb = self.core.total_bytes_downloaded / (1024 * 1024)
                
                # ETA calculation
                eta = "--"
                if speed > 0 and self.core.arquivos_para_baixar:
                    # Very rough global ETA based on remaining files (assuming avg 50MB per file as fallback)
                    # For a real global ETA we need total bytes of all files, which Drive doesn't always provide easily.
                    # We will show speed instead.
                    pass
                
                speed_str = f"{speed / (1024 * 1024):.1f} MB/s" if speed > 1024*1024 else f"{speed / 1024:.1f} KB/s"
                self.global_stats_label.configure(text=f"Baixado: {downloaded_mb:.1f} MB | Vel: {speed_str}")
                
        self.after(1000, self.update_global_stats)

    def atualizar_status(self, file_id, status_text, color, frame_color, is_highlighted, is_completed, is_failed, is_existing, progresso):
        # Encontrar arquivo
        target = None
        target_idx = -1
        for i, item in enumerate(self.queue_data):
            if item[0] == file_id:
                target = item
                target_idx = i
                break
                
        if target:
            # Atualiza lista virtual
            new_item = (target[0], target[1], target[2], status_text, target[4], progresso if progresso else target[5])
            self.queue_data[target_idx] = new_item
            
            # Se a linha atual esta na pagina atual, atualiza a Tree diretamente
            start = self.queue_page * self.queue_page_size
            end = start + self.queue_page_size
            if start <= target_idx < end and file_id in self.file_labels:
                iid = self.file_labels[file_id]["iid"]
                tree = self.trees[self.file_labels[file_id]["tree"]]
                vals = list(tree.item(iid, "values"))
                vals[3] = status_text
                if progresso: vals[4] = progresso
                tree.item(iid, values=vals)

            new_tree_key = "queue"
            if is_completed: new_tree_key = "completed"
            elif is_existing: new_tree_key = "exists"
            elif is_failed: new_tree_key = "failed"
            
            if new_tree_key != "queue":
                # Remove da queue_data virtual e joga pro final
                popped = self.queue_data.pop(target_idx)
                self.counts["queue"] -= 1
                self.counts[new_tree_key] += 1
                
                # Para abas normais (completed, exists, failed), adiciona direto na Tree (sao menos atualizadas simultaneamente)
                tree = self.trees[new_tree_key]
                new_iid = tree.insert("", "end", values=(popped[0], popped[1], popped[4], popped[3], popped[5]))
                self.file_labels[file_id] = {"tree": new_tree_key, "iid": new_iid, "filepath": popped[2]}
                
                self.update_tabs()
                self.render_queue_page() # re-render queue

    def bulk_add_rows(self, data_list, target_tree_key):
        if target_tree_key == "queue":
            for f in data_list:
                self.queue_data.append((f[0], f[1], f[2], f[3], f[4], "0%"))
            self.counts["queue"] += len(data_list)
            self.render_queue_page()
        else:
            tree = self.trees[target_tree_key]
            for file_id, filename, filepath, status, tamanho in data_list:
                iid = tree.insert("", "end", values=(file_id, filename, tamanho, status, "0%"))
                self.file_labels[file_id] = {"tree": target_tree_key, "iid": iid, "filepath": filepath}
            self.counts[target_tree_key] += len(data_list)
            
        self.update_tabs()

    def update_tabs(self):
        for k in self.tab_names:
            base = "Fila" if k == "queue" else "Concluídos" if k == "completed" else "Já Existentes" if k == "exists" else "Falhas"
            new_name = f"{base} ({self.counts[k]})"
            try:
                self.tabview.rename(self.tab_names[k], new_name)
                self.tab_names[k] = new_name
            except Exception: pass

    def handle_analyze_only(self):
        self.analyze_btn.configure(state="disabled", text="⏳")
        self.action_button.configure(state="disabled")
        self.iniciar_analise(False)

    def handle_action(self):
        txt = self.action_button.cget("text")
        if txt == "⬇️":
            self.analyze_btn.configure(state="disabled")
            self.action_button.configure(state="disabled", text="⏳")
            self.iniciar_analise(True)
        elif txt in ["📥", "▶️"]:
            self.comecar_download()
        elif txt == "⏸️":
            self.core.pause_download()
            self.action_button.configure(state="disabled", text="⏳")

    def iniciar_analise(self, auto_download):
        url = self.url_entry.get().strip()
        if not url:
            self.info_label.configure(text="URL inválida.", text_color="#dc3545")
            return
            
        self.salvar_historico(url)
        self.info_label.configure(text="Analisando link...\nAguarde.", text_color="white")
        
        self.queue_data.clear()
        self.file_labels.clear()
        for k in self.trees:
            self.trees[k].delete(*self.trees[k].get_children())
            self.counts[k] = 0
            
        self.update_tabs()
        self.progress_frame.grid_remove()
        
        self.core.config(self.max_workers, self.extrair_zip_var.get(), self.pasta_destino)
        
        if auto_download:
            # Sobrescreve callback de finish para iniciar download direto se sucesso
            def hooked(arquivos, msg, color, has_files):
                self.after(0, self.on_analyze_finish, arquivos, msg, color, has_files)
                if has_files: 
                    self.after(0, self.comecar_download)
            self.core.callbacks['on_analyze_finish'] = hooked
        else:
            self.core.callbacks['on_analyze_finish'] = self.safe_analyze_finish

        self.core.start_analysis(url, self.filtro_var.get(), self.ordem_var.get())

    def comecar_download(self):
        self.url_entry.configure(state="disabled")
        self.filtro_combo.configure(state="disabled")
        self.ordem_combo.configure(state="disabled")
        self.folder_btn.configure(state="disabled")
        self.clear_folder_btn.configure(state="disabled")
        
        self.action_button.configure(state="normal", text="⏸️", fg_color="#ffc107")
        self.progress_frame.grid()
        self.progress_label.configure(text=f"Progresso Total: {self.core.archived_count} / {len(self.core.arquivos_para_baixar)}")
        
        self.global_updater_running = True
        self.last_global_time = time.time()
        self.update_global_stats()
        
        self.core.start_download()

    def login_google(self):
        self.login_btn.configure(text="Autenticando...", state="disabled")
        self.update()
        if self.core.auth_google():
            self.login_btn.configure(text="Logado ✅", fg_color="#28a745", hover_color="#218838")
            CTkMessagebox(title="Sucesso", message="Autenticação com Google bem-sucedida!", icon="check")
        else:
            self.login_btn.configure(text="Google Login", state="normal")
            CTkMessagebox(title="Erro", message="Falha ao autenticar. Verifique o credentials.json", icon="cancel")

    def carregar_historico(self):
        return database.get_recent_urls(5)

    def salvar_historico(self, url):
        database.add_to_history(url, "Desconhecido", "", "Analisado", "0 B")
        self.historico = database.get_recent_urls(5)
        self.url_entry.configure(values=self.historico)

    def escolher_pasta(self):
        folder = filedialog.askdirectory(initialdir=self.pasta_destino)
        if folder:
            self.pasta_destino = folder
            self.folder_path_var.set(self.pasta_destino)

    def abrir_pasta(self):
        if os.path.exists(self.pasta_destino):
            os.startfile(self.pasta_destino)

    def limpar_pasta(self):
        if not os.path.exists(self.pasta_destino): return
        msg = CTkMessagebox(title="Confirmar", message=f"Apagar TUDO em\n{self.pasta_destino}?", icon="warning", option_1="Não", option_2="Sim")
        if msg.get() == "Sim":
            self.clear_folder_btn.configure(state="disabled")
            threading.Thread(target=self._limpar_pasta_thread).start()
            
    def _limpar_pasta_thread(self):
        try:
            for filename in os.listdir(self.pasta_destino):
                fp = os.path.join(self.pasta_destino, filename)
                if os.path.isfile(fp) or os.path.islink(fp): os.unlink(fp)
                elif os.path.isdir(fp): shutil.rmtree(fp)
            self.after(0, lambda: CTkMessagebox(title="Sucesso", message="Pasta limpa.", icon="check"))
        except Exception as e:
            self.after(0, lambda: CTkMessagebox(title="Erro", message=str(e), icon="cancel"))
        finally:
            self.after(0, lambda: self.clear_folder_btn.configure(state="normal"))

    def abrir_configuracoes(self):
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.focus()
            return
        self.settings_window = ctk.CTkToplevel(self)
        self.settings_window.title("Configurações")
        self.settings_window.geometry("400x350")
        
        lbl_tema = ctk.CTkLabel(self.settings_window, text="Modo Escuro:", font=ctk.CTkFont(weight="bold"))
        lbl_tema.grid(row=0, column=0, padx=20, pady=20, sticky="w")
        self.theme_switch = ctk.CTkSwitch(self.settings_window, text="", command=lambda: ctk.set_appearance_mode("Dark") if self.theme_switch.get() else ctk.set_appearance_mode("Light"))
        self.theme_switch.grid(row=0, column=1, padx=20, pady=20, sticky="e")
        if ctk.get_appearance_mode() == "Dark": self.theme_switch.select()
            
        lbl_relat = ctk.CTkLabel(self.settings_window, text="Gerar Relatório TXT:", font=ctk.CTkFont(weight="bold"))
        lbl_relat.grid(row=1, column=0, padx=20, pady=10, sticky="w")
        self.report_switch = ctk.CTkSwitch(self.settings_window, text="", variable=self.gerar_relatorio_ativo)
        self.report_switch.grid(row=1, column=1, padx=20, pady=10, sticky="e")
        
        lbl_zip = ctk.CTkLabel(self.settings_window, text="Extrair arquivos ZIP:", font=ctk.CTkFont(weight="bold"))
        lbl_zip.grid(row=2, column=0, padx=20, pady=10, sticky="w")
        self.zip_switch = ctk.CTkSwitch(self.settings_window, text="", variable=self.extrair_zip_var)
        self.zip_switch.grid(row=2, column=1, padx=20, pady=10, sticky="e")
            
        lbl_simult = ctk.CTkLabel(self.settings_window, text="Downloads Simultâneos:", font=ctk.CTkFont(weight="bold"))
        lbl_simult.grid(row=3, column=0, padx=20, pady=10, sticky="w", columnspan=2)
        
        self.simult_slider = ctk.CTkSlider(self.settings_window, from_=1, to=20, number_of_steps=19, command=lambda v: self.simult_label.configure(text=f"{int(v)} arquivo(s)"))
        self.simult_slider.grid(row=4, column=0, padx=20, pady=5, sticky="ew", columnspan=2)
        self.simult_slider.set(self.max_workers)
        
        self.simult_label = ctk.CTkLabel(self.settings_window, text=f"{self.max_workers} arquivo(s)")
        self.simult_label.grid(row=5, column=0, padx=20, pady=(0, 20), columnspan=2)
        
        def save():
            self.max_workers = int(self.simult_slider.get())
            self.core.config(self.max_workers, self.extrair_zip_var.get(), self.pasta_destino)
            self.settings_window.destroy()
            
        ctk.CTkButton(self.settings_window, text="Salvar", command=save).grid(row=6, column=0, columnspan=2, pady=10)

    def on_tree_double_click(self, event):
        tree = event.widget
        selected = tree.selection()
        if not selected: return
        file_id = tree.item(selected[0], "values")[0]
        if file_id in self.file_labels:
            filepath = self.file_labels[file_id]["filepath"]
            if os.path.exists(filepath): os.startfile(filepath)
            else:
                import webbrowser
                webbrowser.open(f"https://drive.google.com/uc?export=download&id={file_id}")

    def mostrar_menu_fila(self, event):
        try:
            # Seleciona o item onde o usuario clicou (opcional, melhora a UX)
            iid = self.trees["queue"].identify_row(event.y)
            if iid:
                # Se não estiver nos selecionados, limpa seleção e seleciona ele
                if iid not in self.trees["queue"].selection():
                    self.trees["queue"].selection_set(iid)
                    
            if self.trees["queue"].selection():
                self.queue_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.queue_menu.grab_release()

    def excluir_da_fila(self):
        tree = self.trees["queue"]
        selected = tree.selection()
        if not selected: return
        
        ids_to_remove = []
        for item in selected:
            file_id = tree.item(item, "values")[0]
            ids_to_remove.append(file_id)
            if file_id in self.file_labels:
                del self.file_labels[file_id]
                
        # Atualizar Fila Virtual
        self.queue_data = [item for item in self.queue_data if item[0] not in ids_to_remove]
        self.counts["queue"] = len(self.queue_data)
        self.update_tabs()
        
        # Corrigir paginacao se remover itens
        max_page = max(0, (len(self.queue_data) - 1)) // self.queue_page_size
        if self.queue_page > max_page:
            self.queue_page = max_page
            
        self.render_queue_page()
        
        # Remover do Core
        self.core.remove_from_queue(ids_to_remove)
        if hasattr(self.core, 'arquivos_para_baixar'):
            self.progress_label.configure(text=f"Progresso Total: {self.core.archived_count} / {len(self.core.arquivos_para_baixar)}")

    def reordenar_fila(self, acao):
        tree = self.trees["queue"]
        selected = tree.selection()
        if not selected: return
        
        selected_ids = [tree.item(i, "values")[0] for i in selected]
        
        indices = []
        for i, item in enumerate(self.queue_data):
            if item[0] in selected_ids:
                indices.append(i)
                
        if not indices: return
        itens_selecionados = [self.queue_data[i] for i in indices]
        
        for i in reversed(indices):
            self.queue_data.pop(i)
            
        if acao == "topo":
            self.queue_data = itens_selecionados + self.queue_data
        elif acao == "fim":
            self.queue_data = self.queue_data + itens_selecionados
        elif acao == "cima":
            min_idx = min(indices)
            novo_idx = max(0, min_idx - 1)
            for item in reversed(itens_selecionados):
                self.queue_data.insert(novo_idx, item)
        elif acao == "baixo":
            max_idx = max(indices)
            novo_idx = min(len(self.queue_data), max_idx + 1 - len(itens_selecionados) + 1)
            for item in reversed(itens_selecionados):
                self.queue_data.insert(novo_idx, item)
                
        self.render_queue_page()
        
        # Selecionar itens novamente
        for iid in tree.get_children():
            if tree.item(iid, "values")[0] in selected_ids:
                tree.selection_add(iid)
                
        self.sincronizar_fila_core()
        
    def sincronizar_fila_core(self):
        ordered_ids = [item[0] for item in self.queue_data]
        self.core.update_queue_order(ordered_ids)

    def reiniciar_falhas(self):
        if self.counts["failed"] == 0:
            CTkMessagebox(title="Aviso", message="Não há falhas para reiniciar.", icon="info")
            return
            
        # Limpa arvore de falhas
        for item in self.trees["failed"].get_children():
            self.trees["failed"].delete(item)
        self.counts["failed"] = 0
        
        self.core.retry_failed()
        
        # Reconstroi fila virtual da interface com base no Core atual
        self.queue_data = []
        self.counts["queue"] = 0
        for arquivo in self.core.arquivos_para_baixar:
            nome_arquivo = os.path.basename(arquivo.local_path) if getattr(arquivo, 'local_path', None) else arquivo.id
            tamanho = self.core._format_size(os.path.getsize(arquivo.local_path)) if os.path.exists(arquivo.local_path) else "Desconhecido"
            self.queue_data.append((arquivo.id, nome_arquivo, arquivo.local_path, "⏳ Aguardando", tamanho, "0%"))
            self.counts["queue"] += 1
            
        self.queue_page = 0
        self.update_tabs()
        self.render_queue_page()
        
        # Inicia download
        self.comecar_download()

# --- END OF ui.py ---

# --- START OF main.py ---

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

# --- END OF main.py ---
