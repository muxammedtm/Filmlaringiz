import sqlite3
from datetime import date

class Database:
    def __init__(self, db_path="kinobot.db"):
        self.db_path = db_path
        self._init_db()

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._conn() as c:
            c.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id     INTEGER PRIMARY KEY,
                    username    TEXT DEFAULT '',
                    first_name  TEXT DEFAULT '',
                    lang        TEXT DEFAULT 'uz',
                    is_banned   INTEGER DEFAULT 0,
                    joined_at   TEXT DEFAULT (date('now'))
                );

                CREATE TABLE IF NOT EXISTS movies (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    title       TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    year        TEXT DEFAULT '',
                    genre       TEXT DEFAULT '',
                    category    TEXT DEFAULT '',
                    code        TEXT UNIQUE NOT NULL,
                    file_id     TEXT NOT NULL,
                    views       INTEGER DEFAULT 0,
                    added_at    TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS favorites (
                    id       INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id  INTEGER,
                    movie_id INTEGER,
                    UNIQUE(user_id, movie_id)
                );

                CREATE TABLE IF NOT EXISTS history (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id   INTEGER,
                    movie_id  INTEGER,
                    viewed_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS channels (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id  TEXT UNIQUE NOT NULL,
                    username    TEXT NOT NULL,
                    title       TEXT DEFAULT '',
                    is_active   INTEGER DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS settings (
                    key   TEXT PRIMARY KEY,
                    value TEXT DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS admins (
                    user_id  INTEGER PRIMARY KEY,
                    role     TEXT DEFAULT 'moderator',
                    added_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS broadcasts (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    total      INTEGER DEFAULT 0,
                    sent       INTEGER DEFAULT 0,
                    failed     INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now'))
                );

                INSERT OR IGNORE INTO settings(key,value) VALUES
                    ('sub_required','0'),
                    ('forward_block','0'),
                    ('save_block','0');
            """)
            c.commit()

    # ─── USERS ───────────────────────────────────────

    def add_user(self, user_id, username="", first_name="", lang="uz"):
        with self._conn() as c:
            c.execute(
                "INSERT OR IGNORE INTO users(user_id,username,first_name,lang) VALUES(?,?,?,?)",
                (user_id, username, first_name, lang)
            )
            c.commit()

    def get_user(self, user_id) -> dict | None:
        with self._conn() as c:
            row = c.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
            return dict(row) if row else None

    def set_lang(self, user_id, lang):
        with self._conn() as c:
            c.execute("UPDATE users SET lang=? WHERE user_id=?", (lang, user_id))
            c.commit()

    def ban_user(self, user_id):
        with self._conn() as c:
            c.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (user_id,))
            c.commit()

    def unban_user(self, user_id):
        with self._conn() as c:
            c.execute("UPDATE users SET is_banned=0 WHERE user_id=?", (user_id,))
            c.commit()

    def is_banned(self, user_id) -> bool:
        with self._conn() as c:
            row = c.execute("SELECT is_banned FROM users WHERE user_id=?", (user_id,)).fetchone()
            return bool(row and row[0])

    def get_all_user_ids(self) -> list:
        with self._conn() as c:
            return [r[0] for r in c.execute("SELECT user_id FROM users WHERE is_banned=0").fetchall()]

    def get_active_user_ids(self) -> list:
        """So'nggi 7 kun ichida harakatlanganlar"""
        with self._conn() as c:
            rows = c.execute(
                "SELECT DISTINCT user_id FROM history WHERE viewed_at >= date('now','-7 days')"
            ).fetchall()
            return [r[0] for r in rows]

    def get_users_count(self) -> int:
        with self._conn() as c:
            return c.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    def get_today_users_count(self) -> int:
        with self._conn() as c:
            return c.execute(
                "SELECT COUNT(*) FROM users WHERE joined_at=date('now')"
            ).fetchone()[0]

    def get_all_users_info(self, limit=50, offset=0) -> list:
        with self._conn() as c:
            rows = c.execute(
                "SELECT user_id,username,first_name,lang,is_banned,joined_at FROM users LIMIT ? OFFSET ?",
                (limit, offset)
            ).fetchall()
            return [dict(r) for r in rows]

    def search_user(self, query) -> list:
        with self._conn() as c:
            rows = c.execute(
                "SELECT user_id,username,first_name,is_banned FROM users WHERE username LIKE ? OR first_name LIKE ? OR user_id=?",
                (f"%{query}%", f"%{query}%", query if query.isdigit() else -1)
            ).fetchall()
            return [dict(r) for r in rows]

    # ─── MOVIES ──────────────────────────────────────

    def add_movie(self, data: dict):
        with self._conn() as c:
            c.execute(
                """INSERT INTO movies(title,description,year,genre,category,code,file_id)
                   VALUES(:title,:description,:year,:genre,:category,:code,:file_id)""",
                data
            )
            c.commit()

    def update_movie(self, movie_id, field, value):
        allowed = {'title','description','year','genre','category','code'}
        if field not in allowed:
            return
        with self._conn() as c:
            c.execute(f"UPDATE movies SET {field}=? WHERE id=?", (value, movie_id))
            c.commit()

    def get_movie_by_code(self, code) -> dict | None:
        with self._conn() as c:
            row = c.execute("SELECT * FROM movies WHERE code=?", (code,)).fetchone()
            return dict(row) if row else None

    def get_movie_by_id(self, movie_id) -> dict | None:
        with self._conn() as c:
            row = c.execute("SELECT * FROM movies WHERE id=?", (movie_id,)).fetchone()
            return dict(row) if row else None

    def inc_views(self, movie_id):
        with self._conn() as c:
            c.execute("UPDATE movies SET views=views+1 WHERE id=?", (movie_id,))
            c.commit()

    def delete_movie(self, movie_id):
        with self._conn() as c:
            c.execute("DELETE FROM movies WHERE id=?", (movie_id,))
            c.execute("DELETE FROM favorites WHERE movie_id=?", (movie_id,))
            c.commit()

    def get_all_movies(self, limit=30, offset=0) -> list:
        with self._conn() as c:
            rows = c.execute(
                "SELECT id,title,code,genre,category,views FROM movies ORDER BY added_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            ).fetchall()
            return [dict(r) for r in rows]

    def search_movies(self, query) -> list:
        with self._conn() as c:
            rows = c.execute(
                "SELECT id,title,code FROM movies WHERE title LIKE ? OR code=? LIMIT 20",
                (f"%{query}%", query)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_top_movies(self, limit=10) -> list:
        with self._conn() as c:
            rows = c.execute(
                "SELECT id,title,code,views FROM movies ORDER BY views DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_new_movies(self, limit=10) -> list:
        with self._conn() as c:
            rows = c.execute(
                "SELECT id,title,code,added_at FROM movies ORDER BY added_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_categories(self) -> list:
        with self._conn() as c:
            rows = c.execute(
                "SELECT DISTINCT category FROM movies WHERE category!='' ORDER BY category"
            ).fetchall()
            return [r[0] for r in rows]

    def get_genres(self) -> list:
        with self._conn() as c:
            rows = c.execute(
                "SELECT DISTINCT genre FROM movies WHERE genre!='' ORDER BY genre"
            ).fetchall()
            return [r[0] for r in rows]

    def get_movies_count(self) -> int:
        with self._conn() as c:
            return c.execute("SELECT COUNT(*) FROM movies").fetchone()[0]

    # ─── FAVORITES ───────────────────────────────────

    def add_favorite(self, user_id, movie_id):
        with self._conn() as c:
            c.execute("INSERT OR IGNORE INTO favorites(user_id,movie_id) VALUES(?,?)", (user_id, movie_id))
            c.commit()

    def remove_favorite(self, user_id, movie_id):
        with self._conn() as c:
            c.execute("DELETE FROM favorites WHERE user_id=? AND movie_id=?", (user_id, movie_id))
            c.commit()

    def is_favorite(self, user_id, movie_id) -> bool:
        with self._conn() as c:
            row = c.execute(
                "SELECT 1 FROM favorites WHERE user_id=? AND movie_id=?", (user_id, movie_id)
            ).fetchone()
            return bool(row)

    def get_favorites(self, user_id) -> list:
        with self._conn() as c:
            rows = c.execute(
                """SELECT m.id,m.title,m.code FROM favorites f
                   JOIN movies m ON m.id=f.movie_id
                   WHERE f.user_id=? ORDER BY f.id DESC""",
                (user_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    # ─── HISTORY ─────────────────────────────────────

    def add_history(self, user_id, movie_id):
        with self._conn() as c:
            c.execute("INSERT INTO history(user_id,movie_id) VALUES(?,?)", (user_id, movie_id))
            c.commit()

    def get_history(self, user_id, limit=10) -> list:
        with self._conn() as c:
            rows = c.execute(
                """SELECT m.id,m.title,m.code,h.viewed_at FROM history h
                   JOIN movies m ON m.id=h.movie_id
                   WHERE h.user_id=? ORDER BY h.id DESC LIMIT ?""",
                (user_id, limit)
            ).fetchall()
            return [dict(r) for r in rows]

    # ─── CHANNELS ────────────────────────────────────

    def add_channel(self, channel_id, username, title=""):
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO channels(channel_id,username,title) VALUES(?,?,?)",
                (channel_id, username, title)
            )
            c.commit()

    def get_channels(self) -> list:
        with self._conn() as c:
            rows = c.execute("SELECT * FROM channels WHERE is_active=1").fetchall()
            return [dict(r) for r in rows]

    def delete_channel(self, ch_id):
        with self._conn() as c:
            c.execute("DELETE FROM channels WHERE id=?", (ch_id,))
            c.commit()

    def get_channels_count(self) -> int:
        with self._conn() as c:
            return c.execute("SELECT COUNT(*) FROM channels WHERE is_active=1").fetchone()[0]

    # ─── SETTINGS ────────────────────────────────────

    def get_setting(self, key, default="0") -> str:
        with self._conn() as c:
            row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
            return row[0] if row else default

    def set_setting(self, key, value):
        with self._conn() as c:
            c.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, str(value)))
            c.commit()

    # ─── ADMINS ──────────────────────────────────────

    def add_admin(self, user_id, role="moderator"):
        with self._conn() as c:
            c.execute("INSERT OR REPLACE INTO admins(user_id,role) VALUES(?,?)", (user_id, role))
            c.commit()

    def remove_admin(self, user_id):
        with self._conn() as c:
            c.execute("DELETE FROM admins WHERE user_id=?", (user_id,))
            c.commit()

    def get_admins(self) -> list:
        with self._conn() as c:
            rows = c.execute("SELECT user_id,role FROM admins").fetchall()
            return [dict(r) for r in rows]

    def get_admin_ids(self) -> list:
        with self._conn() as c:
            return [r[0] for r in c.execute("SELECT user_id FROM admins").fetchall()]

    def get_admin_role(self, user_id) -> str | None:
        with self._conn() as c:
            row = c.execute("SELECT role FROM admins WHERE user_id=?", (user_id,)).fetchone()
            return row[0] if row else None

    # ─── STATS ───────────────────────────────────────

    def get_stats(self) -> dict:
        return {
            "users":       self.get_users_count(),
            "today_users": self.get_today_users_count(),
            "movies":      self.get_movies_count(),
            "channels":    self.get_channels_count(),
            "admins":      len(self.get_admin_ids()),
        }