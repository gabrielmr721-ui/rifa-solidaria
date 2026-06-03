from flask import Flask, render_template, request, redirect, session
import sqlite3
import os

app = Flask(__name__)

app.secret_key = "troque_por_uma_chave_grande"

SENHA_ADMIN = os.environ.get("ADMIN_PASSWORD", "admin123")


def criar_banco():

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS numeros (
        id INTEGER PRIMARY KEY,
        nome TEXT
    )
    """)

    cursor.execute("SELECT COUNT(*) FROM numeros")

    total = cursor.fetchone()[0]

    if total == 0:

        for i in range(1, 101):
            cursor.execute(
                "INSERT INTO numeros(id, nome) VALUES (?, ?)",
                (i, None)
            )

    conn.commit()
    conn.close()


criar_banco()


@app.route("/")
def index():

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM numeros")

    numeros = cursor.fetchall()

    conn.close()

    return render_template(
        "index.html",
        numeros=numeros
    )


@app.route("/reservar", methods=["POST"])
def reservar():

    numero = request.form["numero"]
    nome = request.form["nome"]

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE numeros
        SET nome = ?
        WHERE id = ? AND nome IS NULL
        """,
        (nome, numero)
    )

    conn.commit()
    conn.close()

    return redirect("/")


@app.route("/admin", methods=["GET", "POST"])
def admin():

    if request.method == "POST":

        senha = request.form["senha"]

        if senha == SENHA_ADMIN:

            session["admin"] = True

            return redirect("/painel")

    return render_template("admin.html")


@app.route("/painel")
def painel():

    if not session.get("admin"):
        return redirect("/admin")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM numeros")

    numeros = cursor.fetchall()

    conn.close()

    return render_template(
        "painel.html",
        numeros=numeros
    )


@app.route("/liberar/<int:numero>")
def liberar(numero):

    if not session.get("admin"):
        return redirect("/admin")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE numeros
        SET nome = NULL
        WHERE id = ?
        """,
        (numero,)
    )

    conn.commit()
    conn.close()

    return redirect("/painel")


@app.route("/resetar")
def resetar():

    if not session.get("admin"):
        return redirect("/admin")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE numeros
        SET nome = NULL
        """
    )

    conn.commit()
    conn.close()

    return redirect("/painel")


@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)