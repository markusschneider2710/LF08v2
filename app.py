import os
import sqlite3
import random
import hashlib
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "quiz_community.db")


# --- BASIS FUNKTIONEN ---
def hash_password(password):
    """Erzeugt einen SHA-256 Hash des Passworts."""
    return hashlib.sha256(password.encode()).hexdigest()


def get_db_connection():
    """Erstellt eine Verbindung zur SQLite-Datenbank."""
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except sqlite3.OperationalError as e:
        print(f"\n[!] FEHLER beim Öffnen der Datenbank: {e}")
        sys.exit(1)


def init_db():
    """Legt die Datenbank und alle benötigten Tabellen an, falls sie noch nicht existieren."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fragen (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                frage TEXT NOT NULL,
                antwort_1 TEXT NOT NULL,
                antwort_2 TEXT NOT NULL,
                antwort_3 TEXT NOT NULL,
                antwort_4 TEXT NOT NULL,
                korrekt_index INTEGER NOT NULL CHECK(korrekt_index BETWEEN 0 AND 3),
                creator_id INTEGER,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
                FOREIGN KEY (creator_id) REFERENCES users(id) ON DELETE SET NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                punkte INTEGER NOT NULL,
                max_punkte INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        conn.commit()


# --- AUTH & LOGIN ---
def auth_process():
    print("\n" + "=" * 30)
    print("      LOGIN / REGISTRIERUNG")
    print("=" * 30)

    user = input("Benutzername: ").strip()
    if not user:
        print("[!] Benutzername darf nicht leer sein.")
        return None, None

    pw = input("Passwort: ").strip()
    if not pw:
        print("[!] Passwort darf nicht leer sein.")
        return None, None

    h = hash_password(pw)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, password_hash FROM users WHERE username = ?", (user,))
        row = cursor.fetchone()

        if row:
            if row[1] == h:
                print(f"\n[OK] Willkommen zurück, {user}!")
                return row[0], user
            else:
                print("\n[!] Falsches Passwort!")
                return None, None
        else:
            try:
                cursor.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (user, h)
                )
                conn.commit()
                print(f"\n[OK] Konto für '{user}' wurde neu erstellt!")
                return cursor.lastrowid, user
            except sqlite3.IntegrityError as e:
                print(f"\n[!] Fehler beim Erstellen des Kontos: {e}")
                return None, None


# --- INHALTE VERWALTEN (EDITOR) ---
def add_content(user_id):
    print("\n--- COMMUNITY EDITOR ---")
    print("1. Neue Kategorie anlegen")
    print("2. Neue Frage hinzufügen")
    print("3. Kategorie löschen")
    print("4. Frage löschen")
    print("5. Zurück")

    wahl = input("Wahl: ").strip()

    with get_db_connection() as conn:
        cursor = conn.cursor()

        if wahl == "1":
            kat_name = input("Name der neuen Kategorie: ").strip()
            if kat_name:
                try:
                    cursor.execute("INSERT INTO categories (name) VALUES (?)", (kat_name,))
                    conn.commit()
                    print(f"Kategorie '{kat_name}' erfolgreich erstellt!")
                except sqlite3.IntegrityError:
                    print("Fehler: Kategorie existiert eventuell schon.")
            else:
                print("Name darf nicht leer sein.")

        elif wahl == "2":
            cursor.execute("SELECT id, name FROM categories ORDER BY name")
            kats = cursor.fetchall()

            if not kats:
                print("Es gibt noch keine Kategorien.")
                return

            print("\nVerfügbare Kategorien:")
            for k in kats:
                print(f"[{k[0]}] {k[1]}")

            try:
                k_id = int(input("Kategorie-ID wählen: "))
            except ValueError:
                print("Ungültige Kategorie-ID.")
                return

            cursor.execute("SELECT 1 FROM categories WHERE id = ?", (k_id,))
            if not cursor.fetchone():
                print("Diese Kategorie existiert nicht.")
                return

            f = input("Frage: ").strip()
            a1 = input("Antwort 1 (Korrekt): ").strip()
            a2 = input("Antwort 2 (Falsch): ").strip()
            a3 = input("Antwort 3 (Falsch): ").strip()
            a4 = input("Antwort 4 (Falsch): ").strip()

            if not all([f, a1, a2, a3, a4]):
                print("Alle Felder müssen ausgefüllt sein.")
                return

            cursor.execute("""
                INSERT INTO fragen (
                    category_id, frage, antwort_1, antwort_2, antwort_3, antwort_4, korrekt_index, creator_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (k_id, f, a1, a2, a3, a4, 0, user_id))

            conn.commit()
            print("Frage wurde gespeichert!")

        elif wahl == "3":
            cursor.execute("SELECT id, name FROM categories ORDER BY id")
            kats = cursor.fetchall()

            if not kats:
                print("Keine Kategorien vorhanden.")
                return

            for k in kats:
                print(f"ID: {k[0]} | Name: {k[1]}")

            try:
                target_id = int(input("\nID der zu löschenden Kategorie: ").strip())
            except ValueError:
                print("Ungültige ID.")
                return

            cursor.execute("DELETE FROM categories WHERE id = ?", (target_id,))
            conn.commit()
            print(f"Gelöscht: {cursor.rowcount} Kategorie(n).")

        elif wahl == "4":
            cursor.execute("SELECT id, frage FROM fragen ORDER BY id")
            fragen = cursor.fetchall()

            if not fragen:
                print("Keine Fragen vorhanden.")
                return

            for f in fragen:
                text = f[1][:50] + "..." if len(f[1]) > 50 else f[1]
                print(f"ID: {f[0]} | Frage: {text}")

            try:
                target_id = int(input("\nID der zu löschenden Frage: ").strip())
            except ValueError:
                print("Ungültige ID.")
                return

            cursor.execute("DELETE FROM fragen WHERE id = ?", (target_id,))
            conn.commit()
            print(f"Gelöscht: {cursor.rowcount} Frage(n).")

        elif wahl == "5":
            return

        else:
            print("Ungültige Auswahl.")


