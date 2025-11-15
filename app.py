from flask import Flask, render_template, request, redirect, url_for
import db_manager
import time

# --- Setup di Flask ---
app = Flask(__name__)

# --- Rotta 1: Pagina Iniziale / Dashboard ---
@app.route('/')
def index():
    """
    Mostra la dashboard e il conteggio dei problemi pronti per la revisione.
    """
    # 1. Recupera i problemi pronti per la revisione
    ready_problems = db_manager.get_problems_for_review()
    
    # 2. Ottiene il conteggio
    num_ready = len(ready_problems)
    
    return render_template('index.html', num_ready=num_ready)

# --- Rotta 2: Visualizzazione del Problema ---
@app.route('/review')
def review_problem():
    """
    Visualizza il problema scacchistico successivo da rivedere.
    """
    ready_problems = db_manager.get_problems_for_review()
    
    if not ready_problems:
        # Nessun problema pronto, reindirizza alla dashboard
        return redirect(url_for('index'))
    
    # Prende il primo problema nell'elenco (il più "scaduto")
    problem = ready_problems[0]
    
    # Nota: Dobbiamo passare i dati FEN alla pagina per visualizzare la scacchiera.
    return render_template(
        'review.html', 
        problem=problem
    )

# --- Rotta 3: Inserimento di un Nuovo Problema ---
@app.route('/new', methods=['GET', 'POST'])
def new_problem():
    """
    Gestisce il modulo di inserimento di un nuovo problema.
    """
    if request.method == 'POST':
        # 1. Recupera i dati dal modulo HTML
        fen = request.form.get('fen')
        solution_str = request.form.get('solution') # Es: "Nf3, Nc6"
        tags_str = request.form.get('tags')         # Es: "matto in 2, inchiodatura"

        # 2. Conversione dati per db_manager (liste)
        # Assumiamo che le mosse e i tag siano separati da virgole
        solution_list = [m.strip() for m in solution_str.split(',') if m.strip()]
        tags_list = [t.strip() for t in tags_str.split(',') if t.strip()]

        # 3. Inserimento nel database
        if fen and solution_list:
            new_id = db_manager.insert_new_problem(fen, solution_list, tags_list)
            if new_id:
                # Reindirizza alla dashboard o a una pagina di successo
                return redirect(url_for('index'))
        
        # Gestione errore (mostra un messaggio o reindirizza al modulo)
        return "Errore nell'inserimento del problema. FEN e Soluzione sono richiesti.", 400
        
    # Per la richiesta GET, mostra il modulo
    return render_template('new_problem.html')


# --- Rotta 4: Gestione della Valutazione (SM-2) ---
@app.route('/rate/<int:problem_id>', methods=['POST'])
def rate_problem(problem_id):
    """
    Riceve la valutazione dell'utente e aggiorna i parametri SM-2.
    """
    # Il rating viene inviato come valore del pulsante (es. 'Facile', 'Sbagliato')
    rating = request.form.get('rating') 
    
    if rating in ['Facile', 'Medio', 'Difficile', 'Sbagliato']:
        # Chiama la funzione di aggiornamento SM-2
        success = db_manager.update_problem_review(problem_id, rating)
        
        if success:
            # Dopo l'aggiornamento, torna alla pagina di revisione per vedere il prossimo
            return redirect(url_for('review_problem'))
            
    # Se la valutazione non è valida o l'aggiornamento fallisce
    return "Valutazione non valida o problema non aggiornato.", 400


# --- Esecuzione dell'App ---
if __name__ == '__main__':
    # Assicurati che il database esista all'avvio
    conn = db_manager.create_connection()
    if conn:
        db_manager.setup_database(conn)
        conn.close()
    
    # Avvia il server Flask in modalità debug
    app.run(debug=True)
