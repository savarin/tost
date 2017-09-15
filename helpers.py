from base64 import b64encode, b64decode
from uuid import uuid4
from werkzeug.datastructures import Headers


def create_token(length):
    return uuid4().hex[:length]


def set_header_auth(email, auth_token):
    auth = b64encode(email + ":" + auth_token)
    headers = Headers()
    headers.add('Authorization', "Basic " + auth)
    return headers


def get_header_auth(request):
    auth = request.headers.environ.get("HTTP_AUTHORIZATION", "").split(" ")[-1]
    return b64decode(auth).split(":")
