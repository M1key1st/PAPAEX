from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.models.db import get_db


class AdminUser(UserMixin):
    """Flask-Login talab qiladigan interfeysni ta'minlovchi yupqa wrapper."""

    def __init__(self, row):
        self.id = str(row["id"])
        self.username = row["username"]
        self.email = row["email"]
        self.is_active_flag = bool(row["is_active"])
        self.role_id = row["role_id"]
        self.role_name = row["role_name"]
        self.permissions = set(
            p.strip() for p in (row["permissions"] or "").split(",") if p.strip()
        )

    @property
    def is_active(self):
        return self.is_active_flag


def _row_to_query():
    return """
        SELECT users.*, roles.name AS role_name, roles.permissions AS permissions
        FROM users
        JOIN roles ON roles.id = users.role_id
        WHERE users.id = ?
    """


def get_user_by_id(user_id):
    db = get_db()
    row = db.execute(_row_to_query(), (user_id,)).fetchone()
    return AdminUser(row) if row else None


def get_user_by_username(username):
    db = get_db()
    row = db.execute(
        """SELECT users.*, roles.name AS role_name, roles.permissions AS permissions
           FROM users JOIN roles ON roles.id = users.role_id
           WHERE users.username = ? OR users.email = ?""",
        (username, username),
    ).fetchone()
    return row


def verify_password(user_row, password):
    return check_password_hash(user_row["password_hash"], password)


def touch_last_login(user_id):
    db = get_db()
    db.execute(
        "UPDATE users SET last_login_at = datetime('now') WHERE id = ?", (user_id,)
    )
    db.commit()


def list_users():
    db = get_db()
    return db.execute(
        """SELECT users.*, roles.name AS role_name, roles.label AS role_label
           FROM users JOIN roles ON roles.id = users.role_id
           ORDER BY users.created_at DESC"""
    ).fetchall()


def list_roles():
    db = get_db()
    return db.execute("SELECT * FROM roles ORDER BY id").fetchall()


def get_role_by_name(name):
    db = get_db()
    return db.execute("SELECT * FROM roles WHERE name = ?", (name,)).fetchone()


def create_user(username, email, password, role_id, is_active=True):
    db = get_db()
    cur = db.execute(
        """INSERT INTO users (username, email, password_hash, role_id, is_active)
           VALUES (?, ?, ?, ?, ?)""",
        (username.strip(), email.strip().lower(), generate_password_hash(password), role_id, int(is_active)),
    )
    db.commit()
    return cur.lastrowid


def update_user(user_id, username, email, role_id, is_active, password=None):
    db = get_db()
    if password:
        db.execute(
            """UPDATE users SET username=?, email=?, role_id=?, is_active=?, password_hash=?
               WHERE id=?""",
            (username.strip(), email.strip().lower(), role_id, int(is_active),
             generate_password_hash(password), user_id),
        )
    else:
        db.execute(
            "UPDATE users SET username=?, email=?, role_id=?, is_active=? WHERE id=?",
            (username.strip(), email.strip().lower(), role_id, int(is_active), user_id),
        )
    db.commit()


def delete_user(user_id):
    db = get_db()
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()


def username_or_email_taken(username, email, exclude_id=None):
    db = get_db()
    query = "SELECT id FROM users WHERE (username = ? OR email = ?)"
    params = [username.strip(), email.strip().lower()]
    if exclude_id:
        query += " AND id != ?"
        params.append(exclude_id)
    return db.execute(query, params).fetchone() is not None
