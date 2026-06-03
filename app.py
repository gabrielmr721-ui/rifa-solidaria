import os
import psycopg2
from psycopg2.extras import DictCursor
from flask import Flask, render_template, request, redirect, session
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'chave-secreta-provisoria-rifa')

# Busca a variável configurada no Render. Se não achar, usa o link direto do Supabase como plano B.
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:973776580Ga@db.ymqrwojkrxgozpygdjvb.supabase.co:5432/postgres')

def get_db():
    if DATABASE_URL:
        # Conecta no PostgreSQL do Supabase (Nuvem Permanente)
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=DictCursor)
        return conn
    else:
        # Caso não encontre nenhum link (Segurança para não quebrar)
        import sqlite3
        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Cria a tabela caso ela não exista no Supabase
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS numeros (
            id INTEGER PRIMARY KEY,
            nome TEXT DEFAULT NULL,
            fone TEXT DEFAULT NULL
        )
    ''')
    
    # Verifica se o banco está vazio para criar as 100 cotas da rifa
    cursor.execute('SELECT COUNT(*) FROM numeros')
    if cursor.fetchone()[0] == 0:
        for i in range(1, 101):
            if DATABASE_URL:
                cursor.execute('INSERT INTO numeros (id) VALUES (%s)', (i,))
            else:
                cursor.execute('INSERT INTO numeros (id) VALUES (?)', (i,))
                
    conn.commit()
    cursor.close()
    conn.close()

# Executa a inicialização do banco de dados na nuvem
init_db()

@app.route('/')
def index():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM numeros ORDER BY id ASC')
    numeros = cursor.fetchall()
    
    cursor.execute('SELECT COUNT(*) FROM numeros WHERE nome IS NOT NULL')
    vendidos = cursor.fetchone()[0]
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
        if atual and list(atual)[0] is not None:
            return "Este número já foi reservado por outra pessoa! Volte e escolha outro.", 400
            
        cursor.execute('UPDATE numeros SET nome = %s, fone = %s WHERE id = %s', (nome, fone, numero_id))
    else:
        cursor.execute('SELECT nome FROM numeros WHERE id = ?', (numero_id,))
        atual = cursor.fetchone()
        if atual and atual['nome'] is not None:
            return "Este número já foi reservado por outra pessoa! Volte e escolha outro.", 400
            
        cursor.execute('UPDATE numeros SET nome = ?, fone = ? WHERE id = ?', (nome, fone, numero_id))
        
    conn.commit()