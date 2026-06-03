import os
import sqlite3
from flask import Flask, render_template, request, redirect, session
from dotenv import load_dotenv

# Carrega as variáveis do arquivo oculto .env
load_dotenv()

app = Flask(__name__)
# Chave secreta para gerenciar os cookies da sessão de forma segura
app.secret_key = os.getenv('SECRET_KEY', 'chave-secreta-provisoria-rifa')

DATABASE = 'database.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS numeros (
                id INTEGER PRIMARY KEY,
                nome TEXT DEFAULT NULL,
                fone TEXT DEFAULT NULL
            )
        ''')
        # Garante a criação de 100 números caso o banco esteja vazio
        cursor = conn.execute('SELECT COUNT(*) FROM numeros')
        if cursor.fetchone()[0] == 0:
            for i in range(1, 101):
                conn.execute('INSERT INTO numeros (id) VALUES (?)', (i,))
        conn.commit()

init_db()

@app.route('/')
def index():
    with get_db() as conn:
        numeros = conn.execute('SELECT * FROM numeros').fetchall()
        vendidos = conn.execute('SELECT COUNT(*) FROM numeros WHERE nome IS NOT NULL').fetchone()[0]
        livres = 100 - vendidos
    return render_template('index.html', numeros=numeros, vendidos=vendidos, livres=livres)

@app.route('/reservar/<int:numero_id>')
def tela_reserva(numero_id):
    return render_template('reservar.html', numero_id=numero_id)

@app.route('/reservar', method=['POST'])
def reservar():
    numero_id = request.form.get('numero_id')
    nome = request.form.get('nome')
    fone = request.form.get('fone')
    
    with get_db() as conn:
        # Verifica se o número já não foi comprado por outra pessoa nesse meio tempo
        atual = conn.execute('SELECT nome FROM numeros WHERE id = ?', (numero_id,)).fetchone()
        if atual and atual['nome'] is not None:
            return "Este número já foi reservado por outra pessoa! Volte e escolha outro.", 400
            
        conn.execute('UPDATE numeros SET nome = ?, fone = ? WHERE id = ?', (nome, fone, numero_id))
        conn.commit()
        
    return render_template('sucesso.html', nome=nome, fone=fone, numero=numero_id)

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        senha_digitada = request.form.get('senha')
        # Busca a senha segura da variável de ambiente (Usa 'Eugenio' como plano B caso não ache)
        senha_correta = os.getenv('ADMIN_PASSWORD', 'Eugenio')
        
        if senha_digitada == senha_correta:
            session['admin_logado'] = True
            return redirect('/painel')
        else:
            return render_template('admin.html', erro=True)
            
    return render_template('admin.html', erro=False)

@app.route('/painel')
def painel():
    if not session.get('admin_logado'):
        return redirect('/admin')
        
    with get_db() as conn:
        numeros = conn.execute('SELECT * FROM numeros').fetchall()
        vendidos = conn.execute('SELECT COUNT(*) FROM numeros WHERE nome IS NOT NULL').fetchone()[0]
        
    return render_template('painel.html', numeros=numeros, vendidos=vendidos)

@app.route('/venda_manual', methods=['POST'])
def venda_manual():
    if not session.get('admin_logado'):
        return redirect('/admin')
        
    nome = request.form.get('nome')
    fone = request.form.get('fone')
    numero_id = request.form.get('numero')
    
    with get_db() as conn:
        conn.execute('UPDATE numeros SET nome = ?, fone = ? WHERE id = ?', (nome, fone, numero_id))
        conn.commit()
        
    return redirect('/painel')

@app.route('/liberar/<int:numero_id>')
def liberar(numero_id):
    if not session.get('admin_logado'):
        return redirect('/admin')
        
    with get_db() as conn:
        conn.execute('UPDATE numeros SET nome = NULL, fone = NULL WHERE id = ?', (numero_id,))
        conn.commit()
        
    return redirect('/painel')

@app.route('/resetar')
def resetar():
    if not session.get('admin_logado'):
        return redirect('/admin')
        
    with get_db() as conn:
        conn.execute('UPDATE numeros SET nome = NULL, fone = NULL')
        conn.commit()
        
    return redirect('/painel')

@app.route('/logout')
def logout():
    session.pop('admin_logado', None)
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)