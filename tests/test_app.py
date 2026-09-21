import os
import tempfile
import unittest

from app import create_app


class SocialAppTests(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        os.close(self.db_fd)
        self.app = create_app({"TESTING": True, "DATABASE": self.db_path})
        self.client = self.app.test_client()

    def tearDown(self):
        os.unlink(self.db_path)

    def test_homepage_redirects_to_login_when_not_logged_in(self):
        response = self.client.get("/", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_user_can_register_and_create_post(self):
        register_response = self.client.post(
            "/register",
            data={"username": "alice", "password": "123456"},
            follow_redirects=True,
        )
        self.assertEqual(register_response.status_code, 200)

        login_response = self.client.post(
            "/login",
            data={"username": "alice", "password": "123456"},
            follow_redirects=True,
        )
        self.assertEqual(login_response.status_code, 200)

        post_response = self.client.post(
            "/posts/create",
            data={"content": "Первый публичный пост"},
            follow_redirects=True,
        )
        self.assertEqual(post_response.status_code, 200)
        self.assertIn("Первый публичный пост", post_response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
