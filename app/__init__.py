from flask_api import FlaskAPI
from flask_httpauth import HTTPBasicAuth
from flask_sqlalchemy import SQLAlchemy
from flask import request, redirect, url_for

from config import app_config
from helpers import get_header_auth, get_header_encoding, compose_response

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
        encoding = get_header_encoding(request)
        email = str(request.data.get("email", ""))
        user = User.query.filter_by(_user_email=email).first()

        if user:
            response = compose_response({
                "code": 10,
                "msg": "already signed up with that email"
            }, encoding=encoding)
            response.status_code = 400
            return response

        user = User(email=email)
        user.save()
        response = compose_response({
            "user": {
                "id": str(user._user_auth_token),
                "email": str(user._user_email)
            }
        }, encoding=encoding)
        response.status_code = 200
        return response

    @app.route("/login", methods=["POST"])
    def login():
        encoding = get_header_encoding(request)
        auth_token = str(request.data.get("auth_token", ""))
        user = User.query.filter_by(_user_auth_token=auth_token).first()

        if not (user and user._user_auth_token == auth_token):
            response = compose_response({
                "code": 20,
                "msg": "invalid token"
            }, encoding=encoding)
            response.status_code = 400
            return response

        response = compose_response({
            "user": {
                "id": str(user._user_auth_token),
                "email": str(user._user_email)
            }
        }, encoding=encoding)
        response.status_code = 200
        return response

    def filter_ppgn_by_user_id(user_id):
        return Propagation.query.filter_by(ppgn_user_id=user_id)\
                                .filter_by(_ppgn_disabled=False)\
                                .filter_by(_ppgn_ancestor_disabled=False)\
                                .all()

    def create_tost_summary(ppgn_token, tost, body, encoding=None):
        return compose_response({
            "tost": {
                "access-token": str(ppgn_token),
                "creator-id": str(tost.tost_creator_user_id),
                "created-at": str(tost.tost_create_timestamp),
                "updator-id": str(tost._tost_updator_user_id),
                "updated-at": str(tost._tost_update_timestamp),
                "body": str(body)
            }
        }, encoding=encoding)

    @app.route("/tost", methods=["GET", "POST"])
    @auth.login_required
    def tost():
        encoding = get_header_encoding(request)
        email, auth_token = get_header_auth(request)
        user = User.query.filter_by(_user_auth_token=auth_token).first()

        if request.method == "GET":
            ppgns = filter_ppgn_by_user_id(user.user_id)
            print len(ppgns)

            result = {}
            for ppgn in ppgns:
                tost = Tost.query.filter_by(tost_id=ppgn.ppgn_tost_id).first()
                result[str(ppgn._ppgn_token)] = str(tost._tost_body[:32])

            response = compose_response(result, encoding=encoding)
            response.status_code = 200
            return response

        elif request.method == "POST":
            body = str(request.data.get("body", ""))

            if not body:
                response = compose_response({
                    "code": 30,
                    "msg": "invalid",
                    "field": {
                        "tost": {
                            "body": "must not be blank"
                        }
                    }
                }, encoding=encoding)
                response.status_code = 400
                return response

            tost = Tost(body, user.user_id)
            tost.save()

            ppgn = Propagation(tost.tost_id, user.user_id)
            ppgn.save()

            response = create_tost_summary(ppgn._ppgn_token, tost, body, encoding)
            response.status_code = 200
            return response

    def get_tost_by_token(ppgn_token):
        ppgn = Propagation.query.filter_by(_ppgn_token=ppgn_token).first()
        return Tost.query.filter_by(tost_id=ppgn.ppgn_tost_id).first()

    def get_ppgn_by_token(ppgn_token):
        return Propagation.query.filter_by(_ppgn_token=ppgn_token)\
                                .filter_by(_ppgn_disabled=False)\
                                .filter_by(_ppgn_ancestor_disabled=False)\
                                .first()

    def get_ppgn_by_user_tost(user_id, tost_id):
        return Propagation.query.filter_by(ppgn_user_id=user_id)\
                                .filter_by(ppgn_tost_id=tost_id)\
                                .filter_by(_ppgn_disabled=False)\
                                .filter_by(_ppgn_ancestor_disabled=False)\
                                .first()

    def review_access_token(access_token, user_id):
        ppgn = get_ppgn_by_token(access_token)

        # case 1: propagation invalid
        if not ppgn:
            return 1, None

        user_ppgn = get_ppgn_by_user_tost(user_id, ppgn.ppgn_tost_id)

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

        # case 4: user propagation is of lower priority than propagation in URL
        if user_ppgn._ppgn_rank > ppgn._ppgn_rank + 1:
            user_ppgn._ppgn_parent_id = ppgn.ppgn_id
            user_ppgn._ppgn_rank = ppgn._ppgn_rank + 1
            user_ppgn.save()

            return 4, user_ppgn._ppgn_token

        # case 5: user propagation is of higher priority than propagation in URL
        if user_ppgn._ppgn_rank <= ppgn._ppgn_rank + 1:
            return 5, user_ppgn._ppgn_token

    @app.route("/tost/<access_token>", methods=["GET", "PUT"])
    @auth.login_required
    def view_tost(access_token):
        encoding = get_header_encoding(request)
        email, auth_token = get_header_auth(request)
        user = User.query.filter_by(_user_auth_token=auth_token).first()
        case, ppgn_token = review_access_token(access_token, user.user_id)

        if request.method == "GET":
            # case 1: propagation invalid
            if case == 1:
                response = compose_response({
                    "code": 40,
                    "msg": "tost not found"
                }, encoding=encoding)
                response.status_code = 404
                return response

            # case 2: user visits resource for the first time
            # case 4: user propagation is of lower priority than propagation in URL
            # case 5: user propagation is of higher priority than propagation in URL
            if case in [2, 4, 5]:
                return redirect(url_for("view_tost", access_token=ppgn_token))

            # case 3: user is creator of tost that propagation points to
            tost = get_tost_by_token(ppgn_token)

            response = create_tost_summary(ppgn_token, tost, tost._tost_body)
            response.status_code = 200
            return response

        if request.method == "PUT":
            # case 1: propagation invalid
            if case == 1:
                response = compose_response({
                    "code": 40,
                    "msg": "tost not found"
                }, encoding=encoding)
                response.status_code = 404
                return response

            # case 2: user visits resource for the first time
            # case 4: user propagation is of lower priority than propagation in URL
            # case 5: user propagation is of higher priority than propagation in URL
            if case in [2, 4, 5]:
                response = compose_response({
                    "code": 50,
                    "msg": "please use refreshed access token",
                    "access-token": str(ppgn_token)
                }, encoding=encoding)
                response.status_code = 302
                return response

            # case 3: user is creator of tost that propagation points to
            tost = get_tost_by_token(ppgn_token)
            tost._tost_body = str(request.data.get("body", ""))
            tost.save()

            response = create_tost_summary(ppgn_token, tost, tost._tost_body)
            response.status_code = 200
            return response

    def filter_ppgn_by_parent_id(ppgn_id):
        return Propagation.query.filter_by(_ppgn_parent_id=ppgn_id)\
                                .filter_by(_ppgn_disabled=False)\
                                .filter_by(_ppgn_ancestor_disabled=False)\
                                .all()

    @app.route("/tost/<access_token>/propagation", methods=["GET"])
    @auth.login_required
    def propagation(access_token):
        encoding = get_header_encoding(request)
        ppgn = get_ppgn_by_token(access_token)
        result = {}

        if ppgn:
            # BFS to find all child propagations
            queue = [(ppgn, access_token)]

            while queue:
                ppgn, ppgn_token = queue.pop(0)
                for child in filter_ppgn_by_parent_id(ppgn.ppgn_id):
                    queue.append((child, child._ppgn_token))

                    user = User.query.filter_by(user_id=child.ppgn_user_id).first()
                    result[user._user_email] = {
                        "access-token": str(child._ppgn_token),
                        "parent-access-token": str(ppgn_token)
                    }

        response = compose_response({
            "propagations": result
        }, encoding=encoding)
        response.status_code = 200
        return response

    @app.route("/tost/<access_token>/propagation/upgrade", methods=["POST"])
    @auth.login_required
    def upgrade_propagation(access_token):
        encoding = get_header_encoding(request)
        src_access_token = str(request.data.get("src-access-token", ""))
        src_ppgn = get_ppgn_by_token(src_access_token)
        ppgn = get_ppgn_by_token(access_token)

        # return 400 if user propagation not descendant of propagation in URL
        if not (src_ppgn and ppgn and
                src_ppgn.ppgn_tost_id == ppgn.ppgn_tost_id and
                src_ppgn._ppgn_rank >= ppgn._ppgn_rank + 1):
            response = compose_response({
                "code": 60,
                "msg": "destination not ancestor"
            }, encoding=encoding)
            response.status_code = 400
            return response

        # upgrade if user propagation not direct descendant to propagation in URL
        if src_ppgn._ppgn_rank > ppgn._ppgn_rank + 1:
            src_ppgn._ppgn_parent_id = ppgn.ppgn_id
            src_ppgn._ppgn_rank = ppgn._ppgn_rank + 1

            # BFS to find all child propagations, then upgrade ranks
            queue = [(src_ppgn, ppgn._ppgn_rank + 1)]

            while queue:
                ppgn, rank = queue.pop(0)
                for child in filter_ppgn_by_parent_id(ppgn.ppgn_id):
                    queue.append((child, rank + 1))
                    child._ppgn_rank = rank + 1

            src_ppgn.save()

        response = compose_response({
            "access-token": str(src_access_token),
            "parent-access-token": str(access_token)
        }, encoding=encoding)
        response.status_code = 200
        return response

    @app.route("/tost/<access_token>/propagation/disable", methods=["POST"])
    @auth.login_required
    def disable_propagation(access_token):
        encoding = get_header_encoding(request)
        src_access_token = str(request.data.get("src-access-token", ""))
        src_ppgn = get_ppgn_by_token(src_access_token)
        ppgn = get_ppgn_by_token(access_token)

        # return 400 if user propagation not descendant of propagation in URL
        if not (src_ppgn and ppgn and
                src_ppgn.ppgn_tost_id == ppgn.ppgn_tost_id and
                src_ppgn._ppgn_rank >= ppgn._ppgn_rank + 1):
            response = compose_response({
                "code": 70,
                "msg": "target not descendant of " + str(access_token)
            }, encoding=encoding)
            response.status_code = 400
            return response

        src_ppgn._ppgn_disabled = True

        # BFS to find all child propagations, then toggle ancestor flag
        queue = [src_ppgn]

        while queue:
            ppgn = queue.pop(0)
            for child in filter_ppgn_by_parent_id(ppgn.ppgn_id):
                queue.append(child)
                child._ppgn_ancestor_disabled = True

        src_ppgn.save()

        response = compose_response({
            "access-token": str(src_access_token),
            "parent-access-token": str(access_token)
        }, encoding=encoding)
        response.status_code = 200
        return response

    @auth.verify_password
    def verify_password(email, auth_token):
        user = User.query.filter_by(_user_email=email).first()
        if not (user and user._user_auth_token == auth_token):
            return False
        return True

    return app
