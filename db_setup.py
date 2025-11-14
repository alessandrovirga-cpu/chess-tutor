import sqlite3
import json

# Definiamo il nome del file del database
DB_NAME = 'chess_tutor.db'

def create_connection():
    """Crea una connessione al database SQLite specificato."""
    conn = None
    try:
        # Tenta di connettersi o creare il file del database se non esiste
        conn = sqlite3.connect(DB_NAME)
        # Permette l'accesso alle colonne per nome (come un dizionario)
        conn.row_factory = sqlite3.Row 
        return conn
    except sqlite3.Error as e:
        print(f"Errore durante la connessione al database: {e}")
        return None

def setup_database(conn):
    """Crea la tabella 'problems' se non esiste."""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS problems (
        id INTEGER PRIMARY KEY,
        fen TEXT NOT NULL,
        solution_moves TEXT,
        tags TEXT,
        last_reviewed REAL,
        next_review REAL NOT NULL,
        ease_factor REAL NOT NULL,
        interval_days INTEGER NOT NULL,
        review_count INTEGER NOT NULL
    );
    """
    try:
        cursor = conn.cursor()
        cursor.execute(create_table_sql)
        conn.commit()
        print("Tabella 'problems' creata o già esistente.")
    except sqlite3.Error as e:
        print(f"Errore durante la creazione della tabella: {e}")

if __name__ == '__main__':
    # 1. Connessione al database
    conn = create_connection()
    
    if conn:
        # 2. Setup della tabella
        setup_database(conn)
        
        # 3. Chiude la connessione
        conn.close()
        print(f"Database '{DB_NAME}' configurato con successo.")
    