# --- STATISTIKEN ---
def show_scores(u_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()

        print("\n" + "★" * 30)
        print("      HIGHSCORES & STATS")
        print("★" * 30)

        print("\n--- GLOBAL TOP 5 ---")
        cursor.execute("""
            SELECT users.username, MAX(scores.punkte)
            FROM scores
            JOIN users ON scores.user_id = users.id
            GROUP BY users.id
            ORDER BY MAX(scores.punkte) DESC, users.username ASC
            LIMIT 5
        """)
        rows = cursor.fetchall()
        if rows:
            for i, r in enumerate(rows, 1):
                print(f"{i}. {r[0]:<15} | {r[1]} Punkte")
        else:
            print("Noch keine Scores vorhanden.")

        print("\n--- DEINE LETZTEN 5 SPIELE ---")
        cursor.execute("""
            SELECT punkte, max_punkte, timestamp
            FROM scores
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT 5
        """, (u_id,))
        rows = cursor.fetchall()
        if rows:
            for r in rows:
                print(f"{r[2][:16]} : {r[0]}/{r[1]} Pkt")
        else:
            print("Du hast noch keine Spiele gespielt.")

        print("\n--- FLEISSIGSTE ERSTELLER ---")
        cursor.execute("""
            SELECT users.username, COUNT(fragen.id)
            FROM fragen
            JOIN users ON fragen.creator_id = users.id
            GROUP BY users.id
            ORDER BY COUNT(fragen.id) DESC, users.username ASC
            LIMIT 3
        """)
        rows = cursor.fetchall()
        if rows:
            for r in rows:
                print(f"{r[0]:<15} | {r[1]} Fragen")
        else:
            print("Noch keine Fragen erstellt.")


# --- SPIEL MODI ---
def play_single(u_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT id, name FROM categories ORDER BY name")
        kats = cursor.fetchall()

        if not kats:
            print("Keine Kategorien vorhanden.")
            return

        kat_mapping = {}
        print("\nWähle eine Kategorie:")
        for index, k in enumerate(kats, 1):
            print(f"[{index}] {k[1]}")
            kat_mapping[index] = k[0]

        try:
            wahl = int(input("Nummer: ").strip())
            k_id = kat_mapping[wahl]
        except (ValueError, KeyError):
            print("Ungültige Wahl.")
            return

        cursor.execute("""
            SELECT frage, antwort_1, antwort_2, antwort_3, antwort_4, korrekt_index
            FROM fragen
            WHERE category_id = ?
        """, (k_id,))
        fragen = cursor.fetchall()

        if not fragen:
            print("Keine Fragen in dieser Kategorie.")
            return

        random.shuffle(fragen)
        score = 0

        for f in fragen:
            print(f"\nFrage: {f[0]}")
            antworten = [f[1], f[2], f[3], f[4]]
            richtig_text = antworten[f[5]]

            random.shuffle(antworten)

            for i, a in enumerate(antworten, 1):
                print(f"{i}. {a}")

            try:
                user_wahl = int(input("Antwort (1-4): ").strip()) - 1
                if user_wahl not in [0, 1, 2, 3]:
                    print("Ungültige Auswahl.")
                    continue

                if antworten[user_wahl] == richtig_text:
                    print("Richtig!")
                    score += 1
                else:
                    print(f"Falsch! Korrekt: {richtig_text}")
            except ValueError:
                print("Ungültige Eingabe.")

        cursor.execute("""
            INSERT INTO scores (user_id, punkte, max_punkte)
            VALUES (?, ?, ?)
        """, (u_id, score, len(fragen)))
        conn.commit()

        print(f"\nFERTIG! Score: {score}/{len(fragen)}")

        print("\n--- GLOBAL TOP 5 ---")
        cursor.execute("""
            SELECT users.username, MAX(scores.punkte)
            FROM scores
            JOIN users ON scores.user_id = users.id
            GROUP BY users.id
            ORDER BY MAX(scores.punkte) DESC, users.username ASC
            LIMIT 5
        """)
        for i, r in enumerate(cursor.fetchall(), 1):
            print(f"{i}. {r[0]:<15} | {r[1]} Punkte")


def play_multi(u1_name, u1_id):
    print("\n⚔ MULTIPLAYER DUELL ⚔")
    print("Spieler 2 bitte anmelden:")
    u2_id, u2_name = auth_process()

    if not u2_id:
        print("Abbruch.")
        return

    if u2_id == u1_id:
        print("Spieler 2 darf nicht derselbe Nutzer sein.")
        return

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT frage, antwort_1, antwort_2, antwort_3, antwort_4, korrekt_index
            FROM fragen
        """)
        alle = cursor.fetchall()

        if len(alle) < 3:
            print("Zu wenig Fragen (mind. 3 nötig).")
            return

        test_fragen = random.sample(alle, 3)
        results = {}

        for p_id, p_name in [(u1_id, u1_name), (u2_id, u2_name)]:
            print(f"\n>>> {p_name.upper()} ist dran! <<<")
            input("Enter zum Starten...")
            p_score = 0

            for f in test_fragen:
                print(f"\n{f[0]}")
                for i in range(1, 5):
                    print(f"{i}. {f[i]}")

                try:
                    antwort = int(input("Antwort (1-4): ").strip()) - 1
                    if antwort == f[5]:
                        p_score += 1
                except ValueError:
                    pass

            results[p_name] = p_score
            print("\n" * 30)

        print("\n=== ERGEBNIS ===")
        for p, s in results.items():
            print(f"{p}: {s} Punkte")

        if results[u1_name] > results[u2_name]:
            print(f"SIEGER: {u1_name}!")
        elif results[u1_name] < results[u2_name]:
            print(f"SIEGER: {u2_name}!")
        else:
            print("UNENTSCHIEDEN!")


# --- MAIN ---
def main():
    init_db()

    while True:
        u_id, u_name = None, None

        while not u_id:
            u_id, u_name = auth_process()

        while True:
            print(f"\n[EINGELOGGT: {u_name.upper()}]")
            print("1. Singleplayer")
            print("2. Multiplayer")
            print("3. Editor")
            print("4. Highscores")
            print("5. Logout")
            print("6. Beenden")

            w = input("Wahl: ").strip()

            if w == "1":
                play_single(u_id)
            elif w == "2":
                play_multi(u_name, u_id)
            elif w == "3":
                add_content(u_id)
            elif w == "4":
                show_scores(u_id)
            elif w == "5":
                break
            elif w == "6":
                sys.exit()
            else:
                print("Ungültige Auswahl.")


if __name__ == "__main__":
    main()