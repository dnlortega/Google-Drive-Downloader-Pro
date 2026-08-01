import re

with open('app.pyw', 'r', encoding='utf-8') as f:
    content = f.read()

# Update download_worker status logic
old_custom_progress = '''            if elapsed > 1.0:
                speed = (bytes_so_far - local_state['last_speed_bytes']) / elapsed if elapsed > 0 else 0
                local_state['last_speed_bytes'] = bytes_so_far
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
                self.after(0, self.atualizar_status, arquivo.id, status_text, "#00ffff", "#1f538d", True)'''

new_custom_progress = '''            if elapsed > 1.0:
                speed = (bytes_so_far - local_state['last_speed_bytes']) / elapsed if elapsed > 0 else 0
                local_state['last_speed_bytes'] = bytes_so_far
                local_state['last_time'] = current_time
                
                if speed > 1024 * 1024:
                    speed_str = f"{speed / (1024 * 1024):.1f} MB/s"
                else:
                    speed_str = f"{speed / 1024:.1f} KB/s"
                    
                percentage = (bytes_so_far / bytes_total * 100) if bytes_total else 0
                prog_text = f"{percentage:.0f}% | {speed_str}" if percentage > 0 else f"{speed_str}"
                
                self.after(0, self.atualizar_status, arquivo.id, "🔄 Baixando...", "#00ffff", "#1f538d", True, False, False, False, prog_text)'''

content = content.replace(old_custom_progress, new_custom_progress)

# Fix `if arquivo.id in self.file_labels and "✅" in self.file_labels[arquivo.id][0].cget("text"):` 
# because file_labels now only contains dict with reference, not UI widgets!
# We can check the Treeview item status text.
old_skip = '''        # Pula se o arquivo já foi concluído antes
        if arquivo.id in self.file_labels and "✅" in self.file_labels[arquivo.id][0].cget("text"):
            return'''

new_skip = '''        # Pula se o arquivo já foi concluído antes
        if arquivo.id in self.file_labels:
            data = self.file_labels[arquivo.id]
            tree = self.trees[data["tree"]]
            try:
                status_atual = tree.item(data["iid"], "values")[3]
                if "✅" in status_atual:
                    return
            except:
                pass'''

content = content.replace(old_skip, new_skip)

with open('app.pyw', 'w', encoding='utf-8') as f:
    f.write(content)
