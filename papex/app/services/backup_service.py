"""Avtomatik Backup — ma'lumotlar bazasi va sozlamalarni zaxiralash."""

import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from flask import current_app, send_file

from app.models.db import get_db


def _backup_dir():
    path = Path(current_app.config.get("BACKUP_DIR", "backups"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def create_backup():
    """Database faylini backup papkasiga nusxalash."""
    db_path = Path(current_app.config["DB_PATH"])
    if not db_path.exists():
        return {"error": "Database not found"}

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"papex_backup_{timestamp}.db"
    backup_path = _backup_dir() / backup_filename

    # SQLite VACUUM orqali toza backup
    try:
        conn = sqlite3.connect(str(db_path))
        conn.execute(f"VACUUM INTO '{backup_path}'")
        conn.close()
    except Exception:
        # VACUUM INTO mavjud bo'lmasa, oddiy nusxalash
        shutil.copy2(str(db_path), str(backup_path))

    size_bytes = backup_path.stat().st_size

    db = get_db()
    db.execute(
        "INSERT INTO backups (filename, size_bytes) VALUES (?, ?)",
        (backup_filename, size_bytes),
    )
    db.commit()

    return {
        "filename": backup_filename,
        "size_bytes": size_bytes,
        "created_at": datetime.now().isoformat(),
    }


def list_backups():
    """Backup lar ro'yxatini qaytarish."""
    db = get_db()
    rows = db.execute("SELECT * FROM backups ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]


def delete_backup(backup_id):
    """Backup ni o'chirish."""
    db = get_db()
    row = db.execute("SELECT filename FROM backups WHERE id = ?", (backup_id,)).fetchone()
    if row:
        backup_path = _backup_dir() / row["filename"]
        if backup_path.exists():
            backup_path.unlink()
        db.execute("DELETE FROM backups WHERE id = ?", (backup_id,))
        db.commit()
        return True
    return False


def download_backup(backup_id):
    """Backup faylini yuklab olish."""
    db = get_db()
    row = db.execute("SELECT filename FROM backups WHERE id = ?", (backup_id,)).fetchone()
    if row:
        backup_path = _backup_dir() / row["filename"]
        if backup_path.exists():
            return send_file(
                str(backup_path),
                as_attachment=True,
                download_name=row["filename"],
            )
    return None


def restore_backup(backup_id):
    """Backup dan tiklash."""
    db = get_db()
    row = db.execute("SELECT filename FROM backups WHERE id = ?", (backup_id,)).fetchone()
    if not row:
        return {"error": "Backup not found"}

    backup_path = _backup_dir() / row["filename"]
    if not backup_path.exists():
        return {"error": "Backup file not found"}

    db_path = Path(current_app.config["DB_PATH"])

    # Joriy database ni backup ga nusxalash
    current_backup = db_path.parent / f"papex_pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy2(str(db_path), str(current_backup))

    # Backup ni tiklash
    shutil.copy2(str(backup_path), str(db_path))

    return {"success": True, "message": "Database restored successfully"}


def get_backup_stats():
    """Backup statistikasi."""
    db = get_db()
    total_backups = db.execute("SELECT COUNT(*) FROM backups").fetchone()[0]
    total_size = db.execute("SELECT COALESCE(SUM(size_bytes), 0) FROM backups").fetchone()[0]
    last_backup = db.execute(
        "SELECT * FROM backups ORDER BY id DESC LIMIT 1"
    ).fetchone()

    return {
        "total_backups": total_backups,
        "total_size_bytes": total_size,
        "last_backup": dict(last_backup) if last_backup else None,
    }
