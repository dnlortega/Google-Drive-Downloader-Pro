import customtkinter as ctk
import tkinter as tk
import threading
import gdown
import os
import sys
import time

# Configurações de aparência profissional
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Google Drive Downloader Pro")
        self.geometry("650x650")
        self.resizable(False, False)

        # Configuração do grid principal
        self.grid_columnconfigure(0, weight=1)

        # Título
        self.title_label = ctk.CTkLabel(self, text="🚀 Google Drive Downloader", font=ctk.CTkFont(size=26, weight="bold"))
        self.title_label.grid(row=0, column=0, padx=20, pady=(30, 5))
        
        # Subtítulo
        self.subtitle_label = ctk.CTkLabel(self, text="Baixe pastas completas de forma rápida, com um design moderno e profissional.", 
                                           font=ctk.CTkFont(size=13, slant="italic"), text_color="gray")
        self.subtitle_label.grid(row=1, column=0, padx=20, pady=(0, 20))

        # Input da URL
        self.url_entry = ctk.CTkEntry(self, placeholder_text="🔗 Insira o link público da pasta do Google Drive...", 
                                      width=550, height=45, font=ctk.CTkFont(size=14))
        self.url_entry.grid(row=2, column=0, padx=20, pady=(0, 15))

        # Botão de Análise
        self.analyze_button = ctk.CTkButton(self, text="🔍 Analisar Link", command=self.analyze_link_thread, 
                                            width=250, height=45, font=ctk.CTkFont(size=14, weight="bold"))
        self.analyze_button.grid(row=3, column=0, padx=20, pady=(0, 15))

        # Caixa de Informações
        self.info_box = ctk.CTkTextbox(self, width=550, height=100, state="disabled", font=ctk.CTkFont(size=13))
        self.info_box.grid(row=4, column=0, padx=20, pady=(0, 15))
        self.update_info("Bem-vindo! Cole o link acima e clique em 'Analisar Link' para começar.")

        # PROGRESSO TOTAL (Arquivos)
        self.progress_label = ctk.CTkLabel(self, text="Progresso Total: 0%", font=ctk.CTkFont(size=12, weight="bold"))
        self.progress_label.grid(row=5, column=0, padx=20, pady=(0, 0), sticky="w")
        self.progress_label.grid_remove()

        self.progress_bar = ctk.CTkProgressBar(self, width=550, height=12)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=6, column=0, padx=20, pady=(0, 15))
        self.progress_bar.grid_remove()

        # PROGRESSO DO ARQUIVO ATUAL (Velocidade e Tempo)
        self.progress_file_label = ctk.CTkLabel(self, text="Arquivo atual: Aguardando...", font=ctk.CTkFont(size=12))
        self.progress_file_label.grid(row=7, column=0, padx=20, pady=(0, 0), sticky="w")
        self.progress_file_label.grid_remove()

        self.progress_file_bar = ctk.CTkProgressBar(self, width=550, height=8, progress_color="#28a745")
        self.progress_file_bar.set(0)
        self.progress_file_bar.grid(row=8, column=0, padx=20, pady=(0, 20))
        self.progress_file_bar.grid_remove()

        # Botão de Iniciar Download
        self.download_button = ctk.CTkButton(self, text="⬇️ Iniciar Download", command=self.download_files_thread, 
                                             width=250, height=45, state="disabled", fg_color="#28a745", 
                                             hover_color="#218838", font=ctk.CTkFont(size=14, weight="bold"))
        self.download_button.grid(row=9, column=0, padx=20, pady=(0, 20))
        
        self.arquivos_para_baixar = []
        self.pasta_destino = os.path.expanduser("~/Downloads/Fotos_Drive")
        
        # Variáveis para cálculo de velocidade
        self.last_time = 0
        self.last_bytes = 0

    def update_info(self, text):
        self.info_box.configure(state="normal")
        self.info_box.delete("1.0", tk.END)
        self.info_box.insert("1.0", text)
        self.info_box.configure(state="disabled")

    def analyze_link_thread(self):
        url = self.url_entry.get().strip()
        if not url:
            self.update_info("❌ URL inválida. Por favor, insira um link válido do Google Drive.")
            return
            
        self.analyze_button.configure(state="disabled")
        self.download_button.configure(state="disabled")
        self.update_info("🔍 Analisando link e buscando arquivos no servidor...\nPor favor, aguarde.")
        
        # Ocultar barras caso existam
        self.progress_label.grid_remove()
        self.progress_bar.grid_remove()
        self.progress_file_label.grid_remove()
        self.progress_file_bar.grid_remove()
        
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
                self.update_info("⚠️ Nenhum arquivo encontrado na pasta especificada.\nVerifique se o link está correto e é público.")
                self.analyze_button.configure(state="normal")
            else:
                # Ordena os arquivos pelo nome em ordem alfabética
                self.arquivos_para_baixar.sort(key=lambda x: getattr(x, 'path', ''))
                
                total = len(self.arquivos_para_baixar)
                self.update_info(f"✅ Análise Concluída com Sucesso!\n\n📸 Total de arquivos encontrados: {total}\n📁 Pasta de destino: {self.pasta_destino}")
                self.analyze_button.configure(state="normal")
                self.download_button.configure(state="normal")
                
        except Exception as e:
            self.update_info(f"❌ Erro ao acessar a pasta do Google Drive:\n{e}")
            self.analyze_button.configure(state="normal")

    def download_files_thread(self):
        self.analyze_button.configure(state="disabled")
        self.download_button.configure(state="disabled")
        self.url_entry.configure(state="disabled")
        
        # Mostra as barras de progresso
        self.progress_label.grid()
        self.progress_bar.grid()
        self.progress_bar.set(0)
        
        self.progress_file_label.grid()
        self.progress_file_bar.grid()
        self.progress_file_bar.set(0)
        
        thread = threading.Thread(target=self.download_files)
        thread.start()
        
    def progress_callback(self, bytes_so_far, bytes_total):
        current_time = time.time()
        elapsed = current_time - self.last_time
        
        # Atualiza a cada 0.2 segundos para não sobrecarregar a interface
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
                
                # Formata tempo restante
                if eta_seconds > 60:
                    eta_str = f"{int(eta_seconds // 60)}m {int(eta_seconds % 60)}s"
                else:
                    eta_str = f"{int(eta_seconds)}s"
                    
                percentage = (bytes_so_far / bytes_total) * 100
                self.progress_file_label.configure(text=f"↳ Velocidade: {speed_str} | Tempo restante do arquivo: {eta_str}")
                self.progress_file_bar.set(bytes_so_far / bytes_total)
            else:
                # Se não souber o tamanho total
                self.progress_file_label.configure(text=f"↳ Velocidade: {speed_str} | Baixando...")
                self.progress_file_bar.set(0)

    def download_files(self):
        total = len(self.arquivos_para_baixar)
        
        for i, arquivo in enumerate(self.arquivos_para_baixar):
            nome_arquivo = os.path.basename(arquivo.local_path) if getattr(arquivo, 'local_path', None) else "Arquivo"
            
            self.progress_label.configure(text=f"Progresso Total ({i+1}/{total}): Baixando {nome_arquivo}...")
            self.progress_file_label.configure(text="↳ Inicializando download...")
            self.progress_file_bar.set(0)
            
            self.last_time = time.time()
            self.last_bytes = 0
            
            try:
                gdown.download(
                    id=arquivo.id, 
                    output=arquivo.local_path, 
                    quiet=True, 
                    progress=self.progress_callback
                )
            except Exception:
                pass # Ignora falha de arquivo individual
                
            # Atualiza a barra total
            progresso_total = (i + 1) / total
            self.progress_bar.set(progresso_total)
            
        self.progress_label.configure(text=f"✨ Todos os {total} downloads foram concluídos com sucesso!")
        self.progress_file_label.configure(text="")
        self.progress_file_bar.set(1.0)
        
        self.update_info(f"✅ Processo finalizado!\n\nSeus {total} arquivos já estão disponíveis na pasta:\n{self.pasta_destino}")
        
        # Reativa os inputs
        self.url_entry.configure(state="normal")
        self.analyze_button.configure(state="normal")

if __name__ == "__main__":
    app = App()
    app.mainloop()