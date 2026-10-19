from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from database import db
from models.user import User
from routes.auth import admin_required

users_bp = Blueprint("users", __name__, url_prefix="/users")


@users_bp.route("/")
@login_required
@admin_required
def index():
    users = User.query.order_by(User.role.asc(), User.username.asc()).all()
    return render_template("users/index.html", users=users)


@users_bp.route("/new", methods=["POST"])
@login_required
@admin_required
def create():
    username = request.form.get("username", "").strip()
    full_name = request.form.get("full_name", "").strip()
    role = request.form.get("role", "cashier").strip()
    password = request.form.get("password", "").strip()

    errors = []
    if not username:
        errors.append("Username is required.")
    elif User.query.filter_by(username=username).first():
        errors.append(f"Username '{username}' is already taken.")

    if not full_name:
        errors.append("Full name is required.")
    if role not in ("admin", "cashier"):
        errors.append("Invalid user role.")
    if not password or len(password) < 6:
        errors.append("Password must be at least 6 characters.")

    if errors:
        for err in errors:
            flash(err, "danger")
        return redirect(url_for("users.index"))

    user = User(
        username=username,
        full_name=full_name,
        role=role,
        is_active=True,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    flash(f"User '{user.username}' ({user.role}) created successfully!", "success")
    return redirect(url_for("users.index"))


@users_bp.route("/<int:user_id>/toggle-status", methods=["POST"])
@login_required
@admin_required
def toggle_status(user_id):
    if user_id == current_user.user_id:
        flash("You cannot deactivate your own account.", "warning")
        return redirect(url_for("users.index"))

    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    status_str = "activated" if user.is_active else "deactivated"
    flash(f"User '{user.username}' has been {status_str}.", "info")
    return redirect(url_for("users.index"))


@users_bp.route("/<int:user_id>/reset-password", methods=["POST"])
@login_required
@admin_required
def reset_password(user_id):
    new_password = request.form.get("new_password", "").strip()
    if not new_password or len(new_password) < 6:
        flash("New password must be at least 6 characters.", "danger")
        return redirect(url_for("users.index"))

    user = User.query.get_or_404(user_id)
    user.set_password(new_password)
    db.session.commit()
    flash(f"Password reset successfully for '{user.username}'.", "success")
    return redirect(url_for("users.index"))
