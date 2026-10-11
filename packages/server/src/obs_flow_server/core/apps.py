from django.apps import AppConfig
from django.core.checks import Error, Tags, register


@register(Tags.compatibility)
def check_review_debounce_setting(app_configs, **kwargs):
    from django.conf import settings
    errors = []
    val = getattr(settings, "REVIEW_DEBOUNCE_MINUTES", None)
    if val is None:
        errors.append(
            Error(
                "REVIEW_DEBOUNCE_MINUTES setting is required.",
                id="core.E001",
            )
        )
    elif not isinstance(val, int) or isinstance(val, bool) or val < 0:
        errors.append(
            Error(
                "REVIEW_DEBOUNCE_MINUTES setting must be a non-negative integer.",
                id="core.E002",
            )
        )
    return errors


class CoreConfig(AppConfig):
    name = "core"
