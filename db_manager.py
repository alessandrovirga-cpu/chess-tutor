import sqlite3
import json
import time # Useremo il timestamp Unix (REALE in SQLite) per le date
from datetime import datetime, timedelta # Useremo timedelta per calcolare la data futura

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
    example_fen = "3R4/8/8/8/8/3R4/8/3K2R1 w - - 0 1"
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

# Costanti iniziali per l'algoritmo SM-2
INITIAL_EASE_FACTOR = 2.5
FIRST_INTERVAL = 1
SECOND_INTERVAL = 6
# I punteggi di qualità (q)
Q_WRONG = 0 # Sbagliato (e reset)
Q_DIFFICULT = 3
Q_MEDIUM = 4
Q_EASY = 5

def calculate_sm2(quality_rating: int, current_ease_factor: float, current_interval: int, review_count: int) -> tuple[int, float, int]:
    """
    Calcola il nuovo intervallo, il nuovo fattore di facilità e il nuovo conteggio
    secondo l'algoritmo SuperMemo-2.
    """
    
    new_ease_factor = current_ease_factor + (0.1 - (5 - quality_rating) * (0.08 + (5 - quality_rating) * 0.02))
    new_ease_factor = max(1.3, new_ease_factor) # E' non può essere inferiore a 1.3
    
    new_review_count = review_count

    if quality_rating < 3:
        # Se l'utente sbaglia, l'intervallo viene resettato e il contatore azzerato.
        new_interval = 0
        new_review_count = 0
    else:
        # Risposta corretta (q >= 3)
        if review_count == 0:
            new_interval = FIRST_INTERVAL  # 1 giorno
        elif review_count == 1:
            new_interval = SECOND_INTERVAL # 6 giorni
        else:
            # I' = I * E' (arrotondato)
            new_interval = round(current_interval * new_ease_factor)
        
        # Incrementiamo il contatore solo per le risposte corrette
        new_review_count += 1

    return new_interval, new_ease_factor, new_review_count

# ----------------------------------------------------------------------
# NUOVA FUNZIONE PER L'AGGIORNAMENTO
# ----------------------------------------------------------------------

def update_problem_review(problem_id: int, user_rating_key: str) -> bool:
    """
    Aggiorna i parametri SM-2 per un problema specifico dopo la revisione dell'utente.

    :param problem_id: L'ID del problema da aggiornare.
    :param user_rating_key: La valutazione dell'utente ('Sbagliato', 'Difficile', 'Medio', 'Facile').
    :return: True se l'aggiornamento ha avuto successo, False altrimenti.
    """
    conn = create_connection()
    if conn is None:
        return False
    
    # Mappiamo il feedback dell'utente al punteggio di qualità (q)
    RATING_MAP = {
        'Sbagliato': Q_WRONG,
        'Difficile': Q_DIFFICULT,
        'Medio': Q_MEDIUM,
        'Facile': Q_EASY
    }
    quality_rating = RATING_MAP.get(user_rating_key, Q_WRONG) # Usa 0 se la chiave non è valida

    # 1. Recupera i dati correnti del problema dal DB
    fetch_sql = "SELECT ease_factor, interval_days, review_count FROM problems WHERE id = ?"
    
    try:
        cursor = conn.cursor()
        cursor.execute(fetch_sql, (problem_id,))
        row = cursor.fetchone()
        
        if not row:
            print(f"Errore: Problema con ID {problem_id} non trovato.")
            return False
            
        current_data = dict(row)
        
        # 2. Calcola i nuovi parametri SM-2
        new_interval, new_ease_factor, new_review_count = calculate_sm2(
            quality_rating,
            current_data['ease_factor'],
            current_data['interval_days'],
            current_data['review_count']
        )
        
        # 3. Calcola la prossima data di revisione (next_review)
        # Convertiamo l'intervallo in secondi e lo aggiungiamo al tempo corrente
        current_time = datetime.now()
        # Se l'intervallo è 0 (Sbagliato), lo impostiamo al giorno successivo per riproporre
        # il problema velocemente, o manteniamo l'intervallo calcolato.
        
        if new_interval == 0:
             # Ri-proponi il problema il giorno stesso o il giorno dopo (qui lo teniamo subito pronto)
             next_review_datetime = current_time 
        else:
             next_review_datetime = current_time + timedelta(days=new_interval)
             
        # Convertiamo la prossima data di revisione in timestamp Unix
        next_review_timestamp = next_review_datetime.timestamp()
        
        # 4. Aggiorna il DB
        update_sql = """
        UPDATE problems 
        SET 
            last_reviewed = ?, 
            next_review = ?, 
            ease_factor = ?, 
            interval_days = ?, 
            review_count = ?
        WHERE id = ?
        """
        
        update_params = (
            current_time.timestamp(),  # last_reviewed (ora)
            next_review_timestamp,     # next_review (la data calcolata)
            new_ease_factor,
            new_interval,
            new_review_count,
            problem_id
        )
        
        cursor.execute(update_sql, update_params)
        conn.commit()
        return True
        
    except sqlite3.Error as e:
        print(f"Errore durante l'aggiornamento del problema: {e}")
        return False
    finally:
        conn.close()

# --- Esempio di Utilizzo della Funzione ---

if __name__ == '__main__':
    # Assumiamo che il problema con ID 1 esista (se hai eseguito l'esempio precedente)
    test_id = 1
    
    print(f"\n--- Aggiornamento Problema ID {test_id} ---")
    
    # Simula la prima revisione: Utente risponde 'Medio'
    success = update_problem_review(test_id, 'Medio')
    
    if success:
        print("Aggiornamento 1 (Medio) riuscito.")
        # Simula la seconda revisione (dopo 1 giorno): Utente risponde 'Facile'
        # Nota: L'intervallo calcolato sarà basato sul nuovo 'ease_factor'
        success_2 = update_problem_review(test_id, 'Facile')
        if success_2:
            print("Aggiornamento 2 (Facile) riuscito.")
            print("Controlla il DB per i valori aggiornati (next_review, ease_factor).")
        
        # Simula una revisione fallita: Utente risponde 'Sbagliato'
        success_fail = update_problem_review(test_id, 'Sbagliato')
        if success_fail:
            print("Aggiornamento 3 (Sbagliato) riuscito. Il problema è pronto per la riproposta immediata.")
