from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import limiter
from app.services import log_service, user_service
from app.utils.security import get_client_ip, is_safe_url

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/kirish", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user_row = user_service.get_user_by_username(username)

        if user_row and user_row["is_active"] and user_service.verify_password(user_row, password):
            user = user_service.get_user_by_id(user_row["id"])
            login_user(user, remember=True)
            user_service.touch_last_login(user_row["id"])
            log_service.add_log(user.username, "login", ip=get_client_ip())

            next_url = request.args.get("next")
            if next_url and is_safe_url(next_url):
                return redirect(next_url)
            return redirect(url_for("admin.dashboard"))

        flash("Login yoki parol noto'g'ri.")

    return render_template("auth/login.html")


@auth_bp.route("/chiqish")
@login_required
def logout():
    log_service.add_log(current_user.username, "logout", ip=get_client_ip())
    logout_user()
    return redirect(url_for("auth.login"))
