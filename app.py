import sqlite3
import random
import hashlib
import sys

DB_NAME = "quiz_community.db"

# --- BASIS FUNKTIONEN ---
def hash_password(password):
    """Erzeugt einen sicheren SHA-256 Hash des Passworts."""
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    """Initialisiert die Datenbank und rüstet Tabellen bei Bedarf nach."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                username TEXT UNIQUE, 
                password_hash TEXT
            )
        """)
        
        cursor.execute("CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fragen (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER,
                frage TEXT,
                antwort_1 TEXT,
                antwort_2 TEXT,
                antwort_3 TEXT,
                antwort_4 TEXT,
                korrekt_index INTEGER,
                creator_id INTEGER,
                FOREIGN KEY (category_id) REFERENCES categories(id),
                FOREIGN KEY (creator_id) REFERENCES users(id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scores (
                user_id INTEGER, 
                punkte INTEGER, 
                max_punkte INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Start-Daten
        cursor.execute("INSERT OR IGNORE INTO categories (name) VALUES ('Allgemeinwissen')")
        conn.commit()

# --- AUTH & LOGIN ---
def auth_process():
    print("\n" + "="*30)
    print("      LOGIN / REGISTRIERUNG")
    print("="*30)
    user = input("Benutzername: ").strip()
    if not user: return None, None
    pw = input("Passwort: ").strip()
    h = hash_password(pw)

    with sqlite3.connect(DB_NAME) as conn:
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
            cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (user, h))
            conn.commit()
            print(f"\n[OK] Konto für '{user}' wurde neu erstellt!")
            return cursor.lastrowid, user

# --- INHALTE VERWALTEN (EDITOR) ---
def add_content(user_id):
    print("\n--- COMMUNITY EDITOR ---")
    print("1. Neue Kategorie anlegen")
    print("2. Neue Frage hinzufügen")
    print("3. Kategorie löschen")
    print("4. Frage löschen")
    print("5. Zurück")
    wahl = input("Wahl: ")
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        
        if wahl == "1":
            kat_name = input("Name der neuen Kategorie: ").strip()
            if kat_name:
                try:
                    cursor.execute("INSERT INTO categories (name) VALUES (?)", (kat_name,))
                    print(f"Kategorie '{kat_name}' erfolgreich erstellt!")
                except:
                    print("Fehler: Kategorie existiert evtl. schon.")

        elif wahl == "2":
            cursor.execute("SELECT id, name FROM categories")
            kats = cursor.fetchall()
            print("\nVerfügbare Kategorien:")
            for k in kats: print(f"[{k[0]}] {k[1]}")
            try:
                k_id = int(input("Kategorie-ID wählen: "))
                f = input("Frage: ")
                a1 = input("Antwort 1 (Korrekt): ")
                a2 = input("Antwort 2 (Falsch): ")
                a3 = input("Antwort 3 (Falsch): ")
                a4 = input("Antwort 4 (Falsch): ")
                
                cursor.execute("""
                    INSERT INTO fragen (category_id, frage, antwort_1, antwort_2, antwort_3, antwort_4, korrekt_index, creator_id) 
                    VALUES (?,?,?,?,?,?,?,?)
                """, (k_id, f, a1, a2, a3, a4, 0, user_id))
                print("Frage wurde gespeichert!")
            except ValueError:
                print("Ungültige Eingabe.")

        elif wahl == "3":
            cursor.execute("SELECT id, name FROM categories")
            kats = cursor.fetchall()
            for k in kats: print(f"ID: {k[0]} | Name: {k[1]}")
            target_id = input("\nID der zu löschenden Kategorie: ")
            cursor.execute("DELETE FROM categories WHERE id = ?", (target_id,))
            print(f"Gelöscht: {cursor.rowcount} Kategorie(n).")

        elif wahl == "4":
            cursor.execute("SELECT id, frage FROM fragen")
            fragen = cursor.fetchall()
            for f in fragen: print(f"ID: {f[0]} | Frage: {f[1][:50]}...")
            target_id = input("\nID der zu löschenden Frage: ")
            cursor.execute("DELETE FROM fragen WHERE id = ?", (target_id,))
            print(f"Gelöscht: {cursor.rowcount} Frage(n).")
            
        conn.commit()

# --- STATISTIKEN ---
def show_scores(u_id):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        print("\n" + "★"*30)
        print("      HIGHSCORES & STATS")
        print("★"*30)
        
        print("\n--- GLOBAL TOP 5 ---")
        cursor.execute("""
            SELECT users.username, MAX(scores.punkte) 
            FROM scores JOIN users ON scores.user_id = users.id 
            GROUP BY users.id ORDER BY MAX(scores.punkte) DESC LIMIT 5
        """)
        for i, r in enumerate(cursor.fetchall(), 1):
            print(f"{i}. {r[0]:<15} | {r[1]} Punkte")

        print("\n--- DEINE LETZTEN 5 SPIELE ---")
        cursor.execute("SELECT punkte, max_punkte, timestamp FROM scores WHERE user_id = ? ORDER BY timestamp DESC LIMIT 5", (u_id,))
        for r in cursor.fetchall():
            print(f"{r[2][:16]} : {r[0]}/{r[1]} Pkt")
        
        print("\n--- FLEISSIGSTE ERSTELLER ---")
        cursor.execute("""
            SELECT users.username, COUNT(fragen.id) 
            FROM fragen JOIN users ON fragen.creator_id = users.id 
            GROUP BY users.id ORDER BY COUNT(fragen.id) DESC LIMIT 3
        """)
        for r in cursor.fetchall():
            print(f"{r[0]:<15} | {r[1]} Fragen")

# --- SPIEL MODI ---
def play_single(u_id):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM categories")
        kats = cursor.fetchall()
        if not kats: return print("Keine Kategorien vorhanden.")
        
        # MAPPING für saubere Anzeige (1, 2, 3...)
        kat_mapping = {}
        print("\nWähle eine Kategorie:")
        for index, k in enumerate(kats, 1):
            print(f"[{index}] {k[1]}")
            kat_mapping[index] = k[0]
        
        try:
            wahl = int(input("Nummer: "))
            k_id = kat_mapping[wahl]
        except: return print("Ungültige Wahl.")

        cursor.execute("SELECT frage, antwort_1, antwort_2, antwort_3, antwort_4, korrekt_index FROM fragen WHERE category_id = ?", (k_id,))
        fragen = cursor.fetchall()
        
        if not fragen: return print("Keine Fragen in dieser Kategorie.")

        random.shuffle(fragen)
        score = 0
        for f in fragen:
            print(f"\nFrage: {f[0]}")
            antworten = [f[1], f[2], f[3], f[4]]
            richtig_text = antworten[f[5]]
            random.shuffle(antworten)
            
            for i, a in enumerate(antworten, 1): print(f"{i}. {a}")
            
            try:
                user_wahl = int(input("Antwort (1-4): ")) - 1
                if antworten[user_wahl] == richtig_text:
                    print("Richtig!"); score += 1
                else:
                    print(f"Falsch! Korrekt: {richtig_text}")
            except: print("Ungültig.")

        cursor.execute("INSERT INTO scores (user_id, punkte, max_punkte) VALUES (?, ?, ?)", (u_id, score, len(fragen)))
        conn.commit()
        print(f"\nFERTIG! Score: {score}/{len(fragen)}")
        print("\n--- GLOBAL TOP 5 ---")
        cursor.execute("""
            SELECT users.username, MAX(scores.punkte) 
            FROM scores JOIN users ON scores.user_id = users.id 
            GROUP BY users.id ORDER BY MAX(scores.punkte) DESC LIMIT 5
        """)
        for i, r in enumerate(cursor.fetchall(), 1):
            print(f"{i}. {r[0]:<15} | {r[1]} Punkte")

def play_multi(u1_name, u1_id):
    print("\n⚔ MULTIPLAYER DUELL ⚔")
    print("Spieler 2 bitte anmelden:")
    u2_id, u2_name = auth_process()
    if not u2_id or u2_id == u1_id: return print("Abbruch.")

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT frage, antwort_1, antwort_2, antwort_3, antwort_4, korrekt_index FROM fragen")
        alle = cursor.fetchall()
        if len(alle) < 3: return print("Zu wenig Fragen (mind. 3 nötig).")
        
        test_fragen = random.sample(alle, 3)
        results = {}
        
        for p_id, p_name in [(u1_id, u1_name), (u2_id, u2_name)]:
            print(f"\n>>> {p_name.upper()} ist dran! <<<")
            input("Enter zum Starten...")
            p_score = 0
            for f in test_fragen:
                print(f"\n{f[0]}")
                for i in range(1, 5): print(f"{i}. {f[i]}")
                try:
                    if int(input("Antwort (1-4): ")) - 1 == f[5]: p_score += 1
                except: pass
            results[p_name] = p_score
            print("\n" * 30) # "Clear" screen

        print("\n=== ERGEBNIS ===")
        for p, s in results.items(): print(f"{p}: {s} Punkte")
        if results[u1_name] > results[u2_name]: print(f"SIEGER: {u1_name}!")
        elif results[u1_name] < results[u2_name]: print(f"SIEGER: {u2_name}!")
        else: print("UNENTSCHIEDEN!")

# --- MAIN ---
def main():
    init_db()
    while True:
        u_id, u_name = None, None
        while not u_id:
            u_id, u_name = auth_process()

        while True:
            print(f"\n[EINGELOGGT: {u_name.upper()}]")
            print("1. Singleplayer\n2. Multiplayer\n3. Editor\n4. Highscores\n5. Logout\n6. Beenden")
            w = input("Wahl: ").strip()
            
            if w == "1": play_single(u_id)
            elif w == "2": play_multi(u_name, u_id)
            elif w == "3": add_content(u_id)
            elif w == "4": show_scores(u_id)
            elif w == "5": break
            elif w == "6": sys.exit()

if __name__ == "__main__":
    main()