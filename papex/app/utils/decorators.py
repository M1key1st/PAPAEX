from functools import wraps

from flask import abort
from flask_login import current_user


def roles_required(*allowed_roles):
    """Berilgan rollardan biriga ega bo'lgan foydalanuvchigagina ruxsat beradi.
    'admin' roli har doim to'liq ruxsatga ega (all permission)."""

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role_name == "admin":
                return view(*args, **kwargs)
            if current_user.role_name not in allowed_roles:
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


def permission_required(permission):
    """Foydalanuvchi rolining permissions ro'yxatida berilgan ruxsat bor-yo'qligini tekshiradi."""

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            perms = current_user.permissions
            if "all" in perms or permission in perms:
                return view(*args, **kwargs)
            abort(403)

        return wrapped

    return decorator
