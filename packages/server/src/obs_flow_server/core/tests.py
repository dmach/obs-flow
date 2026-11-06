import json
from pathlib import Path
from django.test import TestCase, TransactionTestCase, override_settings
from django_bolt.testing import TestClient
from obs_flow_server.api import api

from accounts.models import User
from core.models import Org, Package, Project


class FingerprintTests(TestCase):
    def test_base_payload_sorting_and_omission(self):
        import hashlib

        from core.fingerprint import BasePayload

        class DummyPayload(BasePayload):
            items: list[str] = []
            name: str | None = None

        payload = DummyPayload(items=["b", "a"])
        expected_json = b'{"items":["a","b"]}'
        self.assertEqual(payload._to_canonical_json(), expected_json)
        self.assertEqual(payload.compute_fingerprint(), hashlib.sha256(expected_json).hexdigest())

        # Verify defaults/None omitted
        payload2 = DummyPayload(items=["a"], name=None)
        self.assertEqual(payload2._to_canonical_json(), b'{"items":["a"]}')


class TestProjectAPI(TransactionTestCase):
    def setUp(self):
        self.proj_factory = Project.objects.create(name="openSUSE:Factory", workflow_type=Project.WorkflowType.STAGING)
        self.proj_leap = Project.objects.create(name="openSUSE:Leap:16.0", workflow_type=Project.WorkflowType.DIRECT)

    def test_list_projects(self):
        with TestClient(api) as client:
            response = client.post("/api/v1/project/list", content="{}")
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        projects = res_data["projects"]
        self.assertEqual(len(projects), 2)
        self.assertEqual(projects[0]["name"], "openSUSE:Factory")
        self.assertEqual(projects[0]["workflow_type"], "staging")
        self.assertEqual(projects[1]["name"], "openSUSE:Leap:16.0")
        self.assertEqual(projects[1]["workflow_type"], "direct")

    def test_update_project_workflow_type(self):
        payload = {
            "name": "openSUSE:Leap:16.0",
            "workflow_type": "staging",
        }
        with TestClient(api) as client:
            response = client.post("/api/v1/project/update", content=json.dumps(payload))
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertEqual(res_data["project"]["name"], "openSUSE:Leap:16.0")
        self.assertEqual(res_data["project"]["workflow_type"], "staging")

        # Verify DB
        self.proj_leap.refresh_from_db()
        self.assertEqual(self.proj_leap.workflow_type, Project.WorkflowType.STAGING)

    def test_update_project_invalid_workflow_type(self):
        payload = {
            "name": "openSUSE:Leap:16.0",
            "workflow_type": "invalid_type",
        }
        with TestClient(api) as client:
            response = client.post("/api/v1/project/update", content=json.dumps(payload))
        self.assertNotEqual(response.status_code, 200)

    def test_update_nonexistent_project(self):
        payload = {
            "name": "nonexistent",
            "workflow_type": "staging",
        }
        with TestClient(api) as client:
            response = client.post("/api/v1/project/update", content=json.dumps(payload))
        self.assertNotEqual(response.status_code, 200)

    def test_list_projects_filtering(self):
        with TestClient(api) as client:
            # Filter by name
            response = client.post("/api/v1/project/list", content=json.dumps({"name": "Factory"}))
            self.assertEqual(response.status_code, 200)
            res_data = response.json()
            self.assertEqual(len(res_data["projects"]), 1)
            self.assertEqual(res_data["projects"][0]["name"], "openSUSE:Factory")

            # Filter by workflow_type
            response = client.post("/api/v1/project/list", content=json.dumps({"workflow_type": "direct"}))
            self.assertEqual(response.status_code, 200)
            res_data = response.json()
            self.assertEqual(len(res_data["projects"]), 1)
            self.assertEqual(res_data["projects"][0]["name"], "openSUSE:Leap:16.0")

    def test_show_project(self):
        with TestClient(api) as client:
            response = client.post("/api/v1/project/show", content=json.dumps({"name": "openSUSE:Factory"}))
            self.assertEqual(response.status_code, 200)
            res_data = response.json()
            self.assertEqual(res_data["project"]["name"], "openSUSE:Factory")
            self.assertEqual(res_data["project"]["workflow_type"], "staging")

            # Nonexistent project
            response = client.post("/api/v1/project/show", content=json.dumps({"name": "nonexistent"}))
            self.assertNotEqual(response.status_code, 200)


