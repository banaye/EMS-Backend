from flask_cors  import CORS
from flask import Blueprint, request
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity,
)
from datetime import datetime, timezone
from marshmallow import ValidationError

from app.extensions import db, bcrypt
from app.models import User
from app.schemas import user_schema, register_schema, login_schema
from app.services.utils.helpers import success, error, get_current_user
from flask_mail import Message

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/register")
def register():
    try:
        data = register_schema.load(request.get_json() or {})
    except ValidationError as exc:
        return error("Validation failed.", 422, exc.messages)

    if User.query.filter_by(email=data["email"]).first():
        return error("Email already registered.", 409)
    if User.query.filter_by(username=data["username"]).first():
        return error("Username already taken.", 409)

    user = User(
        username=data["username"],
        email=data["email"],
        password_hash=bcrypt.generate_password_hash(data["password"]).decode("utf-8"),
        first_name=data["first_name"],
        last_name=data["last_name"],
        role=data.get("role", "student"),
        is_active=True,
        is_verified=False,
    )
    db.session.add(user)
    db.session.commit()

    access = create_access_token(identity=str(user.id))
    refresh = create_refresh_token(identity=str(user.id))

    return success(
        {"user": user_schema.dump(user), "access_token": access, "refresh_token": refresh},
        "Registration successful.",
        201,
    )


@auth_bp.post("/login")
def login():
    try:
        data = login_schema.load(request.get_json() or {})
    except ValidationError as exc:
        return error("Validation failed.", 422, exc.messages)

    user = User.query.filter_by(email=data["email"]).first()
    if not user or not bcrypt.check_password_hash(user.password_hash, data["password"]):
        return error("Invalid credentials.", 401)
    if not user.is_active:
        return error("Account is inactive.", 403)

    user.last_login = datetime.now(timezone.utc)
    db.session.commit()

    access = create_access_token(identity=str(user.id))
    refresh = create_refresh_token(identity=str(user.id))

    return success(
        {"user": user_schema.dump(user), "access_token": access, "refresh_token": refresh},
        "Login successful.",
    )


@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()
    access = create_access_token(identity=str(user_id))
    return success({"access_token": access}, "Token refreshed.")


@auth_bp.get("/me")
@jwt_required()
def me():
    user = get_current_user()
    if not user:
        return error("User not found.", 404)
    return success(user_schema.dump(user))


@auth_bp.patch("/me")
@jwt_required()
def update_profile():
    user = get_current_user()
    if not user:
        return error("User not found.", 404)

    data = request.get_json() or {}
    for field in ("first_name", "last_name", "bio", "avatar_url"):
        if field in data:
            setattr(user, field, data[field])

    db.session.commit()
    return success(user_schema.dump(user), "Profile updated.")


@auth_bp.post("/change-password")
@jwt_required()
def change_password():
    user = get_current_user()
    if not user:
        return error("User not found.", 404)

    data = request.get_json() or {}
    current = data.get("current_password")
    new_pw = data.get("new_password")

    if not current or not new_pw:
        return error("Both current_password and new_password are required.", 400)
    if not bcrypt.check_password_hash(user.password_hash, current):
        return error("Current password is incorrect.", 401)
    if len(new_pw) < 8:
        return error("New password must be at least 8 characters.", 422)

    user.password_hash = bcrypt.generate_password_hash(new_pw).decode("utf-8")
    db.session.commit()
    return success(message="Password changed successfully.")


@auth_bp.post("/forgot-password")
def forgot_password():
    data = request.get_json() or {}
    email = data.get("email")

    if not email:
        return error("Email is required.", 422)

    # Always return success to prevent email enumeration
    user = User.query.filter_by(email=email).first()
    if user:
        reset_token=create_token(
            identity=str(user.id),
            additional_claims={"type": "password_reset"},
            expires_delta=timedelta(minutes=15)
        )
        
        reset_url= f"http://localhost:5173/reset-password? token={reset_token}"
        
        try:
            msg=message(
                subject="Reset your EMS password",
                recipients=[user.email],
                html=f"""<h3>Password  Reset Request</h3>
                <p>Hi {user.first_name},</p>
                <p>Click the link below to reset your password. Link expires in 15 minutes.</p>
                <a href="{reset_url}>{reset_url}</a>
                <p>If you did not request this, ignore this email.</p>
                
                """
            )
            
            mail.send(msg)
        except Exception as e:
            print(f"Email send failed: {e}")
            return success(message=f"If an account exists for that email, a reset link has been sent.")
        # TODO: send reset email here
        pass

@auth_bp.post("/reset-password")
def reset_password():
    data=request.get_json()or {}
    token=data.get("token")
    new_password=data.get("new_password")
    
    if not token or not new_password:
        return error("Token and new_password are required.", 422)
    if len("new_password")<6:
        return error("New password must be at least 6 characters", 422)
    
    try:
        decoded=decode_token(token)
        if decoded.get("type") != "password_reset":
            return error("Invalid token type",401)
        User_id=decoded["sub"]
        user=user.query.get(user_id)
        
        if not user:
            return error("Invalid token.",401)
        
    except Exception:
        return error("Token is invalid or expired.",401)
    
    user.password_hash= bcrypt.generate_password_hash(new_password).decode("utf-8")
    db.session.commit()
    
    return success(message="Password reset successfully. You can now log in.")
        