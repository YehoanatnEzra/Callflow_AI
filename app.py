import os
import sqlite3
import json
from pathlib import Path
from typing import Optional

from flask import (
    Flask,
    g,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    send_from_directory,
)

from werkzeug.security import generate_password_hash, check_password_hash
from db.db import DB_PATH, init_db, ensure_schema

from backend.call_service import CallService

# Public webhook base: configurable via env, with sane default for local dev
DEFAULT_PUBLIC_BASE_URL = os.getenv(
    "PUBLIC_BASE_URL",
    "https://brianna-pretibial-unferociously.ngrok-free.dev",
)

BASE_DIR = Path(__file__).resolve().parent
DB_DATA_DIR = BASE_DIR / "db" / "data"
MEETINGS_LOG_PATH = DB_DATA_DIR / "meetings_log.json"
STATIC_DIR = BASE_DIR / "static"
# New centralized place for user-uploaded assets under db/
ASSETS_DIR = BASE_DIR / "db" / "assets"

app = Flask(__name__, template_folder="front", static_folder="static")
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")


def get_db() -> sqlite3.Connection:
    db = getattr(g, "db", None)
    if db is None:
        db = sqlite3.connect(str(DB_PATH))
        db.row_factory = sqlite3.Row
        g.db = db
    return db


## DB init and schema management moved to db/db.py


@app.teardown_appcontext
def close_db(exc: Optional[BaseException]) -> None:
    db = getattr(g, "db", None)
    if db is not None:
        db.close()


def query_user_by_username(username: str) -> Optional[sqlite3.Row]:
    db = get_db()
    cur = db.execute("SELECT * FROM users WHERE username = ?", (username,))
    return cur.fetchone()


def create_user(username: str, password: str, email: str = "") -> int:
    db = get_db()
    password_hash = generate_password_hash(password)
    cur = db.execute(
        "INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)",
        (username, password_hash, email),
    )
    db.commit()
    return cur.lastrowid


@app.route("/")
def index():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        email = request.form.get("email", "").strip()
        if not username or not password or not email:
            flash("Username, password and email are required.")
            return redirect(url_for("signup"))
        if query_user_by_username(username):
            flash("Username already exists.")
            return redirect(url_for("signup"))
        user_id = create_user(username, password, email)
        session["user_id"] = user_id
        session["username"] = username
        flash("Account created. Let's set up your company details.")
        return redirect(url_for("company_setup"))
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = query_user_by_username(username)
        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid username or password.")
            return redirect(url_for("login"))
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        flash("Logged in.")
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("index"))


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    message = None
    # Fetch user info to show company details
    db = get_db()
    cur = db.execute("SELECT username, company_name, company_description FROM users WHERE id = ?", (session["user_id"],))
    user = cur.fetchone()
    needs_company = not (user and user["company_name"] and user["company_description"])
    # Handle call start submission (single form; no action flag needed)
    if request.method == "POST":
        to_number = (request.form.get("to_number") or "").strip()
        if not to_number.startswith("+"):
            flash("Please include country code and + at the beginning of the phone number.")
        else:
            webhook_base = DEFAULT_PUBLIC_BASE_URL.rstrip("/")
            webhook = f"{webhook_base}/voice?user_id={session['user_id']}"
            try:
                cs = CallService()
                cs.make_call(to_number, webhook)
                message = f"Calling to {to_number}"
            except Exception as exc:
                message = f"Failed to start call: {exc}"
    # Fetch user info again for rendering (if not already)
    if not user:
        cur = db.execute("SELECT username, company_name, company_description FROM users WHERE id = ?", (session["user_id"],))
        user = cur.fetchone()
    return render_template(
        "dashboard.html",
        username=user["username"],
        company_name=user["company_name"] if user else "",
        company_description=user["company_description"] if user else "",
        needs_company=needs_company,
        message=message,
    )


@app.route("/meetings", methods=["GET"])  # list and search
def meetings():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    # Load meetings from JSON log
    meetings_data = []
    if MEETINGS_LOG_PATH.exists():
        try:
            with open(MEETINGS_LOG_PATH, 'r', encoding='utf-8') as f:
                meetings_data = json.load(f)
        except json.JSONDecodeError:
            meetings_data = []

    # Prepare rows as (original_index, meeting) and filter if query provided
    query = (request.args.get("q") or "").strip()
    rows = list(enumerate(meetings_data))
    if query:
        q_lower = query.lower()
        def match(m):
            name_val = (m.get("name") or "").lower()
            return q_lower in name_val
        rows = [(i, m) for i, m in rows if match(m)]

    return render_template("meetings.html", rows=rows, query=query)