class TestProjectDebounceSetting(TestCase):
    def test_effective_review_debounce_minutes(self):

        with override_settings(REVIEW_DEBOUNCE_MINUTES=20):
            proj_default = Project.objects.create(name="proj:default")
            self.assertEqual(proj_default.effective_review_debounce_minutes, 20)

            proj_custom = Project.objects.create(name="proj:custom", review_debounce_minutes=5)
            self.assertEqual(proj_custom.effective_review_debounce_minutes, 5)

            proj_zero = Project.objects.create(name="proj:zero", review_debounce_minutes=0)
            self.assertEqual(proj_zero.effective_review_debounce_minutes, 0)

    def test_system_check_validation(self):

        from core.apps import check_review_debounce_setting

        # Valid setting
        with override_settings(REVIEW_DEBOUNCE_MINUTES=15):
            errors = check_review_debounce_setting(None)
            self.assertEqual(errors, [])

        # Missing / None setting
        with override_settings(REVIEW_DEBOUNCE_MINUTES=None):
            errors = check_review_debounce_setting(None)
            self.assertEqual(len(errors), 1)
            self.assertEqual(errors[0].id, "core.E001")

        # Invalid setting (negative)
        with override_settings(REVIEW_DEBOUNCE_MINUTES=-1):
            errors = check_review_debounce_setting(None)
            self.assertEqual(len(errors), 1)
            self.assertEqual(errors[0].id, "core.E002")

        # Invalid setting (non-integer)
        with override_settings(REVIEW_DEBOUNCE_MINUTES="not-an-int"):
            errors = check_review_debounce_setting(None)
            self.assertEqual(len(errors), 1)
            self.assertEqual(errors[0].id, "core.E002")


class TestNativeGitForgeDomainModels(TransactionTestCase):
    def test_org_creation_and_properties(self):

        from core.models import Org

        # Shared org
        shared = Org.objects.create(name="openSUSE")
        self.assertFalse(shared.is_personal)
        self.assertEqual(str(shared), "openSUSE")

        # Personal org linked to user
        user = User.objects.create(username="tux", username_lower="tux", account_type=User.AccountType.HUMAN)
        personal = user.implicit_personal_org
        self.assertTrue(personal.is_personal)
        self.assertEqual(personal.name, "~tux")
        self.assertEqual(personal.user, user)

    def test_org_name_validations(self):
        from django.core.exceptions import ValidationError

        from core.models import Org

        # Invalid characters or formats
        invalid_names = [".hidden", "bad..name", "invalid.git", "", "-starts-with-dash"]
        for bad_name in invalid_names:
            with self.subTest(bad_name=bad_name):
                with self.assertRaises(ValidationError):
                    Org.objects.create(name=bad_name)

    def test_org_immutability(self):
        from django.core.exceptions import ValidationError

        from core.models import Org

        org = Org.objects.create(name="suse-org")
        org.name = "suse-renamed"
        with self.assertRaises(ValidationError):
            org.save()

    def test_org_case_insensitive_uniqueness(self):
        from django.db import IntegrityError

        from core.models import Org

        Org.objects.create(name="MyOrg")
        with self.assertRaises(IntegrityError):
            Org.objects.create(name="myorg")

    def test_project_with_org_and_branch(self):
        from django.core.exceptions import ValidationError

        from core.models import Org, Project

        org = Org.objects.create(name="opensuse-distro")
        proj = Project.objects.create(name="openSUSE:Factory", org=org, branch_name="factory")
        self.assertEqual(proj.org, org)
        self.assertEqual(proj.branch_name, "factory")

        # Branch name cannot contain '/'
        with self.assertRaises(ValidationError):
            Project.objects.create(name="proj2", org=org, branch_name="feature/foo")

        # Branch name cannot contain '..'
        with self.assertRaises(ValidationError):
            Project.objects.create(name="proj3", org=org, branch_name="foo..bar")

    def test_project_branch_unique_per_org(self):
        from django.db import IntegrityError

        from core.models import Org, Project

        org1 = Org.objects.create(name="org1")
        org2 = Org.objects.create(name="org2")

        Project.objects.create(name="p1", org=org1, branch_name="master")

        # Same branch in different org is allowed
        Project.objects.create(name="p2", org=org2, branch_name="master")

        # Same branch in same org is forbidden
        with self.assertRaises(IntegrityError):
            Project.objects.create(name="p3", org=org1, branch_name="master")

    def test_project_immutability(self):
        from django.core.exceptions import ValidationError

        from core.models import Org, Project

        org = Org.objects.create(name="myorg")
        proj = Project.objects.create(name="myproject", org=org, branch_name="main")

        # Cannot rename project
        proj.name = "renamed"
        with self.assertRaises(ValidationError):
            proj.save()

        proj.refresh_from_db()

        # Cannot change branch name
        proj.branch_name = "devel"
        with self.assertRaises(ValidationError):
            proj.save()

    def test_package_validations_and_forks(self):
        from django.core.exceptions import ValidationError

        from core.models import Org, Package, Project

        org = Org.objects.create(name="distro")
        proj = Project.objects.create(name="Factory", org=org, branch_name="factory")

        pkg = Package.objects.create(project=proj, name="bash")
        self.assertEqual(str(pkg), "Factory/bash")

        # Package name validation
        with self.assertRaises(ValidationError):
            Package.objects.create(project=proj, name="bash.git")

        # Package renaming forbidden
        pkg.name = "zsh"
        with self.assertRaises(ValidationError):
            pkg.save()

        pkg.refresh_from_db()

        # Fork relationship
        dev_user = User.objects.create(username="developer", username_lower="developer", account_type=User.AccountType.HUMAN)
        user_org = dev_user.implicit_personal_org
        devel_proj = Project.objects.create(name="home:developer", org=user_org, branch_name="dev")
        forked_pkg = Package.objects.create(project=devel_proj, name="bash", forked_from=pkg)
        self.assertEqual(forked_pkg.forked_from, pkg)
        self.assertIn(forked_pkg, pkg.forks.all())


