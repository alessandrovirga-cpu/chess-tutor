import sqlite3
import json
import time # Useremo il timestamp Unix (REALE in SQLite) per le date

# Definiamo il nome del file del database
DB_NAME = 'chess_tutor.db'

# Costanti iniziali per l'algoritmo SM-2
INITIAL_EASE_FACTOR = 2.5
INITIAL_INTERVAL = 0 # Il problema è subito pronto per la prima revisione
INITIAL_REVIEW_COUNT = 0

def create_connection():
    """Crea una connessione al database SQLite e imposta row_factory."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row 
        return conn
    except sqlite3.Error as e:
        print(f"Errore durante la connessione al database: {e}")
        return None

def insert_new_problem(fen: str, solution_moves: list, tags: list):
    """
    Inserisce un nuovo problema scacchistico nel database con i valori SM-2 iniziali.

    :param fen: La posizione scacchistica in notazione FEN.
    :param solution_moves: La sequenza di mosse di soluzione (lista di stringhe).
    :param tags: La lista dei tag tattici (lista di stringhe).
    :return: L'ID del nuovo problema inserito o None in caso di errore.
    """
    conn = create_connection()
    if conn is None:
        return None

    # 1. Preparazione dei Dati
    
    # SQLite non gestisce liste. Convertiamo liste in stringhe JSON.
    solution_json = json.dumps(solution_moves)
    tags_json = json.dumps(tags)
    
    # La data di "next_review" è impostata a "ora" (timestamp Unix) in modo
    # che il problema sia immediatamente disponibile per l'utente.
    current_timestamp = time.time() 

    # 2. Definizione della Query SQL
    sql = """
    INSERT INTO problems (
        fen, solution_moves, tags, 
        last_reviewed, next_review, ease_factor, 
        interval_days, review_count
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    # 3. Parametri da inserire
    params = (
        fen,
        solution_json,
        tags_json,
        current_timestamp,           # last_reviewed (prima volta)
        current_timestamp,           # next_review (subito pronto)
        INITIAL_EASE_FACTOR,         # ease_factor (inizia a 2.5)
        INITIAL_INTERVAL,            # interval_days (inizia a 0)
        INITIAL_REVIEW_COUNT         # review_count (inizia a 0)
    )

    # 4. Esecuzione della Query
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        # Restituisce l'ID della riga appena inserita
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Errore durante l'inserimento del problema: {e}")
        return None
    finally:
        conn.close()


# --- Esempio di Utilizzo della Funzione ---

if __name__ == '__main__':
    # Eseguiamo solo se la tabella esiste già, se non l'hai creata,
    # esegui prima la funzione di setup da db_setup.py.
    
    # Dati di esempio (Matto in uno)
    example_fen = "8/8/8/8/8/3R4/8/3K2R1 w - - 0 1"
    example_solution = ["Rg8#"]
    example_tags = ["matto in 1", "sacrificio", "tattica base"]
    
    new_id = insert_new_problem(example_fen, example_solution, example_tags)

    if new_id:
        print(f"Problema scacchistico inserito con ID: {new_id}")
    else:
        print("Inserimento fallito.")

def get_problems_for_review():
    """
    Recupera tutti i problemi dal database la cui data di revisione
    (next_review) è passata o è il momento attuale.

    :return: Una lista di problemi (come dizionari Python), o una lista vuota.
    """
    conn = create_connection()
    if conn is None:
        return []

    # 1. Otteniamo il timestamp corrente
    current_timestamp = time.time()
    
    # 2. Query SQL per selezionare i problemi
    # Selezioniamo tutti i problemi dove 'next_review' è MINORE O UGUALE al tempo attuale.
    sql = """
    SELECT * FROM problems 
    WHERE next_review <= ?
    ORDER BY next_review ASC; -- Ordina per data, per dare priorità ai problemi più vecchi
    """
    
    problems = []
    
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (current_timestamp,))
        
        # 3. Processiamo i risultati
        rows = cursor.fetchall()
        
        for row in rows:
            # Convertiamo l'oggetto Row di SQLite in un dizionario Python
            problem = dict(row)
            
            # Convertiamo le stringhe JSON di tags e solution_moves in liste Python
            problem['solution_moves'] = json.loads(problem['solution_moves'])
            problem['tags'] = json.loads(problem['tags'])
            
            problems.append(problem)
            
        return problems
        
    except sqlite3.Error as e:
        print(f"Errore durante il recupero dei problemi: {e}")
        return []
    finally:
        conn.close()


# --- Esempio di Utilizzo della Funzione ---

if __name__ == '__main__':
    # Assicurati di aver eseguito una volta la funzione insert_new_problem() 
    # per avere dati di test nel database.
    
    # Inseriamo un problema che sarà immediatamente disponibile (se non l'hai già fatto)
    # example_fen = "8/8/8/8/8/3R4/8/3K2R1 w - - 0 1"
    # insert_new_problem(example_fen, ["Rg8#"], ["matto in 1"])
    
    print("\n--- Problemi pronti per la revisione ---")
    ready_problems = get_problems_for_review()
    
    if ready_problems:
        print(f"Trovati {len(ready_problems)} problemi pronti.")
        for p in ready_problems:
            # Stampa solo i campi chiave per la verifica
            print(f"ID: {p['id']}, FEN: {p['fen'][:20]}..., Prossima Revisione: {p['next_review']}")
    else:
        print("Nessun problema pronto per la revisione.")

