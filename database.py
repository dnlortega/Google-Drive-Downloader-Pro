import sqlite3
import os
import json
from datetime import datetime

DB_FILE = "downloads_db.sqlite3"
OLD_HISTORY_FILE = "history.json"

def get_connection():
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT,
            file_name TEXT,
            file_path TEXT,
            status TEXT,
            file_size TEXT,
            download_date DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    migrate_old_history()

def migrate_old_history():
    # Only migrate old URLs that were stored in history.json
    if os.path.exists(OLD_HISTORY_FILE):
        try:
            with open(OLD_HISTORY_FILE, "r") as f:
                historico = json.load(f)
            
            conn = get_connection()
            cursor = conn.cursor()
            for url in historico:
                # Check if it exists to avoid duplicates during migration
                cursor.execute("SELECT id FROM history WHERE url = ?", (url,))
                if not cursor.fetchone():
                    cursor.execute("INSERT INTO history (url, file_name, file_path, status, file_size) VALUES (?, ?, ?, ?, ?)", (url, "Desconhecido", "", "Migrado", "0 B"))
            conn.commit()
            conn.close()
            os.remove(OLD_HISTORY_FILE) # Remove after migration
        except Exception as e:
            print(f"Erro ao migrar historico: {e}")

def add_to_history(url, file_name, file_path, status, file_size):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO history (url, file_name, file_path, status, file_size)
            VALUES (?, ?, ?, ?, ?)
        ''', (url, file_name, file_path, status, file_size))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Erro ao salvar historico: {e}")

def get_recent_urls(limit=5):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT url FROM history 
            ORDER BY download_date DESC 
            LIMIT ?
        ''', (limit,))
        urls = [row[0] for row in cursor.fetchall() if row[0]]
        conn.close()
        return urls
    except Exception as e:
        print(f"Erro ao buscar URLs: {e}")
        return []

def get_full_history():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT url, file_name, file_path, status, file_size, download_date 
            FROM history 
            ORDER BY download_date DESC
        ''')
        records = cursor.fetchall()
        conn.close()
        return records
    except Exception as e:
        print(f"Erro ao buscar historico completo: {e}")
        return []
