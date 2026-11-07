from django.core.management.base import BaseCommand
from accounts.models import SSHKey, User


class Command(BaseCommand):
    help = "Look up and format authorized SSH public keys for OpenSSH AuthorizedKeysCommand."

    def add_arguments(self, parser):
        parser.add_argument("--user", type=str, default=None, help="Filter by username.")
        parser.add_argument("--fingerprint", type=str, default=None, help="Filter by key fingerprint.")

    def handle(self, *args, **options):
        qs = SSHKey.objects.select_related("user").filter(user__is_active=True)

        user_filter = options.get("user")
        if user_filter:
            qs = qs.filter(user__username__iexact=user_filter)

        fp_filter = options.get("fingerprint")
        if fp_filter:
            qs = qs.filter(fingerprint=fp_filter)

        for key in qs:
            self.stdout.write(
                f'command="python manage.py git_shell {key.user.username}",'
                f'no-port-forwarding,no-X11-forwarding,no-agent-forwarding,no-pty {key.public_key.strip()}\n'
            )
