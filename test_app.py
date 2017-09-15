from app import create_app, db
from helpers import set_header_auth
import ast
import base64
import json
import os
import unittest


class TestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app(config_name="testing")
        self.client = self.app.test_client
        self.email = {"email": "alice@example.com"}
        self.auth_token = {}

    def test_user_signup(self):
        response = self.client().post("/signup", data=self.email)
        self.assertEqual(response.status_code, 200)
        self.assertIn("alice@example.com", str(response.data))

        response = self.client().post("/signup", data=self.email)
        self.assertEqual(response.status_code, 400)
        self.assertIn("already signed up with that email", str(response.data))

    def test_user_login(self):
        response = self.client().post("/signup", data=self.email)
        auth_token = ast.literal_eval(response.data)["user"]["id"]
        self.auth_token = {"auth_token": auth_token}

        response = self.client().post("/auth", data=self.auth_token)
        self.assertEqual(response.status_code, 200)
        self.assertIn("alice@example.com", str(response.data))

        response = self.client().post("/auth", data="")
        self.assertEqual(response.status_code, 400)
        self.assertIn("invalid token", str(response.data))

    def test_tost_create(self):
        response = self.client().post("/signup", data=self.email)
        auth_token = ast.literal_eval(response.data)["user"]["id"]
        headers = set_header_auth(self.email["email"], auth_token)
        body = {"body": "foo"}

        response = self.client().post("/tost", headers=headers, data=body)
        self.assertEqual(response.status_code, 200)
        self.assertIn("foo", str(response.data))

        response = self.client().post("/tost")
        self.assertEqual(response.status_code, 401)

        response = self.client().get("/tost", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn("foo", str(response.data))

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()


if __name__ == "__main__":
    unittest.main()
