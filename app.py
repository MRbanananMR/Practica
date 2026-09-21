import os
import sqlite3

from flask import Flask, current_app, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


TRANSLATIONS = {
    "ru": {
        "app_name": "CHAT",
        "feed": "Лента",
        "logout": "Выйти",
        "login": "Войти",
        "register": "Регистрация",
        "enter_login_and_password": "Введите логин и пароль.",
        "user_exists": "Пользователь с таким именем уже существует.",
        "registration_success": "Регистрация прошла успешно.",
        "invalid_credentials": "Неверный логин или пароль.",
        "logged_in": "Вы вошли в систему.",
        "logged_out": "Вы вышли из системы.",
        "post_empty": "Пост не может быть пустым.",
        "post_published": "Пост опубликован.",
        "username": "Логин",
        "password": "Пароль",
        "create_account": "Создать аккаунт",
        "already_have_account": "Уже есть аккаунт?",
        "dont_have_account": "Нет аккаунта?",
        "feed_title": "Лента",
        "logged_as": "Вы вошли как",
        "new_post": "Новый пост",
        "what_new": "Что у вас нового?",
        "publish": "Опубликовать",
        "no_posts": "Пока никто не опубликовал постов. Будьте первым!",
        "language_ru": "RU",
        "language_en": "EN",
    },
    "en": {
        "app_name": "CHAT",
        "feed": "Feed",
        "logout": "Log out",
        "login": "Log in",
        "register": "Register",
        "enter_login_and_password": "Please enter a username and password.",
        "user_exists": "A user with this name already exists.",
        "registration_success": "Registration was successful.",
        "invalid_credentials": "Invalid username or password.",
        "logged_in": "You have logged in.",
        "logged_out": "You have logged out.",
        "post_empty": "The post cannot be empty.",
        "post_published": "Post published.",
        "username": "Username",
        "password": "Password",
        "create_account": "Create account",
        "already_have_account": "Already have an account?",
        "dont_have_account": "Don't have an account?",
        "feed_title": "Feed",
        "logged_as": "You are logged in as",
        "new_post": "New post",
        "what_new": "What's new?",
        "publish": "Publish",
        "no_posts": "No posts yet. Be the first one!",
        "language_ru": "RU",
        "language_en": "EN",
    },
}


def get_locale():
    return session.get("lang", "ru") if "lang" in session else "ru"


def t(key):
    locale = get_locale()
    translation = TRANSLATIONS.get(locale, TRANSLATIONS["ru"])
    return translation.get(key, key)


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

    @app.context_processor
    def inject_translations():
        return {"t": t, "current_lang": get_locale}

    @app.teardown_appcontext
    def close_db(exception=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.route("/set_language/<lang>")
    def set_language(lang):
        if lang in TRANSLATIONS:
            session["lang"] = lang
        else:
            session["lang"] = "ru"
        return redirect(request.referrer or url_for("index"))

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
                flash(t("enter_login_and_password"))
                return render_template("register.html")

            db = get_db()
            existing_user = db.execute(
                "SELECT id FROM users WHERE username = ?",
                (username,),
            ).fetchone()

            if existing_user is not None:
                flash(t("user_exists"))
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
            flash(t("registration_success"))
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
                flash(t("invalid_credentials"))
                return render_template("login.html")

            session["user_id"] = user["id"]
            flash(t("logged_in"))
            return redirect(url_for("index"))

        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.pop("user_id", None)
        flash(t("logged_out"))
        return redirect(url_for("login"))

    @app.route("/posts/create", methods=["POST"])
    def create_post():
        if not session.get("user_id"):
            return redirect(url_for("login"))

        content = request.form.get("content", "").strip()
        if not content:
            flash(t("post_empty"))
            return redirect(url_for("index"))

        db = get_db()
        db.execute(
            "INSERT INTO posts (user_id, content) VALUES (?, ?)",
            (session["user_id"], content),
        )
        db.commit()

        flash(t("post_published"))
        return redirect(url_for("index"))

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
