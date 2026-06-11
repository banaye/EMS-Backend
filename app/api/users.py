from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from app.extensions import db, bcrypt
from app.models import User
from app.schemas import user_schema, users_schema
from app.services.utils.helpers import (
    success, error, paginate, get_current_user,
    roles_required, admin_required,
)

users_bp = Blueprint("users", __name__, url_prefix="/api/users")


@users_bp.get("")
@users_bp.get("/")
@jwt_required()
@admin_required
def list_users():
    role = request.args.get("role")
    is_active = request.args.get("is_active")
    search = request.args.get("search")

    query = User.query

    if role:
        query = query.filter_by(role=role)
    if is_active is not None:
        query = query.filter_by(is_active=is_active.lower() == "true")
    if search:
        query = query.filter(
            db.or_(
                User.email.ilike(f"%{search}%"),
                User.username.ilike(f"%{search}%"),
                User.first_name.ilike(f"%{search}%"),
                User.last_name.ilike(f"%{search}%"),
            )
        )

    return paginate(query, users_schema)


@users_bp.get("/stats")
@jwt_required()
@admin_required
def user_stats():
    return success({
        "total": User.query.count(),
        "students": User.query.filter_by(role="student").count(),
        "instructors": User.query.filter_by(role="instructor").count(),
        "admins": User.query.filter_by(role="admin").count(),
        "active": User.query.filter_by(is_active=True).count(),
        "inactive": User.query.filter_by(is_active=False).count(),
    })


@users_bp.get("/<int:user_id>")
@jwt_required()
@admin_required
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return success(user_schema.dump(user))


@users_bp.patch("/<int:user_id>")
@jwt_required()
@admin_required
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}

    for field in ("first_name", "last_name", "bio", "avatar_url", "role",
                  "is_active", "is_verified"):
        if field in data:
            setattr(user, field, data[field])

    db.session.commit()
    return success(user_schema.dump(user), "User updated.")


@users_bp.delete("/<int:user_id>")
@jwt_required()
@admin_required
def delete_user(user_id):
    current_user = get_current_user()
    if current_user.id == user_id:
        return error("You cannot delete your own account.", 400)

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return success(message="User deleted.")


@users_bp.patch("/<int:user_id>/toggle-active")
@jwt_required()
@admin_required
def toggle_active(user_id):
    current_user = get_current_user()
    if current_user.id == user_id:
        return error("You cannot deactivate your own account.", 400)

    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    status_str = "activated" if user.is_active else "deactivated"
    return success(user_schema.dump(user), f"User {status_str}.")


@users_bp.post("/<int:user_id>/reset-password")
@jwt_required()
@admin_required
def reset_password(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}
    new_password = data.get("new_password")

    if not new_password or len(new_password) < 8:
        return error("Password must be at least 8 characters.", 422)

    user.password_hash = bcrypt.generate_password_hash(new_password).decode("utf-8")
    db.session.commit()
    return success(message="Password reset successfully.")