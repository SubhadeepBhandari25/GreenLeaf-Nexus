from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_user, logout_user, login_required, current_user
from models.user import User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.url))
        if not current_user.is_admin:
            flash("Access denied: Administrator privileges required.", "danger")
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for("dashboard.index"))
        return redirect(url_for("pos.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        if not username or not password:
            flash("Please enter both username and password.", "warning")
            return render_template("auth/login.html", username=username)

        user = User.query.filter_by(username=username).first()

        if not user or not user.check_password(password):
            flash("Invalid username or password.", "danger")
            return render_template("auth/login.html", username=username)

        if not user.is_active:
            flash("Your account has been deactivated. Please contact an administrator.", "danger")
            return render_template("auth/login.html", username=username)

        login_user(user, remember=remember)
        flash(f"Welcome back, {user.full_name}!", "success")

        next_page = request.args.get("next")
        if next_page and next_page.startswith("/"):
            delim = "&" if "?" in next_page else "?"
            return redirect(f"{next_page}{delim}welcome=true")

        if user.is_admin:
            return redirect(url_for("dashboard.index", welcome="true"))
        return redirect(url_for("pos.index", welcome="true"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been successfully logged out.", "info")
    return redirect(url_for("auth.login"))
