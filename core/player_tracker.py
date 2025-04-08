import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join("data", "db.sqlite3")

# ------------------- Database Setup -------------------

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Session table
    c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT
        )
    ''')

    # Player actions
    c.execute('''
        CREATE TABLE IF NOT EXISTS player_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            timestamp TEXT,
            player_name TEXT,
            position TEXT,
            action TEXT,
            stack INTEGER
        )
    ''')

    # Player notes/tags
    c.execute('''
        CREATE TABLE IF NOT EXISTS player_notes (
            player_name TEXT PRIMARY KEY,
            note TEXT,
            tag TEXT
        )
    ''')

    conn.commit()
    conn.close()

# ------------------- Session Management -------------------

def start_new_session():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO sessions (started_at) VALUES (?)", (datetime.utcnow().isoformat(),))
    conn.commit()
    session_id = c.lastrowid
    conn.close()
    return session_id

def get_latest_session_id():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM sessions ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

# ------------------- Action Logging -------------------

def log_action(player_name, position, action, stack):
    session_id = get_latest_session_id()
    if not session_id:
        session_id = start_new_session()

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO player_actions (session_id, timestamp, player_name, position, action, stack)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (session_id, datetime.utcnow().isoformat(), player_name, position, action, stack))
    conn.commit()
    conn.close()

# ------------------- Stats & Notes -------------------

def classify_player(vpip, pfr):
    if vpip == 0 and pfr == 0:
        return "Unknown"
    elif vpip < 20 and pfr < 10:
        return "NIT"
    elif 20 <= vpip <= 30 and 15 <= pfr <= 25:
        return "TAG"
    elif 30 < vpip <= 40 and 20 <= pfr <= 30:
        return "LAG"
    elif vpip > 40 and pfr > 30:
        return "Maniac"
    else:
        return "Unknown"

def get_player_stats(player_name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT action FROM player_actions WHERE player_name = ?', (player_name,))
    actions = [row[0] for row in c.fetchall()]
    conn.close()

    total = len(actions)
    vpip = sum(1 for a in actions if a.lower() in ['call', 'raise']) / total if total else 0
    pfr = sum(1 for a in actions if a.lower() == 'raise') / total if total else 0

    vpip_pct = round(vpip * 100, 1)
    pfr_pct = round(pfr * 100, 1)
    label = classify_player(vpip_pct, pfr_pct)

    return {
        "hands_logged": total,
        "VPIP": vpip_pct,
        "PFR": pfr_pct,
        "type": label
    }

def get_all_player_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT DISTINCT player_name FROM player_actions')
    player_names = [row[0] for row in c.fetchall()]
    conn.close()

    all_stats = []
    for name in player_names:
        stats = get_player_stats(name)
        stats['player_name'] = name

        note_data = get_note(name)
        stats['note'] = note_data.get('note', '')
        stats['tag'] = note_data.get('tag', '')

        all_stats.append(stats)

    return all_stats

# ------------------- Notes -------------------

def save_note(player_name, note, tag):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO player_notes (player_name, note, tag)
        VALUES (?, ?, ?)
        ON CONFLICT(player_name) DO UPDATE SET note=excluded.note, tag=excluded.tag
    ''', (player_name, note, tag))
    conn.commit()
    conn.close()

def get_note(player_name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT note, tag FROM player_notes WHERE player_name = ?', (player_name,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"note": row[0], "tag": row[1]}
    else:
        return {"note": "", "tag": ""}

# ------------------- Session Summary -------------------

def get_current_session_summary():
    session_id = get_latest_session_id()
    if not session_id:
        return None

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT player_name, action FROM player_actions WHERE session_id = ?', (session_id,))
    actions = c.fetchall()
    conn.close()

    if not actions:
        return None

    total_hands = len(actions)
    vpip = sum(1 for a in actions if a[1].lower() in ['call', 'raise']) / total_hands
    pfr = sum(1 for a in actions if a[1].lower() == 'raise') / total_hands
    players = list(set(a[0] for a in actions))

    return {
        "session_id": session_id,
        "hands_logged": total_hands,
        "vpip_avg": round(vpip * 100, 1),
        "pfr_avg": round(pfr * 100, 1),
        "unique_players": len(players)
    }

def get_all_session_ids():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id FROM sessions ORDER BY id DESC')
    ids = [row[0] for row in c.fetchall()]
    conn.close()
    return ids

def get_session_actions(session_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT timestamp, player_name, position, action, stack
        FROM player_actions
        WHERE session_id = ?
        ORDER BY timestamp ASC
    ''', (session_id,))
    rows = c.fetchall()
    conn.close()

    return rows



