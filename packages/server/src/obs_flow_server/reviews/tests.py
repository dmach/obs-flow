import json
import msgspec
from unittest.mock import MagicMock, patch
from django.test import TransactionTestCase
from django_bolt.testing import TestClient

from accounts.models import User, Group
from core.models import Project
from reviews.models import ReviewConfig
from obs_flow_server.api import api

# Client and CLI imports for testing
from obs_flow_client import (
    Connection,
    add_review_config,
    remove_review_config,
    list_review_configs,
)
from obs_flow_common.messages import (
    ReviewConfigDTO,
    ReviewConfigAddRequest,
    ReviewConfigRemoveRequest,
    ReviewConfigListRequest,
    ReviewConfigAddResponse,
    ReviewConfigRemoveResponse,
    ReviewConfigListResponse,
)
from click.testing import CliRunner
from obs_flow_cli.commands.review_config import cli as review_config_cli


class TestReviewConfigEndpoints(TransactionTestCase):
    fixtures = ["opensuse_data.json"]

    def test_add_review_config_user(self):
        """Verify adding a review configuration for a user."""
        payload = {
            "project": "openSUSE:Factory",
            "type": "project",
            "reviewer": "darix",
            "depends_on": []
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
        self.assertEqual(config_detail["reviewer"], "darix")
        self.assertEqual(config_detail["depends_on"], [])

        # Verify database state
        self.assertTrue(ReviewConfig.objects.filter(
            project__name="openSUSE:Factory",
            type="project",
            reviewer_user__username="darix"
        ).exists())

    def test_add_review_config_group(self):
        """Verify adding a review configuration for a group."""
        payload = {
            "project": "openSUSE:Factory",
            "type": "staging",
            "reviewer": "@opensuse-review-team",
            "depends_on": []
        }
        with TestClient(api) as client:
            response = client.post(
                "/api/v1/review-config/add",
                content=json.dumps(payload),
            )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        config_detail = res_data["data"]
        self.assertEqual(config_detail["reviewer"], "@opensuse-review-team")
        self.assertEqual(config_detail["type"], "staging")

    def test_add_review_config_dynamic_role(self):
        """Verify adding a review configuration for a dynamic role."""
        payload = {
            "project": "openSUSE:Factory",
            "type": "package",
            "reviewer": "role:maintainer",
            "depends_on": []
        }
        with TestClient(api) as client:
            response = client.post(
                "/api/v1/review-config/add",
                content=json.dumps(payload),
            )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        config_detail = res_data["data"]
        self.assertEqual(config_detail["reviewer"], "role:maintainer")
        self.assertEqual(config_detail["type"], "package")

    def test_add_review_config_same_reviewer_different_type(self):
        """Verify that the same reviewer can have configurations for different types."""
        payload1 = {
            "project": "openSUSE:Factory",
            "type": "project",
            "reviewer": "darix",
            "depends_on": []
        }
        payload2 = {
            "project": "openSUSE:Factory",
            "type": "staging",
            "reviewer": "darix",
            "depends_on": []
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

    def test_add_review_config_duplicate_fails(self):
        """Verify that adding a duplicate review configuration for the same reviewer and type fails."""
        payload = {
            "project": "openSUSE:Factory",
            "type": "project",
            "reviewer": "darix",
            "depends_on": []
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

    def test_add_review_config_with_dependencies(self):
        """Verify adding a review configuration that depends on other configurations."""
        # First, add dependency configurations
        project = Project.objects.get(name="openSUSE:Factory")
        dep1 = ReviewConfig.objects.create(
            project=project,
            type="project",
            reviewer_user=User.objects.get(username="darix")
        )
        dep2 = ReviewConfig.objects.create(
            project=project,
            type="project",
            reviewer_group=Group.objects.get(name="opensuse-review-team")
        )

        # Add a configuration that depends on dep1 and dep2
        payload = {
            "project": "openSUSE:Factory",
            "type": "project",
            "reviewer": "dimstar",
            "depends_on": ["darix", "@opensuse-review-team"]
        }
        with TestClient(api) as client:
            response = client.post(
                "/api/v1/review-config/add",
                content=json.dumps(payload),
            )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        config_detail = res_data["data"]
        self.assertEqual(config_detail["reviewer"], "dimstar")
        self.assertCountEqual(config_detail["depends_on"], ["darix", "@opensuse-review-team"])

        # Verify database relations
        config = ReviewConfig.objects.get(reviewer_user__username="dimstar")
        self.assertCountEqual(config.depends_on.all(), [dep1, dep2])

    def test_add_fails_with_missing_dependency(self):
        """Verify that adding a configuration fails if a dependency does not exist."""
        payload = {
            "project": "openSUSE:Factory",
            "type": "project",
            "reviewer": "dimstar",
            "depends_on": ["nonexistent_user"]
        }
        with TestClient(api) as client:
            response = client.post(
                "/api/v1/review-config/add",
                content=json.dumps(payload),
            )
        self.assertEqual(response.status_code, 404)
        self.assertIn("User matching query does not exist", response.text)

    def test_list_review_configs(self):
        """Verify listing review configurations for a project."""
        project = Project.objects.get(name="openSUSE:Factory")
        ReviewConfig.objects.create(
            project=project,
            type="project",
            reviewer_user=User.objects.get(username="darix")
        )
        ReviewConfig.objects.create(
            project=project,
            type="package",
            reviewer_group=Group.objects.get(name="opensuse-review-team")
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
        self.assertEqual(len(configs), 2)

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
        self.assertEqual(configs[0]["reviewer"], "@opensuse-review-team")

    def test_remove_review_config_by_reviewer(self):
        """Verify removing a review configuration by reviewer string."""
        project = Project.objects.get(name="openSUSE:Factory")
        config = ReviewConfig.objects.create(
            project=project,
            type="project",
            reviewer_user=User.objects.get(username="darix")
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
        self.assertEqual(config_detail["reviewer"], "darix")
        self.assertFalse(ReviewConfig.objects.filter(
            project=project,
            type="project",
            reviewer_user__username="darix"
        ).exists())


class TestClientLibrary(TransactionTestCase):
    @patch.object(Connection, "post")
    def test_add_review_config_client(self, mock_post):
        """Verify client library add_review_config function."""
        dto = ReviewConfigDTO(
            id=1,
            project="openSUSE:Factory",
            type="project",
            reviewer="darix",
            depends_on=[]
        )
        response_payload = ReviewConfigAddResponse(data=dto)
        mock_post.return_value = msgspec.json.encode(response_payload)

        conn = Connection(base_url="http://localhost:8000")
        req = ReviewConfigAddRequest(
            project="openSUSE:Factory",
            type="project",
            reviewer="darix",
            depends_on=[]
        )
        res = add_review_config(conn, req)
        self.assertEqual(res.data.id, 1)
        self.assertEqual(res.data.reviewer, "darix")
        mock_post.assert_called_once_with("/api/v1/review-config/add", data=msgspec.json.encode(req))

    @patch.object(Connection, "post")
    def test_remove_review_config_client(self, mock_post):
        """Verify client library remove_review_config function."""
        dto = ReviewConfigDTO(
            id=1,
            project="openSUSE:Factory",
            type="project",
            reviewer="darix",
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
        res = remove_review_config(conn, req)
        self.assertEqual(res.data.id, 1)
        self.assertEqual(res.data.reviewer, "darix")
        mock_post.assert_called_once_with("/api/v1/review-config/remove", data=msgspec.json.encode(req))

    @patch.object(Connection, "post")
    def test_list_review_configs_client(self, mock_post):
        """Verify client library list_review_configs function."""
        dto = ReviewConfigDTO(
            id=1,
            project="openSUSE:Factory",
            type="project",
            reviewer="darix",
            depends_on=[]
        )
        response_payload = ReviewConfigListResponse(data=[dto])
        mock_post.return_value = msgspec.json.encode(response_payload)

        conn = Connection(base_url="http://localhost:8000")
        req = ReviewConfigListRequest(
            project="openSUSE:Factory",
            type="project"
        )
        res = list_review_configs(conn, req)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0].reviewer, "darix")
        mock_post.assert_called_once_with("/api/v1/review-config/list", data=msgspec.json.encode(req))


class TestCLIManagement(TransactionTestCase):
    @patch("obs_flow_client.add_review_config")
    def test_cli_add_review_config(self, mock_add):
        """Verify CLI review-config add command."""
        dto = ReviewConfigDTO(
            id=1,
            project="openSUSE:Factory",
            type="project",
            reviewer="darix",
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

    @patch("obs_flow_client.remove_review_config")
    def test_cli_remove_review_config(self, mock_remove):
        """Verify CLI review-config remove command."""
        dto = ReviewConfigDTO(
            id=1,
            project="openSUSE:Factory",
            type="project",
            reviewer="darix",
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

    @patch("obs_flow_client.list_review_configs")
    def test_cli_list_review_configs(self, mock_list):
        """Verify CLI review-config list command."""
        dto = ReviewConfigDTO(
            id=1,
            project="openSUSE:Factory",
            type="project",
            reviewer="darix",
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