class TestNativeGitForgeAPIs(TransactionTestCase):
    def test_org_api_create_and_list(self):
        import json
        with TestClient(api) as client:
            # Create shared org
            res = client.post("/api/v1/org/create", content=json.dumps({"name": "openSUSE"}))
            self.assertEqual(res.status_code, 200)
            data = res.json()["org"]
            self.assertEqual(data["name"], "openSUSE")
            self.assertFalse(data["is_personal"])

            # List orgs
            res = client.post("/api/v1/org/list", content="{}")
            self.assertEqual(res.status_code, 200)
            org_names = [o["name"] for o in res.json()["orgs"]]
            self.assertIn("openSUSE", org_names)

    def test_project_api_create_and_list(self):
        import json

        from core.models import Org
        org = Org.objects.create(name="distro")

        with TestClient(api) as client:
            res = client.post(
                "/api/v1/project/create",
                content=json.dumps({
                    "name": "openSUSE:Factory",
                    "org": "distro",
                    "branch_name": "factory",
                    "workflow_type": "staging",
                }),
            )
            self.assertEqual(res.status_code, 200)
            proj = res.json()["project"]
            self.assertEqual(proj["name"], "openSUSE:Factory")
            self.assertEqual(proj["org"], "distro")
            self.assertEqual(proj["branch_name"], "factory")
            self.assertEqual(proj["workflow_type"], "staging")

            # Check list includes org and branch_name
            res = client.post("/api/v1/project/list", content="{}")
            self.assertEqual(res.status_code, 200)
            matching = [p for p in res.json()["projects"] if p["name"] == "openSUSE:Factory"]
            self.assertEqual(len(matching), 1)
            self.assertEqual(matching[0]["org"], "distro")
            self.assertEqual(matching[0]["branch_name"], "factory")

    def test_package_api_create_and_list(self):
        import json

        from core.models import Org, Project

        org = Org.objects.create(name="distro")
        proj = Project.objects.create(name="Factory", org=org, branch_name="factory")

        with TestClient(api) as client:
            # Create package
            res = client.post(
                "/api/v1/package/create",
                content=json.dumps({
                    "project": "Factory",
                    "name": "bash",
                }),
            )
            self.assertEqual(res.status_code, 200)
            pkg = res.json()["package"]
            self.assertEqual(pkg["name"], "bash")
            self.assertEqual(pkg["project"], "Factory")

            # List packages
            res = client.post(
                "/api/v1/package/list",
                content=json.dumps({"project": "Factory"}),
            )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(len(res.json()["packages"]), 1)
            self.assertEqual(res.json()["packages"][0]["name"], "bash")

    def test_package_api_show_and_filter(self):
        import json
        from core.models import Org, Project

        org = Org.objects.create(name="distro2")
        proj = Project.objects.create(name="Factory2", org=org, branch_name="factory2")

        with TestClient(api) as client:
            client.post("/api/v1/package/create", content=json.dumps({"project": "Factory2", "name": "pkg-a"}))
            client.post("/api/v1/package/create", content=json.dumps({"project": "Factory2", "name": "pkg-b"}))

            # Filter by name
            res = client.post("/api/v1/package/list", content=json.dumps({"project": "Factory2", "name": "pkg-a"}))
            self.assertEqual(res.status_code, 200)
            self.assertEqual(len(res.json()["packages"]), 1)
            self.assertEqual(res.json()["packages"][0]["name"], "pkg-a")

            # Show package
            res = client.post("/api/v1/package/show", content=json.dumps({"project": "Factory2", "name": "pkg-a"}))
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["package"]["name"], "pkg-a")
            self.assertEqual(res.json()["package"]["project"], "Factory2")

            # Show nonexistent package
            res = client.post("/api/v1/package/show", content=json.dumps({"project": "Factory2", "name": "nonexistent"}))
            self.assertNotEqual(res.status_code, 200)

    def test_git_forge_repo_creation_and_fork(self):
        import tempfile
        import json
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            with override_settings(GIT_FORGE_ROOT=Path(tmpdir)):
                with TestClient(api) as client:
                    client.post("/api/v1/org/create", content=json.dumps({"name": "openSUSE"}))
                    client.post(
                        "/api/v1/project/create",
                        content=json.dumps({
                            "name": "openSUSE:Factory",
                            "org": "openSUSE",
                            "branch_name": "factory",
                        }),
                    )
                    client.post(
                        "/api/v1/package/create",
                        content=json.dumps({
                            "project": "openSUSE:Factory",
                            "name": "zypper",
                        }),
                    )

                    repo_path = Path(tmpdir) / "openSUSE" / "zypper.git"
                    self.assertTrue(repo_path.exists())
                    self.assertTrue((repo_path / "HEAD").exists())

                    # Create user org and fork
                    from accounts.models import User
                    user = User.objects.create(username="contributor", username_lower="contributor", account_type=User.AccountType.HUMAN)
                    user_org = user.implicit_personal_org
                    client.post(
                        "/api/v1/project/create",
                        content=json.dumps({
                            "name": "home:contributor",
                            "org": user_org.name,
                            "branch_name": "feature",
                        }),
                    )
                    client.post(
                        "/api/v1/package/create",
                        content=json.dumps({
                            "project": "home:contributor",
                            "name": "zypper",
                            "fork_from_project": "openSUSE:Factory",
                            "fork_from_package": "zypper",
                        }),
                    )

                    fork_path = Path(tmpdir) / user_org.name / "zypper.git"
                    self.assertTrue(fork_path.exists())
                    self.assertTrue((fork_path / "HEAD").exists())


