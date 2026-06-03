from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
import os

app = Flask(__name__)

# Chave secreta para as sessões (troque por algo único)
app.secret_key = os.environ.get("SECRET_KEY", "chave_secreta_padrao_mude_isso")

# Senha do admin — defina a variável ADMIN_PASSWORD no Render (mais seguro)
SENHA_ADMIN = os.environ.get("ADMIN_PASSWORD", "admin123")

# ─────────────────────────────────────────────
# BANCO DE DADOS
# ─────────────────────────────────────────────

def get_db():
    """Abre conexão com o banco SQLite."""
    conn = sqlite3.connect("/data/database.db")
    conn.row_factory = sqlite3.Row  # permite acessar colunas pelo nome
    return conn

def init_db():
    """Cria a tabela de números caso ainda não exista."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS numeros (
            id    INTEGER PRIMARY KEY,
            nome  TEXT,
            fone  TEXT
        )
    """)

    # Popula com 100 números se a tabela estiver vazia
    cursor.execute("SELECT COUNT(*) FROM numeros")
    if cursor.fetchone()[0] == 0:
        for i in range(1, 101):
            cursor.execute(
                "INSERT INTO numeros (id, nome, fone) VALUES (?, NULL, NULL)",
                (i,)
            )

    conn.commit()
    conn.close()

# Inicializa o banco ao subir a aplicação
init_db()


# ─────────────────────────────────────────────
# PÁGINA PRINCIPAL
# ─────────────────────────────────────────────

@app.route("/")
def index():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM numeros ORDER BY id")
    numeros = cursor.fetchall()
    conn.close()

    # Conta disponíveis e vendidos
    disponiveis = sum(1 for n in numeros if n["nome"] is None)
    vendidos    = len(numeros) - disponiveis

    return render_template(
        "index.html",
        numeros=numeros,
        disponiveis=disponiveis,
        vendidos=vendidos
    )


# ─────────────────────────────────────────────
# COMPRA ONLINE (cliente clica no número)
# ─────────────────────────────────────────────

@app.route("/reservar/<int:id_numero>", methods=["GET", "POST"])
def reservar(id_numero):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM numeros WHERE id = ?", (id_numero,))
    numero = cursor.fetchone()

    if numero is None or numero["nome"] is not None:
        conn.close()
        return redirect("/")

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        fone = request.form.get("fone", "").strip()

        if nome:
            cursor.execute(
                "UPDATE numeros SET nome = ?, fone = ? WHERE id = ?",
                (nome, fone, id_numero)
            )
            conn.commit()
            conn.close()
            return redirect("/")

    conn.close()
    return render_template("reservar.html", numero=id_numero)


# ─────────────────────────────────────────────
# LOGIN DO ADMIN
# ─────────────────────────────────────────────

@app.route("/admin", methods=["GET", "POST"])
def admin():
    erro = None

    if request.method == "POST":
        senha = request.form.get("senha", "")

        if senha == SENHA_ADMIN:
            session["admin"] = True
            return redirect("/painel")
        else:
            erro = "Senha incorreta. Tente novamente."

    return render_template("admin.html", erro=erro)


# ─────────────────────────────────────────────
# PAINEL ADMINISTRATIVO
# ─────────────────────────────────────────────

@app.route("/painel")
def painel():
    if not session.get("admin"):
        return redirect("/admin")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM numeros ORDER BY id")
    numeros = cursor.fetchall()
    conn.close()

    disponiveis = sum(1 for n in numeros if n["nome"] is None)
    vendidos    = len(numeros) - disponiveis

    return render_template(
        "painel.html",
        numeros=numeros,
        disponiveis=disponiveis,
        vendidos=vendidos
    )


# ─────────────────────────────────────────────
# VENDA MANUAL (admin registra venda do WhatsApp)
# ─────────────────────────────────────────────

@app.route("/venda_manual", methods=["POST"])
def venda_manual():
    if not session.get("admin"):
        return redirect("/admin")

    numero = request.form.get("numero")
    nome   = request.form.get("nome", "").strip()
    fone   = request.form.get("fone", "").strip()

    if numero and nome:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE numeros SET nome = ?, fone = ? WHERE id = ? AND nome IS NULL",
            (nome, fone, numero)
        )

        conn.commit()
        conn.close()

    return redirect("/painel")


# ─────────────────────────────────────────────
# LIBERAR UM NÚMERO ESPECÍFICO
# ─────────────────────────────────────────────

@app.route("/liberar/<int:id_numero>")
def liberar(id_numero):
    if not session.get("admin"):
        return redirect("/admin")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE numeros SET nome = NULL, fone = NULL WHERE id = ?",
        (id_numero,)
    )

    conn.commit()
    conn.close()

    return redirect("/painel")


# ─────────────────────────────────────────────
# RESETAR TODA A RIFA
# ─────────────────────────────────────────────

@app.route("/resetar")
def resetar():
    if not session.get("admin"):
        return redirect("/admin")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("UPDATE numeros SET nome = NULL, fone = NULL")

    conn.commit()
    conn.close()

    return redirect("/painel")


# ─────────────────────────────────────────────
# LOGOUT
# ─────────────────────────────────────────────

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ─────────────────────────────────────────────
# RODAR LOCALMENTE
# ─────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True)