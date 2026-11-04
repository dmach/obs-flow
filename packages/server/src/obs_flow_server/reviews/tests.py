import os
import json
import msgspec
from unittest.mock import MagicMock, patch
from django.test import TestCase, TransactionTestCase
from django_bolt.testing import TestClient

from accounts.models import User, Group
from core.models import Project, GitMapping
from pull_requests.models import PullRequest, PullRequestRevision, PullRequestReview
from reviews.models import ReviewConfig, ReviewScope
from obs_flow_server.api import api

# Client and CLI imports for testing
from obs_flow_client import (
    Connection,
    review_config_add,
    review_config_remove,
    review_config_list,
)
from obs_flow_common.messages import (
    ReviewConfigDTO,
    ReviewConfigAddRequest,
    ReviewConfigRemoveRequest,
    ReviewConfigListRequest,
    ReviewConfigAddResponse,
    ReviewConfigRemoveResponse,
    ReviewConfigListResponse,
    PersonReviewerDTO,
)
from click.testing import CliRunner
from obs_flow_cli.commands.config__review import cli as review_config_cli


class TestReviewConfigEndpoints(TransactionTestCase):
    fixtures = ["opensuse_data.json"]

    def test_review_config_add_user(self):
        """Verify adding a review configuration for a user."""
        payload = {
            "project": "openSUSE:Factory",
            "type": "project",
            "reviewer": "darix",
            "depends_on": [],
            "scope": "global",
        }
        with TestClient(api) as client:
            response = client.post(
                "/api/v1/review-config/add",
                content=json.dumps(payload),
            )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        config_detail = res_data["data"]
        self.assertEqual(config_detail["project"], "openSUSE:Factory")
        self.assertEqual(config_detail["type"], "project")
        self.assertEqual(config_detail["reviewer"], {
            "type": "person",
            "username": "darix",
            "full_name": "Marcus Rueckert",
            "email": "mrueckert@suse.com",
            "is_active": True,
        })
        self.assertEqual(config_detail["depends_on"], [])

        # Verify database state
        self.assertTrue(ReviewConfig.objects.filter(
            project__name="openSUSE:Factory",
            type="project",
            reviewer_user__username="darix"
        ).exists())

    def test_review_config_add_requires_scope(self):
        """Verify that scope is mandatory in the API; only the CLI may default it."""
        payload = {
            "project": "openSUSE:Factory",
            "type": "project",
            "reviewer": "darix",
            "depends_on": [],
        }
        with TestClient(api) as client:
            response = client.post(
                "/api/v1/review-config/add",
                content=json.dumps(payload),
            )
        self.assertGreaterEqual(response.status_code, 400)
        self.assertLess(response.status_code, 500)
        self.assertFalse(ReviewConfig.objects.filter(
            project__name="openSUSE:Factory",
            type="project",
            reviewer_user__username="darix",
        ).exists())

    def test_review_config_add_group(self):
        """Verify adding a review configuration for a group."""
        payload = {
            "project": "openSUSE:Factory",
            "type": "staging",
            "reviewer": "@opensuse-review-team",
            "depends_on": [],
            "scope": "global",
        }
        with TestClient(api) as client:
            response = client.post(
                "/api/v1/review-config/add",
                content=json.dumps(payload),
            )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        config_detail = res_data["data"]
        self.assertEqual(config_detail["reviewer"], {
            "type": "group",
            "name": "opensuse-review-team",
            "email": None,
        })
        self.assertEqual(config_detail["type"], "staging")

    def test_review_config_add_dynamic_role(self):
        """Verify adding a review configuration for a dynamic role."""
        payload = {
            "project": "openSUSE:Factory",
            "type": "package",
            "reviewer": "role:maintainer",
            "depends_on": [],
            "scope": "global",
        }
        with TestClient(api) as client:
            response = client.post(
                "/api/v1/review-config/add",
                content=json.dumps(payload),
            )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        config_detail = res_data["data"]
        self.assertEqual(config_detail["reviewer"], {
            "type": "role",
            "role": "maintainer",
        })
        self.assertEqual(config_detail["type"], "package")

    def test_review_config_add_same_reviewer_different_type(self):
        """Verify that the same reviewer can have configurations for different types."""
        payload1 = {
            "project": "openSUSE:Factory",
            "type": "project",
            "reviewer": "darix",
            "depends_on": [],
            "scope": "global",
        }
        payload2 = {
            "project": "openSUSE:Factory",
            "type": "staging",
            "reviewer": "darix",
            "depends_on": [],
            "scope": "global",
        }
        with TestClient(api) as client:
            response1 = client.post(
                "/api/v1/review-config/add",
                content=json.dumps(payload1),
            )
            response2 = client.post(
                "/api/v1/review-config/add",
                content=json.dumps(payload2),
            )
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)
        self.assertTrue(ReviewConfig.objects.filter(
            project__name="openSUSE:Factory",
            type="project",
            reviewer_user__username="darix"
        ).exists())
        self.assertTrue(ReviewConfig.objects.filter(
            project__name="openSUSE:Factory",
            type="staging",
            reviewer_user__username="darix"
        ).exists())

    def test_review_config_add_duplicate_fails(self):
        """Verify that adding a duplicate review configuration for the same reviewer and type fails."""
        payload = {
            "project": "openSUSE:Factory",
            "type": "project",
            "reviewer": "darix",
            "depends_on": [],
            "scope": "global",
        }
        with TestClient(api) as client:
            response1 = client.post(
                "/api/v1/review-config/add",
                content=json.dumps(payload),
            )
            response2 = client.post(
                "/api/v1/review-config/add",
                content=json.dumps(payload),
            )
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 400)
        self.assertIn("already exists", response2.text)

    def test_review_config_add_with_dependencies(self):
        """Verify adding a review configuration that depends on other configurations."""
        # First, add dependency configurations
        project = Project.objects.get(name="openSUSE:Factory")
        dep1 = ReviewConfig.objects.create(
            project=project,
            type="project",
            reviewer_user=User.objects.get(username="darix"),
            scope=ReviewScope.objects.get(name="global"),
        )
        dep2 = ReviewConfig.objects.create(
            project=project,
            type="project",
            reviewer_group=Group.objects.get(name="opensuse-review-team"),
            scope=ReviewScope.objects.get(name="global"),
        )

        # Add a configuration that depends on dep1 and dep2
        payload = {
            "project": "openSUSE:Factory",
            "type": "project",
            "reviewer": "dimstar",
            "depends_on": ["darix", "@opensuse-review-team"],
            "scope": "global",
        }
        with TestClient(api) as client:
            response = client.post(
                "/api/v1/review-config/add",
                content=json.dumps(payload),
            )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        config_detail = res_data["data"]
        self.assertEqual(config_detail["reviewer"], {
            "type": "person",
            "username": "dimstar",
            "full_name": "Dominique Leuenberger",
            "email": "dimstar@opensuse.org",
            "is_active": True,
        })
        self.assertCountEqual(config_detail["depends_on"], [
            {
                "type": "person",
                "username": "darix",
                "full_name": "Marcus Rueckert",
                "email": "mrueckert@suse.com",
                "is_active": True,
            },
            {
                "type": "group",
                "name": "opensuse-review-team",
                "email": None,
            }
        ])

        # Verify database relations
        config = ReviewConfig.objects.get(reviewer_user__username="dimstar", type="project")
        self.assertCountEqual(config.depends_on.all(), [dep1, dep2])

    def test_add_fails_with_missing_dependency(self):
        """Verify that adding a configuration fails if a dependency does not exist."""
        payload = {
            "project": "openSUSE:Factory",
            "type": "project",
            "reviewer": "dimstar",
            "depends_on": ["nonexistent_user"],
            "scope": "global",
        }
        with TestClient(api) as client:
            response = client.post(
                "/api/v1/review-config/add",
                content=json.dumps(payload),
            )
        self.assertEqual(response.status_code, 404)
        self.assertIn("User matching query does not exist", response.text)

    def test_review_config_add_self_dependency_fails(self):
        """Verify that adding a configuration that depends on itself fails."""
        payload = {
            "project": "openSUSE:Factory",
            "type": "project",
            "reviewer": "admin",
            "depends_on": ["admin"],
            "scope": "global",
        }
        with TestClient(api) as client:
            response = client.post(
                "/api/v1/review-config/add",
                content=json.dumps(payload),
            )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Circular dependency detected", response.text)
        # Verify it was not saved
        self.assertFalse(ReviewConfig.objects.filter(project__name="openSUSE:Factory", type="project", reviewer_user__username="admin").exists())

    def test_review_config_validate_no_cycles_indirect(self):
        """Verify that multi-node indirect cycles raise ValueError."""
        project = Project.objects.create(name="test:dag-project")
        u1 = User.objects.create(username="u1", username_lower="u1", account_type=User.AccountType.HUMAN)
        u2 = User.objects.create(username="u2", username_lower="u2", account_type=User.AccountType.HUMAN)
        u3 = User.objects.create(username="u3", username_lower="u3", account_type=User.AccountType.HUMAN)

        c1 = ReviewConfig.objects.create(project=project, type=ReviewConfig.ConfigType.PROJECT, reviewer_user=u1, scope=ReviewScope.objects.get(name="global"))
        c2 = ReviewConfig.objects.create(project=project, type=ReviewConfig.ConfigType.PROJECT, reviewer_user=u2, scope=ReviewScope.objects.get(name="global"))
        c3 = ReviewConfig.objects.create(project=project, type=ReviewConfig.ConfigType.PROJECT, reviewer_user=u3, scope=ReviewScope.objects.get(name="global"))

        # c2 depends on c1
        c2.depends_on.add(c1)
        # c3 depends on c2
        c3.depends_on.add(c2)

        # Trying to make c1 depend on c3 would create c1 -> c3 -> c2 -> c1
        with self.assertRaises(ValueError) as ctx:
            c1.validate_no_cycles([c3])
        self.assertIn("Circular dependency detected", str(ctx.exception))

    def test_review_config_list(self):
        """Verify listing review configurations for a project."""
        project = Project.objects.get(name="openSUSE:Factory")
        ReviewConfig.objects.create(
            project=project,
            type="project",
            reviewer_user=User.objects.get(username="darix"),
            scope=ReviewScope.objects.get(name="global"),
        )
        ReviewConfig.objects.create(
            project=project,
            type="package",
            reviewer_group=Group.objects.get(name="opensuse-review-team"),
            scope=ReviewScope.objects.get(name="global"),
        )

        # List all
        payload = {
            "project": "openSUSE:Factory"
        }
        with TestClient(api) as client:
            response = client.post(
                "/api/v1/review-config/list",
                content=json.dumps(payload),
            )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        configs = res_data["data"]
        self.assertEqual(len(configs), 4)

        # List filtered by type
        payload = {
            "project": "openSUSE:Factory",
            "type": "package"
        }
        with TestClient(api) as client:
            response = client.post(
                "/api/v1/review-config/list",
                content=json.dumps(payload),
            )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        configs = res_data["data"]
        self.assertEqual(len(configs), 1)
        self.assertEqual(configs[0]["reviewer"], {
            "type": "group",
            "name": "opensuse-review-team",
            "email": None,
        })

    def test_review_config_remove_by_reviewer(self):
        """Verify removing a review configuration by reviewer string."""
        project = Project.objects.get(name="openSUSE:Factory")
        config = ReviewConfig.objects.create(
            project=project,
            type="project",
            reviewer_user=User.objects.get(username="darix"),
            scope=ReviewScope.objects.get(name="global"),
        )

        payload = {
            "project": "openSUSE:Factory",
            "type": "project",
            "reviewer": "darix"
        }
        with TestClient(api) as client:
            response = client.post(
                "/api/v1/review-config/remove",
                content=json.dumps(payload),
            )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        config_detail = res_data["data"]
        self.assertEqual(config_detail["id"], config.id)
        self.assertEqual(config_detail["reviewer"], {
            "type": "person",
            "username": "darix",
            "full_name": "Marcus Rueckert",
            "email": "mrueckert@suse.com",
            "is_active": True,
        })
        self.assertFalse(ReviewConfig.objects.filter(
            project=project,
            type="project",
            reviewer_user__username="darix"
        ).exists())


