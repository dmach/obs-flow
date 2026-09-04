from django.contrib.messages import get_messages
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse
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
        self.assertTrue(StagingReview.objects.filter(revision__staging_batch=batch, reviewer_user__username="darix").exists())


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

        reviews = StagingReview.objects.filter(revision__staging_batch=batch)
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


class TestStagingViews(TransactionTestCase):
    def test_staging_list_filtering_and_pagination(self):
        """Verify that the staging list page correctly filters and paginates staging batches."""
        from django.test import Client

        project1 = Project.objects.create(name="suse:obs-flow")
        project2 = Project.objects.create(name="openSUSE:Factory")
        author = User.objects.create(username="john_doe", username_lower="john_doe", account_type=User.AccountType.HUMAN)

        # Create 205 staging batches to test pagination (page size is 200)
        for i in range(1, 206):
            StagingBatch.objects.create(
                project=project1 if i % 2 == 0 else project2,
                title=f"Batch {i}",
                author=author,
                state=StagingBatch.State.COLLECTING
            )

        client = Client()

        # 1. Test pagination (page 1 should have 200 items, page 2 should have 5 items)
        response = client.get("/staging/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Page 1 of 2")
        self.assertContains(response, "Batch 205")

        response = client.get("/staging/?page=2")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Page 2 of 2")
        self.assertContains(response, "Batch 1")

        # 2. Test filtering by target_owner (project name)
        response = client.get("/staging/?target_owner=suse:obs-flow")
        self.assertEqual(response.status_code, 200)
        # 102 batches should fit on 1 page
        self.assertNotContains(response, "Page 1 of 2")


