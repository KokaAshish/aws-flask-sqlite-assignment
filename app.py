from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
import sqlite3
import os

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "app.db")
UPLOAD_DIR = os.path.join(APP_DIR, "uploads")

app = Flask(__name__)
app.secret_key = "replace-this-with-any-random-string"


def db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def word_count_file(path: str) -> int:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return len(f.read().split())


@app.route("/")
def home():
    return redirect(url_for("register_page"))


@app.route("/register", methods=["GET"])
def register_page():
    return render_template("register.html")


@app.route("/register", methods=["POST"])
def register_submit():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    email = request.form.get("email", "").strip()
    address = request.form.get("address", "").strip()

    if not all([username, password, first_name, last_name, email, address]):
        flash("All fields are required.")
        return redirect(url_for("register_page"))

    conn = db_conn()
    try:
        conn.execute(
            "INSERT INTO users (username, password, first_name, last_name, email, address) VALUES (?, ?, ?, ?, ?, ?)",
            (username, password, first_name, last_name, email, address),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        flash("Username already exists. Please pick another.")
        return redirect(url_for("register_page"))
    finally:
        conn.close()

    return redirect(url_for("profile", username=username))


@app.route("/profile/<username>")
def profile(username):
    conn = db_conn()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if not user:
        return "User not found", 404

    limerick_wc = None
    if user["limerick_filename"]:
        file_path = os.path.join(UPLOAD_DIR, user["limerick_filename"])
        if os.path.exists(file_path):
            limerick_wc = word_count_file(file_path)

    return render_template("profile.html", user=user, limerick_wc=limerick_wc)


@app.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login_submit():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    conn = db_conn()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ? AND password = ?",
        (username, password),
    ).fetchone()
    conn.close()

    if not user:
        flash("Invalid username or password.")
        return redirect(url_for("login_page"))

    return redirect(url_for("profile", username=username))


@app.route("/upload/<username>", methods=["POST"])
def upload(username):
    if "file" not in request.files:
        flash("No file part.")
        return redirect(url_for("profile", username=username))

    f = request.files["file"]
    if f.filename == "":
        flash("No selected file.")
        return redirect(url_for("profile", username=username))

    # requirement: Limerick.txt
    if f.filename.lower() != "limerick.txt":
        flash("Upload must be named exactly: Limerick.txt")
        return redirect(url_for("profile", username=username))

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    save_path = os.path.join(UPLOAD_DIR, "Limerick.txt")
    f.save(save_path)

    conn = db_conn()
    conn.execute("UPDATE users SET limerick_filename=? WHERE username=?", ("Limerick.txt", username))
    conn.commit()
    conn.close()

    flash("File uploaded successfully.")
    return redirect(url_for("profile", username=username))


@app.route("/download/<username>")
def download(username):
    conn = db_conn()
    row = conn.execute("SELECT limerick_filename FROM users WHERE username=?", (username,)).fetchone()
    conn.close()

    if not row or not row["limerick_filename"]:
        return "No file uploaded.", 404

    return send_from_directory(UPLOAD_DIR, row["limerick_filename"], as_attachment=True)
