import flet as ft
import os
import gdown
import threading
import concurrent.futures
import time
import zipfile
import json
from datetime import datetime
import shutil

HISTORY_FILE = "history.json"

class DriveDownloaderMobile:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Drive Downloader Pro"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.window_width = 400
        self.page.window_height = 750
        self.page.padding = 15
        self.page.scroll = "auto"
        
        # Estado
        self.pasta_destino = os.path.expanduser("~/Downloads/Fotos_Drive")
        self.historico = self.carregar_historico()
        
        self.arquivos_para_baixar = []
        self.file_controls = {} # file_id -> row_control
        self.is_downloading = False
        self.cancel_event = threading.Event()
        self.lock = threading.Lock()
        self.archived_count = 0
        self.log_entries = []
        
        # Configurações
        self.max_workers = 4
        self.gerar_relatorio = True
        self.extrair_zip = True
        
        self.build_ui()
        
    def carregar_historico(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r") as f:
                    return json.load(f)
            except:
                pass
        return []

    def salvar_historico(self, url):
        if url in self.historico:
            self.historico.remove(url)
        self.historico.insert(0, url)
        self.historico = self.historico[:5]
        try:
            with open(HISTORY_FILE, "w") as f:
                json.dump(self.historico, f)
        except:
            pass

    def build_ui(self):
        # 1. Componentes Flet
        # Pickers e Dialogs
        self.file_picker = ft.FilePicker(on_result=self.on_folder_selected)
        self.page.overlay.append(self.file_picker)
        
        # Cabeçalho
        title = ft.Text("🚀 Drive Downloader", size=24, weight=ft.FontWeight.BOLD)
        subtitle = ft.Text("Filtros e Gerenciamento Inteligente.", color=ft.colors.GREY_400, italic=True)
        
        # Destino
        self.folder_text = ft.TextField(
            label="Destino", value=self.pasta_destino, expand=True, read_only=True
        )
        btn_folder = ft.IconButton(icon=ft.icons.FOLDER_OPEN, tooltip="Procurar Pasta", on_click=lambda _: self.file_picker.get_directory_path())
        btn_settings = ft.IconButton(icon=ft.icons.SETTINGS, tooltip="Opções", on_click=self.abrir_configuracoes)
        folder_row = ft.Row([self.folder_text, btn_folder, btn_settings])
        
        # URL Input
        self.url_input = ft.TextField(label="Link do Google Drive", value=self.historico[0] if self.historico else "")
        self.btn_analyze = ft.ElevatedButton("🔍 Analisar", expand=True, on_click=self.analyze_link_click)
        self.btn_download = ft.ElevatedButton("⬇️ Iniciar", expand=True, color=ft.colors.WHITE, bgcolor=ft.colors.GREEN_600, disabled=True, on_click=self.toggle_download)
        
        # Filtros
        self.filter_type = ft.Dropdown(
            label="Tipo", options=[ft.dropdown.Option("Todos"), ft.dropdown.Option("Imagens"), ft.dropdown.Option("Vídeos"), ft.dropdown.Option("Documentos")],
            value="Todos", expand=True
        )
        self.sort_order = ft.Dropdown(
            label="Ordenar", options=[ft.dropdown.Option("Nome (A-Z)"), ft.dropdown.Option("Nome (Z-A)"), ft.dropdown.Option("Padrão (Drive)")],
            value="Nome (A-Z)", expand=True
        )
        filters_row = ft.Row([self.filter_type, self.sort_order])
        
        self.info_label = ft.Text("Selecione o destino, um filtro e cole o link para começar.", color=ft.colors.BLUE_200, text_align=ft.TextAlign.CENTER)
        
        # Tabs de Fila e Concluídos
        self.queue_list = ft.ListView(expand=True, spacing=10, height=250)
        self.completed_list = ft.ListView(expand=True, spacing=10, height=250)
        self.exists_list = ft.ListView(expand=True, spacing=10, height=250)
        self.failed_list = ft.ListView(expand=True, spacing=10, height=250)
        
        self.tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(text="Fila", content=self.queue_list),
                ft.Tab(text="Concluídos", content=self.completed_list),
                ft.Tab(text="Já Existentes", content=self.exists_list),
                ft.Tab(text="Falhas", content=self.failed_list),
            ],
            height=300
        )
        
        # Progresso Global
        self.progress_bar = ft.ProgressBar(value=0, visible=False)
        self.progress_text = ft.Text("Progresso: 0%", visible=False, weight=ft.FontWeight.BOLD)
        
        # Adicionar tudo à página
        self.page.add(
            title, subtitle, 
            ft.Divider(height=10, color=ft.colors.TRANSPARENT),
            folder_row, 
            self.url_input,
            ft.Row([self.btn_analyze, self.btn_download]),
            filters_row,
            self.info_label,
            self.progress_text,
            self.progress_bar,
            self.tabs
        )
        
    def show_snackbar(self, msg, color=ft.colors.GREEN):
        self.page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=color)
        self.page.snack_bar.open = True
        self.page.update()

    def on_folder_selected(self, e: ft.FilePickerResultEvent):
        if e.path:
            self.pasta_destino = e.path
            self.folder_text.value = e.path
            self.folder_text.update()

    def abrir_configuracoes(self, e):
        # BottomSheet para configurações
        theme_switch = ft.Switch(label="Modo Escuro", value=(self.page.theme_mode == ft.ThemeMode.DARK), on_change=self.toggle_theme)
        zip_switch = ft.Switch(label="Extrair arquivos ZIP", value=self.extrair_zip, on_change=lambda e: setattr(self, 'extrair_zip', e.control.value))
        relatorio_switch = ft.Switch(label="Gerar Relatório TXT", value=self.gerar_relatorio, on_change=lambda e: setattr(self, 'gerar_relatorio', e.control.value))
        
        simult_slider = ft.Slider(min=1, max=10, divisions=9, value=self.max_workers, label="{value} arquivos por vez", on_change=lambda e: setattr(self, 'max_workers', int(e.control.value)))

        bs = ft.BottomSheet(
            ft.Container(
                padding=20,
                content=ft.Column(
                    [
                        ft.Text("⚙️ Configurações", size=20, weight=ft.FontWeight.BOLD),
                        theme_switch,
                        zip_switch,
                        relatorio_switch,
                        ft.Text("Downloads Simultâneos (1 a 10):"),
                        simult_slider
                    ],
                    tight=True,
                ),
            )
        )
        self.page.overlay.append(bs)
        bs.open = True
        self.page.update()

    def toggle_theme(self, e):
        self.page.theme_mode = ft.ThemeMode.DARK if e.control.value else ft.ThemeMode.LIGHT
        self.page.update()

    def filtrar_arquivos(self, arquivos):
        filtro = self.filter_type.value
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

    def analyze_link_click(self, e):
        url = self.url_input.value.strip()
        if not url:
            self.info_label.value = "❌ URL inválida."
            self.info_label.color = ft.colors.RED_400
            self.info_label.update()
            return
            
        self.btn_analyze.disabled = True
        self.btn_download.disabled = True
        self.info_label.value = "🔍 Analisando link... Aguarde."
        self.info_label.color = ft.colors.WHITE
        self.queue_list.controls.clear()
        self.completed_list.controls.clear()
        self.exists_list.controls.clear()
        self.failed_list.controls.clear()
        self.file_controls.clear()
        self.page.update()
        
        thread = threading.Thread(target=self.analyze_link, args=(url,))
        thread.start()

    def analyze_link(self, url):
        os.makedirs(self.pasta_destino, exist_ok=True)
        try:
            url_lower = url.lower()
            if "folder" in url_lower or "drive.google.com/drive/folders/" in url_lower:
                arquivos_brutos = gdown.download_folder(url, output=self.pasta_destino, quiet=True, skip_download=True)
            else:
                res = gdown.download(url, output=self.pasta_destino, quiet=True, skip_download=True)
                class SingleFile:
                    def __init__(self, f_id, path):
                        self.id = f_id
                        self.local_path = path if path else os.path.join(self.pasta_destino, 'downloaded_file')
                file_id = url.split("id=")[1].split("&")[0] if "id=" in url else url.split("/d/")[1].split("/")[0] if "/d/" in url else url
                arquivos_brutos = [SingleFile(file_id, getattr(res, 'path', str(res) if res else None))] if res else []
                
            self.arquivos_para_baixar = self.filtrar_arquivos(arquivos_brutos)
            
            if not self.arquivos_para_baixar:
                self.info_label.value = "⚠️ Nenhum arquivo encontrado."
                self.info_label.color = ft.colors.AMBER_400
                self.btn_analyze.disabled = False
                self.page.update()
            else:
                self.salvar_historico(url)
                
                ordem = self.sort_order.value
                if ordem == "Nome (A-Z)":
                    self.arquivos_para_baixar.sort(key=lambda x: getattr(x, 'path', '').lower() if hasattr(x, 'path') else "")
                elif ordem == "Nome (Z-A)":
                    self.arquivos_para_baixar.sort(key=lambda x: getattr(x, 'path', '').lower() if hasattr(x, 'path') else "", reverse=True)
                
                for i, arquivo in enumerate(self.arquivos_para_baixar):
                    nome_arquivo = os.path.basename(arquivo.local_path) if getattr(arquivo, 'local_path', None) else f"Arquivo_{i}"
                    self.add_file_row(arquivo.id, nome_arquivo, arquivo.local_path)
                
                total = len(self.arquivos_para_baixar)
                self.info_label.value = f"✅ Análise Concluída! {total} arquivo(s)."
                self.info_label.color = ft.colors.GREEN_400
                self.btn_analyze.disabled = False
                self.btn_download.disabled = False
                self.btn_download.text = "⬇️ Iniciar"
                self.page.update()
                
        except Exception as e:
            self.info_label.value = f"❌ Erro na análise:\n{e}"
            self.info_label.color = ft.colors.RED_400
            self.btn_analyze.disabled = False
            self.page.update()

    def add_file_row(self, file_id, filename, filepath, is_completed=False, initial_status="⏳ Aguardando"):
        status_text = ft.Text(initial_status, size=12, weight=ft.FontWeight.BOLD, color=ft.colors.WHITE, width=120)
        name_text = ft.Text(filename, size=12, expand=True)
        
        def open_file_or_link(e):
            if os.path.exists(filepath):
                os.startfile(filepath)
            else:
                import webbrowser
                webbrowser.open(f"https://drive.google.com/uc?export=download&id={file_id}")
                
        btn_open = ft.IconButton(
            icon=ft.icons.OPEN_IN_NEW, 
            tooltip="Abrir arquivo local ou no Drive", 
            icon_color=ft.colors.BLUE_400,
            on_click=open_file_or_link
        )
        
        row_frame = ft.Container(
            content=ft.Row([status_text, name_text, btn_open]),
            padding=10,
            bgcolor=ft.colors.GREY_900,
            border_radius=8
        )
        
        self.file_controls[file_id] = (status_text, row_frame, name_text, filename, filepath)
        
        if is_completed:
            self.completed_list.controls.append(row_frame)
        else:
            self.queue_list.controls.append(row_frame)

    def toggle_download(self, e):
        if not self.is_downloading:
            self.start_download()
        else:
            self.pause_download()

    def start_download(self):
        self.is_downloading = True
        self.cancel_event.clear()
        
        if self.archived_count == 0 or self.archived_count == len(self.arquivos_para_baixar):
            self.log_entries = []
            self.archived_count = 0
            
        self.btn_analyze.disabled = True
        self.btn_download.text = "⏸️ Pausar"
        self.btn_download.bgcolor = ft.colors.AMBER_600
        
        self.progress_bar.visible = True
        self.progress_text.visible = True
        self.progress_text.value = f"Progresso Total: {self.archived_count} / {len(self.arquivos_para_baixar)}"
        self.page.update()
        
        thread = threading.Thread(target=self.download_files)
        thread.start()

    def pause_download(self):
        self.cancel_event.set()
        self.btn_download.disabled = True
        self.btn_download.text = "Pausando..."
        self.page.update()

    def atualizar_status(self, file_id, status_str, color, is_completed=False, is_failed=False, is_existing=False):
        if file_id in self.file_controls:
            status_text, row_frame, name_text, filename, filepath = self.file_controls[file_id]
            
            if is_completed and row_frame in self.queue_list.controls:
                self.queue_list.controls.remove(row_frame)
                self.completed_list.controls.append(row_frame)
            elif is_existing and row_frame in self.queue_list.controls:
                self.queue_list.controls.remove(row_frame)
                self.exists_list.controls.append(row_frame)
            elif is_failed and row_frame in self.queue_list.controls:
                self.queue_list.controls.remove(row_frame)
                self.failed_list.controls.append(row_frame)
            
            status_text.value = status_str
            status_text.color = color
            self.page.update()

    def download_worker(self, arquivo):
        nome_arquivo = os.path.basename(arquivo.local_path)
        
        if self.cancel_event.is_set():
            self.atualizar_status(arquivo.id, "⏸️ Pausado", ft.colors.AMBER)
            return
            
        local_state = {'last_time': time.time(), 'last_bytes': 0}
        
        def custom_progress(bytes_so_far, bytes_total):
            if self.cancel_event.is_set():
                raise Exception("Pausado pelo usuário")
                
            current_time = time.time()
            elapsed = current_time - local_state['last_time']
            
            if elapsed > 0.5:
                speed = (bytes_so_far - local_state['last_bytes']) / elapsed if elapsed > 0 else 0
                local_state['last_bytes'] = bytes_so_far
                local_state['last_time'] = current_time
                
                speed_str = f"{speed / (1024 * 1024):.1f} MB/s" if speed > 1024 * 1024 else f"{speed / 1024:.1f} KB/s"
                percentage = (bytes_so_far / bytes_total * 100) if bytes_total else 0
                
                status_text = f"🔄 {percentage:.0f}% | {speed_str}" if percentage > 0 else f"🔄 {speed_str}"
                self.atualizar_status(arquivo.id, status_text, ft.colors.CYAN)
        
        sucesso = False
        ultimo_erro = "Desconhecido"
        for tentativa in range(3):
            if self.cancel_event.is_set():
                break
            try:
                if tentativa > 0:
                    self.atualizar_status(arquivo.id, f"⚠️ Tentando ({tentativa+1}/3)", ft.colors.AMBER)
                    time.sleep(3) 
                    
                self.atualizar_status(arquivo.id, "🔄 Baixando...", ft.colors.CYAN)
                gdown.download(id=arquivo.id, url=arquivo.id if "http" in arquivo.id else None, output=arquivo.local_path, quiet=True, progress=custom_progress, resume=True)
                
                self.atualizar_status(arquivo.id, "✅ Concluído", ft.colors.GREEN, is_completed=True)
                self.log_entries.append(f"SUCESSO: {nome_arquivo}")
                sucesso = True
                
                if self.extrair_zip and arquivo.local_path.lower().endswith('.zip'):
                    self.atualizar_status(arquivo.id, "📦 Extraindo ZIP...", ft.colors.CYAN)
                    try:
                        extract_path = os.path.splitext(arquivo.local_path)[0]
                        with zipfile.ZipFile(arquivo.local_path, 'r') as zip_ref:
                            zip_ref.extractall(extract_path)
                        self.atualizar_status(arquivo.id, "✅ Extraído", ft.colors.GREEN)
                    except Exception as e:
                        self.atualizar_status(arquivo.id, "⚠️ Erro no ZIP", ft.colors.AMBER)
                break
            except Exception as e:
                if "Pausado" in str(e):
                    break
                else:
                    ultimo_erro = str(e).replace('\n', ' ')
                    continue 
                    
        if not sucesso:
            if self.cancel_event.is_set():
                self.atualizar_status(arquivo.id, "⏸️ Pausado", ft.colors.AMBER)
            elif os.path.exists(arquivo.local_path) and os.path.getsize(arquivo.local_path) > 0:
                self.atualizar_status(arquivo.id, "✅ Já existe", ft.colors.GREEN, is_completed=False, is_failed=False, is_existing=True)
                self.log_entries.append(f"JÁ EXISTE: {nome_arquivo}")
                sucesso = True
            else:
                erro_curto = ultimo_erro[:30] + "..." if len(ultimo_erro) > 30 else ultimo_erro
                self.atualizar_status(arquivo.id, f"❌ Erro: {erro_curto}", ft.colors.RED, is_completed=False, is_failed=True)
                self.log_entries.append(f"FALHA [Motivo: {ultimo_erro}]: {nome_arquivo}")

        if sucesso or (not sucesso and not self.cancel_event.is_set()):
            with self.lock:
                self.archived_count += 1
                p = self.archived_count / len(self.arquivos_para_baixar)
                self.progress_bar.value = p
                self.progress_text.value = f"Progresso Total: {self.archived_count} / {len(self.arquivos_para_baixar)}"
                self.page.update()

    def gerar_relatorio_txt(self):
        if not self.gerar_relatorio:
            return
        filepath = os.path.join(self.pasta_destino, "relatorio_downloads.txt")
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"Relatório de Download - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
                f.write("="*60 + "\n\n")
                for entry in self.log_entries:
                    f.write(entry + "\n")
        except:
            pass

    def download_files(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self.download_worker, arg) for arg in self.arquivos_para_baixar]
            concurrent.futures.wait(futures)
            
        self.gerar_relatorio_txt()
        self.is_downloading = False
        
        if self.cancel_event.is_set():
            self.show_snackbar("Download Pausado.", ft.colors.AMBER_600)
            self.info_label.value = "⏸️ Processo Pausado."
            self.info_label.color = ft.colors.AMBER
            self.btn_download.disabled = False
            self.btn_download.text = "▶️ Retomar"
            self.btn_download.bgcolor = ft.colors.GREEN_600
        else:
            self.show_snackbar(f"{len(self.arquivos_para_baixar)} arquivos processados.", ft.colors.GREEN_600)
            self.info_label.value = "✨ Todos os downloads concluídos!\nRelatório salvo (se ativado)."
            self.info_label.color = ft.colors.GREEN
            self.btn_download.disabled = False
            self.btn_download.text = "⬇️ Iniciar"
            self.btn_download.bgcolor = ft.colors.GREEN_600
            self.btn_analyze.disabled = False
            self.archived_count = 0
            
        self.page.update()

def main(page: ft.Page):
    app = DriveDownloaderMobile(page)

if __name__ == '__main__':
    ft.app(target=main)
