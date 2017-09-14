from flask_api import FlaskAPI
from flask_sqlalchemy import SQLAlchemy
from flask import jsonify

from config import app_config


db = SQLAlchemy()


def create_app(config_name):
    from models import db, User

    app = FlaskAPI(__name__)
    app.config.from_object(app_config[config_name])

    db.init_app(app)
    with app.app_context():
        db.create_all()
        db.session.commit()

    @app.route("/", methods=["GET"])
    def index():
        response = jsonify({
            "foo": "bar"
            })
        response.status_code = 200
        return response.data

    return app
