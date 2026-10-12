import json
from unittest.mock import MagicMock, patch
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from django_bolt.testing import TestClient

from accounts.models import User
from core.models import Project, GitMapping
from pull_requests.models import PullRequest, PullRequestRevision, PullRequestReview
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

    def test_pull_request_target_project_property(self):
        pr = PullRequest.objects.get(number=1234)
        project = Project.objects.get(name="openSUSE:Factory")
        self.assertEqual(pr.target_project, project)

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
        """Verify that syncing a non-existent PR creates it and its author/revision."""
        # Create Project and GitMapping first
        project = Project.objects.create(name="suse:obs-flow")
        GitMapping.objects.create(owner="suse", repo="obs-flow", branch="main", project=project)

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
                "sha": "0000000000000000000000000000000000000000",
                "ref": "main"
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
        self.assertEqual(pr_detail["is_draft"], True)
        self.assertEqual(pr_detail["is_mergeable"], True)
        self.assertEqual(pr_detail["author"], {
            "username": "john_doe",
            "full_name": None,
            "email": None,
            "is_active": True,
        })
        self.assertEqual(pr_detail["latest_revision"], 1)
        self.assertEqual(pr_detail["head_sha"], "1111111111111111111111111111111111111111")

        # Verify DB state
        self.assertTrue(User.objects.filter(username="john_doe").exists())
        self.assertTrue(Project.objects.filter(name="suse:obs-flow").exists())
        self.assertTrue(GitMapping.objects.filter(owner="suse", repo="obs-flow").exists())
        pr = PullRequest.objects.get(number=123)
        self.assertTrue(pr.is_draft)
        latest_rev = pr.revisions.first()
        self.assertTrue(latest_rev.is_draft)
        self.assertIsNotNone(latest_rev.draft_expires_at)
        self.assertEqual(latest_rev.reviews.count(), 0)
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
            base_sha="0000000000000000000000000000000000000000",
            is_draft=True,
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
                "sha": "0000000000000000000000000000000000000000",
                "ref": "main"
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
        self.assertEqual(pr_detail["is_draft"], True)
        self.assertEqual(pr_detail["is_mergeable"], True)
        self.assertEqual(pr_detail["latest_revision"], 2)
        self.assertEqual(pr_detail["head_sha"], "2222222222222222222222222222222222222222")

        # Verify DB state
        pr.refresh_from_db()
        self.assertEqual(pr.title, "New Title")
        self.assertEqual(pr.is_draft, True)
        self.assertEqual(pr.is_mergeable, True)

        # Verify both revisions exist
        self.assertEqual(pr.revisions.count(), 2)

        # Verify review is NOT created initially while in debounce draft mode
        latest_revision = pr.revisions.get(revision_number=2)
        from pull_requests.fingerprint import PRRevisionPayload
        expected_fp = PRRevisionPayload(
            head_sha="2222222222222222222222222222222222222222",
            base_sha="0000000000000000000000000000000000000000",
            target_branch="main"
        ).compute_fingerprint()
        self.assertEqual(latest_revision.fingerprint, expected_fp)
        self.assertTrue(latest_revision.is_draft)
        self.assertIsNotNone(latest_revision.draft_expires_at)
        self.assertEqual(latest_revision.reviews.count(), 0)

        # Transition out of draft mode and verify reviews are now created
        from pull_requests.api import mark_ready_for_review
        mark_ready_for_review(latest_revision)
        pr.refresh_from_db()
        self.assertFalse(pr.is_draft)
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
            base_sha="0000000000000000000000000000000000000000",
            is_draft=True,
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
                "sha": "0000000000000000000000000000000000000000",
                "ref": "main"
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

        # Verify revision was created in draft mode and no reviews yet
        latest_revision = pr.revisions.get(revision_number=2)
        self.assertTrue(latest_revision.is_draft)
        self.assertEqual(latest_revision.reviews.count(), 0)

        # Transition out of draft mode and verify review was created for the new revision and it is the package config, not project config
        from pull_requests.api import mark_ready_for_review
        mark_ready_for_review(latest_revision)
        self.assertEqual(latest_revision.reviews.count(), 1)
        review = latest_revision.reviews.first()
        self.assertEqual(review.reviewer_user, reviewer_user)
        from pull_requests.models import PullRequestReview
        self.assertEqual(review.state, PullRequestReview.State.PENDING)

    @override_settings(GITEA_URL="https://gitea.example.com", GITEA_TOKEN="secret-token")
    @patch("urllib.request.urlopen")
    def test_sync_rebase_creates_new_revision(self, mock_urlopen):
        """Verify that rebasing (head SHA unchanged, but base SHA changed) creates a new revision."""
        project = Project.objects.create(name="suse:rebase-test")
        git_mapping = GitMapping.objects.create(owner="suse", repo="rebase-repo", branch="main", project=project)
        author = User.objects.create(username="rebase_user", username_lower="rebase_user", account_type=User.AccountType.HUMAN)
        pr = PullRequest.objects.create(
            target=git_mapping,
            number=999,
            author=author,
            title="Rebase PR",
            is_mergeable=True,
            state=PullRequest.State.OPEN,
            source_owner="rebase_user",
            source_repo="rebase-repo",
            source_branch="feat"
        )
        from pull_requests.fingerprint import PRRevisionPayload
        fp1 = PRRevisionPayload(
            head_sha="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            base_sha="1111111111111111111111111111111111111111",
            target_branch="main"
        ).compute_fingerprint()
        PullRequestRevision.objects.create(
            pull_request=pr,
            revision_number=1,
            head_sha="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            base_sha="1111111111111111111111111111111111111111",
            fingerprint=fp1
        )

        # Mock Gitea response where head is still "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", but base changed to "2222222222222222222222222222222222222222"
        mock_response = MagicMock()
        gitea_data = {
            "title": "Rebase PR",
            "draft": False,
            "mergeable": True,
            "state": "open",
            "user": {"login": "rebase_user"},
            "head": {
                "sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "ref": "feat",
                "repo": {
                    "owner": {"login": "rebase_user"},
                    "name": "rebase-repo"
                }
            },
            "base": {
                "sha": "2222222222222222222222222222222222222222",
                "ref": "main"
            }
        }
        mock_response.read.return_value = json.dumps(gitea_data).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        payload = {
            "owner": "suse",
            "repo": "rebase-repo",
            "number": 999
        }
        with TestClient(api) as client:
            response = client.post(
                "/api/v1/pr/sync",
                content=json.dumps(payload),
            )
        self.assertEqual(response.status_code, 200)

        # Verify a new revision was created despite head SHA being identical!
        self.assertEqual(pr.revisions.count(), 2)
        rev2 = pr.revisions.get(revision_number=2)
        self.assertEqual(rev2.head_sha, "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        self.assertEqual(rev2.base_sha, "2222222222222222222222222222222222222222")
        fp2 = PRRevisionPayload(
            head_sha="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            base_sha="2222222222222222222222222222222222222222",
            target_branch="main"
        ).compute_fingerprint()
        self.assertEqual(rev2.fingerprint, fp2)
        self.assertNotEqual(rev2.fingerprint, fp1)


class TestPRViews(TransactionTestCase):
    def test_pr_detail_view_with_package(self):
        """Verify that the PR detail page correctly renders the project name and package name when the target is a package."""
        from django.test import Client
        from core.models import Package

        project = Project.objects.create(name="suse:obs-flow")
        package = Package.objects.create(project=project, name="my-package")
        git_mapping = GitMapping.objects.create(owner="suse", repo="obs-flow", branch="main", package=package)
        author = User.objects.create(username="john_doe", username_lower="john_doe", account_type=User.AccountType.HUMAN)
        pr = PullRequest.objects.create(
            target=git_mapping,
            number=123,
            author=author,
            title="My PR",
            is_mergeable=True,
            state=PullRequest.State.OPEN,
            source_owner="john_doe",
            source_repo="obs-flow",
            source_branch="bugfix"
        )

        client = Client()
        response = client.get(f"/pull-requests/{pr.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "suse:obs-flow")
        self.assertContains(response, "my-package")

    def test_pr_list_filtering_and_pagination(self):
        """Verify that the PR list page correctly filters and paginates pull requests."""
        from django.test import Client
        from accounts.models import User, UserPreferences

        # Create a user with page_size=200 and log them in
        user = User.objects.create_user(username="testuser", password="password123", is_local_account=True)
        UserPreferences.objects.create(user=user, page_size=200)

        project = Project.objects.create(name="suse:obs-flow")
        git_mapping = GitMapping.objects.create(owner="suse", repo="obs-flow", branch="main", project=project)
        author1 = User.objects.create(username="john_doe", username_lower="john_doe", account_type=User.AccountType.HUMAN)
        author2 = User.objects.create(username="jane_doe", username_lower="jane_doe", account_type=User.AccountType.HUMAN)

        # Create 205 PRs to test pagination (page size is 200)
        for i in range(1, 206):
            PullRequest.objects.create(
                target=git_mapping,
                number=i,
                author=author1 if i % 2 == 0 else author2,
                title=f"PR {i}",
                is_mergeable=True,
                state=PullRequest.State.OPEN,
                source_owner="john_doe" if i % 2 == 0 else "jane_doe",
                source_repo="obs-flow",
                source_branch=f"bugfix-{i}"
            )

        client = Client()
        client.login(username="testuser", password="password123")

        # 1. Test pagination (page 1 should have 200 items, page 2 should have 5 items)
        response = client.get("/pull-requests/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Page 1 of 2")
        self.assertContains(response, "PR 205") # Ordered by -id, so PR 205 is on page 1

        response = client.get("/pull-requests/?page=2")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Page 2 of 2")
        self.assertContains(response, "PR 1")

        # 2. Test filtering by author (john_doe has 102 PRs, jane_doe has 103 PRs)
        response = client.get("/pull-requests/?author=john_doe")
        self.assertEqual(response.status_code, 200)
        # 102 PRs should fit on 1 page (no pagination links needed or page 1 of 1)
        self.assertNotContains(response, "Page 1 of 2")

        # 3. Test exact filtering by title
        response = client.get("/pull-requests/?title=PR 10&title_exact=on")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PR 10")
        self.assertNotContains(response, "PR 11")


class TestPRRevisionPayload(TestCase):
    def test_pr_revision_fingerprint(self):
        from pull_requests.fingerprint import PRRevisionPayload
        import hashlib

        payload = PRRevisionPayload(
            head_sha="head123",
            base_sha="base456",
            target_branch="main",
        )
        # Expected alphabetical JSON: {"base_sha":"base456","head_sha":"head123","target_branch":"main"}
        expected_json = b'{"base_sha":"base456","head_sha":"head123","target_branch":"main"}'
        self.assertEqual(payload._to_canonical_json(), expected_json)
        self.assertEqual(payload.compute_fingerprint(), hashlib.sha256(expected_json).hexdigest())


class TestPullRequestRevisionModel(TestCase):
    def test_revision_draft_fields_default_and_assignment(self):
        project = Project.objects.create(name="test:project")
        git_mapping = GitMapping.objects.create(owner="test", repo="repo", branch="main", project=project)
        author = User.objects.create(username="author1", username_lower="author1", account_type=User.AccountType.HUMAN)
        pr = PullRequest.objects.create(
            target=git_mapping,
            number=1,
            author=author,
            source_owner="author1",
            source_repo="repo",
            source_branch="feat",
        )

        # Default values
        rev1 = PullRequestRevision.objects.create(
            pull_request=pr,
            revision_number=1,
            head_sha="1111",
            base_sha="0000",
            fingerprint="fp1",
        )
        self.assertFalse(rev1.is_draft)
        self.assertIsNone(rev1.draft_expires_at)

        # Explicit draft values
        expiry = timezone.now()
        rev2 = PullRequestRevision.objects.create(
            pull_request=pr,
            revision_number=2,
            head_sha="2222",
            base_sha="0000",
            fingerprint="fp2",
            is_draft=True,
            draft_expires_at=expiry,
        )
        self.assertTrue(rev2.is_draft)
        self.assertEqual(rev2.draft_expires_at, expiry)


class TestPullRequestReviewProvisioning(TestCase):
    def test_provision_reviews_and_mark_ready_for_review(self):
        from reviews.models import ReviewConfig
        from pull_requests.api import provision_reviews_for_revision, mark_ready_for_review

        project = Project.objects.create(name="test:project")
        git_mapping = GitMapping.objects.create(owner="test", repo="repo", branch="main", project=project)
        author = User.objects.create(username="author1", username_lower="author1", account_type=User.AccountType.HUMAN)
        reviewer = User.objects.create(username="reviewer1", username_lower="reviewer1", account_type=User.AccountType.HUMAN)
        ReviewConfig.objects.create(
            project=project,
            type=ReviewConfig.ConfigType.PROJECT,
            reviewer_user=reviewer,
        )

        pr = PullRequest.objects.create(
            target=git_mapping,
            number=1,
            author=author,
            source_owner="author1",
            source_repo="repo",
            source_branch="feat",
        )
        rev = PullRequestRevision.objects.create(
            pull_request=pr,
            revision_number=1,
            head_sha="1111",
            base_sha="0000",
            fingerprint="fp1",
            is_draft=True,
            draft_expires_at=timezone.now(),
        )

        # Reviews should not exist initially
        self.assertEqual(rev.reviews.count(), 0)

        # Calling mark_ready_for_review clears draft and provisions reviews
        mark_ready_for_review(rev)
        rev.refresh_from_db()
        self.assertFalse(rev.is_draft)
        self.assertIsNone(rev.draft_expires_at)
        self.assertEqual(rev.reviews.count(), 1)
        self.assertEqual(rev.reviews.first().reviewer_user, reviewer)

        # Subsequent call does not duplicate reviews
        mark_ready_for_review(rev)
        self.assertEqual(rev.reviews.count(), 1)

    def test_provision_reviews_wires_dependencies(self):
        from reviews.models import ReviewConfig
        from pull_requests.api import provision_reviews_for_revision

        project = Project.objects.create(name="test:deps-project")
        git_mapping = GitMapping.objects.create(owner="test", repo="repo", branch="main", project=project)
        author = User.objects.create(username="author_dep", username_lower="author_dep", account_type=User.AccountType.HUMAN)
        rev1 = User.objects.create(username="reviewer_a", username_lower="reviewer_a", account_type=User.AccountType.HUMAN)
        rev2 = User.objects.create(username="reviewer_b", username_lower="reviewer_b", account_type=User.AccountType.HUMAN)

        cfg1 = ReviewConfig.objects.create(
            project=project,
            type=ReviewConfig.ConfigType.PROJECT,
            reviewer_user=rev1,
        )
        cfg2 = ReviewConfig.objects.create(
            project=project,
            type=ReviewConfig.ConfigType.PROJECT,
            reviewer_user=rev2,
        )
        cfg2.depends_on.add(cfg1)

        pr = PullRequest.objects.create(
            target=git_mapping,
            number=99,
            author=author,
            source_owner="author_dep",
            source_repo="repo",
            source_branch="feat",
        )
        rev = PullRequestRevision.objects.create(
            pull_request=pr,
            revision_number=1,
            head_sha="1111",
            base_sha="0000",
            fingerprint="fp1",
            is_draft=False,
            draft_expires_at=None,
        )

        reviews = provision_reviews_for_revision(rev)
        self.assertEqual(len(reviews), 2)

        review_a = rev.reviews.get(reviewer_user=rev1)
        review_b = rev.reviews.get(reviewer_user=rev2)

        self.assertIn(review_a, review_b.depends_on.all())
        self.assertEqual(review_a.depends_on.count(), 0)
        self.assertEqual(review_a.state, PullRequestReview.State.PENDING)
        self.assertEqual(review_b.state, PullRequestReview.State.WAITING)

    def test_cascading_unblocking_on_approval(self):
        from reviews.models import ReviewConfig
        from pull_requests.api import provision_reviews_for_revision

        project = Project.objects.create(name="test:cascade-pr")
        git_mapping = GitMapping.objects.create(owner="test", repo="repo", branch="main", project=project)
        author = User.objects.create(username="author_cas", username_lower="author_cas", account_type=User.AccountType.HUMAN)
        u1 = User.objects.create(username="rev_1", username_lower="rev_1", account_type=User.AccountType.HUMAN)
        u2 = User.objects.create(username="rev_2", username_lower="rev_2", account_type=User.AccountType.HUMAN)
        u3 = User.objects.create(username="rev_3", username_lower="rev_3", account_type=User.AccountType.HUMAN)

        cfg1 = ReviewConfig.objects.create(project=project, type=ReviewConfig.ConfigType.PROJECT, reviewer_user=u1)
        cfg2 = ReviewConfig.objects.create(project=project, type=ReviewConfig.ConfigType.PROJECT, reviewer_user=u2)
        cfg3 = ReviewConfig.objects.create(project=project, type=ReviewConfig.ConfigType.PROJECT, reviewer_user=u3)

        # cfg3 depends on BOTH cfg1 and cfg2
        cfg3.depends_on.add(cfg1, cfg2)

        pr = PullRequest.objects.create(
            target=git_mapping,
            number=101,
            author=author,
            source_owner="author_cas",
            source_repo="repo",
            source_branch="feat",
        )
        rev = PullRequestRevision.objects.create(
            pull_request=pr,
            revision_number=1,
            head_sha="1111",
            base_sha="0000",
            fingerprint="fp1",
            is_draft=False,
            draft_expires_at=None,
        )

        provision_reviews_for_revision(rev)

        r1 = rev.reviews.get(reviewer_user=u1)
        r2 = rev.reviews.get(reviewer_user=u2)
        r3 = rev.reviews.get(reviewer_user=u3)

        self.assertEqual(r1.state, PullRequestReview.State.PENDING)
        self.assertEqual(r2.state, PullRequestReview.State.PENDING)
        self.assertEqual(r3.state, PullRequestReview.State.WAITING)

        from accounts.helpers import generate_secure_token
        from accounts.models import Token
        raw_token, last_eight, token_hash = generate_secure_token()
        Token.objects.create(user=u1, token_hash=token_hash, last_eight=last_eight)
        auth_headers = {"Authorization": f"Bearer {raw_token}"}

        # Approve review 1 via API endpoint
        payload = {"pull_request_id": "test/repo#101", "reviewer": "rev_1"}
        with TestClient(api) as client:
            res = client.post("/api/v1/pr_review/approve", content=json.dumps(payload), headers=auth_headers)
        self.assertEqual(res.status_code, 200)

        r1.refresh_from_db()
        r2.refresh_from_db()
        r3.refresh_from_db()
        self.assertEqual(r1.state, PullRequestReview.State.ACCEPTED)
        self.assertEqual(r2.state, PullRequestReview.State.PENDING)
        # r3 is still WAITING because r2 is not resolved yet
        self.assertEqual(r3.state, PullRequestReview.State.WAITING)

        # Approve review 2 via API endpoint
        payload = {"pull_request_id": "test/repo#101", "reviewer": "rev_2"}
        with TestClient(api) as client:
            res = client.post("/api/v1/pr_review/approve", content=json.dumps(payload), headers=auth_headers)
        self.assertEqual(res.status_code, 200)

        r2.refresh_from_db()
        r3.refresh_from_db()
        self.assertEqual(r2.state, PullRequestReview.State.ACCEPTED)
        # All prerequisites resolved -> r3 cascades to PENDING!
        self.assertEqual(r3.state, PullRequestReview.State.PENDING)

    def test_early_approval_of_waiting_review(self):
        from reviews.models import ReviewConfig
        from pull_requests.api import provision_reviews_for_revision

        project = Project.objects.create(name="test:early-pr")
        git_mapping = GitMapping.objects.create(owner="test", repo="repo", branch="main", project=project)
        author = User.objects.create(username="author_early", username_lower="author_early", account_type=User.AccountType.HUMAN)
        u1 = User.objects.create(username="rev_early_1", username_lower="rev_early_1", account_type=User.AccountType.HUMAN)
        u2 = User.objects.create(username="rev_early_2", username_lower="rev_early_2", account_type=User.AccountType.HUMAN)

        cfg1 = ReviewConfig.objects.create(project=project, type=ReviewConfig.ConfigType.PROJECT, reviewer_user=u1)
        cfg2 = ReviewConfig.objects.create(project=project, type=ReviewConfig.ConfigType.PROJECT, reviewer_user=u2)
        cfg2.depends_on.add(cfg1)

        pr = PullRequest.objects.create(
            target=git_mapping,
            number=102,
            author=author,
            source_owner="author_early",
            source_repo="repo",
            source_branch="feat",
        )
        rev = PullRequestRevision.objects.create(
            pull_request=pr,
            revision_number=1,
            head_sha="1111",
            base_sha="0000",
            fingerprint="fp1",
            is_draft=False,
            draft_expires_at=None,
        )

        provision_reviews_for_revision(rev)

        r1 = rev.reviews.get(reviewer_user=u1)
        r2 = rev.reviews.get(reviewer_user=u2)

        self.assertEqual(r1.state, PullRequestReview.State.PENDING)
        self.assertEqual(r2.state, PullRequestReview.State.WAITING)

        from accounts.helpers import generate_secure_token
        from accounts.models import Token
        raw_token, last_eight, token_hash = generate_secure_token()
        Token.objects.create(user=u2, token_hash=token_hash, last_eight=last_eight)
        auth_headers = {"Authorization": f"Bearer {raw_token}"}

        # Early approval of r2 (which is in WAITING state)
        payload = {"pull_request_id": "test/repo#102", "reviewer": "rev_early_2"}
        with TestClient(api) as client:
            res = client.post("/api/v1/pr_review/approve", content=json.dumps(payload), headers=auth_headers)
        self.assertEqual(res.status_code, 200)

        r2.refresh_from_db()
        self.assertEqual(r2.state, PullRequestReview.State.ACCEPTED)



class TestPRSyncDebounceLifecycle(TransactionTestCase):
    @override_settings(GITEA_URL="https://gitea.example.com", GITEA_TOKEN="secret-token", DEBOUNCE_TIMEOUT_MINUTES=15)
    @patch("urllib.request.urlopen")
    def test_sync_manual_draft_pr_sets_no_expiry(self, mock_urlopen):
        project = Project.objects.create(name="suse:obs-flow")
        GitMapping.objects.create(owner="suse", repo="obs-flow", branch="main", project=project)

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "title": "Manual Draft PR",
            "draft": True,
            "mergeable": True,
            "state": "open",
            "user": {"login": "dev"},
            "head": {"sha": "1111", "ref": "feat", "repo": {"owner": {"login": "dev"}, "name": "obs-flow"}},
            "base": {"sha": "0000", "ref": "main"},
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with TestClient(api) as client:
            res = client.post("/api/v1/pr/sync", content=json.dumps({"owner": "suse", "repo": "obs-flow", "number": 1}))
        self.assertEqual(res.status_code, 200)

        pr = PullRequest.objects.get(number=1)
        rev = pr.revisions.first()
        self.assertTrue(rev.is_draft)
        self.assertIsNone(rev.draft_expires_at)
        self.assertEqual(rev.reviews.count(), 0)

    @override_settings(GITEA_URL="https://gitea.example.com", GITEA_TOKEN="secret-token", DEBOUNCE_TIMEOUT_MINUTES=15)
    @patch("urllib.request.urlopen")
    def test_sync_transition_manual_draft_to_published_without_new_push(self, mock_urlopen):
        project = Project.objects.create(name="suse:obs-flow")
        git_mapping = GitMapping.objects.create(owner="suse", repo="obs-flow", branch="main", project=project)
        author = User.objects.create(username="dev", username_lower="dev", account_type=User.AccountType.HUMAN)
        reviewer = User.objects.create(username="rev", username_lower="rev", account_type=User.AccountType.HUMAN)
        from reviews.models import ReviewConfig
        ReviewConfig.objects.create(project=project, type=ReviewConfig.ConfigType.PROJECT, reviewer_user=reviewer)

        pr = PullRequest.objects.create(
            target=git_mapping,
            number=1,
            author=author,
            source_owner="dev",
            source_repo="obs-flow",
            source_branch="feat",
        )
        from pull_requests.fingerprint import PRRevisionPayload
        fp = PRRevisionPayload(head_sha="1111", base_sha="0000", target_branch="main").compute_fingerprint()
        rev = PullRequestRevision.objects.create(
            pull_request=pr,
            revision_number=1,
            head_sha="1111",
            base_sha="0000",
            fingerprint=fp,
            is_draft=True,
            draft_expires_at=None,
        )

        # Now mock Gitea returning draft: False with the exact same head & base sha
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "title": "Published PR",
            "draft": False,
            "mergeable": True,
            "state": "open",
            "user": {"login": "dev"},
            "head": {"sha": "1111", "ref": "feat", "repo": {"owner": {"login": "dev"}, "name": "obs-flow"}},
            "base": {"sha": "0000", "ref": "main"},
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with TestClient(api) as client:
            res = client.post("/api/v1/pr/sync", content=json.dumps({"owner": "suse", "repo": "obs-flow", "number": 1}))
        self.assertEqual(res.status_code, 200)

        rev.refresh_from_db()
        self.assertFalse(rev.is_draft)
        self.assertIsNone(rev.draft_expires_at)
        self.assertEqual(rev.reviews.count(), 1)

    @override_settings(GITEA_URL="https://gitea.example.com", GITEA_TOKEN="secret-token", REVIEW_DEBOUNCE_MINUTES=0)
    @patch("urllib.request.urlopen")
    def test_sync_zero_debounce_publishes_immediately(self, mock_urlopen):
        project = Project.objects.create(name="suse:obs-flow")
        git_mapping = GitMapping.objects.create(owner="suse", repo="obs-flow", branch="main", project=project)
        reviewer = User.objects.create(username="rev", username_lower="rev", account_type=User.AccountType.HUMAN)
        from reviews.models import ReviewConfig
        ReviewConfig.objects.create(project=project, type=ReviewConfig.ConfigType.PROJECT, reviewer_user=reviewer)

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "title": "Zero Debounce PR",
            "draft": False,
            "mergeable": True,
            "state": "open",
            "user": {"login": "dev"},
            "head": {"sha": "1111", "ref": "feat", "repo": {"owner": {"login": "dev"}, "name": "obs-flow"}},
            "base": {"sha": "0000", "ref": "main"},
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with TestClient(api) as client:
            res = client.post("/api/v1/pr/sync", content=json.dumps({"owner": "suse", "repo": "obs-flow", "number": 1}))
        self.assertEqual(res.status_code, 200)

        pr = PullRequest.objects.get(number=1)
        rev = pr.revisions.first()
        self.assertFalse(rev.is_draft)
        self.assertIsNone(rev.draft_expires_at)
        self.assertFalse(pr.is_draft)
        self.assertEqual(rev.reviews.count(), 1)


class TestPRReadyForReviewEndpoint(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="test:project")
        self.git_mapping = GitMapping.objects.create(owner="suse", repo="obs-flow", branch="main", project=self.project)
        self.author = User.objects.create(username="dev", username_lower="dev", account_type=User.AccountType.HUMAN)
        self.reviewer = User.objects.create(username="rev", username_lower="rev", account_type=User.AccountType.HUMAN)
        from reviews.models import ReviewConfig
        ReviewConfig.objects.create(project=self.project, type=ReviewConfig.ConfigType.PROJECT, reviewer_user=self.reviewer)

        self.pr1 = PullRequest.objects.create(
            target=self.git_mapping,
            number=42,
            author=self.author,
            source_owner="dev",
            source_repo="obs-flow",
            source_branch="feat-1",
        )
        self.rev1 = PullRequestRevision.objects.create(
            pull_request=self.pr1,
            revision_number=1,
            head_sha="1111",
            base_sha="0000",
            fingerprint="fp1",
            is_draft=True,
            draft_expires_at=timezone.now(),
        )

        self.pr2 = PullRequest.objects.create(
            target=self.git_mapping,
            number=43,
            author=self.author,
            source_owner="dev",
            source_repo="obs-flow",
            source_branch="feat-2",
        )
        self.rev2 = PullRequestRevision.objects.create(
            pull_request=self.pr2,
            revision_number=1,
            head_sha="2222",
            base_sha="0000",
            fingerprint="fp2",
            is_draft=True,
            draft_expires_at=timezone.now(),
        )

    def test_ready_for_review_bulk_success(self):
        self.assertTrue(self.pr1.is_draft)
        self.assertTrue(self.pr2.is_draft)
        self.assertEqual(self.rev1.reviews.count(), 0)
        self.assertEqual(self.rev2.reviews.count(), 0)

        payload = {"pull_request_ids": ["suse/obs-flow#42", "suse/obs-flow#43"]}
        with TestClient(api) as client:
            response = client.post("/api/v1/pr/ready-for-review", content=json.dumps(payload))
        self.assertEqual(response.status_code, 200)

        res_data = response.json()
        self.assertEqual(len(res_data["pull_requests"]), 2)
        self.assertFalse(res_data["pull_requests"][0]["is_draft"])
        self.assertFalse(res_data["pull_requests"][1]["is_draft"])

        self.pr1.refresh_from_db()
        self.rev1.refresh_from_db()
        self.assertFalse(self.pr1.is_draft)
        self.assertFalse(self.rev1.is_draft)
        self.assertEqual(self.rev1.reviews.count(), 1)

        self.pr2.refresh_from_db()
        self.rev2.refresh_from_db()
        self.assertFalse(self.pr2.is_draft)
        self.assertFalse(self.rev2.is_draft)
        self.assertEqual(self.rev2.reviews.count(), 1)

    def test_ready_for_review_invalid_id(self):
        with TestClient(api) as client:
            response = client.post("/api/v1/pr/ready-for-review", content=json.dumps({"pull_request_ids": ["invalid"]}))
        self.assertEqual(response.status_code, 400)

    def test_ready_for_review_nonexistent_pr(self):
        with TestClient(api) as client:
            response = client.post("/api/v1/pr/ready-for-review", content=json.dumps({"pull_request_ids": ["suse/obs-flow#999"]}))
        self.assertEqual(response.status_code, 400)


class TestPRDraftWebViews(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="test:project")
        self.git_mapping = GitMapping.objects.create(owner="suse", repo="obs-flow", branch="main", project=self.project)
        self.author = User.objects.create(username="dev", username_lower="dev", account_type=User.AccountType.HUMAN)
        self.reviewer = User.objects.create(username="rev", username_lower="rev", account_type=User.AccountType.HUMAN)
        from reviews.models import ReviewConfig
        ReviewConfig.objects.create(project=self.project, type=ReviewConfig.ConfigType.PROJECT, reviewer_user=self.reviewer)

        self.pr = PullRequest.objects.create(
            target=self.git_mapping,
            number=42,
            author=self.author,
            source_owner="dev",
            source_repo="obs-flow",
            source_branch="feat",
        )
        self.rev = PullRequestRevision.objects.create(
            pull_request=self.pr,
            revision_number=1,
            head_sha="1111",
            base_sha="0000",
            fingerprint="fp1",
            is_draft=True,
            draft_expires_at=timezone.now() + timezone.timedelta(days=1),
        )

    def test_pr_detail_shows_countdown_and_ready_button(self):
        from django.test import Client
        client = Client()
        res = client.get(f"/pull-requests/{self.pr.id}/")
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "debouncing:")
        self.assertContains(res, "Ready for Review")

    def test_pr_ready_and_convert_to_draft_actions(self):
        from django.test import Client
        client = Client()

        # 1. Click Ready for Review
        res = client.post(f"/pull-requests/{self.pr.id}/ready-for-review/")
        self.assertRedirects(res, f"/pull-requests/{self.pr.id}/")
        self.pr.refresh_from_db()
        self.assertFalse(self.pr.is_draft)
        self.assertEqual(self.rev.reviews.count(), 1)

        # PR detail now shows Convert to Draft
        res = client.get(f"/pull-requests/{self.pr.id}/")
        self.assertContains(res, "Convert to Draft")
        self.assertNotContains(res, "debouncing:")

        # 2. Click Convert to Draft
        res = client.post(f"/pull-requests/{self.pr.id}/convert-to-draft/")
        self.assertRedirects(res, f"/pull-requests/{self.pr.id}/")
        self.pr.refresh_from_db()
        self.rev.refresh_from_db()
        self.assertTrue(self.pr.is_draft)
        self.assertIsNone(self.rev.draft_expires_at)
        # Reviews remain intact
        self.assertEqual(self.rev.reviews.count(), 1)

    def test_pr_htmx_actions_and_draft_status_expiration(self):
        from django.test import Client
        client = Client()

        # HTMX ready for review returns partial directly with OOB reviews section containing reviewer
        res = client.post(f"/pull-requests/{self.pr.id}/ready-for-review/", HTTP_HX_REQUEST="true")
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'id="pr-draft-section"')
        self.assertContains(res, "Convert to Draft")
        self.assertContains(res, 'id="pr-reviews-section"')
        self.assertContains(res, 'hx-swap-oob="true"')
        self.assertContains(res, "rev")

        # Set expired draft timer
        self.rev.is_draft = True
        self.rev.draft_expires_at = timezone.now() - timezone.timedelta(seconds=1)
        self.rev.save()

        # GET /draft-status/ auto-publishes expired draft and returns partial with Convert to Draft and updated reviews
        res = client.get(f"/pull-requests/{self.pr.id}/draft-status/", HTTP_HX_REQUEST="true")
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Convert to Draft")
        self.assertNotContains(res, "debouncing:")
        self.assertContains(res, 'id="pr-reviews-section"')
        self.assertContains(res, 'hx-swap-oob="true"')
        self.assertContains(res, "rev")
        self.rev.refresh_from_db()
        self.assertFalse(self.rev.is_draft)

    def test_pr_cancel_timeout_action(self):
        from django.test import Client
        client = Client()

        # Initially in debounce with draft_expires_at
        self.assertTrue(self.rev.is_draft)
        self.assertIsNotNone(self.rev.draft_expires_at)

        # Detail contains Cancel Timeout button
        res = client.get(f"/pull-requests/{self.pr.id}/")
        self.assertContains(res, "Cancel Timeout")

        # Click Cancel Timeout
        res = client.post(f"/pull-requests/{self.pr.id}/cancel-timeout/")
        self.assertRedirects(res, f"/pull-requests/{self.pr.id}/")
        self.rev.refresh_from_db()
        self.assertTrue(self.rev.is_draft)
        self.assertIsNone(self.rev.draft_expires_at)


