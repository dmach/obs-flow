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

