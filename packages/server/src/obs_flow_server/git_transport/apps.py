from django.apps import AppConfig


class GitTransportConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "git_transport"

    def ready(self):
        import sys
        # Only start the server when running commands, serving requests, or testing
        from .hook_server import start_hook_server
        try:
            start_hook_server()
        except Exception:
            pass
