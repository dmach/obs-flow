from django.apps import AppConfig


class GitTransportConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "git_transport"

    def ready(self):
        # We will initialize the Unix socket server in Iteration 2
        pass