@app.route("/meetings/delete", methods=["POST"])  # delete a specific meeting by index
def delete_meeting():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    # Load meetings
    meetings_data = []
    if MEETINGS_LOG_PATH.exists():
        try:
            with open(MEETINGS_LOG_PATH, 'r', encoding='utf-8') as f:
                meetings_data = json.load(f)
        except json.JSONDecodeError:
            meetings_data = []
    # Parse index and delete if valid
    idx_raw = request.form.get("idx", "-1")
    try:
        idx = int(idx_raw)
    except ValueError:
        idx = -1
    if 0 <= idx < len(meetings_data):
        removed = meetings_data.pop(idx)
        try:
            with open(MEETINGS_LOG_PATH, 'w', encoding='utf-8') as f:
                json.dump(meetings_data, f, ensure_ascii=False, indent=2)
            flash("Meeting removed.")
        except Exception as e:
            flash(f"Failed to update meetings log: {e}")
    else:
        flash("Invalid meeting selection.")
    # Preserve search query if present
    return redirect(url_for("meetings", q=request.args.get("q") or None))


@app.route("/meetings/clear", methods=["POST"])  # clear all meetings
def clear_meetings():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    try:
        DB_DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(MEETINGS_LOG_PATH, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        flash("All meetings cleared.")
    except Exception as e:
        flash(f"Failed to clear meetings: {e}")
    return redirect(url_for("meetings"))


@app.route("/health", methods=["GET"])  # simple health endpoint for uptime checks
def health():
    try:
        # quick DB ping
        db = get_db()
        db.execute("SELECT 1")
        db_ok = True
    except Exception:
        db_ok = False
    public_base = DEFAULT_PUBLIC_BASE_URL.rstrip("/") if DEFAULT_PUBLIC_BASE_URL else None
    return {
        "status": "ok",
        "db": "ok" if db_ok else "error",
        "public_base_url": public_base,
    }, 200


@app.route("/company_setup", methods=["GET", "POST"])
def company_setup():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    if request.method == "POST":
        name = (request.form.get("company_name") or "").strip()
        desc = (request.form.get("company_description") or "").strip()
        assistant = (request.form.get("assistant_name") or "").strip()
        logo_file = request.files.get("logo_image")
        if not name or not desc:
            flash("Please provide both company name and description.")
            return redirect(url_for("company_setup"))

        # Optional: handle company logo upload, saved per-user under db/assets
        logo_path_value = None
        if logo_file and getattr(logo_file, 'filename', ''):
            filename = logo_file.filename
            ext = (filename.rsplit('.', 1)[-1] or '').lower()
            if ext in {"jpg", "jpeg", "png", "webp", "gif"}:
                try:
                    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
                    safe_name = f"user_{session['user_id']}_logo.{ext}"
                    abs_path = ASSETS_DIR / safe_name
                    logo_file.save(str(abs_path))
                    logo_path_value = f"/assets/{safe_name}"
                except Exception as e:
                    flash(f"Failed to save logo image: {e}")
            else:
                flash("Unsupported logo image type. Please upload JPG, PNG, WEBP or GIF.")

        db = get_db()
        if logo_path_value:
            db.execute(
                "UPDATE users SET company_name = ?, company_description = ?, assistant_name = ?, logo_image = ? WHERE id = ?",
                (name, desc, assistant or None, logo_path_value, session["user_id"]),
            )
        else:
            db.execute(
                "UPDATE users SET company_name = ?, company_description = ?, assistant_name = ? WHERE id = ?",
                (name, desc, assistant or None, session["user_id"]),
            )
        db.commit()
        flash("Company details saved.")
        return redirect(url_for("dashboard"))
    # Pre-fill if exists
    db = get_db()
    cur = db.execute("SELECT company_name, company_description, assistant_name, logo_image FROM users WHERE id = ?", (session["user_id"],))
    row = cur.fetchone()
    # Company profile image is a fixed asset uploaded manually as db/assets/background.jpg
    bg_file = ASSETS_DIR / "background.jpg"
    bg_url = "/assets/background.jpg" if bg_file.exists() else ""
    return render_template(
        "company_setup.html",
        company_name=(row["company_name"] if row else ""),
        company_description=(row["company_description"] if row else ""),
        assistant_name=(row["assistant_name"] if row and row["assistant_name"] else "Alice"),
        background_image=bg_url,
        logo_image=(row["logo_image"] if row and row["logo_image"] else ""),
    )




@app.context_processor
def inject_theme():
    """Expose the fixed background and per-user logo to all templates."""
    try:
        bg_file = ASSETS_DIR / "background.jpg"
        bg = "/assets/background.jpg" if bg_file.exists() else None
        logo = None
        if session.get("user_id"):
            db = get_db()
            cur = db.execute("SELECT logo_image FROM users WHERE id = ?", (session["user_id"],))
            row = cur.fetchone()
            if row and row["logo_image"]:
                logo = row["logo_image"]
        return {"current_background_image": bg, "current_logo_image": logo}
    except Exception:
        return {"current_background_image": None, "current_logo_image": None}


# Serve assets from db/assets via /assets/<filename>
@app.route("/assets/<path:filename>")
def assets(filename: str):
    try:
        ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return send_from_directory(ASSETS_DIR, filename)


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)), debug=True)
