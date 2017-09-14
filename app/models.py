from app import db
from uuid import uuid4


def create_token():
    return uuid4().hex


class User(db.Model):
    user_id = db.Column(db.String(32), primary_key=True)
    _user_email = db.Column(db.String(32), unique=True)
    _user_auth_token = db.Column(db.String(32), unique=True)

    def __init__(self, email):
        self.user_id = create_token()
        self._user_email = email
        self._user_auth_token = create_token()

    def save(self):
        db.session.add(self)
        db.session.commit()

    def __repr__(self):
        return "<email: {}>".format(self._user_email)
