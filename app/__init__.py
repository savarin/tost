from flask_api import FlaskAPI
from flask_httpauth import HTTPBasicAuth
from flask_sqlalchemy import SQLAlchemy
from flask import request, jsonify, redirect, url_for

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
        user = User.query.filter_by(_user_email=email).first()

        if user:
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
                ppgn_token = Propagation.query.filter_by(ppgn_user_id=user.user_id)\
                                              .filter_by(ppgn_tost_id=tost.tost_id)\
                                              .filter_by(_ppgn_disabled=False)\
                                              .filter_by(_ppgn_ancestor_disabled=False)\
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
                    "access-token": ppgn._ppgn_token,
                    "creator-id": tost.tost_creator_user_id,
                    "created-at": tost.tost_create_timestamp,
                    "updator-id": tost._tost_updator_user_id,
                    "updated-at": tost._tost_update_timestamp,
                    "body": body
                }
            })
            response.status_code = 200
            return response

    @app.route("/tost/<access_token>", methods=["GET"])
    @auth.login_required
    def tost_by_access_token(access_token):
        email, auth_token = helpers.get_header_auth(request)
        user = User.query.filter_by(_user_auth_token=auth_token).first()

        if request.method == "GET":
            ppgn = Propagation.query.filter_by(_ppgn_token=access_token)\
                                    .filter_by(_ppgn_disabled=False)\
                                    .filter_by(_ppgn_ancestor_disabled=False)\
                                    .first()

            # case 1: propagation invalid
            if not ppgn:
                response = jsonify({
                    "code": 40,
                    "msg": "tost not found"
                })
                response.status_code = 404
                return response

            user_ppgn = Propagation.query.filter_by(ppgn_user_id=user.user_id)\
                                         .filter_by(ppgn_tost_id=ppgn.ppgn_tost_id)\
                                         .filter_by(_ppgn_disabled=False)\
                                         .filter_by(_ppgn_ancestor_disabled=False)\
                                         .first()

            # case 2: user visits resource for the first time
            if not user_ppgn:
                new_ppgn = Propagation(ppgn.ppgn_tost_id,
                                       user.user_id,
                                       ppgn.ppgn_id,
                                       ppgn._ppgn_rank+1)
                new_ppgn.save()
                return redirect(url_for("tost_by_access_token",
                                        access_token=new_ppgn._ppgn_token))

            # case 3: user is creator of tost that propagation points to
            if ppgn.ppgn_id == user_ppgn.ppgn_id:
                tost = Tost.query.filter_by(tost_id=ppgn.ppgn_tost_id).first()

                response = jsonify({
                    "tost": {
                        "access-token": access_token,
                        "creator-id": tost.tost_creator_user_id,
                        "created-at": tost.tost_create_timestamp,
                        "updator-id": tost._tost_updator_user_id,
                        "updated_at": tost._tost_update_timestamp,
                        "body": tost._tost_body
                    }
                })
                response.status_code = 200
                return response

            # case 4: user propagation is of higher priority than propagation in url
            if user_ppgn._ppgn_rank <= ppgn._ppgn_rank + 1:
                return redirect(url_for("tost_by_access_token",
                                        access_token=user_ppgn._ppgn_token))

            # case 5: user propagation is of lower rank than propagation in url
            if user_ppgn._ppgn_rank > ppgn._ppgn_rank + 1:
                user_ppgn._ppgn_parent_id = ppgn.ppgn_id
                user_ppgn._ppgn_rank = ppgn._ppgn_rank + 1
                user_ppgn.save()

                tost = Tost.query.filter_by(tost_id=user_ppgn.ppgn_tost_id).first()

                response = jsonify({
                    "tost": {
                        "access-token": access_token,
                        "creator-id": tost.tost_creator_user_id,
                        "created-at": tost.tost_create_timestamp,
                        "updator-id": tost._tost_updator_user_id,
                        "updated_at": tost._tost_update_timestamp,
                        "body": tost._tost_body
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
