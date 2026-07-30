import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import threading
import gdown
import os
import sys
import time
import json
import concurrent.futures
from datetime import datetime

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

HISTORY_FILE = "history.json"

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Google Drive Downloader Pro")
        self.geometry("850x800")
        self.resizable(True, True)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(6, weight=1) # Scrollable frame

        # Título
        self.title_label = ctk.CTkLabel(self, text="🚀 Google Drive Downloader Pro", font=ctk.CTkFont(size=26, weight="bold"))
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 5))
        
        self.subtitle_label = ctk.CTkLabel(self, text="Multithreading, Histórico e Gerenciamento de Downloads.", font=ctk.CTkFont(size=13, slant="italic"), text_color="gray")
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

        # Input Frame (URL & Analyze)
        self.input_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.input_frame.grid(row=3, column=0, padx=20, pady=0, sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)
        
        self.historico = self.carregar_historico()
        self.url_entry = ctk.CTkComboBox(self.input_frame, values=self.historico, height=40)
        self.url_entry.grid(row=0, column=0, padx=(0, 10), pady=0, sticky="ew")
        self.url_entry.set(self.historico[0] if self.historico else "")

        self.analyze_button = ctk.CTkButton(self.input_frame, text="🔍 Analisar", command=self.analyze_link_thread, width=120, height=40, font=ctk.CTkFont(weight="bold"))
        self.analyze_button.grid(row=0, column=1, padx=0, pady=0)
        
        self.download_button = ctk.CTkButton(self.input_frame, text="⬇️ Iniciar Download", command=self.toggle_download, width=150, height=40, state="disabled", fg_color="#28a745", hover_color="#218838", font=ctk.CTkFont(weight="bold"))
        self.download_button.grid(row=0, column=2, padx=(10, 0), pady=0)

        # Info Label
        self.info_label = ctk.CTkLabel(self, text="Bem-vindo! Selecione o destino e cole o link para começar.", font=ctk.CTkFont(size=14))
        self.info_label.grid(row=4, column=0, padx=20, pady=10)

        # Open Folder Button
        self.open_folder_btn = ctk.CTkButton(self, text="📁 Abrir Pasta de Destino", command=self.abrir_pasta, fg_color="#6c757d", hover_color="#5a6268")
        self.open_folder_btn.grid(row=5, column=0, padx=20, pady=(0, 10))
        self.open_folder_btn.grid_remove() 

        # Scrollable Frame
        self.file_list_frame = ctk.CTkScrollableFrame(self, width=750, height=350)
        self.file_list_frame.grid(row=6, column=0, padx=20, pady=(0, 15), sticky="nsew")

        # Global Progress
        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_frame.grid(row=7, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.progress_frame.grid_columnconfigure(0, weight=1)

        self.progress_label = ctk.CTkLabel(self.progress_frame, text="Progresso Total: 0%", font=ctk.CTkFont(size=13, weight="bold"))
        self.progress_label.grid(row=0, column=0, pady=(0, 5), sticky="w")
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, height=14)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=1, column=0, pady=(0, 5), sticky="ew")
        self.progress_frame.grid_remove()

        # Variables
        self.arquivos_para_baixar = []
        self.file_labels = {} 
        self.is_downloading = False
        self.cancel_event = threading.Event()
        self.lock = threading.Lock()
        self.archived_count = 0
        self.log_entries = []
        
        # Variáveis de Configuração
        self.max_workers = 4
        self.gerar_relatorio_ativo = ctk.BooleanVar(value=True)
        self.settings_window = None

    def abrir_configuracoes(self):
        if self.settings_window is not None and self.settings_window.winfo_exists():
            self.settings_window.focus()
            return
            
        self.settings_window = ctk.CTkToplevel(self)
        self.settings_window.title("⚙️ Configurações")
        self.settings_window.geometry("400x350")
        self.settings_window.attributes("-topmost", True)
        self.settings_window.resizable(False, False)
        
        # Tema
        lbl_tema = ctk.CTkLabel(self.settings_window, text="Modo Escuro:", font=ctk.CTkFont(weight="bold"))
        lbl_tema.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        self.theme_switch = ctk.CTkSwitch(self.settings_window, text="", command=self.toggle_theme)
        self.theme_switch.grid(row=0, column=1, padx=20, pady=(20, 10), sticky="e")
        if ctk.get_appearance_mode() == "Dark":
            self.theme_switch.select()
            
        # Relatório TXT
        lbl_relat = ctk.CTkLabel(self.settings_window, text="Gerar Relatório TXT:", font=ctk.CTkFont(weight="bold"))
        lbl_relat.grid(row=1, column=0, padx=20, pady=15, sticky="w")
        
        self.report_switch = ctk.CTkSwitch(self.settings_window, text="", variable=self.gerar_relatorio_ativo)
        self.report_switch.grid(row=1, column=1, padx=20, pady=15, sticky="e")
            
        # Slider de Threads
        lbl_simult = ctk.CTkLabel(self.settings_window, text="Downloads Simultâneos (1 a 10):", font=ctk.CTkFont(weight="bold"))
        lbl_simult.grid(row=2, column=0, padx=20, pady=(15, 5), sticky="w", columnspan=2)
        
        self.simult_slider = ctk.CTkSlider(self.settings_window, from_=1, to=10, number_of_steps=9, command=self.update_simult_label)
        self.simult_slider.grid(row=3, column=0, padx=20, pady=5, sticky="ew", columnspan=2)
        self.simult_slider.set(self.max_workers)
        
        self.simult_label = ctk.CTkLabel(self.settings_window, text=f"{self.max_workers} arquivos por vez")
        self.simult_label.grid(row=4, column=0, padx=20, pady=(0, 20), columnspan=2)

    def toggle_theme(self):
        if self.theme_switch.get():
            ctk.set_appearance_mode("Dark")
        else:
            ctk.set_appearance_mode("Light")
            
    def update_simult_label(self, value):
        val = int(value)
        self.simult_label.configure(text=f"{val} arquivo{'s' if val > 1 else ''} por vez")
        self.max_workers = val

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
        self.historico = self.historico[:5] # keep last 5
        self.url_entry.configure(values=self.historico)
        try:
            with open(HISTORY_FILE, "w") as f:
                json.dump(self.historico, f)
        except:
            pass

    def escolher_pasta(self):
        folder = filedialog.askdirectory(initialdir=self.pasta_destino)
        if folder:
            self.pasta_destino = folder
            self.folder_path_var.set(self.pasta_destino)

    def abrir_pasta(self):
        if os.path.exists(self.pasta_destino):
            os.startfile(self.pasta_destino)

    def analyze_link_thread(self):
        url = self.url_entry.get().strip()
        if not url:
            self.info_label.configure(text="❌ URL inválida.", text_color="#dc3545")
            return
            
        self.analyze_button.configure(state="disabled")
        self.download_button.configure(state="disabled")
        self.info_label.configure(text="🔍 Analisando link e buscando arquivos no servidor...\nPor favor, aguarde.", text_color="white")
        self.progress_frame.grid_remove()
        
        for widget in self.file_list_frame.winfo_children():
            widget.destroy()
        self.file_labels.clear()
            
        thread = threading.Thread(target=self.analyze_link, args=(url,))
        thread.start()

    def analyze_link(self, url):
        os.makedirs(self.pasta_destino, exist_ok=True)
        try:
            self.arquivos_para_baixar = gdown.download_folder(url, output=self.pasta_destino, quiet=True, skip_download=True)
            if not self.arquivos_para_baixar:
                self.after(0, lambda: self.info_label.configure(text="⚠️ Nenhum arquivo encontrado.", text_color="#ffc107"))
                self.after(0, lambda: self.analyze_button.configure(state="normal"))
            else:
                self.salvar_historico(url)
                self.arquivos_para_baixar.sort(key=lambda x: getattr(x, 'path', ''))
                
                # Setup rows
                for i, arquivo in enumerate(self.arquivos_para_baixar):
                    nome_arquivo = os.path.basename(arquivo.local_path) if getattr(arquivo, 'local_path', None) else f"Arquivo_{i}"
                    self.after(0, self.add_file_row, arquivo.id, nome_arquivo, arquivo.local_path)
                
                total = len(self.arquivos_para_baixar)
                msg = f"✅ Análise Concluída! {total} arquivos encontrados."
                self.after(0, lambda: self.info_label.configure(text=msg, text_color="#28a745"))
                self.after(0, lambda: self.analyze_button.configure(state="normal"))
                self.after(0, lambda: self.download_button.configure(state="normal", text="⬇️ Iniciar Download", fg_color="#28a745", hover_color="#218838"))
                self.after(0, lambda: self.open_folder_btn.grid())
                
        except Exception as e:
            self.after(0, lambda: self.info_label.configure(text=f"❌ Erro:\n{e}", text_color="#dc3545"))
            self.after(0, lambda: self.analyze_button.configure(state="normal"))

    def add_file_row(self, file_id, filename, filepath):
        row_frame = ctk.CTkFrame(self.file_list_frame, fg_color="#333333")
        row_frame.pack(fill="x", padx=5, pady=2)
        
        status_lbl = ctk.CTkLabel(row_frame, text="⏳ Aguardando", font=ctk.CTkFont(size=12, weight="bold"), width=140, anchor="w")
        status_lbl.pack(side="left", padx=10, pady=5)
        
        name_lbl = ctk.CTkLabel(row_frame, text=filename, font=ctk.CTkFont(size=12))
        name_lbl.pack(side="left", padx=10, pady=5)
        
        btn = ctk.CTkButton(row_frame, text="Abrir", width=60, height=24, fg_color="#007bff", hover_color="#0056b3",
                            command=lambda: os.startfile(filepath) if os.path.exists(filepath) else None)
        btn.pack(side="right", padx=10, pady=5)
        
        self.file_labels[file_id] = (status_lbl, row_frame, btn)

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
        self.folder_btn.configure(state="disabled")
        
        self.download_button.configure(text="🛑 Cancelar Download", fg_color="#dc3545", hover_color="#c82333")
        
        self.progress_frame.grid()
        self.progress_bar.set(0)
        self.progress_label.configure(text=f"Progresso Total: 0 / {len(self.arquivos_para_baixar)}")
        
        thread = threading.Thread(target=self.download_files)
        thread.start()

    def cancel_download(self):
        self.cancel_event.set()
        self.download_button.configure(state="disabled", text="Cancelando...")

    def atualizar_status(self, file_id, status_text, color, frame_color):
        if file_id in self.file_labels:
            lbl, frm, _ = self.file_labels[file_id]
            lbl.configure(text=status_text, text_color=color)
            frm.configure(fg_color=frame_color)

    def download_worker(self, arquivo):
        nome_arquivo = os.path.basename(arquivo.local_path)
        
        if self.cancel_event.is_set():
            self.after(0, self.atualizar_status, arquivo.id, "🛑 Cancelado", "#dc3545", "#2d2d2d")
            return
            
        # Check if already exists
        if os.path.exists(arquivo.local_path) and os.path.getsize(arquivo.local_path) > 0:
            self.after(0, self.atualizar_status, arquivo.id, "⏭️ Pulado", "#ffc107", "#2d2d2d")
            self.log_entries.append(f"PULADO (Já existe): {nome_arquivo}")
        else:
            self.after(0, self.atualizar_status, arquivo.id, "🔄 Baixando...", "#17a2b8", "#333333")
            
            local_state = {'last_time': time.time(), 'last_bytes': 0}
            
            def custom_progress(bytes_so_far, bytes_total):
                if self.cancel_event.is_set():
                    raise Exception("Cancelado pelo usuário")
                    
                current_time = time.time()
                elapsed = current_time - local_state['last_time']
                
                # Atualizar a velocidade a cada 0.5 segundos
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
                        
                    self.after(0, self.atualizar_status, arquivo.id, status_text, "#17a2b8", "#333333")
                
            try:
                gdown.download(id=arquivo.id, output=arquivo.local_path, quiet=True, progress=custom_progress)
                self.after(0, self.atualizar_status, arquivo.id, "✅ Concluído", "#28a745", "#2d2d2d")
                self.log_entries.append(f"SUCESSO: {nome_arquivo}")
            except Exception as e:
                if "Cancelado" in str(e):
                    self.after(0, self.atualizar_status, arquivo.id, "🛑 Cancelado", "#dc3545", "#2d2d2d")
                    self.log_entries.append(f"CANCELADO: {nome_arquivo}")
                else:
                    self.after(0, self.atualizar_status, arquivo.id, "❌ Falha", "#dc3545", "#2d2d2d")
                    self.log_entries.append(f"FALHA ({e}): {nome_arquivo}")

        # Update global progress
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

    def download_files(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self.download_worker, arg) for arg in self.arquivos_para_baixar]
            concurrent.futures.wait(futures)
            
        self.gerar_relatorio()
        self.is_downloading = False
        
        if self.cancel_event.is_set():
            msg = "🛑 Processo Cancelado."
            color = "#ffc107"
        else:
            msg = "✨ Todos os downloads concluídos!"
            color = "#28a745"
            
        self.after(0, lambda: self.info_label.configure(text=f"{msg}\nRelatório salvo em relatorio_downloads.txt", text_color=color))
        self.after(0, lambda: self.download_button.configure(state="normal", text="⬇️ Iniciar Download", fg_color="#28a745", hover_color="#218838"))
        self.after(0, lambda: self.url_entry.configure(state="normal"))
        self.after(0, lambda: self.folder_btn.configure(state="normal"))
        self.after(0, lambda: self.analyze_button.configure(state="normal"))

if __name__ == "__main__":
    app = App()
    app.mainloop()