import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import gdown
import os
import sys
import time
import json
import concurrent.futures
from datetime import datetime
import shutil
from plyer import notification

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

HISTORY_FILE = "history.json"

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Google Drive Downloader Pro")
        self.geometry("900x850")
        self.resizable(True, True)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(6, weight=1)

        self.title_label = ctk.CTkLabel(self, text="🚀 Google Drive Downloader Pro", font=ctk.CTkFont(size=26, weight="bold"))
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 5))
        
        self.subtitle_label = ctk.CTkLabel(self, text="Filtros, Auto-retry, e Gerenciamento Inteligente.", font=ctk.CTkFont(size=13, slant="italic"), text_color="gray")
        self.subtitle_label.grid(row=1, column=0, padx=20, pady=(0, 15))

        # Folder Selection Frame
        self.folder_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.folder_frame.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.folder_frame.grid_columnconfigure(1, weight=1)

        self.pasta_destino = os.path.expanduser("~/Downloads/Fotos_Drive")
        
        self.folder_label = ctk.CTkLabel(self.folder_frame, text="Destino:", font=ctk.CTkFont(weight="bold"))
        self.folder_label.grid(row=0, column=0, padx=(0, 5), sticky="w")
        
        self.folder_path_var = ctk.StringVar(value=self.pasta_destino)
        self.folder_path_label = ctk.CTkLabel(self.folder_frame, textvariable=self.folder_path_var, text_color="gray", anchor="w")
        self.folder_path_label.grid(row=0, column=1, padx=5, sticky="ew")
        
        self.folder_btn = ctk.CTkButton(self.folder_frame, text="Procurar Pasta", command=self.escolher_pasta, width=120)
        self.folder_btn.grid(row=0, column=2, padx=0)
        
        self.settings_btn = ctk.CTkButton(self.folder_frame, text="⚙️ Opções", command=self.abrir_configuracoes, width=100, fg_color="#6c757d", hover_color="#5a6268")
        self.settings_btn.grid(row=0, column=3, padx=(15, 0))

        # Input Frame (URL, Filter & Analyze)
        self.input_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.input_frame.grid(row=3, column=0, padx=20, pady=0, sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)
        
        self.historico = self.carregar_historico()
        self.url_entry = ctk.CTkComboBox(self.input_frame, values=self.historico, height=40)
        self.url_entry.grid(row=0, column=0, padx=(0, 10), pady=0, sticky="ew")
        self.url_entry.set(self.historico[0] if self.historico else "")

        self.analyze_button = ctk.CTkButton(self.input_frame, text="🔍 Analisar", command=self.analyze_link_thread, width=120, height=40, font=ctk.CTkFont(weight="bold"))
        self.analyze_button.grid(row=0, column=1, padx=(0, 10), pady=0)
        
        self.download_button = ctk.CTkButton(self.input_frame, text="⬇️ Iniciar Download", command=self.toggle_download, width=150, height=40, state="disabled", fg_color="#28a745", hover_color="#218838", font=ctk.CTkFont(weight="bold"))
        self.download_button.grid(row=0, column=2, padx=0, pady=0)

        # Filters & Sorting Frame
        self.filters_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.filters_frame.grid(row=4, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        ctk.CTkLabel(self.filters_frame, text="Filtro de Tipo:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(0, 5))
        self.filtro_var = ctk.StringVar(value="Todos")
        self.filtro_combo = ctk.CTkComboBox(self.filters_frame, values=["Todos", "Imagens", "Vídeos", "Documentos"], variable=self.filtro_var, width=130)
        self.filtro_combo.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(self.filters_frame, text="Ordenar por:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(0, 5))
        self.ordem_var = ctk.StringVar(value="Nome (A-Z)")
        self.ordem_combo = ctk.CTkComboBox(self.filters_frame, values=["Nome (A-Z)", "Nome (Z-A)", "Padrão (Drive)"], variable=self.ordem_var, width=150)
        self.ordem_combo.pack(side="left")

        self.info_label = ctk.CTkLabel(self, text="Bem-vindo! Selecione o destino, um filtro e cole o link para começar.", font=ctk.CTkFont(size=14))
        self.info_label.grid(row=5, column=0, padx=20, pady=10)

        # Folder action buttons
        self.actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.actions_frame.grid(row=6, column=0, padx=20, pady=(0, 10))
        
        self.open_folder_btn = ctk.CTkButton(self.actions_frame, text="📁 Abrir Pasta", command=self.abrir_pasta, fg_color="#6c757d", hover_color="#5a6268", width=150)
        self.open_folder_btn.grid(row=0, column=0, padx=10)
        
        self.clear_folder_btn = ctk.CTkButton(self.actions_frame, text="🧹 Limpar Pasta", command=self.limpar_pasta, fg_color="#dc3545", hover_color="#c82333", width=150)
        self.clear_folder_btn.grid(row=0, column=1, padx=10)

        self.tabview = ctk.CTkTabview(self, height=320)
        self.tabview.grid(row=7, column=0, padx=20, pady=(0, 15), sticky="nsew")
        self.tabview.add("Fila de Download")
        self.tabview.add("Concluídos")
        
        self.queue_frame = ctk.CTkScrollableFrame(self.tabview.tab("Fila de Download"), fg_color="transparent")
        self.queue_frame.pack(fill="both", expand=True)
        
        self.completed_frame = ctk.CTkScrollableFrame(self.tabview.tab("Concluídos"), fg_color="transparent")
        self.completed_frame.pack(fill="both", expand=True)

        # Global Progress
        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_frame.grid(row=8, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.progress_frame.grid_columnconfigure(0, weight=1)

        self.progress_label = ctk.CTkLabel(self.progress_frame, text="Progresso Total: 0%", font=ctk.CTkFont(size=13, weight="bold"))
        self.progress_label.grid(row=0, column=0, pady=(0, 5), sticky="w")
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, height=14)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=1, column=0, pady=(0, 5), sticky="ew")
        self.progress_frame.grid_remove()

        # Vars
        self.arquivos_para_baixar = []
        self.file_labels = {} 
        self.is_downloading = False
        self.cancel_event = threading.Event()
        self.lock = threading.Lock()
        self.archived_count = 0
        self.log_entries = []
        
        self.max_workers = 4
        self.gerar_relatorio_ativo = ctk.BooleanVar(value=True)
        self.settings_window = None
        
        # Fecha o splash screen do PyInstaller se estiver rodando o executável
        self.after(200, self.fechar_splash)

    def fechar_splash(self):
        try:
            import pyi_splash
            if pyi_splash.is_alive():
                pyi_splash.close()
        except ImportError:
            pass

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
        self.url_entry.configure(values=self.historico)
        try:
            with open(HISTORY_FILE, "w") as f:
                json.dump(self.historico, f)
        except:
            pass

    def abrir_configuracoes(self):
        if self.settings_window is not None and self.settings_window.winfo_exists():
            self.settings_window.focus()
            return
            
        self.settings_window = ctk.CTkToplevel(self)
        self.settings_window.title("⚙️ Configurações")
        self.settings_window.geometry("400x350")
        self.settings_window.attributes("-topmost", True)
        self.settings_window.resizable(False, False)
        
        lbl_tema = ctk.CTkLabel(self.settings_window, text="Modo Escuro:", font=ctk.CTkFont(weight="bold"))
        lbl_tema.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        self.theme_switch = ctk.CTkSwitch(self.settings_window, text="", command=lambda: ctk.set_appearance_mode("Dark") if self.theme_switch.get() else ctk.set_appearance_mode("Light"))
        self.theme_switch.grid(row=0, column=1, padx=20, pady=(20, 10), sticky="e")
        if ctk.get_appearance_mode() == "Dark":
            self.theme_switch.select()
            
        lbl_relat = ctk.CTkLabel(self.settings_window, text="Gerar Relatório TXT:", font=ctk.CTkFont(weight="bold"))
        lbl_relat.grid(row=1, column=0, padx=20, pady=15, sticky="w")
        
        self.report_switch = ctk.CTkSwitch(self.settings_window, text="", variable=self.gerar_relatorio_ativo)
        self.report_switch.grid(row=1, column=1, padx=20, pady=15, sticky="e")
            
        lbl_simult = ctk.CTkLabel(self.settings_window, text="Downloads Simultâneos (1 a 10):", font=ctk.CTkFont(weight="bold"))
        lbl_simult.grid(row=2, column=0, padx=20, pady=(15, 5), sticky="w", columnspan=2)
        
        self.simult_slider = ctk.CTkSlider(self.settings_window, from_=1, to=10, number_of_steps=9, command=self.update_simult_label)
        self.simult_slider.grid(row=3, column=0, padx=20, pady=5, sticky="ew", columnspan=2)
        self.simult_slider.set(self.max_workers)
        
        self.simult_label = ctk.CTkLabel(self.settings_window, text=f"{self.max_workers} arquivos por vez")
        self.simult_label.grid(row=4, column=0, padx=20, pady=(0, 20), columnspan=2)
        
    def update_simult_label(self, value):
        val = int(value)
        self.simult_label.configure(text=f"{val} arquivo{'s' if val > 1 else ''} por vez")
        self.max_workers = val

    def escolher_pasta(self):
        folder = filedialog.askdirectory(initialdir=self.pasta_destino)
        if folder:
            self.pasta_destino = folder
            self.folder_path_var.set(self.pasta_destino)

    def abrir_pasta(self):
        if os.path.exists(self.pasta_destino):
            os.startfile(self.pasta_destino)
            
    def limpar_pasta(self):
        if not os.path.exists(self.pasta_destino):
            return
            
        if messagebox.askyesno("Confirmar Limpeza", f"ATENÇÃO: Você tem certeza que deseja APAGAR TODOS os arquivos da pasta\n{self.pasta_destino}?\n\nIsso não pode ser desfeito."):
            try:
                for filename in os.listdir(self.pasta_destino):
                    file_path = os.path.join(self.pasta_destino, filename)
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                messagebox.showinfo("Sucesso", "A pasta foi esvaziada com sucesso.")
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível limpar a pasta:\n{e}")

    def filtrar_arquivos(self, arquivos):
        filtro = self.filtro_var.get()
        if filtro == "Todos":
            return arquivos
            
        ext_imagens = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'}
        ext_videos = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm'}
        ext_docs = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt'}
        
        filtrados = []
        for a in arquivos:
            ext = os.path.splitext(a.local_path)[1].lower()
            if filtro == "Imagens" and ext in ext_imagens:
                filtrados.append(a)
            elif filtro == "Vídeos" and ext in ext_videos:
                filtrados.append(a)
            elif filtro == "Documentos" and ext in ext_docs:
                filtrados.append(a)
        
        return filtrados

    def analyze_link_thread(self):
        url = self.url_entry.get().strip()
        if not url:
            self.info_label.configure(text="❌ URL inválida.", text_color="#dc3545")
            return
            
        self.analyze_button.configure(state="disabled")
        self.download_button.configure(state="disabled")
        self.info_label.configure(text="🔍 Analisando link e buscando arquivos no servidor...\nPor favor, aguarde.", text_color="white")
        self.progress_frame.grid_remove()
        
        for widget in self.queue_frame.winfo_children():
            widget.destroy()
        for widget in self.completed_frame.winfo_children():
            widget.destroy()
        self.file_labels.clear()
            
        thread = threading.Thread(target=self.analyze_link, args=(url,))
        thread.start()

    def analyze_link(self, url):
        os.makedirs(self.pasta_destino, exist_ok=True)
        try:
            arquivos_brutos = gdown.download_folder(url, output=self.pasta_destino, quiet=True, skip_download=True)
            self.arquivos_para_baixar = self.filtrar_arquivos(arquivos_brutos)
            
            if not self.arquivos_para_baixar:
                self.after(0, lambda: self.info_label.configure(text="⚠️ Nenhum arquivo encontrado com esse filtro.", text_color="#ffc107"))
                self.after(0, lambda: self.analyze_button.configure(state="normal"))
            else:
                self.salvar_historico(url)
                
                # Sorting logic
                ordem = self.ordem_var.get()
                if ordem == "Nome (A-Z)":
                    self.arquivos_para_baixar.sort(key=lambda x: getattr(x, 'path', '').lower())
                elif ordem == "Nome (Z-A)":
                    self.arquivos_para_baixar.sort(key=lambda x: getattr(x, 'path', '').lower(), reverse=True)
                # If "Padrão (Drive)", we leave the original scraped order
                
                for i, arquivo in enumerate(self.arquivos_para_baixar):
                    nome_arquivo = os.path.basename(arquivo.local_path) if getattr(arquivo, 'local_path', None) else f"Arquivo_{i}"
                    self.after(0, self.add_file_row, arquivo.id, nome_arquivo, arquivo.local_path)
                
                total = len(self.arquivos_para_baixar)
                msg = f"✅ Análise Concluída! {total} arquivos encontrados ({self.filtro_var.get()})."
                self.after(0, lambda: self.info_label.configure(text=msg, text_color="#28a745"))
                self.after(0, lambda: self.analyze_button.configure(state="normal"))
                self.after(0, lambda: self.download_button.configure(state="normal", text="⬇️ Iniciar Download", fg_color="#28a745", hover_color="#218838"))
                
        except Exception as e:
            self.after(0, lambda: self.info_label.configure(text=f"❌ Erro:\n{e}", text_color="#dc3545"))
            self.after(0, lambda: self.analyze_button.configure(state="normal"))

    def add_file_row(self, file_id, filename, filepath, target_frame=None, initial_status="⏳ Aguardando", initial_color="#ffffff", initial_bg="#333333"):
        parent = target_frame if target_frame else self.queue_frame
        row_frame = ctk.CTkFrame(parent, fg_color=initial_bg)
        row_frame.pack(fill="x", padx=5, pady=2)
        
        status_lbl = ctk.CTkLabel(row_frame, text=initial_status, text_color=initial_color, font=ctk.CTkFont(size=12, weight="bold"), width=150, anchor="w")
        status_lbl.pack(side="left", padx=10, pady=5)
        
        name_lbl = ctk.CTkLabel(row_frame, text=filename, font=ctk.CTkFont(size=12))
        name_lbl.pack(side="left", padx=10, pady=5)
        
        btn = ctk.CTkButton(row_frame, text="Abrir", width=60, height=24, fg_color="#007bff", hover_color="#0056b3",
                            command=lambda: os.startfile(filepath) if os.path.exists(filepath) else None)
        btn.pack(side="right", padx=10, pady=5)
        
        self.file_labels[file_id] = (status_lbl, row_frame, btn, name_lbl, filename, filepath)

    def toggle_download(self):
        if not self.is_downloading:
            self.start_download()
        else:
            self.cancel_download()

    def start_download(self):
        self.is_downloading = True
        self.cancel_event.clear()
        self.log_entries = []
        self.archived_count = 0
        
        self.analyze_button.configure(state="disabled")
        self.url_entry.configure(state="disabled")
        self.filtro_combo.configure(state="disabled")
        self.ordem_combo.configure(state="disabled")
        self.folder_btn.configure(state="disabled")
        self.clear_folder_btn.configure(state="disabled")
        
        self.download_button.configure(text="🛑 Cancelar", fg_color="#dc3545", hover_color="#c82333")
        
        self.progress_frame.grid()
        self.progress_bar.set(0)
        self.progress_label.configure(text=f"Progresso Total: 0 / {len(self.arquivos_para_baixar)}")
        
        thread = threading.Thread(target=self.download_files)
        thread.start()

    def cancel_download(self):
        self.cancel_event.set()
        self.download_button.configure(state="disabled", text="Cancelando...")

    def atualizar_status(self, file_id, status_text, color, frame_color, is_highlighted=False, is_completed=False):
        if file_id in self.file_labels:
            lbl, frm, btn, name_lbl, filename, filepath = self.file_labels[file_id]
            
            if is_completed:
                frm.destroy()
                self.add_file_row(file_id, filename, filepath, target_frame=self.completed_frame, initial_status=status_text, initial_color=color, initial_bg=frame_color)
            else:
                lbl.configure(text=status_text, text_color=color)
                frm.configure(fg_color=frame_color)
                name_lbl.configure(font=ctk.CTkFont(size=13 if is_highlighted else 12, weight="bold" if is_highlighted else "normal"))

    def download_worker(self, arquivo):
        nome_arquivo = os.path.basename(arquivo.local_path)
        
        if self.cancel_event.is_set():
            self.after(0, self.atualizar_status, arquivo.id, "🛑 Cancelado", "#dc3545", "#242424", False, True)
            return
            
        if os.path.exists(arquivo.local_path) and os.path.getsize(arquivo.local_path) > 0:
            self.after(0, self.atualizar_status, arquivo.id, "⏭️ Pulado", "#ffc107", "#242424", False, True)
            self.log_entries.append(f"PULADO: {nome_arquivo}")
        else:
            local_state = {'last_time': time.time(), 'last_bytes': 0}
            
            def custom_progress(bytes_so_far, bytes_total):
                if self.cancel_event.is_set():
                    raise Exception("Cancelado pelo usuário")
                    
                current_time = time.time()
                elapsed = current_time - local_state['last_time']
                
                if elapsed > 0.5:
                    speed = (bytes_so_far - local_state['last_bytes']) / elapsed if elapsed > 0 else 0
                    local_state['last_bytes'] = bytes_so_far
                    local_state['last_time'] = current_time
                    
                    if speed > 1024 * 1024:
                        speed_str = f"{speed / (1024 * 1024):.1f} MB/s"
                    else:
                        speed_str = f"{speed / 1024:.1f} KB/s"
                        
                    percentage = (bytes_so_far / bytes_total * 100) if bytes_total else 0
                    if percentage > 0:
                        status_text = f"🔄 {percentage:.0f}% | {speed_str}"
                    else:
                        status_text = f"🔄 {speed_str}"
                    self.after(0, self.atualizar_status, arquivo.id, status_text, "#00ffff", "#1f538d", True)
            
            # Auto-Retry System
            max_retries = 3
            sucesso = False
            for tentativa in range(max_retries):
                if self.cancel_event.is_set():
                    break
                try:
                    if tentativa > 0:
                        self.after(0, self.atualizar_status, arquivo.id, f"⚠️ Tentando ({tentativa+1}/3)", "#ffc107", "#1f538d", True)
                        time.sleep(3) 
                        
                    self.after(0, self.atualizar_status, arquivo.id, "🔄 Baixando...", "#00ffff", "#1f538d", True)
                    gdown.download(id=arquivo.id, output=arquivo.local_path, quiet=True, progress=custom_progress)
                    
                    self.after(0, self.atualizar_status, arquivo.id, "✅ Concluído", "#28a745", "#242424", False, True)
                    self.log_entries.append(f"SUCESSO: {nome_arquivo}")
                    sucesso = True
                    break
                except Exception as e:
                    if "Cancelado" in str(e):
                        break
                    else:
                        continue 
                        
            if not sucesso:
                if self.cancel_event.is_set():
                    self.after(0, self.atualizar_status, arquivo.id, "🛑 Cancelado", "#dc3545", "#242424", False, True)
                    self.log_entries.append(f"CANCELADO: {nome_arquivo}")
                else:
                    self.after(0, self.atualizar_status, arquivo.id, "❌ Falha", "#dc3545", "#242424", False, True)
                    self.log_entries.append(f"FALHA (Após 3 tentativas): {nome_arquivo}")

        with self.lock:
            self.archived_count += 1
            p = self.archived_count / len(self.arquivos_para_baixar)
            self.after(0, lambda: self.progress_bar.set(p))
            self.after(0, lambda: self.progress_label.configure(text=f"Progresso Total: {self.archived_count} / {len(self.arquivos_para_baixar)}"))

    def gerar_relatorio(self):
        if not self.gerar_relatorio_ativo.get():
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
            
    def emitir_notificacao(self, title, msg):
        try:
            notification.notify(title=title, message=msg, timeout=10)
        except:
            pass

    def download_files(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self.download_worker, arg) for arg in self.arquivos_para_baixar]
            concurrent.futures.wait(futures)
            
        self.gerar_relatorio()
        self.is_downloading = False
        
        if self.cancel_event.is_set():
            msg = "🛑 Processo Cancelado."
            color = "#ffc107"
            self.emitir_notificacao("Download Cancelado", "O processo foi interrompido pelo usuário.")
        else:
            msg = "✨ Todos os downloads concluídos!"
            color = "#28a745"
            self.emitir_notificacao("Download Concluído", f"{len(self.arquivos_para_baixar)} arquivos foram processados com sucesso.")
            
        self.after(0, lambda: self.info_label.configure(text=f"{msg}\nRelatório salvo (se ativado).", text_color=color))
        self.after(0, lambda: self.download_button.configure(state="normal", text="⬇️ Iniciar Download", fg_color="#28a745", hover_color="#218838"))
        self.after(0, lambda: self.url_entry.configure(state="normal"))
        self.after(0, lambda: self.filtro_combo.configure(state="normal"))
        self.after(0, lambda: self.ordem_combo.configure(state="normal"))
        self.after(0, lambda: self.folder_btn.configure(state="normal"))
        self.after(0, lambda: self.clear_folder_btn.configure(state="normal"))
        self.after(0, lambda: self.analyze_button.configure(state="normal"))

if __name__ == "__main__":
    app = App()
    app.mainloop()