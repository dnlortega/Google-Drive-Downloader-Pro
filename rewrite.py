import re

with open('app.pyw', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('from tkinter import filedialog', 'from tkinter import filedialog, ttk')

old_init = '''        self.tabview = ctk.CTkTabview(self, height=320)
        self.tabview.grid(row=7, column=0, padx=20, pady=(0, 15), sticky="nsew")
        self.tabview.add(self.tab_names["queue"])
        self.tabview.add(self.tab_names["completed"])
        self.tabview.add(self.tab_names["exists"])
        self.tabview.add(self.tab_names["failed"])
        
        self.queue_frame = ctk.CTkScrollableFrame(self.tabview.tab(self.tab_names["queue"]), fg_color="transparent")
        self.queue_frame.pack(fill="both", expand=True)
        
        self.completed_frame = ctk.CTkScrollableFrame(self.tabview.tab(self.tab_names["completed"]), fg_color="transparent")
        self.completed_frame.pack(fill="both", expand=True)
        
        self.exists_frame = ctk.CTkScrollableFrame(self.tabview.tab(self.tab_names["exists"]), fg_color="transparent")
        self.exists_frame.pack(fill="both", expand=True)
        
        self.failed_frame = ctk.CTkScrollableFrame(self.tabview.tab(self.tab_names["failed"]), fg_color="transparent")
        self.failed_frame.pack(fill="both", expand=True)'''

new_init = '''        self.tabview = ctk.CTkTabview(self, height=320)
        self.tabview.grid(row=7, column=0, padx=20, pady=(0, 15), sticky="nsew")
        
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("Treeview", 
                        background="#2b2b2b",
                        foreground="white",
                        rowheight=30,
                        fieldbackground="#2b2b2b",
                        bordercolor="#343638",
                        borderwidth=0,
                        font=("Inter", 11))
        style.map('Treeview', background=[('selected', '#22559b')])
        
        style.configure("Treeview.Heading", 
                        background="#565b5e", 
                        foreground="white", 
                        relief="flat", 
                        font=("Inter", 12, "bold"))
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
            self.trees[key] = tree'''

content = content.replace(old_init, new_init)

with open('app.pyw', 'w', encoding='utf-8') as f:
    f.write(content)
