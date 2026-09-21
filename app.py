import os
import sqlite3

from flask import Flask, current_app, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


def get_db():
    if "db" not in g:
        db = sqlite3.connect(current_app.config["DATABASE"])
        db.row_factory = sqlite3.Row
        g.db = db
    return g.db


def init_db():
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )
    db.commit()


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY="homework-social-secret",
        DATABASE=os.path.join(app.instance_path, "social.db"),
    )

    if test_config is not None:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    @app.teardown_appcontext
    def close_db(exception=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with app.app_context():
        init_db()

    @app.route("/")
    def index():
        if not session.get("user_id"):
            return redirect(url_for("login"))

        db = get_db()
        user = db.execute(
            "SELECT id, username FROM users WHERE id = ?",
            (session["user_id"],),
        ).fetchone()

        posts = db.execute(
            """
            SELECT posts.id, posts.content, posts.created_at, users.username
            FROM posts
            JOIN users ON users.id = posts.user_id
            ORDER BY posts.created_at DESC
            """
        ).fetchall()

        return render_template("feed.html", user=user, posts=posts)

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")

            if not username or not password:
                flash("Введите логин и пароль.")
                return render_template("register.html")

            db = get_db()
            existing_user = db.execute(
                "SELECT id FROM users WHERE username = ?",
                (username,),
            ).fetchone()

            if existing_user is not None:
                flash("Пользователь с таким именем уже существует.")
                return render_template("register.html")

            db.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, generate_password_hash(password)),
            )
            db.commit()

            user = db.execute(
                "SELECT id FROM users WHERE username = ?", (username,),
            ).fetchone()
            session["user_id"] = user["id"]
            flash("Регистрация прошла успешно.")
            return redirect(url_for("index"))

        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")

            db = get_db()
            user = db.execute(
                "SELECT id, username, password_hash FROM users WHERE username = ?",
                (username,),
            ).fetchone()

            if user is None or not check_password_hash(user["password_hash"], password):
                flash("Неверный логин или пароль.")
                return render_template("login.html")

            session["user_id"] = user["id"]
            flash("Вы вошли в систему.")
            return redirect(url_for("index"))

        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.pop("user_id", None)
        flash("Вы вышли из системы.")
        return redirect(url_for("login"))

    @app.route("/posts/create", methods=["POST"])
    def create_post():
        if not session.get("user_id"):
            return redirect(url_for("login"))

        content = request.form.get("content", "").strip()
        if not content:
            flash("Пост не может быть пустым.")
            return redirect(url_for("index"))

        db = get_db()
        db.execute(
            "INSERT INTO posts (user_id, content) VALUES (?, ?)",
            (session["user_id"], content),
        )
        db.commit()

        flash("Пост опубликован.")
        return redirect(url_for("index"))

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
