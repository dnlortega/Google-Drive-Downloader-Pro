import re

with open('app.pyw', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace file_labels clearing
old_clear = '''        for widget in self.queue_frame.winfo_children():
            widget.destroy()
        for widget in self.completed_frame.winfo_children():
            widget.destroy()
        self.file_labels.clear()'''

new_clear = '''        for tree in self.trees.values():
            for item in tree.get_children():
                tree.delete(item)
        self.file_labels.clear()
        
        self.count_queue = 0
        self.count_completed = 0
        self.count_exists = 0
        self.count_failed = 0
        self.update_tabs()'''

content = content.replace(old_clear, new_clear)

# Format Tamanho helper
size_helper = '''    def _format_size(self, size_bytes):
        if not size_bytes: return "0 B"
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
'''

# Replace analyze_link limits and add format_size helper
# The original code has:
#                 self.ui_rendered = 0
#                 for i, arquivo in enumerate(self.arquivos_para_baixar):
old_loop = '''                self.ui_rendered = 0
                for i, arquivo in enumerate(self.arquivos_para_baixar):
                    nome_arquivo = os.path.basename(arquivo.local_path) if getattr(arquivo, 'local_path', None) else f"Arquivo_{i}"
                    
                    if os.path.exists(arquivo.local_path) and os.path.getsize(arquivo.local_path) > 0:
                        if self.ui_rendered < 100:
                            self.after(0, self.add_file_row, arquivo.id, nome_arquivo, arquivo.local_path, self.exists_frame, "✅ Já existe", "#28a745", "#242424")
                            self.ui_rendered += 1
                        self.count_exists += 1
                    else:
                        arquivos_pendentes.append(arquivo)
                        if self.ui_rendered < 100:
                            self.after(0, self.add_file_row, arquivo.id, nome_arquivo, arquivo.local_path)
                            self.ui_rendered += 1
                        self.count_queue += 1
                        
                self.after(0, self.update_tabs)
                
                if len(self.arquivos_para_baixar) > 100:
                    self.after(0, self.add_file_row, "aviso", "⚠️ Lista grande: Mostrando os 100 primeiros arquivos.", "", None, "Aviso", "#ffc107", "#242424")'''

new_loop = '''                for i, arquivo in enumerate(self.arquivos_para_baixar):
                    nome_arquivo = os.path.basename(arquivo.local_path) if getattr(arquivo, 'local_path', None) else f"Arquivo_{i}"
                    tamanho = self._format_size(os.path.getsize(arquivo.local_path)) if os.path.exists(arquivo.local_path) else "Desconhecido"
                    
                    if os.path.exists(arquivo.local_path) and os.path.getsize(arquivo.local_path) > 0:
                        self.after(0, self.add_file_row, arquivo.id, nome_arquivo, arquivo.local_path, "exists", "✅ Já existe", tamanho)
                        self.count_exists += 1
                    else:
                        arquivos_pendentes.append(arquivo)
                        self.after(0, self.add_file_row, arquivo.id, nome_arquivo, arquivo.local_path, "queue", "⏳ Aguardando", tamanho)
                        self.count_queue += 1
                        
                self.after(0, self.update_tabs)'''

content = content.replace(old_loop, new_loop)

# Replace add_file_row
old_add_row = '''    def add_file_row(self, file_id, filename, filepath, target_frame=None, initial_status="⏳ Aguardando", initial_color="#ffffff", initial_bg="#333333"):
        parent = target_frame if target_frame else self.queue_frame
        row_frame = ctk.CTkFrame(parent, fg_color=initial_bg)
        row_frame.pack(fill="x", padx=5, pady=2)
        
        status_lbl = ctk.CTkLabel(row_frame, text=initial_status, text_color=initial_color, font=ctk.CTkFont(size=12, weight="bold"), width=150, anchor="w")
        status_lbl.pack(side="left", padx=10, pady=5)
        
        name_lbl = ctk.CTkLabel(row_frame, text=filename, font=ctk.CTkFont(size=12))
        name_lbl.pack(side="left", padx=10, pady=5)
        
        def abrir_arquivo():
            if os.path.exists(filepath):
                os.startfile(filepath)
            else:
                import webbrowser
                webbrowser.open(f"https://drive.google.com/uc?export=download&id={file_id}")
                
        btn = ctk.CTkButton(row_frame, text="👁️", width=30, height=24, fg_color="#007bff", hover_color="#0056b3",
                            command=abrir_arquivo, font=ctk.CTkFont(size=14))
        btn.pack(side="right", padx=10, pady=5)
        
        self.file_labels[file_id] = (status_lbl, row_frame, btn, name_lbl, filename, filepath)'''

new_add_row = size_helper + '''
    def add_file_row(self, file_id, filename, filepath, target_tree_key="queue", initial_status="⏳ Aguardando", tamanho="Desconhecido"):
        tree = self.trees[target_tree_key]
        iid = tree.insert("", "end", values=(file_id, filename, tamanho, initial_status, "0%"))
        self.file_labels[file_id] = {"tree": target_tree_key, "iid": iid, "filename": filename, "filepath": filepath}
        
    def on_tree_double_click(self, event):
        tree = event.widget
        selected = tree.selection()
        if not selected: return
        file_id = tree.item(selected[0], "values")[0]
        
        if file_id in self.file_labels:
            filepath = self.file_labels[file_id]["filepath"]
            if os.path.exists(filepath):
                os.startfile(filepath)
            else:
                import webbrowser
                webbrowser.open(f"https://drive.google.com/uc?export=download&id={file_id}")'''

content = content.replace(old_add_row, new_add_row)

# Replace atualizar_status
old_status = '''    def atualizar_status(self, file_id, status_text, color, frame_color, is_highlighted=False, is_completed=False, is_failed=False, is_existing=False):
        if file_id in self.file_labels:
            lbl, frm, btn, name_lbl, filename, filepath = self.file_labels[file_id]
            
            if is_completed:
                frm.destroy()
                if self.ui_rendered < 150: # Evitar redesenhar infinito
                    self.add_file_row(file_id, filename, filepath, target_frame=self.completed_frame, initial_status=status_text, initial_color=color, initial_bg=frame_color)
                self.count_queue -= 1
                self.count_completed += 1
                self.update_tabs()
            elif is_existing:
                frm.destroy()
                if self.ui_rendered < 150:
                    self.add_file_row(file_id, filename, filepath, target_frame=self.exists_frame, initial_status=status_text, initial_color=color, initial_bg=frame_color)
                self.count_queue -= 1
                self.count_exists += 1
                self.update_tabs()
            elif is_failed:
                frm.destroy()
                if self.ui_rendered < 150:
                    self.add_file_row(file_id, filename, filepath, target_frame=self.failed_frame, initial_status=status_text, initial_color=color, initial_bg=frame_color)
                self.count_queue -= 1
                self.count_failed += 1
                self.update_tabs()
            else:
                lbl.configure(text=status_text, text_color=color)
                frm.configure(fg_color=frame_color)
                name_lbl.configure(font=ctk.CTkFont(size=13 if is_highlighted else 12, weight="bold" if is_highlighted else "normal"))'''

new_status = '''    def atualizar_status(self, file_id, status_text, color, frame_color, is_highlighted=False, is_completed=False, is_failed=False, is_existing=False, progresso=""):
        if file_id in self.file_labels:
            data = self.file_labels[file_id]
            current_tree_key = data["tree"]
            iid = data["iid"]
            tree = self.trees[current_tree_key]
            
            # Atualiza os valores
            vals = list(tree.item(iid, "values"))
            vals[3] = status_text
            if progresso:
                vals[4] = progresso
            tree.item(iid, values=vals)
            
            # Move para a aba correta se necessário
            new_tree_key = current_tree_key
            if is_completed: new_tree_key = "completed"
            elif is_existing: new_tree_key = "exists"
            elif is_failed: new_tree_key = "failed"
            
            if new_tree_key != current_tree_key:
                # Remove da arvore atual
                tree.delete(iid)
                # Insere na nova
                new_tree = self.trees[new_tree_key]
                new_iid = new_tree.insert("", "end", values=vals)
                self.file_labels[file_id]["tree"] = new_tree_key
                self.file_labels[file_id]["iid"] = new_iid
                
                self.count_queue -= 1
                if is_completed: self.count_completed += 1
                elif is_existing: self.count_exists += 1
                elif is_failed: self.count_failed += 1
                self.update_tabs()'''

content = content.replace(old_status, new_status)

with open('app.pyw', 'w', encoding='utf-8') as f:
    f.write(content)
