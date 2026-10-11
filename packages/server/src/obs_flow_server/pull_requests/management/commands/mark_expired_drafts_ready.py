import logging
from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Find and mark all expired debounced draft revisions as ready for review"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show revisions that would be marked ready without modifying them",
        )

    def handle(self, *args, **options):
        from pull_requests.models import PullRequestRevision
        from pull_requests.api import mark_ready_for_review
        from staging.models import StagingBatchRevision
        from staging.api import mark_staging_ready_for_review

        dry_run = options.get("dry_run", False)
        now = timezone.now()

        # 1. Process expired PullRequestRevisions
        expired_pr_revs = PullRequestRevision.objects.filter(
            is_draft=True,
            draft_expires_at__isnull=False,
            draft_expires_at__lte=now,
        ).select_related("pull_request", "pull_request__target")

        pr_count = 0
        for rev in expired_pr_revs:
            pr = rev.pull_request
            self.stdout.write(
                f"Processing expired draft PullRequestRevision #{rev.revision_number} for PR #{pr.number} on {pr.target}"
            )
            if not dry_run:
                mark_ready_for_review(rev)
            pr_count += 1

        # 2. Process expired StagingBatchRevisions
        expired_staging_revs = StagingBatchRevision.objects.filter(
            is_draft=True,
            draft_expires_at__isnull=False,
            draft_expires_at__lte=now,
        ).select_related("staging_batch")

        staging_count = 0
        for rev in expired_staging_revs:
            batch = rev.staging_batch
            self.stdout.write(
                f"Processing expired draft StagingBatchRevision #{rev.revision_number} for Staging Batch #{batch.id}"
            )
            if not dry_run:
                mark_staging_ready_for_review(rev)
            staging_count += 1

        action_word = "Would mark" if dry_run else "Marked"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action_word} {pr_count} PR revision(s) and {staging_count} staging batch revision(s) ready for review."
            )
        )
