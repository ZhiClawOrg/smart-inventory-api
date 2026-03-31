from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///inventory.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    CORS(app)
    db.init_app(app)

    from app.routes.products import products_bp
    from app.routes.orders import orders_bp

    app.register_blueprint(products_bp, url_prefix="/api/v1")
    app.register_blueprint(orders_bp, url_prefix="/api/v1")

    with app.app_context():
        db.create_all()

    return app
