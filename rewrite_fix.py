import re

with open('app.pyw', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add self.completed_ids = set() to __init__
old_vars = '''        self.count_queue = 0
        self.count_completed = 0
        self.count_exists = 0
        self.count_failed = 0'''

new_vars = '''        self.count_queue = 0
        self.count_completed = 0
        self.count_exists = 0
        self.count_failed = 0
        self.completed_ids = set()'''

content = content.replace(old_vars, new_vars)

# 2. Add self.completed_ids.clear() to analyze_link_thread
old_clear = '''        self.count_queue = 0
        self.count_completed = 0
        self.count_exists = 0
        self.count_failed = 0
        self.update_tabs()'''

new_clear = '''        self.count_queue = 0
        self.count_completed = 0
        self.count_exists = 0
        self.count_failed = 0
        self.completed_ids.clear()
        self.update_tabs()'''

content = content.replace(old_clear, new_clear)

# 3. Fix download_worker to avoid Tkinter thread lock
old_skip = '''        # Pula se o arquivo já foi concluído antes
        if arquivo.id in self.file_labels:
            data = self.file_labels[arquivo.id]
            tree = self.trees[data["tree"]]
            try:
                status_atual = tree.item(data["iid"], "values")[3]
                if "✅" in status_atual:
                    return
            except:
                pass'''

new_skip = '''        # Pula se o arquivo já foi concluído antes
        if arquivo.id in self.completed_ids:
            return'''

content = content.replace(old_skip, new_skip)

# 4. Add to completed_ids on success
old_success = '''                self.after(0, self.atualizar_status, arquivo.id, "✅ Concluído", "#28a745", "#242424", False, True)
                self.log_entries.append(f"SUCESSO: {nome_arquivo}")
                sucesso = True'''

new_success = '''                self.after(0, self.atualizar_status, arquivo.id, "✅ Concluído", "#28a745", "#242424", False, True)
                self.log_entries.append(f"SUCESSO: {nome_arquivo}")
                self.completed_ids.add(arquivo.id)
                sucesso = True'''

content = content.replace(old_success, new_success)

# Also check for already existing before download
old_exists_fallback = '''        if os.path.exists(arquivo.local_path) and os.path.getsize(arquivo.local_path) > 0 and not self.cancel_event.is_set():
            # Apenas um fallback caso pule por já existir (se resume=False)
            pass '''

new_exists_fallback = '''        if os.path.exists(arquivo.local_path) and os.path.getsize(arquivo.local_path) > 0 and not self.cancel_event.is_set():
            self.completed_ids.add(arquivo.id)
            return'''

content = content.replace(old_exists_fallback, new_exists_fallback)

with open('app.pyw', 'w', encoding='utf-8') as f:
    f.write(content)
