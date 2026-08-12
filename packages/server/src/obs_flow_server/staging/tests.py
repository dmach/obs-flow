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
