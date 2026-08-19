import json
from django.test import TransactionTestCase
from django_bolt.testing import TestClient

from core.models import Project, Package, GitMapping
from obs_flow_server.api import api


class TestGitMappingAPI(TransactionTestCase):
    def setUp(self):
        # Create some initial data
        self.project = Project.objects.create(name="openSUSE:Factory")
        self.package = Package.objects.create(project=self.project, name="osc")

    def test_list_git_mappings_empty(self):
        with TestClient(api) as client:
            response = client.post("/api/v1/git-mapping/list", content="{}")
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertEqual(res_data["mappings"], [])

    def test_add_git_mapping_project(self):
        payload = {
            "owner": "openSUSE",
            "repo": "osc",
            "branch": "master",
            "project": "openSUSE:Factory",
        }
        with TestClient(api) as client:
            response = client.post("/api/v1/git-mapping/add", content=json.dumps(payload))
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        mapping_data = res_data["mapping"]
        self.assertEqual(mapping_data["owner"], "openSUSE")
        self.assertEqual(mapping_data["repo"], "osc")
        self.assertEqual(mapping_data["branch"], "master")
        self.assertEqual(mapping_data["project"], "openSUSE:Factory")
        self.assertIsNone(mapping_data["package"])

        # Verify DB
        self.assertTrue(GitMapping.objects.filter(owner="openSUSE", repo="osc", branch="master").exists())

    def test_add_git_mapping_package(self):
        payload = {
            "owner": "openSUSE",
            "repo": "osc",
            "branch": "master",
            "project": "openSUSE:Factory",
            "package": "osc",
        }
        with TestClient(api) as client:
            response = client.post("/api/v1/git-mapping/add", content=json.dumps(payload))
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        mapping_data = res_data["mapping"]
        self.assertEqual(mapping_data["owner"], "openSUSE")
        self.assertEqual(mapping_data["repo"], "osc")
        self.assertEqual(mapping_data["branch"], "master")
        self.assertEqual(mapping_data["project"], "openSUSE:Factory")
        self.assertEqual(mapping_data["package"], "osc")

        # Verify DB
        self.assertTrue(GitMapping.objects.filter(owner="openSUSE", repo="osc", branch="master").exists())

    def test_add_git_mapping_package_missing_project(self):
        payload = {
            "owner": "openSUSE",
            "repo": "osc",
            "branch": "master",
            "project": "NonExistentProject",
            "package": "osc",
        }
        with TestClient(api) as client:
            response = client.post("/api/v1/git-mapping/add", content=json.dumps(payload))
        self.assertEqual(response.status_code, 400)
        self.assertIn("Project 'NonExistentProject' does not exist", response.text)

    def test_add_git_mapping_missing_both(self):
        payload = {
            "owner": "openSUSE",
            "repo": "osc",
            "branch": "master",
        }
        with TestClient(api) as client:
            response = client.post("/api/v1/git-mapping/add", content=json.dumps(payload))
        self.assertEqual(response.status_code, 400)
        self.assertIn("Either project or package must be specified", response.text)

    def test_remove_git_mapping(self):
        mapping = GitMapping.objects.create(
            owner="openSUSE",
            repo="osc",
            branch="master",
            project=self.project,
        )
        payload = {"id": mapping.id}
        with TestClient(api) as client:
            response = client.post("/api/v1/git-mapping/remove", content=json.dumps(payload))
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertTrue(res_data["success"])

        # Verify DB
        self.assertFalse(GitMapping.objects.filter(id=mapping.id).exists())

    def test_remove_git_mapping_not_found(self):
        payload = {"id": 9999}
        with TestClient(api) as client:
            response = client.post("/api/v1/git-mapping/remove", content=json.dumps(payload))
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertFalse(res_data["success"])

    def test_edit_git_mapping(self):
        mapping = GitMapping.objects.create(
            owner="openSUSE",
            repo="osc",
            branch="master",
            project=self.project,
        )
        payload = {
            "id": mapping.id,
            "branch": "develop",
            "project": "openSUSE:Factory",
            "package": "osc",
        }
        with TestClient(api) as client:
            response = client.post("/api/v1/git-mapping/edit", content=json.dumps(payload))
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        mapping_data = res_data["mapping"]
        self.assertEqual(mapping_data["branch"], "develop")
        self.assertEqual(mapping_data["project"], "openSUSE:Factory")
        self.assertEqual(mapping_data["package"], "osc")

        # Verify DB
        mapping.refresh_from_db()
        self.assertEqual(mapping.branch, "develop")
        self.assertIsNone(mapping.project)
        self.assertEqual(mapping.package, self.package)