class TestClientLibrary(TransactionTestCase):
    @patch.object(Connection, "post")
    def test_review_config_add_client(self, mock_post):
        """Verify client library review_config_add function."""
        dto = ReviewConfigDTO(
            id=1,
            project="openSUSE:Factory",
            type="project",
            reviewer=PersonReviewerDTO(username="darix", full_name="Marcus Rueckert", email="mrueckert@suse.com", is_active=True),
            depends_on=[]
        )
        response_payload = ReviewConfigAddResponse(data=dto)
        mock_post.return_value = msgspec.json.encode(response_payload)

        conn = Connection(base_url="http://localhost:8000")
        req = ReviewConfigAddRequest(
            project="openSUSE:Factory",
            type="project",
            reviewer="darix",
            depends_on=[],
            scope="global",
        )
        res = review_config_add(conn, req)
        self.assertEqual(res.data.id, 1)
        self.assertEqual(res.data.reviewer, PersonReviewerDTO(username="darix", full_name="Marcus Rueckert", email="mrueckert@suse.com", is_active=True))
        mock_post.assert_called_once_with("/api/v1/review-config/add", data=msgspec.json.encode(req))

    @patch.object(Connection, "post")
    def test_review_config_remove_client(self, mock_post):
        """Verify client library review_config_remove function."""
        dto = ReviewConfigDTO(
            id=1,
            project="openSUSE:Factory",
            type="project",
            reviewer=PersonReviewerDTO(username="darix", full_name="Marcus Rueckert", email="mrueckert@suse.com", is_active=True),
            depends_on=[]
        )
        response_payload = ReviewConfigRemoveResponse(data=dto)
        mock_post.return_value = msgspec.json.encode(response_payload)

        conn = Connection(base_url="http://localhost:8000")
        req = ReviewConfigRemoveRequest(
            project="openSUSE:Factory",
            type="project",
            reviewer="darix"
        )
        res = review_config_remove(conn, req)
        self.assertEqual(res.data.id, 1)
        self.assertEqual(res.data.reviewer, PersonReviewerDTO(username="darix", full_name="Marcus Rueckert", email="mrueckert@suse.com", is_active=True))
        mock_post.assert_called_once_with("/api/v1/review-config/remove", data=msgspec.json.encode(req))

    @patch.object(Connection, "post")
    def test_review_config_list_client(self, mock_post):
        """Verify client library review_config_list function."""
        dto = ReviewConfigDTO(
            id=1,
            project="openSUSE:Factory",
            type="project",
            reviewer=PersonReviewerDTO(username="darix", full_name="Marcus Rueckert", email="mrueckert@suse.com", is_active=True),
            depends_on=[]
        )
        response_payload = ReviewConfigListResponse(data=[dto])
        mock_post.return_value = msgspec.json.encode(response_payload)

        conn = Connection(base_url="http://localhost:8000")
        req = ReviewConfigListRequest(
            project="openSUSE:Factory",
            type="project"
        )
        res = review_config_list(conn, req)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0].reviewer, PersonReviewerDTO(username="darix", full_name="Marcus Rueckert", email="mrueckert@suse.com", is_active=True))
        mock_post.assert_called_once_with("/api/v1/review-config/list", data=msgspec.json.encode(req))


