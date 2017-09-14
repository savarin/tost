from app import create_app, db
import json
import os
import unittest


class TestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app(config_name="testing")
        self.client = self.app.test_client
        self.email = {"email": "alice@example.com"}

    def test_user_signup(self):
        response = self.client().post("/signup", data=self.email)
        self.assertEqual(response.status_code, 200)
        self.assertIn("alice@example.com", str(response.data))

        response = self.client().post("/signup", data=self.email)
        self.assertEqual(response.status_code, 400)
        self.assertIn("already signed up with that email", str(response.data))

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()


if __name__ == "__main__":
    unittest.main()
