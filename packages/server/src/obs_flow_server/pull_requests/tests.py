import json
from unittest.mock import MagicMock, patch
from django.test import TransactionTestCase, override_settings
from django_bolt.testing import TestClient

from accounts.models import User
from core.models import Project, GitMapping
from pull_requests.models import PullRequest, PullRequestRevision
from obs_flow_server.api import api


class TestPRSyncEndpoint(TransactionTestCase):
    fixtures = ["opensuse_data.json"]

    def test_show_review_endpoint(self):
        """Verify that show_review_endpoint works."""
        payload = {
            "pull_request_id": "openSUSE/osc#1234",
            "reviewer": "darix"
        }
        with TestClient(api) as client:
            response = client.post(
                "/api/v1/pr_review/show",
                content=json.dumps(payload),
            )
        self.assertEqual(response.status_code, 200)

    @override_settings(GITEA_URL=None, GITEA_TOKEN=None)
    def test_sync_fails_without_settings(self):
        """Verify that the endpoint fails if GITEA_URL or GITEA_TOKEN is not set."""
        payload = {
            "owner": "suse",
            "repo": "obs-flow",
            "number": 123
        }
        with TestClient(api) as client:
            response = client.post(
                "/api/v1/pr/sync",
                content=json.dumps(payload),
            )
        self.assertEqual(response.status_code, 500)
        self.assertIn("GITEA_URL and GITEA_TOKEN must be configured", response.text)

    @override_settings(GITEA_URL="https://gitea.example.com", GITEA_TOKEN="secret-token")
    @patch("urllib.request.urlopen")
    def test_sync_creates_new_pr(self, mock_urlopen):
        """Verify that syncing a non-existent PR creates it and its author/project/revision."""
        # Mock Gitea response
        mock_response = MagicMock()
        gitea_data = {
            "title": "Fix some bugs",
            "draft": False,
            "mergeable": True,
            "state": "open",
            "user": {"login": "john_doe"},
            "head": {
                "sha": "1111111111111111111111111111111111111111",
                "ref": "bugfix",
                "repo": {
                    "owner": {"login": "john_doe"},
                    "name": "obs-flow"
                }
            },
            "base": {
                "sha": "0000000000000000000000000000000000000000"
            }
        }
        mock_response.read.return_value = json.dumps(gitea_data).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        payload = {
            "owner": "suse",
            "repo": "obs-flow",
            "number": 123
        }
        with TestClient(api) as client:
            response = client.post(
                "/api/v1/pr/sync",
                content=json.dumps(payload),
            )
        if response.status_code != 200:
            print("RESPONSE TEXT:", response.text)
        self.assertEqual(response.status_code, 200)

        res_data = response.json()
        pr_detail = res_data["pull_request"]
        self.assertEqual(pr_detail["id"], "suse/obs-flow#123")
        self.assertEqual(pr_detail["title"], "Fix some bugs")
        self.assertEqual(pr_detail["state"], "open")
        self.assertEqual(pr_detail["is_draft"], False)
        self.assertEqual(pr_detail["is_mergeable"], True)
        self.assertEqual(pr_detail["author"], "john_doe")
        self.assertEqual(pr_detail["latest_revision"], 1)
        self.assertEqual(pr_detail["head_sha"], "1111111111111111111111111111111111111111")

        # Verify DB state
        self.assertTrue(User.objects.filter(username="john_doe").exists())
        self.assertTrue(Project.objects.filter(name="suse:obs-flow").exists())
        self.assertTrue(GitMapping.objects.filter(owner="suse", repo="obs-flow").exists())
        self.assertTrue(PullRequest.objects.filter(number=123).exists())
        self.assertTrue(PullRequestRevision.objects.filter(revision_number=1).exists())

    @override_settings(GITEA_URL="https://gitea.example.com", GITEA_TOKEN="secret-token")
    @patch("urllib.request.urlopen")
    def test_sync_updates_existing_pr_and_creates_revision(self, mock_urlopen):
        """Verify that syncing an existing PR updates it and creates a new revision if SHA changed."""
        # Create initial DB state
        project = Project.objects.create(name="suse:obs-flow")
        git_mapping = GitMapping.objects.create(owner="suse", repo="obs-flow", branch="main", project=project)
        author = User.objects.create(username="john_doe", username_lower="john_doe", account_type=User.AccountType.HUMAN)
        pr = PullRequest.objects.create(
            target=git_mapping,
            number=123,
            author=author,
            title="Old Title",
            is_draft=True,
            is_mergeable=False,
            state=PullRequest.State.OPEN,
            source_owner="john_doe",
            source_repo="obs-flow",
            source_branch="bugfix"
        )
        PullRequestRevision.objects.create(
            pull_request=pr,
            revision_number=1,
            head_sha="1111111111111111111111111111111111111111",
            base_sha="0000000000000000000000000000000000000000"
        )

        from reviews.models import ReviewConfig
        reviewer_user = User.objects.create(username="reviewer1", username_lower="reviewer1", account_type=User.AccountType.HUMAN)
        ReviewConfig.objects.create(
            project=project,
            type=ReviewConfig.ConfigType.PROJECT,
            reviewer_user=reviewer_user
        )

        # Mock Gitea response with updated title, mergeable, and new head SHA
        mock_response = MagicMock()
        gitea_data = {
            "title": "New Title",
            "draft": False,
            "mergeable": True,
            "state": "open",
            "user": {"login": "john_doe"},
            "head": {
                "sha": "2222222222222222222222222222222222222222",
                "ref": "bugfix",
                "repo": {
                    "owner": {"login": "john_doe"},
                    "name": "obs-flow"
                }
            },
            "base": {
                "sha": "0000000000000000000000000000000000000000"
            }
        }
        mock_response.read.return_value = json.dumps(gitea_data).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        payload = {
            "owner": "suse",
            "repo": "obs-flow",
            "number": 123
        }
        with TestClient(api) as client:
            response = client.post(
                "/api/v1/pr/sync",
                content=json.dumps(payload),
            )
        if response.status_code != 200:
            print("RESPONSE TEXT:", response.text)
        self.assertEqual(response.status_code, 200)

        res_data = response.json()
        pr_detail = res_data["pull_request"]
        self.assertEqual(pr_detail["title"], "New Title")
        self.assertEqual(pr_detail["is_draft"], False)
        self.assertEqual(pr_detail["is_mergeable"], True)
        self.assertEqual(pr_detail["latest_revision"], 2)
        self.assertEqual(pr_detail["head_sha"], "2222222222222222222222222222222222222222")

        # Verify DB state
        pr.refresh_from_db()
        self.assertEqual(pr.title, "New Title")
        self.assertEqual(pr.is_draft, False)
        self.assertEqual(pr.is_mergeable, True)
        
        # Verify both revisions exist
        self.assertEqual(pr.revisions.count(), 2)

        # Verify review was created for the new revision
        latest_revision = pr.revisions.get(revision_number=2)
        self.assertEqual(latest_revision.reviews.count(), 1)
        review = latest_revision.reviews.first()
        self.assertEqual(review.reviewer_user, reviewer_user)
        from pull_requests.models import PullRequestReview
        self.assertEqual(review.state, PullRequestReview.State.PENDING)

    @override_settings(GITEA_URL="https://gitea.example.com", GITEA_TOKEN="secret-token")
    @patch("urllib.request.urlopen")
    def test_sync_creates_revision_for_package_pr_and_creates_reviews(self, mock_urlopen):
        """Verify that syncing a package PR creates reviews based on ReviewConfig for package type."""
        from core.models import Package
        project = Project.objects.create(name="suse:obs-flow")
        package = Package.objects.create(project=project, name="my-package")
        git_mapping = GitMapping.objects.create(owner="suse", repo="obs-flow", branch="main", package=package)
        author = User.objects.create(username="john_doe", username_lower="john_doe", account_type=User.AccountType.HUMAN)
        pr = PullRequest.objects.create(
            target=git_mapping,
            number=123,
            author=author,
            title="Old Title",
            is_draft=True,
            is_mergeable=False,
            state=PullRequest.State.OPEN,
            source_owner="john_doe",
            source_repo="obs-flow",
            source_branch="bugfix"
        )
        PullRequestRevision.objects.create(
            pull_request=pr,
            revision_number=1,
            head_sha="1111111111111111111111111111111111111111",
            base_sha="0000000000000000000000000000000000000000"
        )

        from reviews.models import ReviewConfig
        reviewer_user = User.objects.create(username="reviewer1", username_lower="reviewer1", account_type=User.AccountType.HUMAN)
        # Create a config for package type
        ReviewConfig.objects.create(
            project=project,
            type=ReviewConfig.ConfigType.PACKAGE,
            reviewer_user=reviewer_user
        )
        # Create a config for project type (should NOT be used)
        reviewer_user_project = User.objects.create(username="reviewer_project", username_lower="reviewer_project", account_type=User.AccountType.HUMAN)
        ReviewConfig.objects.create(
            project=project,
            type=ReviewConfig.ConfigType.PROJECT,
            reviewer_user=reviewer_user_project
        )

        # Mock Gitea response with updated title, mergeable, and new head SHA
        mock_response = MagicMock()
        gitea_data = {
            "title": "New Title",
            "draft": False,
            "mergeable": True,
            "state": "open",
            "user": {"login": "john_doe"},
            "head": {
                "sha": "2222222222222222222222222222222222222222",
                "ref": "bugfix",
                "repo": {
                    "owner": {"login": "john_doe"},
                    "name": "obs-flow"
                }
            },
            "base": {
                "sha": "0000000000000000000000000000000000000000"
            }
        }
        mock_response.read.return_value = json.dumps(gitea_data).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        payload = {
            "owner": "suse",
            "repo": "obs-flow",
            "number": 123
        }
        with TestClient(api) as client:
            response = client.post(
                "/api/v1/pr/sync",
                content=json.dumps(payload),
            )
        self.assertEqual(response.status_code, 200)

        # Verify review was created for the new revision and it is the package config, not project config
        latest_revision = pr.revisions.get(revision_number=2)
        self.assertEqual(latest_revision.reviews.count(), 1)
        review = latest_revision.reviews.first()
        self.assertEqual(review.reviewer_user, reviewer_user)
        from pull_requests.models import PullRequestReview
        self.assertEqual(review.state, PullRequestReview.State.PENDING)
