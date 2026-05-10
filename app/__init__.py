from flask import Flask, redirect, url_for

from .config import Config
from .auth import login_manager
from .db import SessionLocal


def create_app() -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config["SECRET_KEY"] = Config.SECRET_KEY

    login_manager.init_app(app)

    from .public import bp as public_bp
    from .admin import bp as admin_bp

    app.register_blueprint(admin_bp)
    app.register_blueprint(public_bp)

    @app.teardown_appcontext
    def remove_session(exc=None):
        SessionLocal.remove()

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    return app
