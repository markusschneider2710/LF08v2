import sqlite3
import app


def create_test_db(db_path):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password_hash TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE
            )
        """)

        cursor.execute("""
            CREATE TABLE fragen (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER,
                frage TEXT,
                antwort_1 TEXT,
                antwort_2 TEXT,
                antwort_3 TEXT,
                antwort_4 TEXT,
                korrekt_index INTEGER,
                creator_id INTEGER
            )
        """)

        cursor.execute("""
            CREATE TABLE scores (
                user_id INTEGER,
                punkte INTEGER,
                max_punkte INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute(
            "INSERT INTO categories (name) VALUES (?)",
            ("Allgemeinwissen",)
        )

        conn.commit()


def test_hash_password_is_deterministic():
    h1 = app.hash_password("geheim123")
    h2 = app.hash_password("geheim123")

    assert h1 == h2
    assert h1 != "geheim123"
    assert len(h1) == 64


def test_get_db_connection_returns_working_connection(tmp_path, monkeypatch):
    test_db = tmp_path / "test_quiz.db"
    create_test_db(test_db)
    monkeypatch.setattr(app, "DB_NAME", str(test_db))

    conn = app.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM categories WHERE name = ?", ("Allgemeinwissen",))
    row = cursor.fetchone()
    conn.close()

    assert row == ("Allgemeinwissen",)


def test_auth_process_registers_new_user(tmp_path, monkeypatch):
    test_db = tmp_path / "test_quiz.db"
    create_test_db(test_db)
    monkeypatch.setattr(app, "DB_NAME", str(test_db))

    inputs = iter(["alice", "passwort123"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    user_id, username = app.auth_process()

    assert username == "alice"
    assert user_id is not None

    with sqlite3.connect(app.DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users WHERE username = ?", ("alice",))
        row = cursor.fetchone()

    assert row == ("alice",)