from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from app.extensions import db, bcrypt
from app.models import User, Course, Exam, ExamAttempt, Notification
from app.schemas import (
    user_schema, users_schema, notification_schema, notifications_schema,
)
from app.services.utils.helpers import (
    success, error, paginate, get_current_user, admin_required, roles_required
)

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")
notifications_bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")


# ═══════════════════════════════════════════════
#  ADMIN — USERS
# ═══════════════════════════════════════════════

@admin_bp.get("/users")
@jwt_required()
@roles_required("admin", "instructor")
def list_users():
    role = request.args.get("role")
    search = request.args.get("search")
    query = User.query

    if role:
        query = query.filter_by(role=role)
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


@admin_bp.get("/users/<int:user_id>")
@jwt_required()
@roles_required("admin", "instructor")
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return success(user_schema.dump(user))


@admin_bp.post("/users")
@jwt_required()
@admin_required
def create_user():
    data = request.get_json() or {}

    if not data.get("email"):
        return error("Email is required.", 422)
    if not data.get("username"):
        return error("Username is required.", 422)
    if not data.get("password"):
        return error("Password is required.", 422)

    if User.query.filter_by(email=data["email"]).first():
        return error("Email already registered.", 409)
    if User.query.filter_by(username=data["username"]).first():
        return error("Username already taken.", 409)

    user = User(
        username=data["username"],
        email=data["email"],
        password_hash=bcrypt.generate_password_hash(data["password"]).decode("utf-8"),
        first_name=data.get("first_name", ""),
        last_name=data.get("last_name", ""),
        role=data.get("role", "student"),
        is_active=True,
        is_verified=True,
    )
    db.session.add(user)
    db.session.commit()
    return success(user_schema.dump(user), "User created.", 201)


@admin_bp.patch("/users/<int:user_id>")
@jwt_required()
@admin_required
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}

    for field in ("first_name", "last_name", "bio", "avatar_url",
                  "role", "is_active", "is_verified"):
        if field in data:
            setattr(user, field, data[field])

    db.session.commit()
    return success(user_schema.dump(user), "User updated.")


@admin_bp.delete("/users/<int:user_id>")
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


@admin_bp.patch("/users/<int:user_id>/toggle-active")
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


@admin_bp.post("/users/<int:user_id>/reset-password")
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


# ═══════════════════════════════════════════════
#  ADMIN — STATS
# ═══════════════════════════════════════════════

@admin_bp.get("/stats")
@jwt_required()
@admin_required
def dashboard_stats():
    return success({
        "total_users": User.query.count(),
        "total_students": User.query.filter_by(role="student").count(),
        "total_instructors": User.query.filter_by(role="instructor").count(),
        "active_users": User.query.filter_by(is_active=True).count(),
        "total_courses": Course.query.count(),
        "published_courses": Course.query.filter_by(is_published=True).count(),
        "total_exams": Exam.query.count(),
        "published_exams": Exam.query.filter_by(is_published=True).count(),
        "total_attempts": ExamAttempt.query.count(),
        "graded_attempts": ExamAttempt.query.filter_by(status="graded").count(),
    })


# ═══════════════════════════════════════════════
#  NOTIFICATIONS
# ═══════════════════════════════════════════════

@notifications_bp.get("")
@jwt_required()
def list_notifications():
    user = get_current_user()
    if not user:
        return error("Unauthorized.", 401)

    query = Notification.query.filter_by(user_id=user.id).order_by(
        Notification.created_at.desc()
    )
    unread_count = Notification.query.filter_by(
        user_id=user.id, is_read=False
    ).count()

    notifications = query.limit(50).all()
    data = notifications_schema.dump(notifications)
    return success(data, meta={"unread_count": unread_count})


@notifications_bp.patch("/<int:notif_id>/read")
@jwt_required()
def mark_read(notif_id):
    user = get_current_user()
    notif = Notification.query.filter_by(
        id=notif_id, user_id=user.id
    ).first_or_404()
    notif.is_read = True
    db.session.commit()
    return success(message="Notification marked as read.")


@notifications_bp.post("/read-all")
@jwt_required()
def mark_all_read():
    user = get_current_user()
    if not user:
        return error("Unauthorized.", 401)

    Notification.query.filter_by(user_id=user.id, is_read=False).update(
        {"is_read": True}
    )
    db.session.commit()
    return success(message="All notifications marked as read.")


@notifications_bp.delete("/<int:notif_id>")
@jwt_required()
def delete_notification(notif_id):
    user = get_current_user()
    notif = Notification.query.filter_by(
        id=notif_id, user_id=user.id
    ).first_or_404()
    db.session.delete(notif)
    db.session.commit()
    return success(message="Notification deleted.")