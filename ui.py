import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, ttk
from CTkMessagebox import CTkMessagebox
import threading
import json
import os
import shutil
import time
from datetime import datetime
import winsound
from plyer import notification
from PIL import Image
import pystray
from pystray import MenuItem as item

from downloader import DownloaderCore
from utils import logger, format_time

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

HISTORY_FILE = "history.json"

class AppUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Google Drive Downloader Pro")
        self.geometry("900x850")
        self.resizable(True, True)
        
        self.protocol('WM_DELETE_WINDOW', self.hide_window)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(6, weight=1)

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
        
        self.folder_btn = ctk.CTkButton(self.folder_frame, text="Abrir", command=self.escolher_pasta, width=60, fg_color="#3b82f6", hover_color="#2563eb", font=ctk.CTkFont(size=14))
        self.folder_btn.grid(row=0, column=2, padx=5, pady=15)
        
        self.settings_btn = ctk.CTkButton(self.folder_frame, text="Config", command=self.abrir_configuracoes, width=60, fg_color="#4b5563", hover_color="#374151", font=ctk.CTkFont(size=14))
        self.settings_btn.grid(row=0, column=3, padx=(5, 15), pady=15)

        self.input_frame = ctk.CTkFrame(self, fg_color="#2b2b2b", corner_radius=12)
        self.input_frame.grid(row=3, column=0, padx=25, pady=(0, 10), sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)
        
        self.historico = self.carregar_historico()
        self.url_entry = ctk.CTkComboBox(self.input_frame, values=self.historico, height=40)
        self.url_entry.grid(row=0, column=0, padx=(15, 10), pady=15, sticky="ew")
        self.url_entry.set(self.historico[0] if self.historico else "")

        self.analyze_btn = ctk.CTkButton(self.input_frame, text="Analisar", command=self.handle_analyze_only, height=40, width=120, fg_color="#3b82f6", hover_color="#2563eb", font=ctk.CTkFont(size=16, weight="bold"))
        self.analyze_btn.grid(row=0, column=1, padx=5, pady=15, sticky="ew")

        self.action_button = ctk.CTkButton(self.input_frame, text="Analisar e Baixar", command=self.handle_action, height=40, width=180, fg_color="#10b981", hover_color="#059669", font=ctk.CTkFont(size=16, weight="bold"))
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
        self.actions_frame.grid(row=6, column=0, padx=20, pady=(0, 10))
        
        self.open_folder_btn = ctk.CTkButton(self.actions_frame, text="Abrir Pasta", command=self.abrir_pasta, fg_color="#6c757d", hover_color="#5a6268", width=100)
        self.open_folder_btn.grid(row=0, column=0, padx=10)
        
        self.clear_folder_btn = ctk.CTkButton(self.actions_frame, text="Limpar Pasta", command=self.limpar_pasta, fg_color="#dc3545", hover_color="#c82333", width=100)
        self.clear_folder_btn.grid(row=0, column=1, padx=10)

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
            
        # Paginacao para a fila
        self.pagination_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.pagination_frame.grid(row=8, column=0, pady=5)
        self.btn_prev = ctk.CTkButton(self.pagination_frame, text="< Anterior", width=80, command=self.prev_page)
        self.btn_prev.pack(side="left", padx=5)
        self.lbl_page = ctk.CTkLabel(self.pagination_frame, text="Pág 1")
        self.lbl_page.pack(side="left", padx=10)
        self.btn_next = ctk.CTkButton(self.pagination_frame, text="Próxima >", width=80, command=self.next_page)
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
        callbacks = {
            'update_status': self.atualizar_status,
            'bulk_add': self.bulk_add_rows,
            'on_analyze_finish': self.on_analyze_finish,
            'on_download_progress': self.on_download_progress,
            'on_download_finish': self.on_download_finish
        }
        self.core = DownloaderCore(callbacks)
        self.core.config(self.max_workers, self.extrair_zip_var.get(), self.pasta_destino)
        
        self.global_updater_running = False
        self.last_global_time = 0
        self.last_global_bytes = 0
        
        self.tray_icon = None

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
            self.action_button.configure(state="normal", text="Baixar Tudo", fg_color="#10b981", hover_color="#059669")
        else:
            self.action_button.configure(state="disabled", text="Tudo Baixado")
        self.analyze_btn.configure(state="normal", text="Analisar")

    def on_download_progress(self, count, total):
        self.progress_bar.set(count / total if total else 0)
        self.progress_label.configure(text=f"Progresso Total: {count} / {total}")

    def on_download_finish(self, is_paused, log_entries):
        self.global_updater_running = False
        if is_paused:
            self.action_button.configure(state="normal", text="Retomar", fg_color="#28a745", hover_color="#218838")
            self.info_label.configure(text="Processo Pausado.", text_color="#ffc107")
        else:
            if self.gerar_relatorio_ativo.get():
                try:
                    with open(os.path.join(self.pasta_destino, "relatorio_downloads.txt"), "w") as f:
                        f.write("\n".join(log_entries))
                except: pass
            self.action_button.configure(state="normal", text="Analisar e Baixar", fg_color="#10b981")
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
        self.analyze_btn.configure(state="disabled", text="⏳...")
        self.action_button.configure(state="disabled")
        self.iniciar_analise(False)

    def handle_action(self):
        txt = self.action_button.cget("text")
        if txt == "Analisar e Baixar":
            self.analyze_btn.configure(state="disabled")
            self.action_button.configure(state="disabled", text="Analisando...")
            self.iniciar_analise(True)
        elif txt in ["Baixar Tudo", "Retomar"]:
            self.comecar_download()
        elif txt == "Pausar":
            self.core.pause_download()
            self.action_button.configure(state="disabled", text="Pausando...")

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
            orig = self.core.callbacks['on_analyze_finish']
            def hooked(arquivos, msg, color, has_files):
                orig(arquivos, msg, color, has_files)
                if has_files: self.comecar_download()
            self.core.callbacks['on_analyze_finish'] = hooked
        else:
            self.core.callbacks['on_analyze_finish'] = self.on_analyze_finish

        self.core.start_analysis(url, self.filtro_var.get(), self.ordem_var.get())

    def comecar_download(self):
        self.url_entry.configure(state="disabled")
        self.filtro_combo.configure(state="disabled")
        self.ordem_combo.configure(state="disabled")
        self.folder_btn.configure(state="disabled")
        self.clear_folder_btn.configure(state="disabled")
        
        self.action_button.configure(state="normal", text="Pausar", fg_color="#ffc107")
        self.progress_frame.grid()
        self.progress_label.configure(text=f"Progresso Total: {self.core.archived_count} / {len(self.core.arquivos_para_baixar)}")
        
        self.global_updater_running = True
        self.last_global_time = time.time()
        self.update_global_stats()
        
        self.core.start_download()

    def carregar_historico(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r") as f: return json.load(f)
            except: pass
        return []

    def salvar_historico(self, url):
        if url in self.historico: self.historico.remove(url)
        self.historico.insert(0, url)
        self.historico = self.historico[:5]
        self.url_entry.configure(values=self.historico)
        try:
            with open(HISTORY_FILE, "w") as f: json.dump(self.historico, f)
        except: pass

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
