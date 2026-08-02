import re

with open('app.pyw', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update the message logic
old_msg_logic = '''                self.arquivos_para_baixar = arquivos_pendentes
                total = len(self.arquivos_para_baixar)
                msg = f"✅ Análise Concluída! {total} arquivo(s) encontrado(s)."
                self.after(0, lambda: self.info_label.configure(text=msg, text_color="#28a745"))
                if len(self.arquivos_para_baixar) > 0:
                    self.after(0, self.start_download)
                else:
                    self.after(0, lambda: self.action_button.configure(state="normal", text="🚀 Analisar e Baixar"))'''

new_msg_logic = '''                self.arquivos_para_baixar = arquivos_pendentes
                total_encontrados = len(arquivos_brutos) if arquivos_brutos else len(self.arquivos_para_baixar) + self.count_exists
                msg = f"✅ Análise Concluída! Total: {total_encontrados} | Pendentes: {len(self.arquivos_para_baixar)} | Já Baixados: {self.count_exists}"
                self.after(0, lambda: self.info_label.configure(text=msg, text_color="#28a745"))
                
                if getattr(self, 'auto_download_after_analysis', True) and len(self.arquivos_para_baixar) > 0:
                    self.after(0, self.start_download)
                else:
                    if len(self.arquivos_para_baixar) > 0:
                        self.after(0, lambda: self.action_button.configure(state="normal", text="🚀 Baixar Tudo", fg_color="#10b981", hover_color="#059669"))
                    else:
                        self.after(0, lambda: self.action_button.configure(state="disabled", text="✅ Tudo Baixado"))
                    self.after(0, lambda: self.analyze_btn.configure(state="normal", text="🔍 Analisar"))'''

content = content.replace(old_msg_logic, new_msg_logic)


# 2. Add the separate Analyze button in setup_ui
old_buttons = '''        self.url_entry = ctk.CTkComboBox(self.input_frame, values=self.historico, height=40)
        self.url_entry.grid(row=0, column=0, padx=(15, 10), pady=15, sticky="ew")
        self.url_entry.set(self.historico[0] if self.historico else "")

        self.action_button = ctk.CTkButton(self.input_frame, text="🚀 Analisar e Baixar", command=self.handle_action, height=40, fg_color="#10b981", hover_color="#059669", font=ctk.CTkFont(size=16, weight="bold"))
        self.action_button.grid(row=0, column=1, padx=(0, 15), pady=15, sticky="ew")
        
        self.input_frame.grid_columnconfigure(1, weight=0)'''

new_buttons = '''        self.url_entry = ctk.CTkComboBox(self.input_frame, values=self.historico, height=40)
        self.url_entry.grid(row=0, column=0, padx=(15, 10), pady=15, sticky="ew")
        self.url_entry.set(self.historico[0] if self.historico else "")

        self.analyze_btn = ctk.CTkButton(self.input_frame, text="🔍 Analisar", command=self.handle_analyze_only, height=40, width=120, fg_color="#3b82f6", hover_color="#2563eb", font=ctk.CTkFont(size=16, weight="bold"))
        self.analyze_btn.grid(row=0, column=1, padx=5, pady=15, sticky="ew")

        self.action_button = ctk.CTkButton(self.input_frame, text="🚀 Analisar e Baixar", command=self.handle_action, height=40, width=180, fg_color="#10b981", hover_color="#059669", font=ctk.CTkFont(size=16, weight="bold"))
        self.action_button.grid(row=0, column=2, padx=(5, 15), pady=15, sticky="ew")
        
        self.input_frame.grid_columnconfigure(1, weight=0)
        self.input_frame.grid_columnconfigure(2, weight=0)'''

content = content.replace(old_buttons, new_buttons)


# 3. Update handle_action to support new states
old_handle = '''    def handle_action(self):
        text = self.action_button.cget("text")
        if text == "🚀 Analisar e Baixar":
            self.action_button.configure(state="disabled", text="⏳ Analisando...")
            self.analyze_link_thread()
        elif text == "▶️ Retomar":
            self.start_download()
        elif text == "⏸️ Pausar":
            self.pause_download()'''

new_handle = '''    def handle_analyze_only(self):
        self.auto_download_after_analysis = False
        self.analyze_btn.configure(state="disabled", text="⏳...")
        self.action_button.configure(state="disabled")
        self.analyze_link_thread()

    def handle_action(self):
        text = self.action_button.cget("text")
        if text == "🚀 Analisar e Baixar":
            self.auto_download_after_analysis = True
            self.action_button.configure(state="disabled", text="⏳ Analisando...")
            if hasattr(self, 'analyze_btn'): self.analyze_btn.configure(state="disabled")
            self.analyze_link_thread()
        elif text == "🚀 Baixar Tudo" or text == "▶️ Retomar":
            self.start_download()
        elif text == "⏸️ Pausar":
            self.pause_download()'''

content = content.replace(old_handle, new_handle)

# 4. Handle errors gracefully for buttons
old_err = '''        except Exception as e:
            self.after(0, lambda: self.info_label.configure(text=f"❌ Erro na análise:\\n{e}", text_color="#dc3545"))
            self.after(0, lambda: self.action_button.configure(state="normal", text="🚀 Analisar e Baixar"))'''

new_err = '''        except Exception as e:
            self.after(0, lambda: self.info_label.configure(text=f"❌ Erro na análise:\\n{e}", text_color="#dc3545"))
            self.after(0, lambda: self.action_button.configure(state="normal", text="🚀 Analisar e Baixar"))
            if hasattr(self, 'analyze_btn'):
                self.after(0, lambda: self.analyze_btn.configure(state="normal", text="🔍 Analisar"))'''

content = content.replace(old_err, new_err)


with open('app.pyw', 'w', encoding='utf-8') as f:
    f.write(content)
