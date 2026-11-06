import json
from django.test import TestCase, TransactionTestCase
from django_bolt.testing import TestClient

from core.models import Project, Package, Org
from obs_flow_server.api import api


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
        from django.test import override_settings

        with override_settings(REVIEW_DEBOUNCE_MINUTES=20):
            proj_default = Project.objects.create(name="proj:default")
            self.assertEqual(proj_default.effective_review_debounce_minutes, 20)

            proj_custom = Project.objects.create(name="proj:custom", review_debounce_minutes=5)
            self.assertEqual(proj_custom.effective_review_debounce_minutes, 5)

            proj_zero = Project.objects.create(name="proj:zero", review_debounce_minutes=0)
            self.assertEqual(proj_zero.effective_review_debounce_minutes, 0)

    def test_system_check_validation(self):
        from core.apps import check_review_debounce_setting
        from django.test import override_settings

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
        from accounts.models import User
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
        from core.models import Org
        from django.core.exceptions import ValidationError

        # Invalid characters or formats
        invalid_names = [".hidden", "bad..name", "invalid.git", "", "-starts-with-dash"]
        for bad_name in invalid_names:
            with self.subTest(bad_name=bad_name):
                with self.assertRaises(ValidationError):
                    Org.objects.create(name=bad_name)

    def test_org_immutability(self):
        from core.models import Org
        from django.core.exceptions import ValidationError

        org = Org.objects.create(name="suse-org")
        org.name = "suse-renamed"
        with self.assertRaises(ValidationError):
            org.save()

    def test_org_case_insensitive_uniqueness(self):
        from core.models import Org
        from django.db import IntegrityError

        Org.objects.create(name="MyOrg")
        with self.assertRaises(IntegrityError):
            Org.objects.create(name="myorg")

    def test_project_with_org_and_branch(self):
        from core.models import Org, Project
        from django.core.exceptions import ValidationError

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
        from core.models import Org, Project
        from django.db import IntegrityError

        org1 = Org.objects.create(name="org1")
        org2 = Org.objects.create(name="org2")

        Project.objects.create(name="p1", org=org1, branch_name="master")

        # Same branch in different org is allowed
        Project.objects.create(name="p2", org=org2, branch_name="master")

        # Same branch in same org is forbidden
        with self.assertRaises(IntegrityError):
            Project.objects.create(name="p3", org=org1, branch_name="master")

    def test_project_immutability(self):
        from core.models import Org, Project
        from django.core.exceptions import ValidationError

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
        from accounts.models import User
        from core.models import Org, Project, Package
        from django.core.exceptions import ValidationError

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
        from django.test import override_settings
        from core.models import Org, Project

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
        response = self.client.get(f"/projects/{self.proj.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "openSUSE:Factory")
        self.assertContains(response, "bash")

        # 404 for missing project
        response = self.client.get("/projects/99999/")
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
        response = self.client.get(f"/packages/{self.pkg.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "bash")
        self.assertContains(response, "openSUSE:Factory")

        # 404 for missing package
        response = self.client.get("/packages/99999/")
        self.assertEqual(response.status_code, 404)

    def test_project_pr_list_view(self):
        from accounts.models import User
        from pull_requests.models import PullRequest
        user = User.objects.create(username="alice", username_lower="alice", account_type=User.AccountType.HUMAN)
        other_proj = Project.objects.create(name="openSUSE:Leap", org=self.org, branch_name="leap")
        PullRequest.objects.create(project=self.proj, package=self.pkg, number=1, author=user, title="Fix bash bug")
        PullRequest.objects.create(project=other_proj, number=1, author=user, title="Leap core change")

        response = self.client.get(f"/projects/{self.proj.id}/pull-requests/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Fix bash bug")
        self.assertNotContains(response, "Leap core change")

    def test_project_staging_list_view(self):
        from accounts.models import User
        from staging.models import StagingBatch
        user = User.objects.create(username="bob", username_lower="bob", account_type=User.AccountType.HUMAN)
        other_proj = Project.objects.create(name="openSUSE:Tumbleweed", org=self.org, branch_name="tw")
        StagingBatch.objects.create(project=self.proj, author=user, title="Factory batch 1")
        StagingBatch.objects.create(project=other_proj, author=user, title="TW batch 1")

        response = self.client.get(f"/projects/{self.proj.id}/staging/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Factory batch 1")
        self.assertNotContains(response, "TW batch 1")

    def test_package_pr_list_view(self):
        from accounts.models import User
        from pull_requests.models import PullRequest
        user = User.objects.create(username="charlie", username_lower="charlie", account_type=User.AccountType.HUMAN)
        pkg2 = Package.objects.create(project=self.proj, name="zsh")
        PullRequest.objects.create(project=self.proj, package=self.pkg, number=1, author=user, title="Bash specific PR")
        PullRequest.objects.create(project=self.proj, package=pkg2, number=2, author=user, title="Zsh specific PR")

        response = self.client.get(f"/packages/{self.pkg.id}/pull-requests/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bash specific PR")
        self.assertNotContains(response, "Zsh specific PR")





