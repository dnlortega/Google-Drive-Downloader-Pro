import re

with open('app.pyw', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('        self.analyze_button.configure(state="disabled")\\n', '')
content = content.replace('        self.download_button.configure(state="disabled")\\n', '')
content = content.replace('        self.analyze_button.configure(state="disabled")', '')
content = content.replace('        self.download_button.configure(state="disabled")', '')
content = content.replace('self.after(0, lambda: self.analyze_button.configure(state="normal"))', '')

with open('app.pyw', 'w', encoding='utf-8') as f:
    f.write(content)
