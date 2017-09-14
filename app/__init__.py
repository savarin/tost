from flask_api import FlaskAPI
from flask_sqlalchemy import SQLAlchemy
from flask import jsonify
from flask import request, jsonify

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


    @app.route("/signup", methods=["POST"])
    def signup():
        email = str(request.data.get("email", ""))
        if User.query.filter_by(_user_email=email).first():
            response = jsonify({
                "code": 10,
                "msg": "already signed up with that email"
            })
            response.status_code = 400
            return response

        user = User(email=email)
        user.save()
        response = jsonify({
            "user": {
                "id": user._user_auth_token,
                "email": user._user_email
            }
        })
        response.status_code = 200
        return response


    @app.route("/authcheck", methods=["POST"])
    def authcheck():
        auth_token = str(request.data.get("auth_token", ""))
        user = User.query.filter_by(_user_auth_token=auth_token).first()

        if not (user and user._user_auth_token == auth_token):
            response = jsonify({
                "code": 20,
                "msg": "invalid token"
            })
            response.status_code = 400
            return response

        response = jsonify({
            "user": {
                "id": user._user_auth_token,
                "email": user._user_email
            }
        })
        response.status_code = 200
        return response


    return app
