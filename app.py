from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "secret"

def get_db():
    return sqlite3.connect("database.db")

@app.route("/")
def home():
    if "user" in session:
        return redirect("/dashboard")
    return redirect("/login")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
        user = cur.fetchone()

        if user:
            session["user"] = email
            return redirect("/dashboard")

    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        db = get_db()
        cur = db.cursor()

        cur.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (
            request.form["name"],
            request.form["email"],
            request.form["password"]
        ))

        db.commit()
        return redirect("/login")

    return render_template("signup.html")

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    return render_template("dashboard.html", user=session["user"])

if __name__ == "__main__":
    app.run(debug=True)