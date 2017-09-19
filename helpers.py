from flask import request, jsonify
from base64 import b64encode, b64decode
from itertools import izip
from uuid import uuid4
from werkzeug.datastructures import Headers
import re


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

    elif isinstance(element, int):
        return "i" + str(element) + "e"

    elif isinstance(element, str):
        return str(len(element)) + ":" + str(element)

    elif isinstance(element, list):
        return "l" + "".join([encode_bencode(item) for item in element]) + "e"

    elif isinstance(element, dict):
        collection = []
        for pairs in sorted(element.iteritems(), key=lambda (x, y): x):
            for item in pairs:
                collection.append(item)
        return "d" + "".join([encode_bencode(item) for item in collection]) + "e"

    else:
        raise ValueError("Neither int, string, list or dictionary.")


def decode_bencode(string):

    def decode(string):
        digits = [str(item) for item in xrange(10)]

        if string == "":
            return None, ""

        elif string.startswith("i"):
            match = re.match("i(-?\d+)e", string)
            return int(match.group(1)), string[match.span()[1]:]

        elif any([string.startswith(item) for item in digits]):
            match = re.match("(\d+):", string)
            start = match.span()[1]
            end = start + int(match.group(1))
            return string[start:end], string[end:]

        elif string.startswith("l") or string.startswith("d"):
            elements = []
            rest = string[1:]
            while not rest.startswith("e"):
                element, rest = decode(rest)
                elements.append(element)
            rest = rest[1:]
            if string.startswith("l"):
                return elements, rest
            else:
                return {k: v for k, v in izip(elements[::2], elements[1::2])}, rest

        else:
            raise ValueError("Malformed string.")

    return decode(string)[0]

def compose_response(content, encoding):
    if encoding == "bencode":
        response = jsonify({
            "content": encode_bencode(content)
        })
        response.content_type = encoding
    else:
        response = jsonify(content)

    return response
