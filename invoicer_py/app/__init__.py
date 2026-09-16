import os
from flask import Flask
from app.extensions import db, login_manager

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


def _resolve_database_uri():
    """Use Postgres if DATABASE_URL is set (e.g. on Render), else fall back to
    a local SQLite file for running on your own laptop."""
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        # Render (and some other hosts) hand out "postgres://" but
        # SQLAlchemy 2.x / psycopg require "postgresql://"
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        return database_url
    return "sqlite:///" + os.path.join(BASE_DIR, "invoicer.db")


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = _resolve_database_uri()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.auth.routes import auth_bp
    from app.main.routes import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    with app.app_context():
        db.create_all()

    return app

