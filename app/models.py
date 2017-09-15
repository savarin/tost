from app import db
from helpers import create_token


class User(db.Model):
    user_id = db.Column(db.String(4), primary_key=True)
    _user_email = db.Column(db.String(8), unique=True)
    _user_auth_token = db.Column(db.String(8), unique=True)

    def __init__(self, email):
        self.user_id = create_token(4)
        self._user_email = email
        self._user_auth_token = create_token(8)

    def save(self):
        db.session.add(self)
        db.session.commit()

    def __repr__(self):
        return "<email: {}>".format(self._user_email)


class Tost(db.Model):
    tost_id = db.Column(db.String(4), primary_key=True)
    _tost_body = db.Column(db.String(16))
    tost_creator_user_id = db.Column(db.String(8))
    tost_create_timestamp = db.Column(db.DateTime)

    def __init__(self, body, user_id):
        self.tost_id = create_token(4)
        self._tost_body = body
        self.tost_creator_user_id = user_id
        self.tost_create_timestamp = db.func.current_timestamp()

    def save(self):
        db.session.add(self)
        db.session.commit()


class Propagation(db.Model):
    ppgn_id = db.Column(db.String(4), primary_key=True)
    ppgn_tost_id = db.Column(db.String(4), unique=True)
    ppgn_user_id = db.Column(db.String(4))
    _ppgn_token = db.Column(db.String(8), unique=True)
    _ppgn_parent_id = db.Column(db.String(4))

    def __init__(self, tost_id, user_id):
        self.ppgn_id = create_token(4)
        self.ppgn_tost_id = tost_id
        self.ppgn_user_id = user_id
        self._ppgn_token = create_token(8)
        self._ppgn_parent_id = None

    def save(self):
        db.session.add(self)
        db.session.commit()