class TestStagingBatchRevision(TransactionTestCase):
    fixtures = ["opensuse_data.json"]

    def test_staging_batch_revision_lifecycle(self):
        """Verify the complete lifecycle of StagingBatchRevision, including creation,
        adding/removing PRs, fingerprinting, and automatic updates on PR code changes.
        """
        import json
        import hashlib
        from unittest.mock import MagicMock, patch
        from django.test import override_settings
        from django_bolt.testing import TestClient
        from obs_flow_server.api import api
        from staging.models import StagingBatchRevision, StagingBatchRevisionPullRequest

        # 1. Create a staging batch
        payload = {
            "project": "openSUSE:Factory",
            "title": "Revision Test Batch",
        }
        with TestClient(api) as client:
            response = client.post(
                "/api/v1/staging/create",
                content=json.dumps(payload),
            )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        batch_id = res_data["id"]

        # Verify revision 1 is created (empty)
        batch = StagingBatch.objects.get(id=batch_id)
        self.assertEqual(batch.revisions.count(), 1)
        rev1 = batch.revisions.get(revision_number=1)
        self.assertEqual(rev1.revision_pull_requests.count(), 0)
        self.assertEqual(rev1.fingerprint, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")

        # 2. Add a PR to the staging batch
        add_payload = {
            "id": batch_id,
            "pull_request_ids": ["openSUSE/osc#1234"],
        }
        with TestClient(api) as client:
            response = client.post(
                "/api/v1/staging/add",
                content=json.dumps(add_payload),
            )
        self.assertEqual(response.status_code, 200)

        # Verify revision 2 is created
        self.assertEqual(batch.revisions.count(), 2)
        rev2 = batch.revisions.order_by("-revision_number").first()
        self.assertEqual(rev2.revision_number, 2)
        self.assertEqual(rev2.revision_pull_requests.count(), 1)

        # Verify fingerprint is computed correctly
        expected_content = "openSUSE/osc#1234.1"
        expected_fingerprint = hashlib.sha256(expected_content.encode("utf-8")).hexdigest()
        self.assertEqual(rev2.fingerprint, expected_fingerprint)

        # 3. Sync a new revision of the PR (PR code changes)
        # This should automatically trigger a new StagingBatchRevision (revision 3)
        gitea_data = {
            "title": "Update osc tool",
            "draft": False,
            "mergeable": True,
            "state": "open",
            "user": {"login": "darix"},
            "head": {
                "sha": "2222222222222222222222222222222222222222",
                "ref": "master",
                "repo": {
                    "owner": {"login": "openSUSE"},
                    "name": "osc"
                }
            },
            "base": {
                "sha": "0000000000000000000000000000000000000000",
                "ref": "master"
            }
        }

        with override_settings(GITEA_URL="https://gitea.example.com", GITEA_TOKEN="secret-token"):
            with patch("urllib.request.urlopen") as mock_urlopen:
                mock_response = MagicMock()
                mock_response.read.return_value = json.dumps(gitea_data).encode("utf-8")
                mock_urlopen.return_value.__enter__.return_value = mock_response

                sync_payload = {
                    "owner": "openSUSE",
                    "repo": "osc",
                    "number": 1234
                }
                with TestClient(api) as client:
                    response = client.post(
                        "/api/v1/pr/sync",
                        content=json.dumps(sync_payload),
                    )
                self.assertEqual(response.status_code, 200)

        # Verify that a new StagingBatchRevision (revision 3) was automatically created
        self.assertEqual(batch.revisions.count(), 3)
        rev3 = batch.revisions.order_by("-revision_number").first()
        self.assertEqual(rev3.revision_number, 3)
        self.assertEqual(rev3.revision_pull_requests.count(), 1)

        # Verify fingerprint is computed correctly using PR revision 2
        expected_content_3 = "openSUSE/osc#1234.2"
        expected_fingerprint_3 = hashlib.sha256(expected_content_3.encode("utf-8")).hexdigest()
        self.assertEqual(rev3.fingerprint, expected_fingerprint_3)

        # 4. Remove the PR from the staging batch
        remove_payload = {
            "id": batch_id,
            "pull_request_ids": ["openSUSE/osc#1234"],
        }
        with TestClient(api) as client:
            response = client.post(
                "/api/v1/staging/remove",
                content=json.dumps(remove_payload),
            )
        self.assertEqual(response.status_code, 200)

        # Verify revision 4 is created (empty again)
        self.assertEqual(batch.revisions.count(), 4)
        rev4 = batch.revisions.order_by("-revision_number").first()
        self.assertEqual(rev4.revision_number, 4)
        self.assertEqual(rev4.revision_pull_requests.count(), 0)
        self.assertEqual(rev4.fingerprint, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")


class TestStagingUIModalViews(TransactionTestCase):
    fixtures = ["opensuse_data.json"]

    def test_select_batch_modal_validation(self):
        """Verify that select_batch modal validates selected PRs correctly."""
        from django.test import Client
        client = Client()

        # 1. Test with no PRs selected
        response = client.post("/staging/ui/modal/select-batch/", {})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No pull requests selected.")

        # 2. Test with mixed projects
        # Let's create a PR targeting a different project
        project2 = Project.objects.create(name="suse:obs-flow")
        mapping2 = GitMapping.objects.create(owner="suse", repo="obs-flow", branch="main", project=project2)

        # Find a user to be the author
        author = User.objects.first()
        pr2 = PullRequest.objects.create(
            target=mapping2,
            number=123,
            author=author,
            title="PR 2",
            state="open",
        )

        # PR 1234 exists in opensuse_data.json (targets openSUSE:Factory)
        pr1 = PullRequest.objects.get(number=1234)
        response = client.post("/staging/ui/modal/select-batch/", {
            "selected_prs": [pr1.id, pr2.id]
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Selected pull requests must target the same project. Mixed projects are not allowed.")

        # 3. Test with valid single project
        response = client.post("/staging/ui/modal/select-batch/", {
            "selected_prs": [pr1.id]
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Stage Selected Pull Requests")
        self.assertContains(response, "openSUSE:Factory")

    def test_confirm_add_modal_conflicts_and_resolution(self):
        """Verify that confirm_add modal detects conflicts and handles resolution choices."""
        from django.test import Client
        from staging.models import StagingBatchRevisionPullRequest
        client = Client()

        # Link PR 1234 to Staging Batch #1 (from opensuse_data.json)
        batch1 = StagingBatch.objects.get(id=1)
        pr1 = PullRequest.objects.get(number=1234)
        pr1_rev = pr1.revisions.first()
        rev1 = batch1.revisions.get(revision_number=1)
        StagingBatchRevisionPullRequest.objects.create(
            staging_batch_revision=rev1,
            pull_request_revision=pr1_rev,
        )

        # Create a second staging batch for openSUSE:Factory
        project = Project.objects.get(name="openSUSE:Factory")
        batch2 = StagingBatch.objects.create(
            project=project,
            title="Staging Batch #2",
            state=StagingBatch.State.COLLECTING,
        )
        # Create revision 1 for batch2
        from staging.api import create_staging_revision
        create_staging_revision(batch2, [])

        # PR 1234 is already in Staging Batch #1
        # Let's try to add it to Staging Batch #2
        response = client.post("/staging/ui/modal/confirm-add/", {
            "selected_prs": [pr1.id],
            "batch_id": batch2.id,
        })
        self.assertEqual(response.status_code, 200)
        # Should show conflict warning
        self.assertContains(response, "Conflict Warning")
        self.assertContains(response, "is in:")
        self.assertContains(response, "#1")

        # Resolve conflict with "safe" (exclude conflicting)
        response = client.post("/staging/ui/modal/confirm-add/", {
            "selected_prs": [pr1.id],
            "batch_id": batch2.id,
            "resolution": "safe",
        })
        self.assertEqual(response.status_code, 200)
        # Should close the modal, refresh the page and queue an error message
        self.assertEqual(response.content, b"")
        self.assertEqual(response["HX-Refresh"], "true")
        self.assertIn(
            "No pull requests were added (all were conflicting).",
            [str(m) for m in get_messages(response.wsgi_request)],
        )

        # Resolve conflict with "all" (add all anyway)
        response = client.post("/staging/ui/modal/confirm-add/", {
            "selected_prs": [pr1.id],
            "batch_id": batch2.id,
            "resolution": "all",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"")
        self.assertEqual(response["HX-Refresh"], "true")
        self.assertIn(
            f"Successfully added 1 PRs to Staging Batch #{batch2.id}.",
            [str(m) for m in get_messages(response.wsgi_request)],
        )


class TestStagingUIModalCsrf(TransactionTestCase):
    """
    Regression tests for "Forbidden (CSRF token missing.)" on the htmx modal endpoints.

    The default test client skips CSRF verification, so these tests explicitly
    enable it via enforce_csrf_checks=True.
    """

    fixtures = ["opensuse_data.json"]

    def test_pr_list_sets_csrf_cookie(self):
        """The PR list page must hand out a CSRF cookie, otherwise htmx has no token to send."""
        client = Client(enforce_csrf_checks=True)
        response = client.get(reverse("pr_list"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", client.cookies)

    def test_select_batch_rejects_request_without_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        client.get(reverse("pr_list"))
        pr = PullRequest.objects.get(number=1234)

        response = client.post(reverse("staging_ui_modal_select_batch"), {"selected_prs": [pr.id]})
        self.assertEqual(response.status_code, 403)

    def test_select_batch_accepts_request_with_csrf_header(self):
        """htmx sends the token in the X-CSRFToken header (see hx-headers in base.html)."""
        client = Client(enforce_csrf_checks=True)
        client.get(reverse("pr_list"))
        token = client.cookies["csrftoken"].value
        pr = PullRequest.objects.get(number=1234)

        response = client.post(
            reverse("staging_ui_modal_select_batch"),
            {"selected_prs": [pr.id]},
            headers={"x-csrftoken": token},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Stage Selected Pull Requests")

    def test_select_batch_accepts_request_with_csrf_form_field(self):
        """The PR list form also posts csrfmiddlewaretoken, which must be accepted too."""
        client = Client(enforce_csrf_checks=True)
        client.get(reverse("pr_list"))
        token = client.cookies["csrftoken"].value
        pr = PullRequest.objects.get(number=1234)

        response = client.post(
            reverse("staging_ui_modal_select_batch"),
            {"selected_prs": [pr.id], "csrfmiddlewaretoken": token},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Stage Selected Pull Requests")

