"""Review lifecycle: building blocks first, I/O procedures last."""

from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone

from accounts.helpers import build_user_dto
from accounts.models import Group, User
from core.models import Project
from obs_flow_common.messages import ReviewDetail
from obs_flow_common.messages.reviews import (
    DynamicRoleReviewerDTO,
    GroupReviewerDTO,
    PersonReviewerDTO,
    ReviewConfigDTO,
    ReviewerDTO,
)
from reviews.models import BaseReview, ReviewConfig, ReviewScope


# =====================================================================
# Building blocks (entity-level, no external I/O)
# =====================================================================


def parse_reviewer(reviewer_str: str | None) -> tuple[User | None, Group | None, str | None]:
    """
    Parses a reviewer string into (user, group, dynamic_role).
    Exactly one of them will be returned as non-None.

    Accepted formats: <username>, @<group_name>, role:<dynamic_role>.
    Raises ValueError if no reviewer is specified.
    """
    if not reviewer_str:
        raise ValueError("No reviewer specified.")

    if reviewer_str.startswith("@"):
        group_name = reviewer_str[1:]
        group = Group.objects.get(name=group_name)
        return None, group, None
    elif reviewer_str.startswith("role:"):
        role_name = reviewer_str[len("role:"):]
        if role_name not in ReviewConfig.DynamicRole.values:
            raise ValueError(f"Invalid dynamic role: {role_name}")
        return None, None, role_name
    else:
        user = User.objects.get(username=reviewer_str)
        return user, None, None


def format_reviewer(config: ReviewConfig) -> str:
    """
    Formats a ReviewConfig's reviewer into a string identifier.
    """
    if config.reviewer_user:
        return config.reviewer_user.username
    elif config.reviewer_group:
        return f"@{config.reviewer_group.name}"
    elif config.dynamic_role:
        return f"role:{config.dynamic_role}"
    else:
        raise ValueError("Invalid review configuration: no reviewer set")


def get_review_config(project: Project, config_type: str, reviewer_str: str) -> ReviewConfig:
    """
    Finds an existing ReviewConfig by project, type, and reviewer string.
    """
    user, group, dynamic_role = parse_reviewer(reviewer_str)
    return ReviewConfig.objects.get(
        project=project,
        type=config_type,
        reviewer_user=user,
        reviewer_group=group,
        dynamic_role=dynamic_role,
    )


def build_reviewer_dto_from_fields(user: User | None, group: Group | None, dynamic_role: str | None) -> ReviewerDTO:
    """
    Converts reviewer fields into a ReviewerDTO message struct.
    """
    if user:
        return PersonReviewerDTO(
            username=user.username,
            full_name=user.full_name,
            email=user.email,
            is_active=user.is_active,
        )
    elif group:
        return GroupReviewerDTO(
            name=group.name,
            email=group.email,
        )
    elif dynamic_role:
        return DynamicRoleReviewerDTO(
            role=dynamic_role,
        )
    else:
        raise ValueError("Invalid reviewer: no user, group, or dynamic role set")


def build_reviewer_dto(config: ReviewConfig) -> ReviewerDTO:
    """
    Converts a ReviewConfig's reviewer into a ReviewerDTO message struct.
    """
    return build_reviewer_dto_from_fields(config.reviewer_user, config.reviewer_group, config.dynamic_role)


def build_review_config_dto(config: ReviewConfig) -> ReviewConfigDTO:
    """
    Converts a ReviewConfig instance to a ReviewConfigDTO message struct.
    """
    depends_on_list = [build_reviewer_dto(dep) for dep in config.depends_on.all()]
    scope_name = config.scope.name
    return ReviewConfigDTO(
        id=config.id,
        project=config.project.name,
        type=config.type,
        reviewer=build_reviewer_dto(config),
        depends_on=depends_on_list,
        scope=scope_name,
    )


def get_or_create_review(revision, reviewer_str: str | None, review_model) -> BaseReview:
    """
    Gets or creates the review of `review_model` for this revision and reviewer.
    A reviewer must be specified; an empty value raises ValueError.
    """
    user, group, role = parse_reviewer(reviewer_str)
    if user:
        reviewer = {"reviewer_user": user}
    elif group:
        reviewer = {"reviewer_group": group}
    else:
        reviewer = {"dynamic_role": role}

    review, _ = review_model.objects.get_or_create(
        revision=revision,
        **reviewer,
        defaults={
            "state": BaseReview.State.PENDING,
            "scope": ReviewScope.objects.get(name="global"),
        },
    )
    return review


def apply_review_action(review: BaseReview, state: str, actor: User, justification: str | None) -> BaseReview:
    """
    Sets the given state/actor/justification on the review, clears inheritance,
    saves it and propagates the decision to dependent reviews.
    """
    review.state = state
    review.actor = actor
    review.justification = justification
    review.is_inherited = False
    review.save()
    review.propagate_decision()
    return review


def clear_needinfo(revision, actor: User, justification: str | None, review_model, reviewer: str | None = None) -> list[BaseReview]:
    """
    Moves NEEDINFO reviews of the revision back to PENDING, stamping actor/justification.
    When `reviewer` is given, only that reviewer's NEEDINFO review is cleared;
    otherwise all NEEDINFO reviews are cleared.
    Returns the list of cleared reviews (in pk order). Raises ValueError if nothing matched.
    """
    reviews = revision.reviews.filter(state=BaseReview.State.NEEDINFO)
    if reviewer:
        user, group, role = parse_reviewer(reviewer)
        if user:
            reviews = reviews.filter(reviewer_user=user)
        elif group:
            reviews = reviews.filter(reviewer_group=group)
        else:
            reviews = reviews.filter(dynamic_role=role)

    cleared = []
    for review in reviews.order_by("pk"):
        apply_review_action(review, BaseReview.State.PENDING, actor, justification)
        cleared.append(review)

    if not cleared:
        raise ValueError("No needinfo reviews to clear.")

    return cleared


