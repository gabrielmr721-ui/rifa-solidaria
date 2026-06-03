import os
import psycopg2
from psycopg2.extras import DictCursor
from flask import Flask, render_template, request, redirect, session
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'chave-secreta-provisoria-rifa')

# Pega a URL do Render ou o plano B do Supabase
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:973776580Ga@db.ymqrwojkrxgozpygdjvb.supabase.co:5432/postgres')

def get_db():
    if DATABASE_URL:
        # Força o uso de SSL requerido pelo Supabase para evitar rejeição de conexão
        if "sslmode" not in DATABASE_URL:
            connect_url = DATABASE_URL + "?sslmode=require"
        else:
            connect_url = DATABASE_URL
        conn = psycopg2.connect(connect_url, cursor_factory=DictCursor)
        return conn
    else:
        import sqlite3
        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Cria a tabela no formato padrão do PostgreSQL
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS numeros (
            id INTEGER PRIMARY KEY,
            nome TEXT DEFAULT NULL,
            fone TEXT DEFAULT NULL
        )
    ''')
    
    cursor.execute('SELECT COUNT(*) FROM numeros')
    row = cursor.fetchone()
    count = row[0] if row else 0
    
    if count == 0:
        for i in range(1, 101):
            if DATABASE_URL:
                cursor.execute('INSERT INTO numeros (id) VALUES (%s)', (i,))
            else:
                cursor.execute('INSERT INTO numeros (id) VALUES (?)', (i,))
                
    conn.commit()
    cursor.close()
    conn.close()

# Executa com tratamento para não derrubar o app se o banco demorar a responder
try:
    init_db()
except Exception as e:
    print(f"Erro ao inicializar o banco de dados: {e}")

@app.route('/')
def index():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM numeros ORDER BY id ASC')
    numeros = cursor.fetchall()
    
    cursor.execute('SELECT COUNT(*) FROM numeros WHERE nome IS NOT NULL')
    row = cursor.fetchone()
    vendidos = row[0] if row else 0
    livres = 100 - vendidos
    
    cursor.close()
    conn.close()
    return render_template('index.html', numeros=numeros, vendidos=vendidos, livres=livres)

@app.route('/reservar/<int:numero_id>')
def tela_reserva(numero_id):
    return render_template('reservar.html', numero_id=numero_id)

@app.route('/reservar', methods=['POST'])
def reservar():
    numero_id = request.form.get('numero_id')
    nome = request.form.get('nome')
    fone = request.form.get('fone')
    
    conn = get_db()
    cursor = conn.cursor()
    
    if DATABASE_URL:
        cursor.execute('SELECT nome FROM numeros WHERE id = %s', (numero_id,))
        atual = cursor.fetchone()
        if atual and atual[0] is not None:
            return "Este número já foi reservado por outra pessoa! Volte e escolha outro.", 400
            
        cursor.execute('UPDATE numeros SET nome = %s, fone = %s WHERE id = %s', (nome, fone, numero_id))
    else:
        cursor.execute('SELECT nome FROM numeros WHERE id = ?', (numero_id,))
        atual = cursor.fetchone()
        if atual and atual['nome'] is not None:
            return "Este número já foi reservado por outra pessoa! Volte e escolha outro.", 400
            
        cursor.execute('UPDATE numeros SET nome = ?, fone = ? WHERE id = ?', (nome, fone, numero_id))
        
    conn.commit()
    cursor.close()
    conn.close()
    return render_template('sucesso.html', nome=nome, fone=fone, numero=numero_id)

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        senha_digitada = request.form.get('senha')
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
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM numeros ORDER BY id ASC')
    numeros = cursor.fetchall()
    
    cursor.execute('SELECT COUNT(*) FROM numeros WHERE nome IS NOT NULL')
    row = cursor.fetchone()
    vendidos = row[0] if row else 0
    
    cursor.close()
    conn.close()
    return render_template('painel.html', numeros=numeros, vendidos=vendidos)

@app.route('/venda_manual', methods=['POST'])
def venda_manual():
    if not session.get('admin_logado'):
        return redirect('/admin')
        
    nome = request.form.get('nome')
    fone = request.form.get('fone')
    numero_id = request.form.get('numero')
    
    conn = get_db()
    cursor = conn.cursor()
    if DATABASE_URL:
        cursor.execute('UPDATE numeros SET nome = %s, fone = %s WHERE id = %s', (nome, fone, numero_id))
    else:
        cursor.execute('UPDATE numeros SET nome = ?, fone = ? WHERE id = ?', (nome, fone, numero_id))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect('/painel')

@app.route('/liberar/<int:numero_id>')
def liberar(numero_id):
    if not session.get('admin_logado'):
        return redirect('/admin')
        
    conn = get_db()
    cursor = conn.cursor()
    if DATABASE_URL:
        cursor.execute('UPDATE numeros SET nome = NULL, fone = NULL WHERE id = %s', (numero_id,))
    else:
        cursor.execute('UPDATE numeros SET nome = NULL, fone = NULL WHERE id = ?', (numero_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect('/painel')

@app.route('/resetar')
def resetar():
    if not session.get('admin_logado'):
        return redirect('/admin')
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE numeros SET nome = NULL, fone = NULL')
    conn.commit()
    cursor.close()
    conn.close()
    return redirect('/painel')

@app.route('/logout')
def logout():
    session.pop('admin_logado', None)
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)