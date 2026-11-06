import base64
import hashlib
from pathlib import Path
from unittest.mock import patch
from django.test import TestCase, TransactionTestCase, LiveServerTestCase, Client
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

    def test_unauthenticated_push_returns_401(self):
        res = self.client.get("/package/testproject/testpkg.git/info/refs?service=git-receive-pack")
        self.assertEqual(res.status_code, 401)
        self.assertIn("WWW-Authenticate", res.headers)
        self.assertIn('Basic realm="OBS Flow Git"', res.headers["WWW-Authenticate"])

    def test_unauthenticated_clone_is_allowed(self):
        res = self.client.get("/package/testproject/testpkg.git/info/refs?service=git-upload-pack")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers["Content-Type"], "application/x-git-upload-pack-advertisement")
        self.assertTrue(res.content.startswith(b"001e# service=git-upload-pack\n0000"))

    def test_invalid_credentials_returns_401(self):
        auth = _make_basic_auth("gituser", "wrongpassword")
        res = self.client.get("/package/testproject/testpkg.git/info/refs?service=git-receive-pack", **auth)
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


class GitTransportPolicyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="devuser",
            password="secretpassword",
            is_local_account=True,
        )
        self.org = Org.objects.create(name="policyorg")
        self.direct_project = Project.objects.create(
            name="direct:project",
            org=self.org,
            branch_name="master",
            workflow_type=Project.WorkflowType.DIRECT,
        )
        self.staging_project = Project.objects.create(
            name="staging:project",
            org=self.org,
            branch_name="factory",
            workflow_type=Project.WorkflowType.STAGING,
        )
        self.package = Package.objects.create(
            project=self.direct_project,
            name="mypkg",
        )

    def test_direct_workflow_allows_project_branch_push(self):
        from .policy import evaluate_ref_update
        allowed, err = evaluate_ref_update(
            username="devuser",
            project_name="direct:project",
            package_name="mypkg",
            old_sha="0000000000000000000000000000000000000000",
            new_sha="1111111111111111111111111111111111111111",
            ref_name="refs/heads/master",
        )
        self.assertTrue(allowed)
        self.assertIsNone(err)

    def test_direct_workflow_rejects_branch_deletion(self):
        from .policy import evaluate_ref_update
        allowed, err = evaluate_ref_update(
            username="devuser",
            project_name="direct:project",
            package_name="mypkg",
            old_sha="1111111111111111111111111111111111111111",
            new_sha="0000000000000000000000000000000000000000",
            ref_name="refs/heads/master",
        )
        self.assertFalse(allowed)
        self.assertIn("Deletion of project branch 'master' is not allowed", err)

    def test_staging_workflow_rejects_direct_push_to_branch(self):
        from .policy import evaluate_ref_update
        allowed, err = evaluate_ref_update(
            username="devuser",
            project_name="staging:project",
            package_name=None,
            old_sha="0000000000000000000000000000000000000000",
            new_sha="1111111111111111111111111111111111111111",
            ref_name="refs/heads/factory",
        )
        self.assertFalse(allowed)
        self.assertIn("staging workflow", err)

    def test_private_branch_allowed_for_own_user(self):
        from .policy import evaluate_ref_update
        allowed, err = evaluate_ref_update(
            username="devuser",
            project_name="staging:project",
            package_name=None,
            old_sha="0000000000000000000000000000000000000000",
            new_sha="1111111111111111111111111111111111111111",
            ref_name="refs/heads/private/devuser/my-feature",
        )
        self.assertTrue(allowed)
        self.assertIsNone(err)

    def test_private_branch_rejected_for_different_user(self):
        from .policy import evaluate_ref_update
        allowed, err = evaluate_ref_update(
            username="devuser",
            project_name="staging:project",
            package_name=None,
            old_sha="0000000000000000000000000000000000000000",
            new_sha="1111111111111111111111111111111111111111",
            ref_name="refs/heads/private/otheruser/my-feature",
        )
        self.assertFalse(allowed)
        self.assertIn("Cannot push to private branch of another user", err)

    def test_arbitrary_branch_rejected(self):
        from .policy import evaluate_ref_update
        allowed, err = evaluate_ref_update(
            username="devuser",
            project_name="direct:project",
            package_name="mypkg",
            old_sha="0000000000000000000000000000000000000000",
            new_sha="1111111111111111111111111111111111111111",
            ref_name="refs/heads/random-topic",
        )
        self.assertFalse(allowed)
        self.assertIn("Ref 'refs/heads/random-topic' is not allowed", err)


class GitTransportHookServerTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="sockuser",
            password="secretpassword",
            is_local_account=True,
        )
        self.org = Org.objects.create(name="sockorg")
        self.project = Project.objects.create(
            name="sock:project",
            org=self.org,
            branch_name="main",
            workflow_type=Project.WorkflowType.DIRECT,
        )
        from .hook_server import start_hook_server
        self.sock_path = start_hook_server()

    def test_unix_socket_pre_receive_allow(self):
        import socket
        import json
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(str(self.sock_path))
        payload = {
            "action": "pre-receive",
            "user": "sockuser",
            "project": "sock:project",
            "package": None,
            "updates": [
                {
                    "old_sha": "0" * 40,
                    "new_sha": "1" * 40,
                    "ref": "refs/heads/main",
                }
            ],
        }
        s.sendall(json.dumps(payload).encode("utf-8") + b"\n")
        resp = json.loads(s.makefile().readline())
        s.close()
        self.assertTrue(resp.get("ok"))

    def test_unix_socket_pre_receive_reject(self):
        import socket
        import json
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(str(self.sock_path))
        payload = {
            "action": "pre-receive",
            "user": "sockuser",
            "project": "sock:project",
            "package": None,
            "updates": [
                {
                    "old_sha": "0" * 40,
                    "new_sha": "1" * 40,
                    "ref": "refs/heads/forbidden-branch",
                }
            ],
        }
        s.sendall(json.dumps(payload).encode("utf-8") + b"\n")
        resp = json.loads(s.makefile().readline())
        s.close()
        self.assertFalse(resp.get("ok"))
        self.assertIn("not allowed", resp.get("error", ""))