def initial_draft_state(is_upstream_draft: bool, timeout_minutes: int) -> tuple[bool, datetime | None]:
    """
    Computes the initial draft state of a new revision.
    Upstream drafts stay in manual draft mode without a timer; otherwise a
    zero debounce timeout means ready immediately, else draft with debounce timer.
    """
    if is_upstream_draft:
        return True, None
    if timeout_minutes == 0:
        return False, None
    return True, timezone.now() + timedelta(minutes=timeout_minutes)


@transaction.atomic
def mark_ready(revision, *, revision_model, provision_fn) -> None:
    """
    Transitions a revision out of draft mode and provisions reviews.
    """
    rev = revision_model.objects.select_for_update().get(pk=revision.pk)
    if not rev.is_draft and rev.draft_expires_at is None:
        return
    rev.is_draft = False
    rev.draft_expires_at = None
    rev.save(update_fields=["is_draft", "draft_expires_at"])
    revision.is_draft = False
    revision.draft_expires_at = None
    provision_fn(rev)


@transaction.atomic
def mark_draft(revision, *, revision_model) -> None:
    """
    Transitions a revision into manual draft mode without debounce timer.
    Existing reviews are not modified or removed.
    """
    rev = revision_model.objects.select_for_update().get(pk=revision.pk)
    if rev.is_draft and rev.draft_expires_at is None:
        return
    rev.is_draft = True
    rev.draft_expires_at = None
    rev.save(update_fields=["is_draft", "draft_expires_at"])
    revision.is_draft = True
    revision.draft_expires_at = None


@transaction.atomic
def provision_reviews_for(revision, configs, *, review_model, revision_model, prev_rev=None) -> list[BaseReview]:
    """
    Provisions reviews for a revision based on the given ReviewConfigs.
    Skips while the revision is in draft mode or reviews already exist.
    Evaluates scopes against changed files and supports decision inheritance
    from the previous revision. Creates one review per config, wires
    depends_on within the created set, and promotes ready reviews from
    WAITING to PENDING.
    """
    rev = revision_model.objects.select_for_update().get(pk=revision.pk)
    if rev.is_draft:
        return []
    if rev.reviews.exists():
        return list(rev.reviews.all())

    created_reviews = []
    if configs.exists():
        config_to_review = {}

        changed_files = rev.get_changed_files()
        inter_files = rev.get_inter_revision_changed_files(prev_rev) if prev_rev else changed_files

        for config in configs:
            scope = config.scope
            is_in_scope = scope.evaluate(changed_files)

            if not is_in_scope:
                review = review_model.objects.create(
                    revision=rev,
                    reviewer_user=config.reviewer_user,
                    reviewer_group=config.reviewer_group,
                    dynamic_role=config.dynamic_role,
                    scope=scope,
                    state=BaseReview.State.SKIPPED,
                    is_inherited=False,
                )
            else:
                prev_review = None
                if prev_rev:
                    prev_review = review_model.objects.filter(
                        revision=prev_rev,
                        reviewer_user=config.reviewer_user,
                        reviewer_group=config.reviewer_group,
                        dynamic_role=config.dynamic_role,
                    ).first()

                if (
                    prev_review
                    and prev_review.scope_id == scope.id
                    and prev_review.state != BaseReview.State.SKIPPED
                    and not scope.evaluate(inter_files)
                ):
                    review = review_model.objects.create(
                        revision=rev,
                        reviewer_user=config.reviewer_user,
                        reviewer_group=config.reviewer_group,
                        dynamic_role=config.dynamic_role,
                        scope=scope,
                        state=prev_review.state,
                        actor=prev_review.actor,
                        justification=prev_review.justification,
                        is_inherited=True,
                    )
                else:
                    review = review_model.objects.create(
                        revision=rev,
                        reviewer_user=config.reviewer_user,
                        reviewer_group=config.reviewer_group,
                        dynamic_role=config.dynamic_role,
                        scope=scope,
                        state=BaseReview.State.WAITING,
                        is_inherited=False,
                    )

            config_to_review[config] = review
            created_reviews.append(review)

        # Set up dependencies between the created reviews
        for config, review in config_to_review.items():
            for dep_config in config.depends_on.all():
                if dep_config in config_to_review:
                    review.depends_on.add(config_to_review[dep_config])

        # Reviews with no unresolved dependencies start as PENDING, others remain WAITING
        for review in created_reviews:
            if review.state == BaseReview.State.WAITING:
                prereqs = review.depends_on.all()
                if not prereqs.exists() or all(
                    p.state in (BaseReview.State.ACCEPTED, BaseReview.State.OVERRIDDEN, BaseReview.State.SKIPPED)
                    for p in prereqs
                ):
                    review.state = BaseReview.State.PENDING
                    review.save(update_fields=["state"])

    return created_reviews


def review_to_detail(review: BaseReview) -> ReviewDetail:
    reviewer_dto = build_reviewer_dto_from_fields(
        review.reviewer_user,
        review.reviewer_group,
        review.dynamic_role,
    )
    actor_dto = build_user_dto(review.actor) if review.actor else None
    scope_name = review.scope.name

    return ReviewDetail(
        reviewer=reviewer_dto,
        state=review.state,
        actor=actor_dto,
        when=review.updated_at.isoformat(),
        why=review.justification,
        scope=scope_name,
        is_inherited=review.is_inherited,
    )
