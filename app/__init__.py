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

    def create_tost_summary(access_token, tost, body):
        return jsonify({
            "tost": {
                "access-token": access_token,
                "creator-id": tost.tost_creator_user_id,
                "created-at": tost.tost_create_timestamp,
                "updator-id": tost._tost_updator_user_id,
                "updated-at": tost._tost_update_timestamp,
                "body": body
            }
        })

    def filter_ppgn_by_user_tost(user_id, tost_id):
        return Propagation.query.filter_by(ppgn_user_id=user_id)\
                                .filter_by(ppgn_tost_id=tost_id)\
                                .filter_by(_ppgn_disabled=False)\
                                .filter_by(_ppgn_ancestor_disabled=False)\
                                .first()

    @app.route("/tost", methods=["GET", "POST"])
    @auth.login_required
    def tost():
        email, auth_token = helpers.get_header_auth(request)
        user = User.query.filter_by(_user_auth_token=auth_token).first()

        if request.method == "GET":
            tosts = Tost.query.filter_by(tost_creator_user_id=user.user_id).all()

            result = {}
            for tost in tosts:
                ppgn = filter_ppgn_by_user_tost(user.user_id, tost.tost_id)
                result[ppgn._ppgn_token[:4]] = tost._tost_body[:32]

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

            response = create_tost_summary(ppgn._ppgn_token, tost, body)
            response.status_code = 200
            return response

    def filter_ppgn_by_token(access_token):
        return Propagation.query.filter_by(_ppgn_token=access_token)\
                                .filter_by(_ppgn_disabled=False)\
                                .filter_by(_ppgn_ancestor_disabled=False)\
                                .first()

    def review_access_token(access_token, user_id):
            ppgn = filter_ppgn_by_token(access_token)

            # case 1: propagation invalid
            if not ppgn:
                return 1, None

            user_ppgn = filter_ppgn_by_user_tost(user_id, ppgn.ppgn_tost_id)

            # case 2: user visits resource for the first time
            if not user_ppgn:
                new_ppgn = Propagation(ppgn.ppgn_tost_id,
                                       user_id,
                                       ppgn.ppgn_id,
                                       ppgn._ppgn_rank+1)
                new_ppgn.save()

                return 2, new_ppgn._ppgn_token

            # case 3: user is creator of tost that propagation points to
            if ppgn.ppgn_id == user_ppgn.ppgn_id:
                return 3, access_token

            # case 4: user propagation is of lower priority than propagation in url
            if user_ppgn._ppgn_rank > ppgn._ppgn_rank + 1:
                user_ppgn._ppgn_parent_id = ppgn.ppgn_id
                user_ppgn._ppgn_rank = ppgn._ppgn_rank + 1
                user_ppgn.save()

                return 4, user_ppgn._ppgn_token

            # case 5: user propagation is of higher priority than propagation in url
            if user_ppgn._ppgn_rank <= ppgn._ppgn_rank + 1:
                return 5, user_ppgn._ppgn_token

    @app.route("/tost/<access_token>", methods=["GET", "PUT"])
    @auth.login_required
    def view_tost(access_token):
        email, auth_token = helpers.get_header_auth(request)
        user = User.query.filter_by(_user_auth_token=auth_token).first()

        if request.method == "GET":
            case, access_token = review_access_token(access_token, user.user_id)

            # case 1: propagation invalid
            if case == 1:
                response = jsonify({
                    "code": 40,
                    "msg": "tost not found"
                })
                response.status_code = 404
                return response

            # case 2: user visits resource for the first time
            # case 4: user propagation is of lower priority than propagation in url
            # case 5: user propagation is of higher priority than propagation in url
            if case in [2, 4, 5]:
                return redirect(url_for("view_tost", access_token=access_token))

            # case 3: user is creator of tost that propagation points to
            ppgn = Propagation.query.filter_by(_ppgn_token=access_token).first()
            tost = Tost.query.filter_by(tost_id=ppgn.ppgn_tost_id).first()

            response = create_tost_summary(access_token, tost, tost._tost_body)
            response.status_code = 200
            return response

        if request.method == "PUT":
            case, access_token = review_access_token(access_token, user.user_id)

            # case 1: propagation invalid
            if case == 1:
                response = jsonify({
                    "code": 40,
                    "msg": "tost not found"
                })
                response.status_code = 404
                return response

            # case 2: user visits resource for the first time
            # case 4: user propagation is of lower priority than propagation in url
            # case 5: user propagation is of higher priority than propagation in url
            if case in [2, 4, 5]:
                response = jsonify({
                    "code": 50,
                    "msg": "please use refreshed access token",
                    "access-token": access_token
                })
                response.status_code = 302
                return response

            # case 3: user is creator of tost that propagation points to
            ppgn = Propagation.query.filter_by(_ppgn_token=access_token).first()
            tost = Tost.query.filter_by(tost_id=ppgn.ppgn_tost_id).first()
            tost._tost_body = str(request.data.get("body", ""))
            tost.save()
            response = create_tost_summary(access_token, tost, tost._tost_body)
            response.status_code = 200
            return response

    def get_ppgn_children(ppgn_id):
        return Propagation.query.filter_by(_ppgn_parent_id=ppgn_id)\
                                .filter_by(_ppgn_disabled=False)\
                                .filter_by(_ppgn_ancestor_disabled=False)\
                                .all()

    @app.route("/tost/<access_token>/propagation", methods=["GET"])
    @auth.login_required
    def propagation(access_token):
        ppgn = filter_ppgn_by_token(access_token)
        result = {}

        if ppgn:
            # BFS to find all child propagations
            queue = [(ppgn, access_token)]

            while queue:
                ppgn, access_token = queue.pop(0)
                for child in get_ppgn_children(ppgn.ppgn_id):
                    queue.append((child, child._ppgn_token))

                    user = User.query.filter_by(user_id=child.ppgn_user_id).first()
                    result[user._user_email] = {
                        "access-token": child._ppgn_token,
                        "parent-access-token": access_token
                    }

        response = jsonify({
            "propagations": result
        })
        response.status_code = 200
        return response

    @app.route("/tost/<access_token>/propagation/upgrade", methods=["POST"])
    @auth.login_required
    def upgrade_propagation(access_token):
        src_access_token = str(request.data.get("src-access-token", ""))
        src_ppgn = filter_ppgn_by_token(src_access_token)
        ppgn = filter_ppgn_by_token(access_token)

        if not (src_ppgn and ppgn and
                src_ppgn.ppgn_tost_id == ppgn.ppgn_tost_id and
                src_ppgn._ppgn_rank >= ppgn._ppgn_rank + 1):
            response = jsonify({
                "code": 60,
                "msg": "destination not ancestor"
            })
            response.status_code = 400
            return response

        if src_ppgn._ppgn_rank > ppgn._ppgn_rank + 1:
            src_ppgn._ppgn_parent_id = ppgn.ppgn_id
            src_ppgn._ppgn_rank = ppgn._ppgn_rank + 1

            # BFS to find all child propagations
            queue = [(src_ppgn, ppgn._ppgn_rank + 1)]

            while queue:
                ppgn, rank = queue.pop(0)
                for child in get_ppgn_children(ppgn.ppgn_id):
                    queue.append((child, rank + 1))
                    child._ppgn_rank = rank + 1

            src_ppgn.save()

        response = jsonify({
            "access-token": src_access_token,
            "parent-access-token": access_token
        })
        response.status_code = 200
        return response

    @app.route("/tost/<access_token>/propagation/disable", methods=["POST"])
    @auth.login_required
    def disable_propagation(access_token):
        src_access_token = str(request.data.get("src-access-token", ""))
        src_ppgn = filter_ppgn_by_token(src_access_token)
        ppgn = filter_ppgn_by_token(access_token)

        if not (src_ppgn and ppgn and
                src_ppgn.ppgn_tost_id == ppgn.ppgn_tost_id and
                src_ppgn._ppgn_rank >= ppgn._ppgn_rank + 1):
            response = jsonify({
                "code": 70,
                "msg": "target not descendant of " + access_token
            })
            response.status_code = 400
            return response

        src_ppgn._ppgn_disabled = True

        # BFS to find all child propagations
        queue = [src_ppgn]

        while queue:
            ppgn = queue.pop(0)
            for child in get_ppgn_children(ppgn.ppgn_id):
                queue.append(child)
                child._ppgn_ancestor_disabled = True

        src_ppgn.save()

        response = jsonify({
            "disabled": src_access_token
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