class GitTransportLiveServerTests(LiveServerTestCase):
    def setUp(self):
        import tempfile
        import shutil
        self.forge_dir = Path(tempfile.mkdtemp())
        self.old_forge_root = settings.GIT_FORGE_ROOT
        settings.GIT_FORGE_ROOT = self.forge_dir
        self.addCleanup(self._cleanup_forge)

        self.user = User.objects.create_user(
            username="liveuser",
            password="livepassword",
            is_local_account=True,
        )
        self.org = Org.objects.create(name="liveorg")
        self.direct_project = Project.objects.create(
            name="live:direct",
            org=self.org,
            branch_name="master",
            workflow_type=Project.WorkflowType.DIRECT,
        )
        self.package = Package.objects.create(
            project=self.direct_project,
            name="livepkg",
        )
        self.staging_project = Project.objects.create(
            name="live:staging",
            org=self.org,
            branch_name="factory",
            workflow_type=Project.WorkflowType.STAGING,
        )
        self.staging_package = Package.objects.create(
            project=self.staging_project,
            name="stagingpkg",
        )
        from .hook_server import start_hook_server
        self.sock_path = start_hook_server()

    def _cleanup_forge(self):
        import shutil
        settings.GIT_FORGE_ROOT = self.old_forge_root
        shutil.rmtree(self.forge_dir, ignore_errors=True)

    def test_git_clone_and_push_flow(self):
        import tempfile
        import shutil
        import subprocess
        from pathlib import Path

        temp_dir = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(temp_dir, ignore_errors=True))

        repo_url = f"{self.live_server_url}/package/live:direct/livepkg.git"
        auth_url = repo_url.replace("://", f"://liveuser:livepassword@")

        # 1. Clone empty repository anonymously
        clone_dir = temp_dir / "checkout"
        res = subprocess.run(
            ["git", "clone", repo_url, str(clone_dir)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, f"Git clone failed: {res.stderr}")

        # 2. Configure user in repo and create initial commit
        subprocess.run(["git", "config", "user.name", "Live User"], cwd=str(clone_dir), check=True)
        subprocess.run(["git", "config", "user.email", "live@example.com"], cwd=str(clone_dir), check=True)
        subprocess.run(["git", "remote", "set-url", "origin", auth_url], cwd=str(clone_dir), check=True)
        (clone_dir / "file.txt").write_text("Hello Git Transport\n")
        subprocess.run(["git", "add", "file.txt"], cwd=str(clone_dir), check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=str(clone_dir), check=True)

        # 3. Push to master (allowed in DIRECT workflow)
        res_push = subprocess.run(
            ["git", "push", "origin", "master"],
            cwd=str(clone_dir),
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_push.returncode, 0, f"Push to master failed: {res_push.stderr}")

        # 4. Push to arbitrary branch (rejected by hook)
        res_bad_branch = subprocess.run(
            ["git", "push", "origin", "master:random-branch"],
            cwd=str(clone_dir),
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(res_bad_branch.returncode, 0)
        self.assertIn("not allowed", res_bad_branch.stderr)

        # 5. Push to private branch for liveuser (allowed)
        res_private = subprocess.run(
            ["git", "push", "origin", "master:private/liveuser/feat-x"],
            cwd=str(clone_dir),
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_private.returncode, 0, f"Push to private branch failed: {res_private.stderr}")

        # 6. Push to private branch for another user (rejected)
        res_other_private = subprocess.run(
            ["git", "push", "origin", "master:private/otheruser/feat-x"],
            cwd=str(clone_dir),
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(res_other_private.returncode, 0)
        self.assertIn("Cannot push to private branch of another user", res_other_private.stderr)

        # 7. Push to staging project branch (rejected for staging workflow)
        repo_staging_url = f"{self.live_server_url}/package/live:staging/stagingpkg.git"
        auth_staging_url = repo_staging_url.replace("://", f"://liveuser:livepassword@")
        staging_clone_dir = temp_dir / "staging_checkout"
        subprocess.run(["git", "clone", auth_staging_url, str(staging_clone_dir)], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Live User"], cwd=str(staging_clone_dir), check=True)
        subprocess.run(["git", "config", "user.email", "live@example.com"], cwd=str(staging_clone_dir), check=True)
        (staging_clone_dir / "staging_file.txt").write_text("Staging\n")
        subprocess.run(["git", "add", "staging_file.txt"], cwd=str(staging_clone_dir), check=True)
        subprocess.run(["git", "commit", "-m", "Staging commit"], cwd=str(staging_clone_dir), check=True)

        res_staging_push = subprocess.run(
            ["git", "push", "origin", "master:factory"],
            cwd=str(staging_clone_dir),
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(res_staging_push.returncode, 0)
        self.assertIn("staging workflow", res_staging_push.stderr)