class TestCoreUIViews(TestCase):
    def setUp(self):
        from django.test import Client
        self.client = Client()
        self.org = Org.objects.create(name="distro-ui")
        self.proj = Project.objects.create(
            name="openSUSE:Factory",
            org=self.org,
            branch_name="factory",
            workflow_type=Project.WorkflowType.STAGING,
        )
        self.pkg = Package.objects.create(project=self.proj, name="bash")

    def test_project_list_view(self):
        response = self.client.get("/projects/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "openSUSE:Factory")

        # Test filter
        response = self.client.get("/projects/?name=Nonexistent")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "openSUSE:Factory")

    def test_project_detail_view(self):
        response = self.client.get(f"/projects/{self.proj.name}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "openSUSE:Factory")
        self.assertContains(response, "bash")

        # 404 for missing project
        response = self.client.get("/projects/Nonexistent/")
        self.assertEqual(response.status_code, 404)

    def test_package_list_view(self):
        response = self.client.get("/packages/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "bash")

        # Test filter
        response = self.client.get("/packages/?name=Nonexistent")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "bash")

    def test_package_detail_view(self):
        response = self.client.get(f"/packages/{self.proj.name}/{self.pkg.name}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "bash")
        self.assertContains(response, "openSUSE:Factory")

        # 404 for missing package
        response = self.client.get("/packages/openSUSE:Factory/nonexistent/")
        self.assertEqual(response.status_code, 404)

    def test_urls_are_human_readable(self):
        self.assertEqual(self.proj.get_absolute_url(), "/projects/openSUSE:Factory/")
        self.assertEqual(self.pkg.get_absolute_url(), "/packages/openSUSE:Factory/bash/")
        response = self.client.get("/projects/openSUSE:Factory/")
        self.assertContains(response, 'href="/packages/openSUSE:Factory/bash/"')
        self.assertContains(response, 'href="/projects/openSUSE:Factory/pull-requests/"')

    def test_same_package_name_in_two_projects(self):
        other = Project.objects.create(name="openSUSE:Leap", org=self.org, branch_name="leap")
        Package.objects.create(project=other, name="bash")
        response = self.client.get("/packages/openSUSE:Leap/bash/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["package"].project, other)
        response = self.client.get("/packages/openSUSE:Factory/bash/")
        self.assertEqual(response.context["package"].project, self.proj)

    def test_project_pr_list_view(self):
        from pull_requests.models import PullRequest
        user = User.objects.create(username="alice", username_lower="alice", account_type=User.AccountType.HUMAN)
        other_proj = Project.objects.create(name="openSUSE:Leap", org=self.org, branch_name="leap")
        PullRequest.objects.create(project=self.proj, package=self.pkg, number=1, author=user, title="Fix bash bug")
        PullRequest.objects.create(project=other_proj, number=1, author=user, title="Leap core change")

        response = self.client.get(f"/projects/{self.proj.name}/pull-requests/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Fix bash bug")
        self.assertNotContains(response, "Leap core change")

    def test_project_staging_list_view(self):
        from staging.models import StagingBatch
        user = User.objects.create(username="bob", username_lower="bob", account_type=User.AccountType.HUMAN)
        other_proj = Project.objects.create(name="openSUSE:Tumbleweed", org=self.org, branch_name="tw")
        StagingBatch.objects.create(project=self.proj, author=user, title="Factory batch 1")
        StagingBatch.objects.create(project=other_proj, author=user, title="TW batch 1")

        response = self.client.get(f"/projects/{self.proj.name}/staging/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Factory batch 1")
        self.assertNotContains(response, "TW batch 1")

    def test_package_pr_list_view(self):
        from pull_requests.models import PullRequest
        user = User.objects.create(username="charlie", username_lower="charlie", account_type=User.AccountType.HUMAN)
        pkg2 = Package.objects.create(project=self.proj, name="zsh")
        PullRequest.objects.create(project=self.proj, package=self.pkg, number=1, author=user, title="Bash specific PR")
        PullRequest.objects.create(project=self.proj, package=pkg2, number=2, author=user, title="Zsh specific PR")

        response = self.client.get(f"/packages/{self.proj.name}/{self.pkg.name}/pull-requests/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bash specific PR")
        self.assertNotContains(response, "Zsh specific PR")







class TestCodeBrowserViews(TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path
        self.tmpdir = tempfile.TemporaryDirectory()
        self.settings_override = override_settings(GIT_FORGE_ROOT=Path(self.tmpdir.name))
        self.settings_override.enable()

        self.org = Org.objects.create(name="obs")
        self.proj = Project.objects.create(
            name="obs:project",
            org=self.org,
            branch_name="master",
            workflow_type=Project.WorkflowType.DIRECT,
        )
        self.pkg = Package.objects.create(project=self.proj, name="testpkg")

    def tearDown(self):
        self.settings_override.disable()
        self.tmpdir.cleanup()

    def test_project_code_empty_repo(self):
        response = self.client.get(f"/projects/{self.proj.name}/code/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Empty directory")
        self.assertContains(response, self.proj.name)

    def test_project_code_with_tree_and_blob(self):
        from core.git_forge import ensure_git_repo
        import subprocess
        import tempfile

        repo_path = ensure_git_repo(self.org.name, initial_branch="master")
        # Populate repo with a commit
        with tempfile.TemporaryDirectory() as workdir:
            subprocess.run(["git", "clone", str(repo_path), workdir], check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=workdir, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=workdir, check=True)
            
            # Create files
            readme = Path(workdir) / "README.md"
            readme.write_text("Hello World\n")
            src_dir = Path(workdir) / "src"
            src_dir.mkdir()
            code_file = src_dir / "main.py"
            code_file.write_text("print('test')\n")
            
            subprocess.run(["git", "add", "."], cwd=workdir, check=True)
            subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=workdir, check=True)
            subprocess.run(["git", "push", "origin", "master"], cwd=workdir, check=True)

        # 1. Root directory
        response = self.client.get(f"/projects/{self.proj.name}/code/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "README.md")
        self.assertContains(response, "src")
        self.assertContains(response, "Initial commit")

        # 2. Subdirectory
        response = self.client.get(f"/projects/{self.proj.name}/code/src")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "main.py")
        self.assertContains(response, "..")

        # 3. File blob
        response = self.client.get(f"/projects/{self.proj.name}/code/src/main.py")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "print(&#x27;test&#x27;)")
        self.assertContains(response, "Copy path")
        self.assertContains(response, "Raw")

        # 4. Raw file
        response = self.client.get(f"/projects/{self.proj.name}/raw/src/main.py")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode("utf-8"), "print('test')\n")
        self.assertEqual(response["Content-Type"], "text/plain")

        # 5. Non-existent path
        response = self.client.get(f"/projects/{self.proj.name}/code/nonexistent")
        self.assertEqual(response.status_code, 404)
        response = self.client.get(f"/projects/{self.proj.name}/raw/nonexistent")
        self.assertEqual(response.status_code, 404)

    def test_package_code_with_tree_and_blob(self):
        from core.git_forge import ensure_git_repo
        import subprocess
        import tempfile

        repo_path = ensure_git_repo(self.org.name, package_name=self.pkg.name, initial_branch="master")
        with tempfile.TemporaryDirectory() as workdir:
            subprocess.run(["git", "clone", str(repo_path), workdir], check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=workdir, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=workdir, check=True)
            
            pkg_file = Path(workdir) / "testpkg.spec"
            pkg_file.write_text("Name: testpkg\nVersion: 1.0\n")
            
            subprocess.run(["git", "add", "."], cwd=workdir, check=True)
            subprocess.run(["git", "commit", "-m", "Add spec file"], cwd=workdir, check=True)
            subprocess.run(["git", "push", "origin", "master"], cwd=workdir, check=True)

        # 1. Package root
        response = self.client.get(f"/packages/{self.proj.name}/{self.pkg.name}/code/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "testpkg.spec")
        self.assertContains(response, "Add spec file")

        # 2. Package blob
        response = self.client.get(f"/packages/{self.proj.name}/{self.pkg.name}/code/testpkg.spec")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Name: testpkg")

        # 3. Package raw
        response = self.client.get(f"/packages/{self.proj.name}/{self.pkg.name}/raw/testpkg.spec")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode("utf-8"), "Name: testpkg\nVersion: 1.0\n")

    def test_project_and_package_commits_view(self):
        from core.git_forge import ensure_git_repo
        import subprocess
        import tempfile

        # Project with 2 commits
        repo_path = ensure_git_repo(self.org.name, initial_branch="master")
        with tempfile.TemporaryDirectory() as workdir:
            subprocess.run(["git", "clone", str(repo_path), workdir], check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Alice Dev"], cwd=workdir, check=True)
            subprocess.run(["git", "config", "user.email", "alice@example.com"], cwd=workdir, check=True)

            (Path(workdir) / "file1.txt").write_text("v1\n")
            subprocess.run(["git", "add", "."], cwd=workdir, check=True)
            subprocess.run(["git", "commit", "--author=Alice Dev <alice@example.com>", "-m", "Commit 1"], cwd=workdir, check=True)

            (Path(workdir) / "file2.txt").write_text("v2\n")
            subprocess.run(["git", "add", "."], cwd=workdir, check=True)
            subprocess.run(["git", "commit", "--author=Alice Dev <alice@example.com>", "-m", "Commit 2"], cwd=workdir, check=True)
            subprocess.run(["git", "push", "origin", "master"], cwd=workdir, check=True)

        # Check project commits page
        response = self.client.get(f"/projects/{self.proj.name}/commits/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Commit 1")
        self.assertContains(response, "Commit 2")
        self.assertContains(response, "Alice Dev")
        self.assertContains(response, "&lt;&gt;")  # Browse code button

        # Package with 1 commit
        pkg_repo = ensure_git_repo(self.org.name, package_name=self.pkg.name, initial_branch="master")
        with tempfile.TemporaryDirectory() as workdir:
            subprocess.run(["git", "clone", str(pkg_repo), workdir], check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Bob Packager"], cwd=workdir, check=True)
            subprocess.run(["git", "config", "user.email", "bob@example.com"], cwd=workdir, check=True)

            (Path(workdir) / "pkg.spec").write_text("spec\n")
            subprocess.run(["git", "add", "."], cwd=workdir, check=True)
            subprocess.run(["git", "commit", "--author=Bob Packager <bob@example.com>", "-m", "Initial pkg commit"], cwd=workdir, check=True)
            subprocess.run(["git", "push", "origin", "master"], cwd=workdir, check=True)

        # Check package commits page
        response = self.client.get(f"/packages/{self.proj.name}/{self.pkg.name}/commits/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Initial pkg commit")
        self.assertContains(response, "Bob Packager")

    def test_browse_code_at_historical_ref(self):
        from core.git_forge import ensure_git_repo
        import subprocess
        import tempfile

        repo_path = ensure_git_repo(self.org.name, initial_branch="master")
        commit1_sha = None
        commit2_sha = None

        with tempfile.TemporaryDirectory() as workdir:
            subprocess.run(["git", "clone", str(repo_path), workdir], check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Dev"], cwd=workdir, check=True)
            subprocess.run(["git", "config", "user.email", "dev@example.com"], cwd=workdir, check=True)

            (Path(workdir) / "first.txt").write_text("first\n")
            subprocess.run(["git", "add", "."], cwd=workdir, check=True)
            subprocess.run(["git", "commit", "-m", "First commit"], cwd=workdir, check=True)
            proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=workdir, capture_output=True, text=True, check=True)
            commit1_sha = proc.stdout.strip()

            (Path(workdir) / "second.txt").write_text("second\n")
            subprocess.run(["git", "add", "."], cwd=workdir, check=True)
            subprocess.run(["git", "commit", "-m", "Second commit"], cwd=workdir, check=True)
            proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=workdir, capture_output=True, text=True, check=True)
            commit2_sha = proc.stdout.strip()

            subprocess.run(["git", "push", "origin", "master"], cwd=workdir, check=True)

        # 1. At HEAD (master), both files exist
        response = self.client.get(f"/projects/{self.proj.name}/code/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "first.txt")
        self.assertContains(response, "second.txt")

        # 2. At commit 1, only first.txt exists, second.txt does not
        response = self.client.get(f"/projects/{self.proj.name}/code/?ref={commit1_sha}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "first.txt")
        self.assertNotContains(response, "second.txt")
        self.assertContains(response, f"@{(commit1_sha[:7])}")
        self.assertContains(response, f"?ref={commit1_sha}")

        # 3. Viewing file blob at commit 1
        response = self.client.get(f"/projects/{self.proj.name}/code/first.txt?ref={commit1_sha}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "first")
        self.assertContains(response, f"?ref={commit1_sha}")
