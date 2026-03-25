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


# LOGIN
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


# SIGNUP
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


# DASHBOARD
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

    cur.execute("INSERT INTO groups (name) VALUES (?)", (group_name,))
    group_id = cur.lastrowid

    cur.execute("INSERT INTO group_members (user_email, group_id) VALUES (?, ?)",
                (session["user"], group_id))

    db.commit()
    return redirect("/groups")


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


# GROUPS PAGE
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

    group_data = []

    for g in user_groups:
        gid = g[0]
        cur.execute("SELECT streak, broken_by FROM group_streaks WHERE group_id=?", (gid,))
        data = cur.fetchone()

        if data:
            group_data.append((g[0], g[1], data[0], data[1]))
        else:
            group_data.append((g[0], g[1], 0, None))

    # get user streak for sidebar
    cur.execute("SELECT streak FROM users WHERE email=?", (session["user"],))
    user_streak = cur.fetchone()[0]

    return render_template("groups.html", groups=group_data, streak=user_streak)


# PRACTICE + GROUP STREAK
@app.route("/practice", methods=["POST"])
def practice():
    if "user" not in session:
        return redirect("/login")

    db = get_db()
    cur = db.cursor()

    email = session["user"]
    today = datetime.now().date()

    # USER STREAK
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

    cur.execute("""
    UPDATE users SET streak=?, last_practice=?, points=?
    WHERE email=?
    """, (streak, str(today), points, email))

    cur.execute("INSERT INTO practice_log (user_email, date) VALUES (?, ?)", (email, str(today)))

    # GROUP STREAK
    cur.execute("SELECT group_id FROM group_members WHERE user_email=?", (email,))
    groups = cur.fetchall()

    for g in groups:
        group_id = g[0]

        cur.execute("SELECT user_email FROM group_members WHERE group_id=?", (group_id,))
        members = [m[0] for m in cur.fetchall()]

        cur.execute("""
        SELECT DISTINCT user_email FROM practice_log 
        WHERE date=? AND user_email IN ({})
        """.format(",".join(["?"]*len(members))), [str(today)] + members)

        practiced_today = [p[0] for p in cur.fetchall()]

        if set(practiced_today) == set(members):
            cur.execute("SELECT streak FROM group_streaks WHERE group_id=?", (group_id,))
            data = cur.fetchone()

            if data:
                new_streak = data[0] + 1
                cur.execute("""
                UPDATE group_streaks SET streak=?, last_updated=?, broken_by=NULL
                WHERE group_id=?
                """, (new_streak, str(today), group_id))
            else:
                cur.execute("""
                INSERT INTO group_streaks (group_id, streak, last_updated)
                VALUES (?, 1, ?)
                """, (group_id, str(today)))
        else:
            missed = list(set(members) - set(practiced_today))

            cur.execute("""
            UPDATE group_streaks SET streak=0, last_updated=?, broken_by=?
            WHERE group_id=?
            """, (str(today), missed[0] if missed else None, group_id))

    db.commit()
    return redirect("/dashboard")


if __name__ == "__main__":
    app.run(debug=True)