class TestCLIManagement(TransactionTestCase):
    def setUp(self):
        super().setUp()
        self.env_patcher = patch.dict(
            os.environ,
            {
                "OBS_FLOW_CONFIG": "/dev/null",
                "OBS_FLOW_SERVER_URL": "http://localhost:8000",
            },
        )
        self.env_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()
        super().tearDown()

    @patch("obs_flow_client.review_config_add")
    def test_cli_review_config_add(self, mock_add):
        """Verify CLI config review add command."""
        dto = ReviewConfigDTO(
            id=1,
            project="openSUSE:Factory",
            type="project",
            reviewer=PersonReviewerDTO(username="darix", full_name="Marcus Rueckert", email="mrueckert@suse.com", is_active=True),
            depends_on=[]
        )
        mock_add.return_value = ReviewConfigAddResponse(data=dto)

        runner = CliRunner()
        result = runner.invoke(
            review_config_cli,
            ["add", "--project", "openSUSE:Factory", "--type", "project", "--user", "darix"]
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("ID", result.output)
        self.assertIn("1", result.output)
        self.assertIn("Reviewer", result.output)
        self.assertIn("darix", result.output)

    @patch("obs_flow_client.review_config_remove")
    def test_cli_review_config_remove(self, mock_remove):
        """Verify CLI config review remove command."""
        dto = ReviewConfigDTO(
            id=1,
            project="openSUSE:Factory",
            type="project",
            reviewer=PersonReviewerDTO(username="darix", full_name="Marcus Rueckert", email="mrueckert@suse.com", is_active=True),
            depends_on=[]
        )
        mock_remove.return_value = ReviewConfigRemoveResponse(data=dto)

        runner = CliRunner()
        result = runner.invoke(
            review_config_cli,
            ["remove", "--project", "openSUSE:Factory", "--type", "project", "--user", "darix"]
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("ID", result.output)
        self.assertIn("1", result.output)
        self.assertIn("Reviewer", result.output)
        self.assertIn("darix", result.output)

    @patch("obs_flow_client.review_config_list")
    def test_cli_review_config_list(self, mock_list):
        """Verify CLI config review list command."""
        dto = ReviewConfigDTO(
            id=1,
            project="openSUSE:Factory",
            type="project",
            reviewer=PersonReviewerDTO(username="darix", full_name="Marcus Rueckert", email="mrueckert@suse.com", is_active=True),
            depends_on=[]
        )
        mock_list.return_value = ReviewConfigListResponse(data=[dto])

        runner = CliRunner()
        result = runner.invoke(
            review_config_cli,
            ["list", "--project", "openSUSE:Factory"]
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("ID", result.output)
        self.assertIn("1", result.output)
        self.assertIn("Reviewer", result.output)
        self.assertIn("darix", result.output)


class TestReviewScopeModelGuard(TestCase):
    """Model-level protection of the reserved 'global' scope."""
    fixtures = ["global_scope.json"]

    def test_global_scope_cannot_be_modified(self):
        scope = ReviewScope.objects.get(name="global")
        scope.include_globs = ["x/*.py"]
        with self.assertRaises(ValueError):
            scope.save()

    def test_global_scope_cannot_be_deleted(self):
        scope = ReviewScope.objects.get(name="global")
        with self.assertRaises(ValueError):
            scope.delete()

    def test_non_global_scope_can_be_modified_and_deleted(self):
        scope = ReviewScope.objects.create(name="code", include_globs=["src/*.py"], exclude_globs=[])
        scope.include_globs = ["lib/*.py"]
        scope.save()
        scope.refresh_from_db()
        self.assertEqual(scope.include_globs, ["lib/*.py"])
        scope.delete()
        self.assertFalse(ReviewScope.objects.filter(name="code").exists())


class TestReviewScopeAPI(TransactionTestCase):
    """API endpoints for managing review scopes (identified by name)."""

    def _post(self, path, payload):
        with TestClient(api) as client:
            return client.post(path, content=json.dumps(payload))

    def test_list_scopes_empty(self):
        response = self._post("/api/v1/review-scope/list", {})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["scopes"], [])

    def test_list_scopes_populated_ordered_by_name(self):
        ReviewScope.objects.create(name="zeta", include_globs=["z/*"], exclude_globs=[])
        ReviewScope.objects.create(name="alpha", include_globs=["a/*"], exclude_globs=[])
        response = self._post("/api/v1/review-scope/list", {})
        self.assertEqual(response.status_code, 200)
        scopes = response.json()["scopes"]
        self.assertEqual([s["name"] for s in scopes], ["alpha", "zeta"])
        self.assertEqual(scopes[0]["include_globs"], ["a/*"])

    def test_add_scope(self):
        payload = {"name": "code", "include_globs": ["src/*.py"], "exclude_globs": ["src/test/*"]}
        response = self._post("/api/v1/review-scope/add", payload)
        self.assertEqual(response.status_code, 200)
        scope = response.json()["scope"]
        self.assertEqual(scope["name"], "code")
        self.assertEqual(scope["include_globs"], ["src/*.py"])
        self.assertEqual(scope["exclude_globs"], ["src/test/*"])
        self.assertTrue(ReviewScope.objects.filter(name="code").exists())

    def test_add_scope_duplicate_fails(self):
        ReviewScope.objects.create(name="code", include_globs=["src/*.py"], exclude_globs=[])
        payload = {"name": "code", "include_globs": ["lib/*.py"]}
        response = self._post("/api/v1/review-scope/add", payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("already exists", response.text)

    def test_add_scope_reserved_global_fails(self):
        payload = {"name": "global", "include_globs": ["**/*"]}
        response = self._post("/api/v1/review-scope/add", payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("reserved", response.text)

    def test_add_scope_empty_include_fails(self):
        payload = {"name": "code", "include_globs": []}
        response = self._post("/api/v1/review-scope/add", payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("at least one include glob", response.text)

    def test_remove_scope(self):
        ReviewScope.objects.create(name="code", include_globs=["src/*.py"], exclude_globs=[])
        response = self._post("/api/v1/review-scope/remove", {"name": "code"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertFalse(ReviewScope.objects.filter(name="code").exists())

    def test_remove_scope_not_found(self):
        response = self._post("/api/v1/review-scope/remove", {"name": "nonexistent"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["success"])

    def test_remove_scope_in_use_fails(self):
        project = Project.objects.create(name="test:scope-inuse")
        user = User.objects.create(
            username="rev_inuse", username_lower="rev_inuse", account_type=User.AccountType.HUMAN
        )
        scope = ReviewScope.objects.create(name="code", include_globs=["src/*.py"], exclude_globs=[])
        ReviewConfig.objects.create(project=project, type="project", reviewer_user=user, scope=scope)
        response = self._post("/api/v1/review-scope/remove", {"name": "code"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("referenced", response.text)
        self.assertTrue(ReviewScope.objects.filter(name="code").exists())

    def test_remove_global_fails(self):
        ReviewScope.objects.create(name="global", include_globs=["**/*"], exclude_globs=[])
        response = self._post("/api/v1/review-scope/remove", {"name": "global"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("reserved", response.text)
        self.assertTrue(ReviewScope.objects.filter(name="global").exists())

    def test_update_scope(self):
        ReviewScope.objects.create(name="code", include_globs=["src/*.py"], exclude_globs=[])
        payload = {"name": "code", "include_globs": ["lib/*.py"], "exclude_globs": ["lib/test/*"]}
        response = self._post("/api/v1/review-scope/update", payload)
        self.assertEqual(response.status_code, 200)
        scope = response.json()["scope"]
        self.assertEqual(scope["include_globs"], ["lib/*.py"])
        self.assertEqual(scope["exclude_globs"], ["lib/test/*"])
        self.assertEqual(ReviewScope.objects.get(name="code").include_globs, ["lib/*.py"])
        self.assertEqual(ReviewScope.objects.get(name="code").exclude_globs, ["lib/test/*"])

    def test_update_scope_not_found(self):
        payload = {"name": "nonexistent", "include_globs": ["x/*"]}
        response = self._post("/api/v1/review-scope/update", payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("does not exist", response.text)

    def test_update_scope_nothing_to_update(self):
        ReviewScope.objects.create(name="code", include_globs=["src/*.py"], exclude_globs=[])
        response = self._post("/api/v1/review-scope/update", {"name": "code"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("at least one", response.text)

    def test_update_global_fails(self):
        ReviewScope.objects.create(name="global", include_globs=["**/*"], exclude_globs=[])
        payload = {"name": "global", "include_globs": ["**/*", "x/*"]}
        response = self._post("/api/v1/review-scope/update", payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("reserved", response.text)


class TestScopeMatching(TestCase):
    def test_file_matches_glob_exact(self):
        self.assertTrue(ReviewScope.matches_glob("src/main.py", "src/main.py"))

    def test_file_matches_glob_wildcard(self):
        self.assertTrue(ReviewScope.matches_glob("src/main.py", "src/*.py"))
        self.assertFalse(ReviewScope.matches_glob("src/main.py", "src/*.md"))

    def test_file_matches_glob_recursive(self):
        self.assertTrue(ReviewScope.matches_glob("a/b/c.py", "**/*.py"))
        self.assertTrue(ReviewScope.matches_glob("src/main.py", "**/*"))
        self.assertFalse(ReviewScope.matches_glob("a/b/c.md", "**/*.py"))

    def test_file_matches_glob_basename(self):
        # A pattern without a slash matches against the basename.
        self.assertTrue(ReviewScope.matches_glob("docs/CHANGELOG.md", "CHANGELOG.md"))
        self.assertTrue(ReviewScope.matches_glob("a/b/CHANGELOG.md", "CHANGELOG.md"))
        self.assertFalse(ReviewScope.matches_glob("docs/README.md", "CHANGELOG.md"))

    def test_file_matches_glob_no_match(self):
        self.assertFalse(ReviewScope.matches_glob("src/main.py", "docs/*.md"))

    def test_is_file_in_scope_include_only(self):
        scope = ReviewScope.objects.create(name="code", include_globs=["src/*.py"], exclude_globs=[])
        self.assertTrue(scope.is_file_in_scope("src/main.py"))
        self.assertFalse(scope.is_file_in_scope("docs/readme.md"))

    def test_is_file_in_scope_exclude_wins(self):
        scope = ReviewScope.objects.create(
            name="all-but-docs", include_globs=["**/*"], exclude_globs=["docs/*.md"]
        )
        self.assertTrue(scope.is_file_in_scope("src/main.py"))
        self.assertFalse(scope.is_file_in_scope("docs/readme.md"))

    def test_evaluate_scope_true_when_any_file_in_scope(self):
        scope = ReviewScope.objects.create(name="code", include_globs=["src/*.py"], exclude_globs=[])
        self.assertTrue(scope.evaluate({"src/main.py", "docs/readme.md"}))

    def test_evaluate_scope_false_when_no_file_in_scope(self):
        scope = ReviewScope.objects.create(name="code", include_globs=["src/*.py"], exclude_globs=[])
        self.assertFalse(scope.evaluate({"docs/readme.md"}))


class TestScopeProvisioningPR(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="test:scope-pr")
        self.git_mapping = GitMapping.objects.create(
            owner="test", repo="repo", branch="main", project=self.project
        )
        self.author = User.objects.create(
            username="author_scope", username_lower="author_scope", account_type=User.AccountType.HUMAN
        )
        self.reviewer = User.objects.create(
            username="reviewer_scope", username_lower="reviewer_scope", account_type=User.AccountType.HUMAN
        )

    def _make_pr(self, number=1):
        return PullRequest.objects.create(
            target=self.git_mapping,
            number=number,
            author=self.author,
            source_owner="dev",
            source_repo="repo",
            source_branch="feat",
        )

    def _make_config(self, scope):
        return ReviewConfig.objects.create(
            project=self.project,
            type=ReviewConfig.ConfigType.PROJECT,
            reviewer_user=self.reviewer,
            scope=scope,
        )

    def test_skipped_when_no_file_in_scope(self):
        from pull_requests.api import provision_reviews_for_revision

        scope = ReviewScope.objects.create(name="code", include_globs=["src/*.py"], exclude_globs=[])
        self._make_config(scope)
        pr = self._make_pr()
        rev = PullRequestRevision.objects.create(
            pull_request=pr, revision_number=1, head_sha="1111", base_sha="0000", fingerprint="fp1", is_draft=False
        )
        with patch("pull_requests.models.PullRequestRevision.get_changed_files", return_value={"docs/readme.md"}):
            reviews = provision_reviews_for_revision(rev)
        self.assertEqual(len(reviews), 1)
        self.assertEqual(reviews[0].state, PullRequestReview.State.SKIPPED)
        self.assertFalse(reviews[0].is_inherited)
        self.assertEqual(reviews[0].scope, scope)

    def test_pending_on_first_touch_in_scope(self):
        from pull_requests.api import provision_reviews_for_revision

        scope = ReviewScope.objects.create(name="code", include_globs=["src/*.py"], exclude_globs=[])
        self._make_config(scope)
        pr = self._make_pr()
        rev = PullRequestRevision.objects.create(
            pull_request=pr, revision_number=1, head_sha="1111", base_sha="0000", fingerprint="fp1", is_draft=False
        )
        with patch("pull_requests.models.PullRequestRevision.get_changed_files", return_value={"src/main.py"}):
            reviews = provision_reviews_for_revision(rev)
        self.assertEqual(len(reviews), 1)
        self.assertEqual(reviews[0].state, PullRequestReview.State.PENDING)
        self.assertFalse(reviews[0].is_inherited)

    def test_inherited_when_scoped_files_unchanged(self):
        from pull_requests.api import provision_reviews_for_revision

        scope = ReviewScope.objects.create(name="code", include_globs=["src/*.py"], exclude_globs=[])
        self._make_config(scope)
        pr = self._make_pr()

        rev1 = PullRequestRevision.objects.create(
            pull_request=pr, revision_number=1, head_sha="1111", base_sha="0000", fingerprint="fp1", is_draft=False
        )
        with patch("pull_requests.models.PullRequestRevision.get_changed_files", return_value={"src/main.py"}):
            provision_reviews_for_revision(rev1)
        rev1_review = rev1.reviews.first()
        self.assertEqual(rev1_review.state, PullRequestReview.State.PENDING)

        # rev2 still touches src/main.py cumulatively, but only docs changed between rev1 and rev2.
        rev2 = PullRequestRevision.objects.create(
            pull_request=pr, revision_number=2, head_sha="2222", base_sha="0000", fingerprint="fp2", is_draft=False
        )
        with patch("pull_requests.models.PullRequestRevision.get_changed_files", return_value={"src/main.py", "docs/readme.md"}), \
             patch("pull_requests.models.PullRequestRevision.get_inter_revision_changed_files", return_value={"docs/readme.md"}):
            provision_reviews_for_revision(rev2)
        rev2_review = rev2.reviews.first()
        self.assertTrue(rev2_review.is_inherited)
        self.assertEqual(rev2_review.state, rev1_review.state)
        self.assertEqual(rev2_review.scope, scope)

    def test_pending_when_scoped_file_changed(self):
        from pull_requests.api import provision_reviews_for_revision

        scope = ReviewScope.objects.create(name="code", include_globs=["src/*.py"], exclude_globs=[])
        self._make_config(scope)
        pr = self._make_pr()

        rev1 = PullRequestRevision.objects.create(
            pull_request=pr, revision_number=1, head_sha="1111", base_sha="0000", fingerprint="fp1", is_draft=False
        )
        with patch("pull_requests.models.PullRequestRevision.get_changed_files", return_value={"src/main.py"}):
            provision_reviews_for_revision(rev1)

        # A new src file changed between rev1 and rev2 -> scoped file changed -> fresh PENDING.
        rev2 = PullRequestRevision.objects.create(
            pull_request=pr, revision_number=2, head_sha="2222", base_sha="0000", fingerprint="fp2", is_draft=False
        )
        with patch("pull_requests.models.PullRequestRevision.get_changed_files", return_value={"src/main.py", "src/new.py"}), \
             patch("pull_requests.models.PullRequestRevision.get_inter_revision_changed_files", return_value={"src/new.py"}):
            provision_reviews_for_revision(rev2)
        rev2_review = rev2.reviews.first()
        self.assertFalse(rev2_review.is_inherited)
        self.assertEqual(rev2_review.state, PullRequestReview.State.PENDING)

    def test_pending_when_scope_identity_changed(self):
        from pull_requests.api import provision_reviews_for_revision

        scope_a = ReviewScope.objects.create(name="code", include_globs=["src/*.py"], exclude_globs=[])
        scope_b = ReviewScope.objects.create(name="docs", include_globs=["docs/*.md"], exclude_globs=[])
        config = self._make_config(scope_a)
        pr = self._make_pr()

        rev1 = PullRequestRevision.objects.create(
            pull_request=pr, revision_number=1, head_sha="1111", base_sha="0000", fingerprint="fp1", is_draft=False
        )
        with patch("pull_requests.models.PullRequestRevision.get_changed_files", return_value={"src/main.py"}):
            provision_reviews_for_revision(rev1)
        rev1_review = rev1.reviews.first()
        self.assertEqual(rev1_review.scope, scope_a)

        # The config's scope identity changes to scope_b before rev2 is provisioned.
        config.scope = scope_b
        config.save()

        rev2 = PullRequestRevision.objects.create(
            pull_request=pr, revision_number=2, head_sha="2222", base_sha="0000", fingerprint="fp2", is_draft=False
        )
        with patch("pull_requests.models.PullRequestRevision.get_changed_files", return_value={"docs/readme.md"}), \
             patch("pull_requests.models.PullRequestRevision.get_inter_revision_changed_files", return_value=set()):
            provision_reviews_for_revision(rev2)
        rev2_review = rev2.reviews.first()
        # Different scope identity -> no inheritance, fresh PENDING under the new scope.
        self.assertFalse(rev2_review.is_inherited)
        self.assertEqual(rev2_review.state, PullRequestReview.State.PENDING)
        self.assertEqual(rev2_review.scope, scope_b)


class TestForwardPropagation(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="test:propagation")
        self.git_mapping = GitMapping.objects.create(
            owner="test", repo="repo", branch="main", project=self.project
        )
        self.author = User.objects.create(
            username="author_prop", username_lower="author_prop", account_type=User.AccountType.HUMAN
        )
        self.reviewer = User.objects.create(
            username="reviewer_prop", username_lower="reviewer_prop", account_type=User.AccountType.HUMAN
        )
        self.scope = ReviewScope.objects.create(name="code", include_globs=["src/*.py"], exclude_globs=[])
        self.pr = PullRequest.objects.create(
            target=self.git_mapping,
            number=1,
            author=self.author,
            source_owner="dev",
            source_repo="repo",
            source_branch="feat",
        )

    def _make_rev(self, number):
        return PullRequestRevision.objects.create(
            pull_request=self.pr,
            revision_number=number,
            head_sha=f"head{number}",
            base_sha="0000",
            fingerprint=f"fp{number}",
            is_draft=False,
        )

    def _make_review(self, rev, state, is_inherited, justification=None):
        return PullRequestReview.objects.create(
            revision=rev,
            reviewer_user=self.reviewer,
            scope=self.scope,
            state=state,
            is_inherited=is_inherited,
            justification=justification,
        )

    def test_propagation_cascades_and_stops_at_non_inherited(self):
        rev1 = self._make_rev(1)
        rev2 = self._make_rev(2)
        rev3 = self._make_rev(3)

        r1 = self._make_review(rev1, PullRequestReview.State.ACCEPTED, is_inherited=False)
        r2 = self._make_review(rev2, PullRequestReview.State.PENDING, is_inherited=True)
        r3 = self._make_review(rev3, PullRequestReview.State.PENDING, is_inherited=False)

        propagated = r1.propagate_decision()

        r2.refresh_from_db()
        r3.refresh_from_db()
        self.assertEqual(r2.state, PullRequestReview.State.ACCEPTED)  # propagated
        self.assertEqual(r3.state, PullRequestReview.State.PENDING)   # stopped at non-inherited
        self.assertEqual([r.revision_id for r in propagated], [rev2.id])

    def test_propagation_stops_at_first_non_inherited(self):
        rev1 = self._make_rev(1)
        rev2 = self._make_rev(2)
        rev3 = self._make_rev(3)

        r1 = self._make_review(
            rev1, PullRequestReview.State.REJECTED, is_inherited=False, justification="not acceptable"
        )
        r2 = self._make_review(rev2, PullRequestReview.State.PENDING, is_inherited=False)
        r3 = self._make_review(rev3, PullRequestReview.State.PENDING, is_inherited=True)

        propagated = r1.propagate_decision()

        r2.refresh_from_db()
        r3.refresh_from_db()
        # rev2 is not inherited -> propagation stops before it; rev3 never reached.
        self.assertEqual(r2.state, PullRequestReview.State.PENDING)
        self.assertEqual(r3.state, PullRequestReview.State.PENDING)
        self.assertEqual(propagated, [])

    def test_propagation_copies_actor_and_justification(self):
        actor = User.objects.create(
            username="actor_prop", username_lower="actor_prop", account_type=User.AccountType.HUMAN
        )
        rev1 = self._make_rev(1)
        rev2 = self._make_rev(2)

        r1 = self._make_review(rev1, PullRequestReview.State.REJECTED, is_inherited=False, justification="broken")
        r1.actor = actor
        r1.save()
        r2 = self._make_review(rev2, PullRequestReview.State.PENDING, is_inherited=True)

        r1.propagate_decision()

        r2.refresh_from_db()
        self.assertEqual(r2.state, PullRequestReview.State.REJECTED)
        self.assertEqual(r2.actor, actor)
        self.assertEqual(r2.justification, "broken")
