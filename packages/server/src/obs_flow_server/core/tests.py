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


class TestSyncGiteaCommand(TransactionTestCase):
    def test_save_to_db_preserves_pull_requests(self):
        from accounts.models import User
        from pull_requests.models import PullRequest
        from core.management.commands.sync_gitea import Command

        user = User.objects.create(username="testuser", username_lower="testuser")
        project1 = Project.objects.create(name="proj1")
        project2 = Project.objects.create(name="proj2")

        # Create a GitMapping for proj1
        mapping = GitMapping.objects.create(
            owner="org", repo="repo", branch="main", project=project1
        )

        # Create a PR for this mapping
        pr = PullRequest.objects.create(
            target=mapping,
            number=1,
            author=user,
            source_owner="org",
            source_repo="repo",
            source_branch="feat",
        )

        self.assertEqual(PullRequest.objects.count(), 1)

        # Run save_to_db to move the mapping to proj2
        cmd = Command()
        cmd.save_to_db(
            obs_project="proj2",
            org="org",
            repo="repo",
            branch="main",
            package_sha={},
            submodule_branches={},
        )

        # Verify that the PR is preserved and the mapping is now associated with proj2
        self.assertEqual(PullRequest.objects.count(), 1)
        mapping.refresh_from_db()
        self.assertEqual(mapping.project, project2)
        self.assertIsNone(mapping.package)

    def test_save_to_db_preserves_pull_requests_package(self):
        from accounts.models import User
        from pull_requests.models import PullRequest
        from core.management.commands.sync_gitea import Command

        user = User.objects.create(username="testuser", username_lower="testuser")
        project = Project.objects.create(name="proj1")
        package1 = Package.objects.create(project=project, name="pkg1")
        package2 = Package.objects.create(project=project, name="pkg2")

        # Create a GitMapping for pkg1
        mapping = GitMapping.objects.create(
            owner="org", repo="repo", branch="main", package=package1
        )

        # Create a PR for this mapping
        pr = PullRequest.objects.create(
            target=mapping,
            number=1,
            author=user,
            source_owner="org",
            source_repo="repo",
            source_branch="feat",
        )

        self.assertEqual(PullRequest.objects.count(), 1)

        # Run save_to_db to move the mapping to pkg2
        cmd = Command()
        cmd.save_to_db(
            obs_project="proj1",
            org="org_proj",
            repo="repo_proj",
            branch="main",
            package_sha={"pkg2": "some-sha"},
            submodule_branches={"pkg2": ("host", "org", "repo", "main")},
        )

        # Verify that the PR is preserved and the mapping is now associated with pkg2
        self.assertEqual(PullRequest.objects.count(), 1)
        mapping.refresh_from_db()
        self.assertEqual(mapping.package, package2)
        self.assertIsNone(mapping.project)


class TestGitMappingViews(TransactionTestCase):
    def test_git_mapping_list_filtering_and_pagination(self):
        """Verify that the git mapping list page correctly filters and paginates git mappings."""
        from django.test import Client

        # Create 205 git mappings to test pagination (page size is 200)
        for i in range(1, 206):
            GitMapping.objects.create(
                owner="suse" if i % 2 == 0 else "openSUSE",
                repo=f"repo-{i}",
                branch=f"branch-{i}",
                project=Project.objects.create(name=f"proj-{i}")
            )

        client = Client()

        # 1. Test pagination (page 1 should have 200 items, page 2 should have 5 items)
        response = client.get("/git-mappings/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Page 1 of 2")
        self.assertContains(response, "repo-205")

        response = client.get("/git-mappings/?page=2")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Page 2 of 2")
        self.assertContains(response, "repo-1")

        # 2. Test filtering by owner
        response = client.get("/git-mappings/?owner=suse&owner_exact=on")
        self.assertEqual(response.status_code, 200)
        # 102 mappings should fit on 1 page
        self.assertNotContains(response, "Page 1 of 2")

    def test_git_mapping_list_filtering_by_project_or_package_project(self):
        """Verify that filtering by project name correctly matches both direct projects and projects linked via a package."""
        from django.test import Client

        # Mapping 1: Direct project
        proj1 = Project.objects.create(name="suse:direct")
        GitMapping.objects.create(owner="org", repo="repo1", branch="main", project=proj1)

        # Mapping 2: Via package
        proj2 = Project.objects.create(name="suse:indirect")
        pkg2 = Package.objects.create(project=proj2, name="mypkg")
        GitMapping.objects.create(owner="org", repo="repo2", branch="main", package=pkg2)

        client = Client()

        # Filter by direct project
        response = client.get("/git-mappings/?project=suse:direct")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "repo1")
        self.assertNotContains(response, "repo2")

        # Filter by indirect project
        response = client.get("/git-mappings/?project=suse:indirect")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "repo2")
        self.assertNotContains(response, "repo1")

        # Filter by common substring
        response = client.get("/git-mappings/?project=suse:")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "repo1")
        self.assertContains(response, "repo2")



