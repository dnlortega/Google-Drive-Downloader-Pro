import customtkinter as ctk
import tkinter as tk
import threading
import gdown
import os
import sys
import time

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Google Drive Downloader Pro")
        self.geometry("800x750")
        self.resizable(False, False)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1) # The scrollable frame will expand

        # 0: Título
        self.title_label = ctk.CTkLabel(self, text="🚀 Google Drive Downloader", font=ctk.CTkFont(size=26, weight="bold"))
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 5))
        
        # 1: Subtítulo
        self.subtitle_label = ctk.CTkLabel(self, text="Baixe pastas completas, acompanhe o progresso e abra os arquivos diretamente.", 
                                           font=ctk.CTkFont(size=13, slant="italic"), text_color="gray")
        self.subtitle_label.grid(row=1, column=0, padx=20, pady=(0, 20))

        # 2: Input da URL e Botões
        self.input_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.input_frame.grid(row=2, column=0, padx=20, pady=0, sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)
        
        self.url_entry = ctk.CTkEntry(self.input_frame, placeholder_text="🔗 Insira o link público da pasta...", height=40)
        self.url_entry.grid(row=0, column=0, padx=(0, 10), pady=0, sticky="ew")

        self.analyze_button = ctk.CTkButton(self.input_frame, text="🔍 Analisar", command=self.analyze_link_thread, width=120, height=40, font=ctk.CTkFont(weight="bold"))
        self.analyze_button.grid(row=0, column=1, padx=0, pady=0)
        
        self.download_button = ctk.CTkButton(self.input_frame, text="⬇️ Iniciar Download", command=self.download_files_thread, width=150, height=40, state="disabled", fg_color="#28a745", hover_color="#218838", font=ctk.CTkFont(weight="bold"))
        self.download_button.grid(row=0, column=2, padx=(10, 0), pady=0)

        # 3: Info Box Minimalista
        self.info_label = ctk.CTkLabel(self, text="Bem-vindo! Cole o link acima para começar.", font=ctk.CTkFont(size=14))
        self.info_label.grid(row=3, column=0, padx=20, pady=15)

        # 4: Abrir Pasta (Global)
        self.open_folder_btn = ctk.CTkButton(self, text="📁 Abrir Pasta de Destino", command=self.abrir_pasta, fg_color="#6c757d", hover_color="#5a6268")
        self.open_folder_btn.grid(row=4, column=0, padx=20, pady=(0, 10))
        self.open_folder_btn.grid_remove() # Oculta até ter a pasta

        # 5: Scrollable Frame para os arquivos
        self.file_list_frame = ctk.CTkScrollableFrame(self, width=700, height=300)
        self.file_list_frame.grid(row=5, column=0, padx=20, pady=(0, 15), sticky="nsew")

        # 6 & 7 & 8 & 9: Progress Bars
        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_frame.grid(row=6, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.progress_frame.grid_columnconfigure(0, weight=1)

        self.progress_label = ctk.CTkLabel(self.progress_frame, text="Progresso Total: 0%", font=ctk.CTkFont(size=12, weight="bold"))
        self.progress_label.grid(row=0, column=0, pady=(0, 2), sticky="w")
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, height=12)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=1, column=0, pady=(0, 10), sticky="ew")

        self.progress_file_label = ctk.CTkLabel(self.progress_frame, text="Arquivo atual: Aguardando...", font=ctk.CTkFont(size=12))
        self.progress_file_label.grid(row=2, column=0, pady=(0, 2), sticky="w")
        self.progress_file_bar = ctk.CTkProgressBar(self.progress_frame, height=8, progress_color="#28a745")
        self.progress_file_bar.set(0)
        self.progress_file_bar.grid(row=3, column=0, pady=(0, 0), sticky="ew")

        self.progress_frame.grid_remove()

        self.arquivos_para_baixar = []
        self.pasta_destino = os.path.expanduser("~/Downloads/Fotos_Drive")
        
        self.last_time = 0
        self.last_bytes = 0

    def abrir_pasta(self):
        if os.path.exists(self.pasta_destino):
            os.startfile(self.pasta_destino)

    def analyze_link_thread(self):
        url = self.url_entry.get().strip()
        if not url:
            self.info_label.configure(text="❌ URL inválida. Por favor, insira um link válido do Google Drive.", text_color="#dc3545")
            return
            
        self.analyze_button.configure(state="disabled")
        self.download_button.configure(state="disabled")
        self.info_label.configure(text="🔍 Analisando link e buscando arquivos no servidor...\nPor favor, aguarde.", text_color="white")
        
        self.progress_frame.grid_remove()
        
        # Limpar a lista visual de arquivos
        for widget in self.file_list_frame.winfo_children():
            widget.destroy()
            
        thread = threading.Thread(target=self.analyze_link, args=(url,))
        thread.start()

    def analyze_link(self, url):
        os.makedirs(self.pasta_destino, exist_ok=True)
        try:
            self.arquivos_para_baixar = gdown.download_folder(
                url, 
                output=self.pasta_destino, 
                quiet=True, 
                skip_download=True
            )
            
            if not self.arquivos_para_baixar:
                self.after(0, lambda: self.info_label.configure(text="⚠️ Nenhum arquivo encontrado na pasta especificada.\nVerifique se o link está correto e é público.", text_color="#ffc107"))
                self.after(0, lambda: self.analyze_button.configure(state="normal"))
            else:
                self.arquivos_para_baixar.sort(key=lambda x: getattr(x, 'path', ''))
                total = len(self.arquivos_para_baixar)
                
                msg = f"✅ Análise Concluída! {total} arquivos encontrados.\nPasta: {self.pasta_destino}"
                self.after(0, lambda: self.info_label.configure(text=msg, text_color="#28a745"))
                self.after(0, lambda: self.analyze_button.configure(state="normal"))
                self.after(0, lambda: self.download_button.configure(state="normal"))
                self.after(0, lambda: self.open_folder_btn.grid())
                
        except Exception as e:
            self.after(0, lambda: self.info_label.configure(text=f"❌ Erro ao acessar a pasta do Google Drive:\n{e}", text_color="#dc3545"))
            self.after(0, lambda: self.analyze_button.configure(state="normal"))

    def download_files_thread(self):
        self.analyze_button.configure(state="disabled")
        self.download_button.configure(state="disabled")
        self.url_entry.configure(state="disabled")
        
        self.progress_frame.grid()
        self.progress_bar.set(0)
        self.progress_file_bar.set(0)
        
        thread = threading.Thread(target=self.download_files)
        thread.start()
        
    def progress_callback(self, bytes_so_far, bytes_total):
        current_time = time.time()
        elapsed = current_time - self.last_time
        
        if elapsed > 0.2:
            speed = (bytes_so_far - self.last_bytes) / elapsed if elapsed > 0 else 0
            self.last_bytes = bytes_so_far
            self.last_time = current_time
            
            if speed > 1024 * 1024:
                speed_str = f"{speed / (1024 * 1024):.1f} MB/s"
            else:
                speed_str = f"{speed / 1024:.1f} KB/s"
                
            if bytes_total:
                eta_seconds = (bytes_total - bytes_so_far) / speed if speed > 0 else 0
                if eta_seconds > 60:
                    eta_str = f"{int(eta_seconds // 60)}m {int(eta_seconds % 60)}s"
                else:
                    eta_str = f"{int(eta_seconds)}s"
                    
                percentage = (bytes_so_far / bytes_total) * 100
                self.after(0, lambda: self.progress_file_label.configure(text=f"↳ Velocidade: {speed_str} | Tempo restante do arquivo: {eta_str}"))
                self.after(0, lambda: self.progress_file_bar.set(bytes_so_far / bytes_total))
            else:
                self.after(0, lambda: self.progress_file_label.configure(text=f"↳ Velocidade: {speed_str} | Baixando..."))
                self.after(0, lambda: self.progress_file_bar.set(0))

    def add_file_row(self, filename, filepath, is_skipped=False):
        row_frame = ctk.CTkFrame(self.file_list_frame, fg_color="#333333" if not is_skipped else "#2d2d2d")
        row_frame.pack(fill="x", padx=5, pady=2)
        
        icon = "⏭️" if is_skipped else "✅"
        lbl = ctk.CTkLabel(row_frame, text=f"{icon} {filename}", font=ctk.CTkFont(size=12))
        lbl.pack(side="left", padx=10, pady=5)
        
        def open_file():
            if os.path.exists(filepath):
                os.startfile(filepath)
                
        btn = ctk.CTkButton(row_frame, text="Abrir", width=60, height=24, command=open_file, fg_color="#007bff", hover_color="#0056b3")
        btn.pack(side="right", padx=10, pady=5)

    def download_files(self):
        total = len(self.arquivos_para_baixar)
        
        for i, arquivo in enumerate(self.arquivos_para_baixar):
            nome_arquivo = os.path.basename(arquivo.local_path) if getattr(arquivo, 'local_path', None) else "Arquivo"
            
            self.after(0, lambda i=i, n=nome_arquivo: self.progress_label.configure(text=f"Progresso Total ({i+1}/{total}): Baixando {n}..."))
            self.after(0, lambda: self.progress_file_label.configure(text="↳ Inicializando download..."))
            self.after(0, lambda: self.progress_file_bar.set(0))
            
            self.last_time = time.time()
            self.last_bytes = 0
            
            # Verifica se já existe
            is_skipped = False
            if os.path.exists(arquivo.local_path) and os.path.getsize(arquivo.local_path) > 0:
                self.after(0, lambda: self.progress_file_label.configure(text=f"↳ Arquivo já existe, pulando..."))
                self.after(0, lambda: self.progress_file_bar.set(1.0))
                time.sleep(0.05)
                is_skipped = True
            else:
                try:
                    gdown.download(
                        id=arquivo.id, 
                        output=arquivo.local_path, 
                        quiet=True, 
                        progress=self.progress_callback
                    )
                except Exception:
                    pass
            
            # Adiciona na lista visual
            self.after(0, self.add_file_row, nome_arquivo, arquivo.local_path, is_skipped)
                
            progresso_total = (i + 1) / total
            self.after(0, lambda p=progresso_total: self.progress_bar.set(p))
            
        self.after(0, lambda: self.progress_label.configure(text=f"✨ Todos os {total} downloads foram concluídos com sucesso!"))
        self.after(0, lambda: self.progress_file_label.configure(text=""))
        self.after(0, lambda: self.progress_file_bar.set(1.0))
        
        self.after(0, lambda: self.info_label.configure(text=f"✅ Processo finalizado! Todos os arquivos estão na pasta.", text_color="#28a745"))
        
        self.after(0, lambda: self.url_entry.configure(state="normal"))
        self.after(0, lambda: self.analyze_button.configure(state="normal"))

if __name__ == "__main__":
    app = App()
    app.mainloop()