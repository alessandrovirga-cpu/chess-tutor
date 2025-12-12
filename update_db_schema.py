import sqlite3

DB_NAME = 'chess_tutor.db'

def add_list_column():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # Aggiungiamo la colonna per il nome della lista
        cursor.execute("ALTER TABLE problems ADD COLUMN custom_list TEXT")
        print("Colonna 'custom_list' aggiunta con successo.")
    except sqlite3.OperationalError as e:
        print(f"Errore o colonna già esistente: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    add_list_column()