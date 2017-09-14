from app import db
from uuid import uuid4


def create_token():
    return uuid4.hex()


class User(db.Model):
    user_id = db.Column(db.String(32), primary_key=True)

    def __init__(self):
        self.user_id = create_token()
