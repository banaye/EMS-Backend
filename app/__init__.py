import os
from flask import Flask, jsonify, send_from_directory
from flask_jwt_extended import JWTManager
from flask_cors import CORS

from app.extensions import db, jwt, bcrypt, ma, mail, migrate
from config import config_map


def create_app(config_name: str = None) -> Flask:
    config_name = config_name or os.getenv("FLASK_ENV", "development")
    config_obj = config_map.get(config_name, config_map["default"])

    app = Flask(__name__)
    app.config.from_object(config_obj)
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'your_email@gmail.com'
    app.config['MAIL_PASSWORD'] = 'your_app_password'

    # ── Extensions ──────────────────────────────
    db.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)
    ma.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)

    # ── CORS ─────────────────────────────────────
    CORS(app,
         resources={
             r"/api/*": {
                 "origins": ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
                 "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
                 "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
                 "expose_headers": ["Content-Type", "Authorization"],
                 "supports_credentials": True,
                 "max_age": 3600,
             },
             r"/uploads/*": {
                 "origins": "*",
                 "methods": ["GET", "OPTIONS"],
             },
         })

    # ── JWT error handlers ───────────────────────
    @jwt.unauthorized_loader
    def missing_token(reason):
        return jsonify({"success": False, "message": f"Unauthorized: {reason}"}), 401

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return jsonify({"success": False, "message": f"Invalid token: {reason}"}), 422

    @jwt.expired_token_loader
    def expired_token(header, payload):
        return jsonify({"success": False, "message": "Token has expired."}), 401

    # ── Global error handlers ────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"success": False, "message": "Resource not found."}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"success": False, "message": "Method not allowed."}), 405

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"success": False, "message": "Internal server error."}), 500

    # ── Blueprints ───────────────────────────────
    from app.api.auth import auth_bp
    from app.api.courses import courses_bp
    from app.api.exams import exams_bp, questions_bp, banks_bp
    from app.api.admin import admin_bp, notifications_bp
    from app.api.users import users_bp
    from app.api.reports import reports_bp

    for bp in (auth_bp, courses_bp, exams_bp, questions_bp, banks_bp,
               admin_bp, notifications_bp, users_bp, reports_bp):
        app.register_blueprint(bp)

    # ── Upload folder path (shared) ───────────────
    # __file__ is server/app/__init__.py
    # dirname x1 = server/app
    # dirname x2 = server
    # + static/uploads = server/static/uploads
    UPLOAD_FOLDER = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'static', 'uploads'
    )

    # ── Serve uploaded files ──────────────────────
    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        response = send_from_directory(UPLOAD_FOLDER, filename)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response

    # ── Debug uploads ─────────────────────────────
    @app.route('/debug/uploads')
    def debug_uploads():
        files = os.listdir(UPLOAD_FOLDER) if os.path.exists(UPLOAD_FOLDER) else []
        return jsonify({
            "upload_folder": UPLOAD_FOLDER,
            "folder_exists": os.path.exists(UPLOAD_FOLDER),
            "files": files,
            "file_count": len(files),
        })

    # ── Health check ─────────────────────────────
    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "env": config_name})

    # ── OPTIONS preflight handler ─────────────────
    @app.route('/api/<path:path>', methods=['OPTIONS'])
    @app.route('/api', methods=['OPTIONS'])
    def handle_options(path=None):
        return jsonify({}), 200

    # ── Create tables (dev convenience) ──────────
    with app.app_context():
        db.create_all()

    return app