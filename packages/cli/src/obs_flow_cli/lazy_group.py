import importlib
import os
from typing import Any

import click

from . import commands


COMMANDS_MODULE = commands
if COMMANDS_MODULE.__file__ is None:
    raise RuntimeError("The commands module must be a regular package with an __init__.py file.")

# Path to the commands directory relative to this file
COMMANDS_FOLDER = os.path.dirname(COMMANDS_MODULE.__file__)


class LazyGroup(click.Group):
    """
    A Click Group that lazily loads its commands from the commands directory.
    If cmd_prefix is provided, it loads subcommands using '__' as a level separator.
    Otherwise, it loads top-level commands.
    """

    def __init__(self, *args: Any, cmd_prefix: str = "", **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.cmd_prefix = cmd_prefix

        # If CLICK_LAZY_SUBCOMMANDS=0, force import of all subcommands immediately during initialization.
        # This is highly useful for CI/CD or local testing to catch ImportErrors and SyntaxErrors early.
        if os.environ.get("CLICK_LAZY_SUBCOMMANDS") == "0":
            # Pass None for ctx as our implementation doesn't use it
            for name in self.list_commands(None):
                self.get_command(None, name)

    def list_commands(self, ctx: click.Context | None) -> list[str]:
        """
        Lists all available commands by scanning the flat commands directory.
        """
        if not os.path.exists(COMMANDS_FOLDER):
            return []

        commands: list[str] = []

        for filename in os.listdir(COMMANDS_FOLDER):
            if not filename.endswith(".py") or filename == "__init__.py":
                continue

            if self.cmd_prefix:
                prefix = f"{self.cmd_prefix}__"
                if filename.startswith(prefix):
                    # Extract the direct child name
                    # e.g., cmd__subcmd.py -> subcmd
                    # e.g., cmd__subcmd__subsubcmd.py -> ignore (not a direct child)
                    rest = filename[len(prefix) : -3]
                    if "__" not in rest:
                        # Map underscores to hyphens for user-friendly CLI command names
                        commands.append(rest.replace("_", "-"))
            else:
                if "__" not in filename:
                    commands.append(filename[:-3].replace("_", "-"))

        commands.sort()
        return commands

    def get_command(self, ctx: click.Context | None, name: str) -> click.Command | None:
        """
        Loads and returns the requested command dynamically.
        """
        # Map hyphens back to underscores to find the correct Python module
        module_suffix = name.replace("-", "_")

        if self.cmd_prefix:
            module_name = f"{COMMANDS_MODULE.__name__}.{self.cmd_prefix}__{module_suffix}"
        else:
            module_name = f"{COMMANDS_MODULE.__name__}.{module_suffix}"

        try:
            mod = importlib.import_module(module_name)
        except ImportError as e:
            click.secho(f"Error loading command '{name}': {e}", fg="red", err=True)
            return None

        if not hasattr(mod, "cli"):
            click.secho(f"Command module '{name}' does not define a 'cli' entrypoint.", fg="red", err=True)
            return None

        cmd = mod.cli
        if not isinstance(cmd, click.Command):
            click.secho(f"Entrypoint 'cli' in module '{name}' is not a Click Command/Group.", fg="red", err=True)
            return None

        return cmd
