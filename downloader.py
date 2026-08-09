import os
import threading
import time
import zipfile
import concurrent.futures
import gdown
from utils import logger

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
            if "folder" in url_lower or "drive.google.com/drive/folders/" in url_lower:
                arquivos_brutos = gdown.download_folder(url, output=self.pasta_destino, quiet=True, skip_download=True)
            else:
                res = gdown.download(url, output=self.pasta_destino, quiet=True, skip_download=True)
                file_id = url.split("id=")[1].split("&")[0] if "id=" in url else url.split("/d/")[1].split("/")[0] if "/d/" in url else url
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
            
            for i, arquivo in enumerate(filtrados):
                nome_arquivo = os.path.basename(arquivo.local_path) if getattr(arquivo, 'local_path', None) else f"Arquivo_{i}"
                tamanho = self._format_size(os.path.getsize(arquivo.local_path)) if os.path.exists(arquivo.local_path) else "Desconhecido"
                
                if os.path.exists(arquivo.local_path) and os.path.getsize(arquivo.local_path) > 0:
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
                prog_text = f"{percentage:.0f}% | {speed_str}" if percentage > 0 else speed_str
                
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
                gdown.download(id=arquivo.id, url=arquivo.id if "http" in arquivo.id else None, output=arquivo.local_path, quiet=True, progress=custom_progress, resume=True)
                
                self.callbacks.get('update_status')(arquivo.id, "✅ Concluído", "#28a745", "#242424", False, True, False, False, "")
                self.log_entries.append(f"SUCESSO: {nome_arquivo}")
                self.completed_ids.add(arquivo.id)
                sucesso = True
                
                if self.extrair_zip and arquivo.local_path.lower().endswith('.zip'):
                    self.callbacks.get('update_status')(arquivo.id, "📦 Extraindo ZIP...", "#17a2b8", "#1f538d", True, False, False, False, "")
                    try:
                        extract_path = os.path.splitext(arquivo.local_path)[0]
                        with zipfile.ZipFile(arquivo.local_path, 'r') as zip_ref:
                            zip_ref.extractall(extract_path)
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
