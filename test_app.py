import sqlite3
import app


def test_hash_password_is_deterministic():
    h1 = app.hash_password("geheim123")
    h2 = app.hash_password("geheim123")

    assert h1 == h2
    assert h1 != "geheim123"
    assert len(h1) == 64


def test_init_db_creates_tables_and_default_category(tmp_path, monkeypatch):
    test_db = tmp_path / "test_quiz.db"
    monkeypatch.setattr(app, "DB_NAME", str(test_db))

    app.init_db()

    with sqlite3.connect(app.DB_NAME) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        assert cursor.fetchone() is not None

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='categories'")
        assert cursor.fetchone() is not None

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='fragen'")
        assert cursor.fetchone() is not None

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scores'")
        assert cursor.fetchone() is not None

        cursor.execute("SELECT name FROM categories WHERE name = 'Allgemeinwissen'")
        assert cursor.fetchone() is not None


def test_auth_process_registers_new_user(tmp_path, monkeypatch):
    test_db = tmp_path / "test_quiz.db"
    monkeypatch.setattr(app, "DB_NAME", str(test_db))
    app.init_db()

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