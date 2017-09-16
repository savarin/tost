from app import create_app, db
from helpers import set_header_auth
import ast
import re
import unittest


class TestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app(config_name="testing")
        self.client = self.app.test_client
        self.email_0 = {"email": "alice@example.com"}
        self.email_1 = {"email": "bob@example.com"}
        self.email_2 = {"email": "carol@example.com"}
        self.email_3 = {"email": "david@example.com"}
        self.auth_token_0 = {}
        self.auth_token_1 = {}
        self.auth_token_2 = {}
        self.auth_token_3 = {}

    def test_user_signup(self):
        response = self.client().post("/signup", data=self.email_0)
        self.assertEqual(response.status_code, 200)
        self.assertIn("alice@example.com", str(response.data))

        response = self.client().post("/signup", data=self.email_0)
        self.assertEqual(response.status_code, 400)
        self.assertIn("already signed up with that email", str(response.data))

    def test_user_login(self):
        response = self.client().post("/signup", data=self.email_0)
        auth_token = ast.literal_eval(response.data)["user"]["id"]
        self.auth_token = {"auth_token": auth_token}

        response = self.client().post("/auth", data=self.auth_token)
        self.assertEqual(response.status_code, 200)
        self.assertIn("alice@example.com", str(response.data))

        response = self.client().post("/auth", data="")
        self.assertEqual(response.status_code, 400)
        self.assertIn("invalid token", str(response.data))

    def test_tost_create(self):
        response = self.client().post("/signup", data=self.email_0)
        auth_token = ast.literal_eval(response.data)["user"]["id"]
        headers = set_header_auth(self.email_0["email"], auth_token)
        body = {"body": "foo"}

        response = self.client().post("/tost", headers=headers, data=body)
        self.assertEqual(response.status_code, 200)
        self.assertIn("foo", str(response.data))

        response = self.client().post("/tost", headers=headers)
        self.assertEqual(response.status_code, 400)
        self.assertIn("invalid", str(response.data))

        response = self.client().post("/tost")
        self.assertEqual(response.status_code, 401)

        response = self.client().get("/tost", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn("foo", str(response.data))

    def test_tost_view(self):
        response = self.client().post("/signup", data=self.email_0)
        auth_token_0 = ast.literal_eval(response.data)["user"]["id"]
        headers_0 = set_header_auth(self.email_0["email"], auth_token_0)
        body = {"body": "foo"}

        # case 3: user is creator of tost that propagation points to
        response = self.client().post("/tost", headers=headers_0, data=body)
        ppgn_token_0 = ast.literal_eval(response.data)["tost"]["access-token"]

        response = self.client().get("/tost/" + ppgn_token_0, headers=headers_0)
        self.assertEqual(response.status_code, 200)
        self.assertIn("foo", str(response.data))

        # case 2: user visits resource for the first time
        response = self.client().post("/signup", data=self.email_1)
        auth_token_1 = ast.literal_eval(response.data)["user"]["id"]
        headers_1 = set_header_auth(self.email_1["email"], auth_token_1)

        response = self.client().get("/tost/" + ppgn_token_0, headers=headers_1)
        ppgn_token_1 = re.search("\/tost\/[0-9a-f]*", response.data).group(0).split("/")[-1]

        response = self.client().get("/tost/" + ppgn_token_1, headers=headers_1)
        self.assertEqual(response.status_code, 200)
        self.assertIn("foo", str(response.data))

        # case 4: user propagation is of higher priority than propagation in url
        response = self.client().post("/signup", data=self.email_2)
        auth_token_2 = ast.literal_eval(response.data)["user"]["id"]
        headers_2 = set_header_auth(self.email_2["email"], auth_token_2)

        response = self.client().get("/tost/" + ppgn_token_0, headers=headers_2)
        ppgn_token_2 = re.search("\/tost\/[0-9a-f]*", response.data).group(0).split("/")[-1]

        response = self.client().get("/tost/" + ppgn_token_2, headers=headers_2)
        self.assertEqual(response.status_code, 200)
        self.assertIn("foo", str(response.data))

        # case 5: user propagation is of lower rank than propagation in url
        response = self.client().post("/signup", data=self.email_3)
        auth_token_3 = ast.literal_eval(response.data)["user"]["id"]
        headers_3 = set_header_auth(self.email_3["email"], auth_token_3)

        response = self.client().get("/tost/" + ppgn_token_1, headers=headers_3)
        response = self.client().get("/tost/" + ppgn_token_0, headers=headers_3)
        self.assertEqual(response.status_code, 200)
        self.assertIn("foo", str(response.data))

        # case 1: propagation invalid
        response = self.client().get("/tost/" + "foo", headers=headers_0)
        self.assertEqual(response.status_code, 404)
        self.assertIn("tost not found", str(response.data))

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()


if __name__ == "__main__":
    unittest.main()
