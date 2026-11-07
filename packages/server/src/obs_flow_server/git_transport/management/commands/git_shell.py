import os
import sys
from django.core.management.base import BaseCommand
from git_transport.ssh import handle_ssh_command


class Command(BaseCommand):
    help = "Execute git transport commands (git-upload-pack, git-receive-pack) in an SSH session."

    def add_arguments(self, parser):
        parser.add_argument("username", type=str, help="Username of the connecting user.")
        parser.add_argument(
            "-c",
            "--command",
            type=str,
            default=None,
            help="Original SSH command. If not passed, SSH_ORIGINAL_COMMAND environment variable is used.",
        )

    def handle(self, *args, **options):
        username = options["username"]
        command_str = options["command"] or os.environ.get("SSH_ORIGINAL_COMMAND", "")

        if not command_str:
            self.stderr.write("OBS Flow SSH Error: No command provided.\n")
            sys.exit(1)

        ret = handle_ssh_command(
            username=username,
            command_str=command_str,
            stdin=sys.stdin.buffer,
            stdout=sys.stdout.buffer,
            stderr=sys.stderr,
        )
        sys.exit(ret)
