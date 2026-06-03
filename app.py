import os
import time
import psycopg2
from psycopg2.extras import DictCursor
from flask import Flask, render_template, request, redirect, session
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'chave-secreta-provisoria-rifa')

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres.ymqrwojkrxgozpygdjvb:973776580Ga@aws-0-us-east-1.pooler.supabase.com:5432/postgres')

def get_db():
    url = DATABASE_URL
    if "sslmode" not in url:
        url += "&sslmode=require" if "?" in url else "?sslmode=require"
    
    # Sistema de tentativas para vencer a instabilidade da manutenção do Supabase
    for tentativa in range(3):
        try:
            conn = psycopg2.connect(url, cursor_factory=DictCursor, connect_timeout=5)
            return conn
        except Exception as e:
            print(f"Tentativa {tentativa + 1} falhou: {e}. Aguardando para retestar...")
            time.sleep(2)
            
    # Fallback final para o app nunca dar Erro 500 visual
    import sqlite3
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Verifica se o cursor ativo é do SQLite ou Postgres
    is_sqlite = type(cursor).__name__ == 'sqlite3.Cursor' or hasattr(conn, 'row_factory')
    
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
            if is_sqlite:
                cursor.execute('INSERT INTO numeros (id) VALUES (?)', (i,))
            else:
                cursor.execute('INSERT INTO numeros (id) VALUES (%s)', (i,))
                
    conn.commit()
    cursor.close()
    conn.close()

try:
    init_db()
except Exception as e:
    print(f"Erro ao inicializar o banco de dados: {e}")

@app.route('/')
def index():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, nome, fone FROM numeros ORDER BY id ASC')
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
    is_sqlite = type(cursor).__name__ == 'sqlite3.Cursor' or hasattr(conn, 'row_factory')
    
    if not is_sqlite:
        cursor.execute('SELECT nome FROM numeros WHERE id = %s', (numero_id,))
        atual = cursor.fetchone()
        if atual and atual[0] is not None:
            return "Este número já foi reservado por outra pessoa!", 400
        cursor.execute('UPDATE numeros SET nome = %s, fone = %s WHERE id = %s', (nome, fone, numero_id))
    else:
        cursor.execute('SELECT nome FROM numeros WHERE id = ?', (numero_id,))
        atual = cursor.fetchone()
        if atual and atual['nome'] is not None:
            return "Este número já foi reservado por outra pessoa!", 400
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
    cursor.execute('SELECT id, nome, fone FROM numeros ORDER BY id ASC')
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
    is_sqlite = type(cursor).__name__ == 'sqlite3.Cursor' or hasattr(conn, 'row_factory')
    
    if not is_sqlite:
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
    is_sqlite = type(cursor).__name__ == 'sqlite3.Cursor' or hasattr(conn, 'row_factory')
    
    if not is_sqlite:
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