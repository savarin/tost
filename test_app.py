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

    def sign_up(self, email):
        response = self.client().post("/signup", data=email)
        auth_token = ast.literal_eval(response.data)["user"]["id"]
        headers = set_header_auth(email["email"], auth_token)
        return auth_token, headers

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
        auth_token, headers = self.sign_up(self.email_0)
        body = {"body": "foo"}

        response = self.client().post("/tost", headers=headers, data=body)
        self.assertEqual(response.status_code, 200)
        self.assertIn("foo", str(response.data))

        response = self.client().post("/tost", headers=headers)
        self.assertEqual(response.status_code, 400)
        self.assertIn("invalid", str(response.data))

        response = self.client().post("/tost")
        self.assertEqual(response.status_code, 401)

    def test_tost_list(self):
        auth_token, headers = self.sign_up(self.email_0)
        body = {"body": "foo"}

        response = self.client().post("/tost", headers=headers, data=body)
        response = self.client().get("/tost", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn("foo", str(response.data))

    def test_tost_view(self):
        auth_token_0, headers_0 = self.sign_up(self.email_0)
        auth_token_1, headers_1 = self.sign_up(self.email_1)
        auth_token_2, headers_2 = self.sign_up(self.email_2)
        auth_token_3, headers_3 = self.sign_up(self.email_3)
        body = {"body": "foo"}

        # case 3: user is creator of tost that propagation points to
        response = self.client().post("/tost", headers=headers_0, data=body)
        ppgn_token_0 = ast.literal_eval(response.data)["tost"]["access-token"]

        response = self.client().get("/tost/" + ppgn_token_0, headers=headers_0)
        self.assertEqual(response.status_code, 200)
        self.assertIn("foo", str(response.data))

        # case 2: user visits resource for the first time
        response = self.client().get("/tost/" + ppgn_token_0, headers=headers_1)
        ppgn_token_1 = re.search("\/tost\/[0-9a-f]{8}", response.data)\
                         .group(0).split("/")[-1]

        response = self.client().get("/tost/" + ppgn_token_1, headers=headers_1)
        self.assertEqual(response.status_code, 200)
        self.assertIn("foo", str(response.data))

        # case 4: user propagation is of lower priority than propagation in url
        response = self.client().get("/tost/" + ppgn_token_1, headers=headers_2)
        response = self.client().get("/tost/" + ppgn_token_0, headers=headers_2)
        ppgn_token_2 = re.search("\/tost\/[0-9a-f]{8}", response.data)\
                         .group(0).split("/")[-1]

        response = self.client().get("/tost/" + ppgn_token_2, headers=headers_2)
        self.assertEqual(response.status_code, 200)
        self.assertIn("foo", str(response.data))

        # case 5: user propagation is of higher priority than propagation in url
        response = self.client().get("/tost/" + ppgn_token_0, headers=headers_3)
        response = self.client().get("/tost/" + ppgn_token_1, headers=headers_3)
        ppgn_token_3 = re.search("\/tost\/[0-9a-f]{8}", response.data)\
                         .group(0).split("/")[-1]

        response = self.client().get("/tost/" + ppgn_token_3, headers=headers_3)
        self.assertEqual(response.status_code, 200)
        self.assertIn("foo", str(response.data))

        # case 1: propagation invalid
        response = self.client().get("/tost/" + "foo", headers=headers_0)
        self.assertEqual(response.status_code, 404)
        self.assertIn("tost not found", str(response.data))

    def test_tost_edit(self):
        auth_token_0, headers_0 = self.sign_up(self.email_0)
        body = {"body": "foo"}

        # case 3: user is creator of tost that propagation points to
        response = self.client().post("/tost", headers=headers_0, data=body)
        ppgn_token_0 = ast.literal_eval(response.data)["tost"]["access-token"]
        body = {"body": "bar"}

        response = self.client().put("/tost/" + ppgn_token_0, headers=headers_0, data=body)
        self.assertEqual(response.status_code, 200)
        self.assertIn("bar", str(response.data))

    def test_ppgn_view(self):
        auth_token_0, headers_0 = self.sign_up(self.email_0)
        auth_token_1, headers_1 = self.sign_up(self.email_1)
        body = {"body": "foo"}

        response = self.client().post("/tost", headers=headers_0, data=body)
        ppgn_token_0 = ast.literal_eval(response.data)["tost"]["access-token"]

        response = self.client().get("/tost/" + ppgn_token_0, headers=headers_1)
        response = self.client().get("/tost/" + ppgn_token_0 + "/propagation",
                                     headers=headers_0)
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.email_1["email"], str(response.data))

    def test_ppgn_upgrade(self):
        auth_token_0, headers_0 = self.sign_up(self.email_0)
        auth_token_1, headers_1 = self.sign_up(self.email_1)
        auth_token_2, headers_2 = self.sign_up(self.email_2)
        body = {"body": "foo"}

        response = self.client().post("/tost", headers=headers_0, data=body)
        ppgn_token_0 = ast.literal_eval(response.data)["tost"]["access-token"]

        response = self.client().get("/tost/" + ppgn_token_0, headers=headers_1)
        ppgn_token_1 = re.search("\/tost\/[0-9a-f]{8}", response.data)\
                         .group(0).split("/")[-1]

        response = self.client().get("/tost/" + ppgn_token_1, headers=headers_2)
        ppgn_token_2 = re.search("\/tost\/[0-9a-f]{8}", response.data)\
                         .group(0).split("/")[-1]
        data = {"src-access-token": ppgn_token_2}

        response = self.client().post("/tost/" + ppgn_token_0 +
                                      "/propagation/upgrade",
                                      headers=headers_0, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertIn(ppgn_token_2, str(response.data))

        response = self.client().post("/tost/" + ppgn_token_1 +
                                      "/propagation/upgrade",
                                      headers=headers_1, data=data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("destination not ancestor", str(response.data))

    def test_ppgn_disable(self):
        auth_token_0, headers_0 = self.sign_up(self.email_0)
        auth_token_1, headers_1 = self.sign_up(self.email_1)
        body = {"body": "foo"}

        response = self.client().post("/tost", headers=headers_0, data=body)
        ppgn_token_0 = ast.literal_eval(response.data)["tost"]["access-token"]

        response = self.client().get("/tost/" + ppgn_token_0, headers=headers_1)
        ppgn_token_1 = re.search("\/tost\/[0-9a-f]{8}", response.data)\
                         .group(0).split("/")[-1]
        data = {"src-access-token": ppgn_token_1}

        response = self.client().post("/tost/" + ppgn_token_0 +
                                      "/propagation/disable",
                                      headers=headers_0, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertIn(ppgn_token_1, str(response.data))

        response = self.client().post("/tost/" + ppgn_token_1 +
                                      "/propagation/disable",
                                      headers=headers_1, data=data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("target not descendant of " + ppgn_token_1, str(response.data))

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

if __name__ == "__main__":
    unittest.main()