class TestPRConvertToDraftEndpoint(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="test:project")
        self.git_mapping = GitMapping.objects.create(owner="suse", repo="obs-flow", branch="main", project=self.project)
        self.author = User.objects.create(username="dev", username_lower="dev", account_type=User.AccountType.HUMAN)

        self.pr = PullRequest.objects.create(
            target=self.git_mapping,
            number=42,
            author=self.author,
            source_owner="dev",
            source_repo="obs-flow",
            source_branch="feat",
        )
        self.rev = PullRequestRevision.objects.create(
            pull_request=self.pr,
            revision_number=1,
            head_sha="1111",
            base_sha="0000",
            fingerprint="fp1",
            is_draft=False,
            draft_expires_at=None,
        )

    def test_convert_to_draft_endpoint_success(self):
        payload = {"pull_request_ids": ["suse/obs-flow#42"]}
        with TestClient(api) as client:
            response = client.post("/api/v1/pr/convert-to-draft", content=json.dumps(payload))
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertTrue(res_data["pull_requests"][0]["is_draft"])

        self.rev.refresh_from_db()
        self.assertTrue(self.rev.is_draft)
        self.assertIsNone(self.rev.draft_expires_at)


class TestMarkExpiredDraftsReadyCommand(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="test:project")
        self.git_mapping = GitMapping.objects.create(owner="suse", repo="obs-flow", branch="main", project=self.project)
        self.author = User.objects.create(username="dev", username_lower="dev", account_type=User.AccountType.HUMAN)
        self.reviewer = User.objects.create(username="rev", username_lower="rev", account_type=User.AccountType.HUMAN)
        from reviews.models import ReviewConfig
        ReviewConfig.objects.create(project=self.project, type=ReviewConfig.ConfigType.PROJECT, reviewer_user=self.reviewer)
        ReviewConfig.objects.create(project=self.project, type="staging", reviewer_user=self.reviewer)

        # 1. Expired PR revision
        self.pr_expired = PullRequest.objects.create(
            target=self.git_mapping,
            number=1,
            author=self.author,
            source_owner="dev",
            source_repo="obs-flow",
            source_branch="feat-1",
        )
        self.rev_pr_expired = PullRequestRevision.objects.create(
            pull_request=self.pr_expired,
            revision_number=1,
            head_sha="1111",
            base_sha="0000",
            fingerprint="fp1",
            is_draft=True,
            draft_expires_at=timezone.now() - timezone.timedelta(minutes=5),
        )

        # 2. Non-expired PR revision
        self.pr_active = PullRequest.objects.create(
            target=self.git_mapping,
            number=2,
            author=self.author,
            source_owner="dev",
            source_repo="obs-flow",
            source_branch="feat-2",
        )
        self.rev_pr_active = PullRequestRevision.objects.create(
            pull_request=self.pr_active,
            revision_number=1,
            head_sha="2222",
            base_sha="0000",
            fingerprint="fp2",
            is_draft=True,
            draft_expires_at=timezone.now() + timezone.timedelta(minutes=10),
        )

        # 3. Manual draft PR revision (no timer)
        self.pr_manual = PullRequest.objects.create(
            target=self.git_mapping,
            number=3,
            author=self.author,
            source_owner="dev",
            source_repo="obs-flow",
            source_branch="feat-3",
        )
        self.rev_pr_manual = PullRequestRevision.objects.create(
            pull_request=self.pr_manual,
            revision_number=1,
            head_sha="3333",
            base_sha="0000",
            fingerprint="fp3",
            is_draft=True,
            draft_expires_at=None,
        )

        # 4. Expired Staging Batch revision
        from staging.models import StagingBatch, StagingBatchRevision
        self.batch_expired = StagingBatch.objects.create(project=self.project)
        self.rev_staging_expired = StagingBatchRevision.objects.create(
            staging_batch=self.batch_expired,
            revision_number=1,
            fingerprint="sfp1",
            is_draft=True,
            draft_expires_at=timezone.now() - timezone.timedelta(minutes=5),
        )

        # 5. Non-expired Staging Batch revision
        self.batch_active = StagingBatch.objects.create(project=self.project)
        self.rev_staging_active = StagingBatchRevision.objects.create(
            staging_batch=self.batch_active,
            revision_number=1,
            fingerprint="sfp2",
            is_draft=True,
            draft_expires_at=timezone.now() + timezone.timedelta(minutes=10),
        )

    def test_command_marks_expired_revisions_ready(self):
        from django.core.management import call_command
        import io

        out = io.StringIO()
        call_command("mark_expired_drafts_ready", stdout=out)
        output = out.getvalue()

        self.assertIn("Marked 1 PR revision(s) and 1 staging batch revision(s) ready for review.", output)

        # Expired PR revision is published and has reviews
        self.rev_pr_expired.refresh_from_db()
        self.assertFalse(self.rev_pr_expired.is_draft)
        self.assertIsNone(self.rev_pr_expired.draft_expires_at)
        self.assertEqual(self.rev_pr_expired.reviews.count(), 1)

        # Active PR revision remains in draft without reviews
        self.rev_pr_active.refresh_from_db()
        self.assertTrue(self.rev_pr_active.is_draft)
        self.assertIsNotNone(self.rev_pr_active.draft_expires_at)
        self.assertEqual(self.rev_pr_active.reviews.count(), 0)

        # Manual draft PR revision remains in draft without reviews
        self.rev_pr_manual.refresh_from_db()
        self.assertTrue(self.rev_pr_manual.is_draft)
        self.assertIsNone(self.rev_pr_manual.draft_expires_at)
        self.assertEqual(self.rev_pr_manual.reviews.count(), 0)

        # Expired Staging revision is published and has reviews
        self.rev_staging_expired.refresh_from_db()
        self.assertFalse(self.rev_staging_expired.is_draft)
        self.assertIsNone(self.rev_staging_expired.draft_expires_at)
        self.assertEqual(self.rev_staging_expired.reviews.count(), 1)

        # Active Staging revision remains in draft without reviews
        self.rev_staging_active.refresh_from_db()
        self.assertTrue(self.rev_staging_active.is_draft)
        self.assertEqual(self.rev_staging_active.reviews.count(), 0)

    def test_command_dry_run_leaves_database_unmodified(self):
        from django.core.management import call_command
        import io

        out = io.StringIO()
        call_command("mark_expired_drafts_ready", dry_run=True, stdout=out)
        output = out.getvalue()

        self.assertIn("Would mark 1 PR revision(s) and 1 staging batch revision(s) ready for review.", output)

        # Expired revisions should remain draft in dry-run
        self.rev_pr_expired.refresh_from_db()
        self.assertTrue(self.rev_pr_expired.is_draft)
        self.assertEqual(self.rev_pr_expired.reviews.count(), 0)

        self.rev_staging_expired.refresh_from_db()
        self.assertTrue(self.rev_staging_expired.is_draft)
        self.assertEqual(self.rev_staging_expired.reviews.count(), 0)


