# app/extensions.py

from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_marshmallow import Marshmallow
from flask_migrate import Migrate
from flask_cors import CORS
from flask_mail import Mail

mail=Mail()

db = SQLAlchemy()
jwt = JWTManager()
bcrypt = Bcrypt()
ma = Marshmallow()
migrate = Migrate()
cors = CORS()