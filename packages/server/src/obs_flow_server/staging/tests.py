from django.test import TestCase
from accounts.models import User, Group
from core.models import Project, GitMapping
from pull_requests.models import PullRequest, PullRequestRevision, PullRequestReview
from staging.models import StagingBatch, StagingReview


class TestEmptyDatabase(TestCase):
    def test_database_is_initially_empty(self):
        """Verify that the database is clean initially."""
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(Group.objects.count(), 0)
        self.assertEqual(Project.objects.count(), 0)
        self.assertEqual(GitMapping.objects.count(), 0)
        self.assertEqual(PullRequest.objects.count(), 0)
        self.assertEqual(PullRequestRevision.objects.count(), 0)
        self.assertEqual(PullRequestReview.objects.count(), 0)
        self.assertEqual(StagingBatch.objects.count(), 0)
        self.assertEqual(StagingReview.objects.count(), 0)


class TestFixtureData(TestCase):
    fixtures = ["opensuse_data.json"]

    def test_fixture_data_loaded(self):
        """Verify that the openSUSE/OBS themed fixture data is loaded correctly."""
        # Verify Users
        self.assertTrue(User.objects.filter(username="darix").exists())
        self.assertTrue(User.objects.filter(username="factory-auto").exists())
        self.assertTrue(User.objects.filter(username="dimstar").exists())

        # Verify Groups
        self.assertTrue(Group.objects.filter(name="opensuse-review-team").exists())
        self.assertTrue(Group.objects.filter(name="factory-staging").exists())

        # Verify UserGroups
        darix = User.objects.get(username="darix")
        dimstar = User.objects.get(username="dimstar")
        opensuse_review_team = Group.objects.get(name="opensuse-review-team")
        factory_staging = Group.objects.get(name="factory-staging")

        self.assertTrue(darix.user_groups.filter(group=opensuse_review_team).exists())
        self.assertTrue(dimstar.user_groups.filter(group=opensuse_review_team).exists())
        self.assertTrue(dimstar.user_groups.filter(group=factory_staging).exists())

        # Verify Project
        self.assertTrue(Project.objects.filter(name="openSUSE:Factory").exists())

        # Verify GitMapping
        self.assertTrue(GitMapping.objects.filter(owner="openSUSE", repo="osc", branch="master").exists())

        # Verify PullRequest
        self.assertTrue(PullRequest.objects.filter(number=1234).exists())

        # Verify PullRequestRevision
        pr = PullRequest.objects.get(number=1234)
        self.assertTrue(PullRequestRevision.objects.filter(pull_request=pr, revision_number=1).exists())

        # Verify PullRequestReviews
        revision = PullRequestRevision.objects.get(pull_request=pr, revision_number=1)
        self.assertTrue(PullRequestReview.objects.filter(revision=revision, reviewer_user__username="factory-auto").exists())
        self.assertTrue(PullRequestReview.objects.filter(revision=revision, reviewer_group__name="opensuse-review-team", state="rejected", actor__username="darix").exists())
        self.assertTrue(PullRequestReview.objects.filter(revision=revision, reviewer_group__name="factory-staging", state="accepted", actor__username="dimstar").exists())

        # Verify StagingBatch
        self.assertTrue(StagingBatch.objects.filter(id=1).exists())

        # Verify StagingReview
        batch = StagingBatch.objects.get(id=1)
        self.assertTrue(StagingReview.objects.filter(staging=batch, reviewer_user__username="darix").exists())


import json
from django.test import TransactionTestCase
from django_bolt.testing import TestClient
from obs_flow_server.api import api


class TestStagingAPI(TransactionTestCase):
    fixtures = ["opensuse_data.json"]

    def setUp(self):
        User.objects.create(username="admin", username_lower="admin")

    def test_create_staging_batch_with_project(self):
        """Verify that creating a staging batch requires a project and sets it correctly."""
        payload = {
            "project": "openSUSE:Factory",
            "title": "My Staging Batch",
        }
        with TestClient(api) as client:
            response = client.post(
                "/api/v1/staging/create",
                content=json.dumps(payload),
            )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertEqual(res_data["target_project"], "openSUSE:Factory")
        self.assertEqual(res_data["title"], "My Staging Batch")

        # Verify it was created in the database
        batch = StagingBatch.objects.get(id=res_data["id"])
        self.assertEqual(batch.project.name, "openSUSE:Factory")
        self.assertEqual(batch.title, "My Staging Batch")

    def test_create_staging_batch_missing_project(self):
        """Verify that creating a staging batch without a project fails."""
        payload = {
            "title": "My Staging Batch",
        }
        with TestClient(api) as client:
            response = client.post(
                "/api/v1/staging/create",
                content=json.dumps(payload),
            )
        self.assertNotEqual(response.status_code, 200)