class TestPRMergeEndpoint(TestCase):
    def setUp(self):
        self.project_direct = Project.objects.create(name="test:direct", workflow_type=Project.WorkflowType.DIRECT)
        self.mapping_direct = GitMapping.objects.create(owner="suse", repo="direct-repo", branch="main", project=self.project_direct)

        self.project_staging = Project.objects.create(name="test:staging", workflow_type=Project.WorkflowType.STAGING)
        self.mapping_staging = GitMapping.objects.create(owner="suse", repo="staging-repo", branch="main", project=self.project_staging)

        self.author = User.objects.create(username="merger", username_lower="merger", account_type=User.AccountType.HUMAN)

        self.pr_direct = PullRequest.objects.create(
            target=self.mapping_direct,
            number=1,
            author=self.author,
            source_owner="merger",
            source_repo="direct-repo",
            source_branch="feat-1",
        )
        self.pr_direct_2 = PullRequest.objects.create(
            target=self.mapping_direct,
            number=2,
            author=self.author,
            source_owner="merger",
            source_repo="direct-repo",
            source_branch="feat-2",
        )
        self.pr_staging = PullRequest.objects.create(
            target=self.mapping_staging,
            number=3,
            author=self.author,
            source_owner="merger",
            source_repo="staging-repo",
            source_branch="feat-3",
        )

    @override_settings(GITEA_URL="https://gitea.example.com", GITEA_TOKEN="secret-token")
    @patch("urllib.request.urlopen")
    def test_merge_direct_project_pr_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        payload = {"pull_request_ids": ["suse/direct-repo#1"]}
        with TestClient(api) as client:
            res = client.post("/api/v1/pr/merge", content=json.dumps(payload))
        self.assertEqual(res.status_code, 200)

        data = res.json()
        self.assertEqual(len(data["pull_requests"]), 1)
        self.assertEqual(data["pull_requests"][0]["state"], "merged")

        self.pr_direct.refresh_from_db()
        self.assertEqual(self.pr_direct.state, PullRequest.State.MERGED)

    @override_settings(GITEA_URL="https://gitea.example.com", GITEA_TOKEN="secret-token")
    @patch("urllib.request.urlopen")
    def test_merge_staging_project_pr_fails(self, mock_urlopen):
        payload = {"pull_request_ids": ["suse/staging-repo#3"]}
        with TestClient(api) as client:
            res = client.post("/api/v1/pr/merge", content=json.dumps(payload))
        self.assertEqual(res.status_code, 400)
        self.assertIn("Direct merges are not allowed", res.text)

        self.pr_staging.refresh_from_db()
        self.assertEqual(self.pr_staging.state, PullRequest.State.OPEN)
        mock_urlopen.assert_not_called()

    @override_settings(GITEA_URL="https://gitea.example.com", GITEA_TOKEN="secret-token")
    @patch("urllib.request.urlopen")
    def test_merge_bulk_direct_prs(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        payload = {"pull_request_ids": ["suse/direct-repo#1", "suse/direct-repo#2"]}
        with TestClient(api) as client:
            res = client.post("/api/v1/pr/merge", content=json.dumps(payload))
        self.assertEqual(res.status_code, 200)

        data = res.json()
        self.assertEqual(len(data["pull_requests"]), 2)
        self.assertEqual(data["pull_requests"][0]["state"], "merged")
        self.assertEqual(data["pull_requests"][1]["state"], "merged")

        self.pr_direct.refresh_from_db()
        self.pr_direct_2.refresh_from_db()
        self.assertEqual(self.pr_direct.state, PullRequest.State.MERGED)
        self.assertEqual(self.pr_direct_2.state, PullRequest.State.MERGED)

    def test_merge_collects_all_errors(self):
        # Already merged PR
        self.pr_direct.state = PullRequest.State.MERGED
        self.pr_direct.save()

        # Try merging pr_direct (already merged), pr_staging (staging workflow), and nonexistent PR
        payload = {"pull_request_ids": ["suse/direct-repo#1", "suse/staging-repo#3", "suse/direct-repo#999"]}
        with TestClient(api) as client:
            res = client.post("/api/v1/pr/merge", content=json.dumps(payload))
        self.assertEqual(res.status_code, 400)
        self.assertIn("already merged", res.text)
        self.assertIn("Direct merges are not allowed", res.text)
        self.assertIn("does not exist", res.text)
