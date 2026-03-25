from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime, timedelta

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

    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT streak, points FROM users WHERE email=?", (session["user"],))
    data = cur.fetchone()

    streak = data[0] if data else 0
    points = data[1] if data else 0

    return render_template("dashboard.html", user=session["user"], streak=streak, points=points)

# CREATE GROUP
@app.route("/create_group", methods=["POST"])
def create_group():
    if "user" not in session:
        return redirect("/login")

    group_name = request.form["group_name"]

    db = get_db()
    cur = db.cursor()

    # insert group
    cur.execute("INSERT INTO groups (name) VALUES (?)", (group_name,))
    group_id = cur.lastrowid

    # add creator as member
    cur.execute("INSERT INTO group_members (user_email, group_id) VALUES (?, ?)",
                (session["user"], group_id))

    db.commit()
    return redirect("/groups")


# VIEW GROUPS
@app.route("/groups")
def groups():
    if "user" not in session:
        return redirect("/login")

    db = get_db()
    cur = db.cursor()

    cur.execute("""
    SELECT g.id, g.name FROM groups g
    JOIN group_members gm ON g.id = gm.group_id
    WHERE gm.user_email = ?
    """, (session["user"],))

    user_groups = cur.fetchall()

    return render_template("groups.html", groups=user_groups)


# JOIN GROUP
@app.route("/join_group", methods=["POST"])
def join_group():
    group_id = request.form["group_id"]

    db = get_db()
    cur = db.cursor()

    cur.execute("INSERT INTO group_members (user_email, group_id) VALUES (?, ?)",
                (session["user"], group_id))

    db.commit()
    return redirect("/groups")

@app.route("/practice", methods=["POST"])
def practice():
    if "user" not in session:
        return redirect("/login")

    db = get_db()
    cur = db.cursor()

    email = session["user"]
    today = datetime.now().date()

    cur.execute("SELECT streak, last_practice, points FROM users WHERE email=?", (email,))
    user = cur.fetchone()

    streak, last_date, points = user

    if last_date:
        last_date = datetime.strptime(last_date, "%Y-%m-%d").date()

        if last_date == today:
            return redirect("/dashboard")

        elif last_date == today - timedelta(days=1):
            streak += 1
        else:
            streak = 1
    else:
        streak = 1

    points += 10

    if streak % 7 == 0:
        points += 50

    cur.execute("""
    UPDATE users SET streak=?, last_practice=?, points=?
    WHERE email=?
    """, (streak, str(today), points, email))

    cur.execute("INSERT INTO practice_log (user_email, date) VALUES (?, ?)", (email, str(today)))

    db.commit()

    return redirect("/dashboard")

@app.route("/leaderboard/<int:group_id>")
def leaderboard(group_id):
    if "user" not in session:
        return redirect("/login")

    db = get_db()
    cur = db.cursor()

    cur.execute("""
    SELECT u.name, u.points, u.streak
    FROM users u
    JOIN group_members gm ON u.email = gm.user_email
    WHERE gm.group_id = ?
    ORDER BY u.points DESC
    """, (group_id,))

    members = cur.fetchall()

    return render_template("leaderboard.html", members=members)

if __name__ == "__main__":
    app.run(debug=True)