from app.models.db import get_db
from app.utils.pagination import paginate


def add_log(actor, action, target=None, details=None, ip=None):
    db = get_db()
    db.execute(
        "INSERT INTO logs (actor, action, target, details, ip) VALUES (?, ?, ?, ?, ?)",
        (actor, action, target, details, ip),
    )
    db.commit()


def list_logs(page=1, per_page=50):
    db = get_db()
    base = "SELECT * FROM logs ORDER BY id DESC"
    count = "SELECT COUNT(*) FROM logs"
    return paginate(db, base, count, [], page, per_page)
