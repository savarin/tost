from flask import request, jsonify
from base64 import b64encode, b64decode
from uuid import uuid4
from werkzeug.datastructures import Headers


def create_token(length):
    return uuid4().hex[:length]


def set_headers(email, auth_token, encoding):
    headers = Headers()

    if email and auth_token:
        auth = b64encode(email + ":" + auth_token)
        headers.add("Authorization", "Basic " + auth)

    if encoding:
        headers.add("Accept", encoding)

    return headers


def get_header_auth(request):
    auth = request.headers.environ.get("HTTP_AUTHORIZATION", "").split(" ")[-1]
    return b64decode(auth).split(":")


def get_header_encoding(request):
    return request.headers.environ.get("HTTP_ACCEPT", None)


def encode_bencode(element):
    result = ""
    if element is None:
        return result
    elif type(element) == int:
        return "i" + str(element) + "e"
    elif type(element) == str:
        return str(len(element)) + ":" + str(element)
    elif type(element) == list:
        return "l" + "".join([encode_bencode(item) for item in element]) + "e"
    elif type(element) == dict:
        collection = []
        for pairs in sorted(element.iteritems(), key=lambda (x, y): x):
            for item in pairs:
                collection.append(item)
        return "d" + "".join([encode_bencode(item) for item in collection]) + "e"
    else:
        raise TypeError("Neither int, string, list or dictionary.")


def compose_response(content, encoding):
    if encoding == "bencode":
        response = jsonify({
            "content": encode_bencode(content)
        })
    else:
        response = jsonify(content)

    return response
