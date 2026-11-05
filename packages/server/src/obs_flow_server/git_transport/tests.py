import base64
import hashlib
from unittest.mock import patch
from django.test import TestCase, Client
from django.conf import settings
from accounts.models import User, Token
from core.models import Org, Project, Package


def _make_basic_auth(username: str, password: str) -> dict[str, str]:
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("utf-8")
    return {"HTTP_AUTHORIZATION": f"Basic {token}"}


class GitTransportAuthTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="gituser",
            password="secretpassword",
            is_local_account=True,
        )
        self.org = Org.objects.create(name="testorg")
        self.project = Project.objects.create(
            name="testproject",
            org=self.org,
            branch_name="main",
            workflow_type=Project.WorkflowType.DIRECT,
        )
        self.package = Package.objects.create(
            project=self.project,
            name="testpkg",
        )
        self.client = Client()

    def test_unauthenticated_request_returns_401(self):
        res = self.client.get("/package/testproject/testpkg.git/info/refs?service=git-upload-pack")
        self.assertEqual(res.status_code, 401)
        self.assertIn("WWW-Authenticate", res.headers)
        self.assertIn('Basic realm="OBS Flow Git"', res.headers["WWW-Authenticate"])

    def test_invalid_credentials_returns_401(self):
        auth = _make_basic_auth("gituser", "wrongpassword")
        res = self.client.get("/package/testproject/testpkg.git/info/refs?service=git-upload-pack", **auth)
        self.assertEqual(res.status_code, 401)

    def test_valid_user_password_authenticates(self):
        auth = _make_basic_auth("gituser", "secretpassword")
        res = self.client.get("/package/testproject/testpkg.git/info/refs?service=git-upload-pack", **auth)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers["Content-Type"], "application/x-git-upload-pack-advertisement")
        self.assertTrue(res.content.startswith(b"001e# service=git-upload-pack\n0000"))

    def test_token_in_password_field_authenticates(self):
        raw_token = "flow-sampletoken1234567890abcdef"
        tok_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        Token.objects.create(user=self.user, token_hash=tok_hash, last_eight="cdef")

        auth = _make_basic_auth("gituser", raw_token)
        res = self.client.get("/package/testproject/testpkg.git/info/refs?service=git-upload-pack", **auth)
        self.assertEqual(res.status_code, 200)

    def test_token_in_username_field_authenticates(self):
        raw_token = "flow-sampletoken1234567890abcdef"
        tok_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        Token.objects.create(user=self.user, token_hash=tok_hash, last_eight="cdef")

        auth = _make_basic_auth(raw_token, "")
        res = self.client.get("/package/testproject/testpkg.git/info/refs?service=git-upload-pack", **auth)
        self.assertEqual(res.status_code, 200)


class GitTransportHttpProtocolTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="gituser",
            password="secretpassword",
            is_local_account=True,
        )
        self.org = Org.objects.create(name="testorg")
        self.project = Project.objects.create(
            name="testproject",
            org=self.org,
            branch_name="main",
            workflow_type=Project.WorkflowType.DIRECT,
        )
        self.package = Package.objects.create(
            project=self.project,
            name="testpkg",
        )
        self.auth = _make_basic_auth("gituser", "secretpassword")
        self.client = Client()

    def test_missing_or_invalid_service_returns_400(self):
        res = self.client.get("/package/testproject/testpkg.git/info/refs", **self.auth)
        self.assertEqual(res.status_code, 400)

        res = self.client.get("/package/testproject/testpkg.git/info/refs?service=invalid-service", **self.auth)
        self.assertEqual(res.status_code, 400)

    def test_receive_pack_info_refs_advertisement(self):
        res = self.client.get("/package/testproject/testpkg.git/info/refs?service=git-receive-pack", **self.auth)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers["Content-Type"], "application/x-git-receive-pack-advertisement")
        self.assertTrue(res.content.startswith(b"001f# service=git-receive-pack\n0000"))

    def test_project_level_info_refs_advertisement(self):
        res = self.client.get("/project/testproject.git/info/refs?service=git-upload-pack", **self.auth)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers["Content-Type"], "application/x-git-upload-pack-advertisement")
        self.assertTrue(res.content.startswith(b"001e# service=git-upload-pack\n0000"))

    def test_urls_without_git_suffix_work(self):
        res = self.client.get("/package/testproject/testpkg/info/refs?service=git-upload-pack", **self.auth)
        self.assertEqual(res.status_code, 200)

        res = self.client.get("/project/testproject/info/refs?service=git-upload-pack", **self.auth)
        self.assertEqual(res.status_code, 200)

    def test_nonexistent_project_returns_404(self):
        res = self.client.get("/package/nonexistent/testpkg.git/info/refs?service=git-upload-pack", **self.auth)
        self.assertEqual(res.status_code, 404)

        res = self.client.get("/project/nonexistent.git/info/refs?service=git-upload-pack", **self.auth)
        self.assertEqual(res.status_code, 404)

    def test_nonexistent_package_returns_404(self):
        res = self.client.get("/package/testproject/nonexistent.git/info/refs?service=git-upload-pack", **self.auth)
        self.assertEqual(res.status_code, 404)

    def test_upload_pack_handler_invocation(self):
        res = self.client.post(
            "/package/testproject/testpkg.git/git-upload-pack",
            data=b"0000",
            content_type="application/x-git-upload-pack-request",
            **self.auth,
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers["Content-Type"], "application/x-git-upload-pack-result")
