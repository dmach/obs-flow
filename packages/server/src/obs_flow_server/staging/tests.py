from django.test import TestCase, TransactionTestCase
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


class TestStagingCreationWithReviewConfig(TransactionTestCase):
    fixtures = ["opensuse_data.json"]

    def test_create_staging_with_review_configs(self):
        """Verify that creating a staging batch for a project with staging review configurations
        correctly populates the staging reviews and their dependencies.
        """
        import json
        from django_bolt.testing import TestClient
        from obs_flow_server.api import api
        from reviews.models import ReviewConfig

        project = Project.objects.get(name="openSUSE:Factory")
        user_darix = User.objects.get(username="darix")
        user_dimstar = User.objects.get(username="dimstar")
        group_team = Group.objects.get(name="opensuse-review-team")

        # 1. Add review configurations for staging
        config_darix = ReviewConfig.objects.create(
            project=project,
            type="staging",
            reviewer_user=user_darix,
        )
        config_team = ReviewConfig.objects.create(
            project=project,
            type="staging",
            reviewer_group=group_team,
        )
        config_dimstar = ReviewConfig.objects.create(
            project=project,
            type="staging",
            reviewer_user=user_dimstar,
        )
        config_dimstar.depends_on.add(config_darix, config_team)

        # 2. Create a staging batch for openSUSE:Factory
        payload = {
            "project": "openSUSE:Factory",
            "title": "Factory Staging Batch A",
        }
        with TestClient(api) as client:
            response = client.post(
                "/api/v1/staging/create",
                content=json.dumps(payload),
            )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertEqual(res_data["target_project"], "openSUSE:Factory")
        self.assertEqual(res_data["title"], "Factory Staging Batch A")

        # 3. Verify that the created staging batch has exactly the configured reviewers
        batch_id = res_data["id"]
        batch = StagingBatch.objects.get(id=batch_id)
        self.assertEqual(batch.project, project)

        reviews = StagingReview.objects.filter(staging=batch)
        self.assertEqual(reviews.count(), 3)

        # Verify individual reviews and their states
        review_darix = reviews.get(reviewer_user=user_darix)
        self.assertEqual(review_darix.state, StagingReview.State.PENDING)

        review_team = reviews.get(reviewer_group=group_team)
        self.assertEqual(review_team.state, StagingReview.State.PENDING)

        review_dimstar = reviews.get(reviewer_user=user_dimstar)
        self.assertEqual(review_dimstar.state, StagingReview.State.PENDING)

        # Verify dependencies are correctly mapped
        self.assertCountEqual(
            review_dimstar.depends_on.all(),
            [review_darix, review_team]
        )

