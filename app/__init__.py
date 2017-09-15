from flask_api import FlaskAPI
from flask_httpauth import HTTPBasicAuth
from flask_sqlalchemy import SQLAlchemy
from flask import request, jsonify

from config import app_config
import helpers

db = SQLAlchemy()


def create_app(config_name):
    from models import db, User, Tost, Propagation

    app = FlaskAPI(__name__)
    app.config.from_object(app_config[config_name])

    db.init_app(app)
    with app.app_context():
        db.create_all()
        db.session.commit()

    auth = HTTPBasicAuth()

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

    @app.route("/auth", methods=["POST"])
    def login():
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

    @app.route("/tost", methods=["GET", "POST"])
    @auth.login_required
    def tost():
        email, auth_token = helpers.get_header_auth(request)
        user = User.query.filter_by(_user_auth_token=auth_token).first()

        if request.method == "GET":
            tosts = Tost.query.filter_by(tost_creator_user_id=user.user_id).all()

            result = {}
            for tost in tosts:
                ppgn_token = Propagation.query.filter_by(ppgn_tost_id=tost.tost_id)\
                                              .filter_by(ppgn_user_id=user.user_id)\
                                              .first()\
                                              ._ppgn_token
                result[ppgn_token[:4]] = tost._tost_body[:32]

            response = jsonify(result)
            response.status_code = 200
            return response

        elif request.method == "POST":
            body = str(request.data.get("body", ""))

            if not body:
                response = jsonify({
                    "code": 30,
                    "msg": "invalid",
                    "field": {
                        "tost": {
                            "body": "must not be blank"
                        }
                    }
                })
                response.status_code = 400
                return response

            tost = Tost(body, user.user_id)
            tost.save()

            ppgn = Propagation(tost.tost_id, user.user_id)
            ppgn.save()

            response = jsonify({
                "tost": {
                    "creator-id": user.user_id,
                    "created-at": tost.tost_create_timestamp,
                    "body": body
                }
            })
            response.status_code = 200
            return response

    @app.route("/list", methods=["GET"])
    @auth.login_required
    def list():
        email, auth_token = helpers.get_header_auth(request)
        user = User.query.filter_by(_user_auth_token=auth_token).first()

        tosts = Tost.query.filter_by(tost_creator_user_id=user.user_id).all()

        result = {}
        for tost in tosts:
            ppgn_token = Propagation.query.filter_by(ppgn_tost_id=tost.tost_id)\
                                          .filter_by(ppgn_user_id=user.user_id)\
                                          .first()\
                                          ._ppgn_token
            result[ppgn_token[:4]] = tost._tost_body[:32]

        response = jsonify(result)
        response.status_code = 200
        return response

    @app.route("/create", methods=["POST"])
    @auth.login_required
    def create():
        body = str(request.data.get("body", ""))

        if not body:
            response = jsonify({
                "code": 30,
                "msg": "invalid",
                "field": {
                    "tost": {
                        "body": "must not be blank"
                    }
                }
            })
            response.status_code = 400
            return response

        email, auth_token = helpers.get_header_auth(request)
        user = User.query.filter_by(_user_auth_token=auth_token).first()

        tost = Tost(body, user.user_id)
        tost.save()

        ppgn = Propagation(tost.tost_id, user.user_id)
        ppgn.save()

        response = jsonify({
            "tost": {
                "creator-id": user.user_id,
                "created-at": tost.tost_create_timestamp,
                "body": body
            }
        })
        response.status_code = 200
        return response

    @auth.verify_password
    def verify_password(email, auth_token):
        user = User.query.filter_by(_user_email=email).first()
        if not (user and user._user_auth_token == auth_token):
            return False
        return True

    return app
