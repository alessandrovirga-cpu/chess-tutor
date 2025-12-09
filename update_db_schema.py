import sqlite3

DB_NAME = 'chess_tutor.db'

def add_columns():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Elenco delle nuove colonne e dei loro tipi
    new_columns = [
        ("white_player", "TEXT"),
        ("black_player", "TEXT"),
        ("game_year", "INTEGER"),
        ("tournament", "TEXT"),
        ("winner", "INTEGER") # 0 = Bianco, 1 = Nero
    ]
    
    print("Inizio aggiornamento database...")
    
    for col_name, col_type in new_columns:
        try:
            # Tenta di aggiungere la colonna
            cursor.execute(f"ALTER TABLE problems ADD COLUMN {col_name} {col_type}")
            print(f"Colonna '{col_name}' aggiunta con successo.")
        except sqlite3.OperationalError as e:
            # Se l'errore è "duplicate column name", ignoriamo
            if "duplicate column name" in str(e):
                print(f"Colonna '{col_name}' esiste già. Salto.")
            else:
                print(f"Errore aggiungendo '{col_name}': {e}")

    conn.commit()
    conn.close()
    print("Database aggiornato!")

if __name__ == "__main__":
    add_columns()