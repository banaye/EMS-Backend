from functools import wraps
from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from app.extensions import db
from app.models import User
import re
import uuid


# ─────────────────────────────────────────────
#  Response helpers
# ─────────────────────────────────────────────

def success(data=None, message="Success", status=200, meta=None):
    body = {"success": True, "message": message}
    if data is not None:
        body["data"] = data
    if meta:
        body["meta"] = meta
    return jsonify(body), status


def error(message="An error occurred", status=400, errors=None):
    body = {"success": False, "message": message}
    if errors:
        body["errors"] = errors
    return jsonify(body), status


# ─────────────────────────────────────────────
#  Pagination
# ─────────────────────────────────────────────

def paginate(query, schema, page=None, per_page=20):
    page = page or request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", per_page, type=int)
    per_page = min(per_page, 100)

    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    meta = {
        "page": paginated.page,
        "per_page": paginated.per_page,
        "total": paginated.total,
        "pages": paginated.pages,
        "has_next": paginated.has_next,
        "has_prev": paginated.has_prev,
    }
    return success(schema.dump(paginated.items), meta=meta)


# ─────────────────────────────────────────────
#  Auth helpers
# ─────────────────────────────────────────────

def get_current_user():
    user_id = get_jwt_identity()
    if user_id is None:
        return None
    try:
        return db.session.get(User, int(user_id))
    except (ValueError, TypeError):
        return None


def roles_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user = get_current_user()
            if not user or user.role not in roles:
                return error("Insufficient permissions.", 403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user = get_current_user()
        if not user or user.role != "admin":
            return error("Admin access required.", 403)
        return fn(*args, **kwargs)
    return wrapper


def active_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user = get_current_user()
        if not user or not user.is_active:
            return error("Account is inactive.", 403)
        return fn(*args, **kwargs)
    return wrapper


# ─────────────────────────────────────────────
#  Slugify
# ─────────────────────────────────────────────

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text


def unique_slug(model, text: str, field="slug") -> str:
    base = slugify(text)
    slug = base
    n = 1
    while db.session.query(model).filter(getattr(model, field) == slug).first():
        slug = f"{base}-{n}"
        n += 1
    return slug


# ─────────────────────────────────────────────
#  Certificate number
# ─────────────────────────────────────────────

def generate_certificate_number():
    return f"CERT-{uuid.uuid4().hex[:10].upper()}"