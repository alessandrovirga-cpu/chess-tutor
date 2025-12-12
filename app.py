from flask import Flask, render_template, request, redirect, url_for, session, flash
import db_manager, db_setup
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
import random
import string
import os                     # <--- NUOVO IMPORT
from dotenv import load_dotenv # <--- NUOVO IMPORT

# Carica le variabili dal file .env
load_dotenv()

app = Flask(__name__)

# --- CONFIGURAZIONE SICUREZZA ---
# Ora prende il valore dal file .env. Se non lo trova, usa una stringa di default (per sicurezza)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'chiave-di-fallback-non-sicura')

# --- CONFIGURAZIONE EMAIL (GMAIL) ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True

# Qui leggiamo le credenziali del MITTENTE dal file .env
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')

# Opzionale: imposta il mittente di default per non doverlo ripetere nei messaggi
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

mail = Mail(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Se non sei loggato, ti manda qui

# --- UTENTE UNICO (Hardcoded per semplicità) ---
# In futuro potrai metterlo nel DB, ma per ora va bene così per uso personale.
# Password di esempio: "password_scacchi" (La hash è generata per sicurezza)
# --- UTENTE UNICO ---
MY_USER = {
    "id": "1",
    "username": "admin",
    # Puoi anche mettere la password hash nel .env se vuoi, ma per ora va bene qui
    "password_hash": generate_password_hash("password_scacchi"), 
    
    # Qui leggiamo la mail del DESTINATARIO (dove arriva il codice)
    "email": os.getenv('RECEIVER_EMAIL') 
}

# Modello Utente per Flask-Login
class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    if user_id == MY_USER['id']:
        return User(user_id)
    return None

# --- ROTTE DI AUTENTICAZIONE ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # 1. Verifica Username e Password
        if username == MY_USER['username'] and check_password_hash(MY_USER['password_hash'], password):
            
            # 2. Genera Codice OTP (One Time Password)
            otp_code = ''.join(random.choices(string.digits, k=6))
            
            # 3. Salva codice in sessione (temporaneo)
            session['otp'] = otp_code
            session['temp_user_id'] = MY_USER['id'] # Ricordiamo chi sta cercando di entrare
            
            # 4. Invia Email
            try:
                msg = Message('Codice Accesso Scacchi', sender=app.config['MAIL_USERNAME'], recipients=[MY_USER['email']])
                msg.body = f"Il tuo codice di verifica è: {otp_code}"
                mail.send(msg)
                flash('Credenziali corrette. Controlla la mail per il codice!', 'info')
                return redirect(url_for('verify_2fa'))
            except Exception as e:
                return f"Errore invio mail: {e}"
        
        flash('Username o Password errati.', 'error')
    
    return render_template('login.html')

@app.route('/verify_2fa', methods=['GET', 'POST'])
def verify_2fa():
    if 'otp' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        user_code = request.form.get('code')
        
        # 5. Verifica il codice
        if user_code == session.get('otp'):
            # LOGIN EFFETTIVO
            user = User(session['temp_user_id'])
            login_user(user)
            
            # Pulizia sessione
            session.pop('otp', None)
            session.pop('temp_user_id', None)
            
            return redirect(url_for('index'))
        else:
            flash('Codice errato. Riprova.', 'error')
            
    return render_template('verify_2fa.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- ROTTE DELL'APP (ORA PROTETTE) ---

@app.route('/')
@login_required  # <--- AGGIUNGI QUESTO A TUTTE LE ROTTE PROTETTE
def index():
    ready_problems = db_manager.get_problems_for_review()
    num_ready = len(ready_problems)
    return render_template('index.html', num_ready=num_ready)

@app.route('/review')
@login_required # <--- PROTEZIONE
def review_problem():
    ready_problems = db_manager.get_problems_for_review()
    if not ready_problems:
        return redirect(url_for('index'))
    problem = ready_problems[0]
    return render_template('review.html', problem=problem)

# --- Rotta 3: Inserimento di un Nuovo Problema (Testuale) ---
@app.route('/new', methods=['GET', 'POST'])
@login_required # Assicurati di mantenere il login_required se lo hai attivato
def new_problem():
    """
    Gestisce il modulo di inserimento testuale (FEN).
    """
    if request.method == 'POST':
        # 1. Recupera i dati base
        fen = request.form.get('fen')
        solution_str = request.form.get('solution')
        tags_str = request.form.get('tags')

        # 2. Recupera i nuovi dati opzionali (Dati Storici)
        white = request.form.get('white_player') or None
        black = request.form.get('black_player') or None
        year = request.form.get('game_year') or None
        tournament = request.form.get('tournament') or None
        winner = request.form.get('winner')

        # Conversione tipi
        if year: year = int(year)
        if winner is not None and winner != "": winner = int(winner)
        else: winner = None

        # 3. Pulizia liste
        solution_list = [m.strip() for m in solution_str.split(',') if m.strip()]
        tags_list = [t.strip() for t in tags_str.split(',') if t.strip()]

        # 4. Inserimento nel database
        if fen and solution_list:
            new_id = db_manager.insert_new_problem(
                fen, solution_list, tags_list,
                white_player=white, black_player=black,
                game_year=year, tournament=tournament, winner=winner
            )
            if new_id:
                return redirect(url_for('index'))
        
        return "Errore: FEN e Soluzione sono obbligatori.", 400
        
    return render_template('new_problem.html')

@app.route('/new_graphical', methods=['GET', 'POST'])
@login_required
def new_problem_graphical():
    if request.method == 'POST':
        fen = request.form.get('fen')
        solution_str = request.form.get('solution')
        tags_str = request.form.get('tags')
        
        # --- NUOVI CAMPI ---
        white = request.form.get('white_player') or None
        black = request.form.get('black_player') or None
        year = request.form.get('game_year') or None
        tournament = request.form.get('tournament') or None
        winner = request.form.get('winner') # Arriva come stringa "0" o "1" o None
        
        # Convertiamo anno e vincitore in interi se presenti
        if year: year = int(year)
        if winner is not None and winner != "": winner = int(winner)
        else: winner = None

        solution_list = [m.strip() for m in solution_str.split(',') if m.strip()]
        tags_list = [t.strip() for t in tags_str.split(',') if t.strip()]

        if fen and solution_list:
            # Passiamo i nuovi argomenti alla funzione aggiornata
            new_id = db_manager.insert_new_problem(
                fen, solution_list, tags_list,
                white_player=white, black_player=black,
                game_year=year, tournament=tournament, winner=winner
            )
            if new_id:
                return redirect(url_for('index'))
        
        return "Errore: Dati mancanti.", 400
    return render_template('new_graphical.html')

@app.route('/rate/<int:problem_id>', methods=['POST'])
@login_required # <--- PROTEZIONE
def rate_problem(problem_id):
    rating = request.form.get('rating') 
    if rating in ['Facile', 'Medio', 'Difficile', 'Sbagliato']:
        success = db_manager.update_problem_review(problem_id, rating)
        if success:
            return redirect(url_for('review_problem'))
    return "Errore.", 400

@app.route('/list')
@login_required # <--- PROTEZIONE
def problems_list():
    all_problems = db_manager.get_all_problems()
    return render_template('problems_list.html', problems=all_problems)

@app.template_filter('format_date')
def format_date(timestamp):
    from datetime import datetime
    if timestamp:
        return datetime.fromtimestamp(timestamp).strftime('%d/%m/%Y %H:%M')
    return "Mai"


# --- Rotta: Modifica Problema ---
@app.route('/edit/<int:problem_id>', methods=['GET', 'POST'])
@login_required
def edit_problem(problem_id):
    problem = db_manager.get_problem_by_id(problem_id)
    if not problem:
        return "Problema non trovato", 404

    if request.method == 'POST':
        # Recupera i dati dal form
        tags_str = request.form.get('tags')
        white = request.form.get('white_player') or None
        black = request.form.get('black_player') or None
        year = request.form.get('game_year') or None
        tournament = request.form.get('tournament') or None
        winner = request.form.get('winner')

        # Conversioni
        if year: year = int(year)
        if winner is not None and winner != "": winner = int(winner)
        else: winner = None
        
        tags_list = [t.strip() for t in tags_str.split(',') if t.strip()]

        # Aggiorna nel DB
        success = db_manager.update_problem_details(
            problem_id, tags_list, white, black, year, tournament, winner
        )
        
        if success:
            flash('Problema aggiornato con successo!', 'info')
            return redirect(url_for('problems_list'))
        else:
            flash('Errore durante l\'aggiornamento.', 'error')

    # Prepara i tag per la visualizzazione (da lista JSON a stringa separata da virgole)
    import json
    tags_list = json.loads(problem['tags']) if problem['tags'] else []
    problem['tags_str'] = ", ".join(tags_list)
    
    return render_template('edit_problem.html', problem=problem)

# --- Rotta: Elimina Problema ---
@app.route('/delete/<int:problem_id>', methods=['POST'])
@login_required
def delete_problem_route(problem_id):
    success = db_manager.delete_problem(problem_id)
    if success:
        flash('Problema eliminato definitivamente.', 'info')
    else:
        flash('Errore durante l\'eliminazione.', 'error')
    return redirect(url_for('problems_list'))

if __name__ == '__main__':
    conn = db_manager.create_connection()
    if conn:
        db_setup.setup_database(conn)
        conn.close()
    
    app.run(host='0.0.0.0', debug=True)