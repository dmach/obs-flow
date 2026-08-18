from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import click
import msgspec


# style can be either a string ("green"), a dict ({"fg": "green", "bold": True}) or a callable
StyleType = str | dict[str, Any] | Callable[[Any], str | dict[str, Any]]


@dataclass(kw_only=True)
class Field:
    """
    Info about how a msgspec.Struct field should be rendered.
    """

    label: str | None = None
    style: StyleType | None = None
    formatter: Callable[[Any], str] | None = None
    include_none: bool = False  # show the field only if it contains None
    verbose_only: bool = False  # show the field only in the verbose mode

    @staticmethod
    def format_datetime(value: Any) -> str:
        if not value:
            return ""

        if isinstance(value, datetime):
            dt = value
        else:
            dt = datetime.fromisoformat(value)
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def format_yes_no(value: Any) -> str:
        if isinstance(value, str):
            if value.lower() in ["1", "yes", "true", "on"]:
                return "yes"
            if value.lower() in ["0", "no", "false", "off"]:
                return "no"
        return "yes" if value else "no"


class Renderer:
    """
    Base class for renderers that render msgspec.Struct or [msgspec.Struct].
    """

    _fields: dict[str, Field]

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._fields = {k: v for k, v in cls.__dict__.items() if isinstance(v, Field)}

    def __init__(self, data: Any):
        self.data = data

    def render(
        self,
        fmt: str = "text",
        verbose: bool = False,
    ) -> None:
        if fmt == "json":
            self.render_json()
        else:
            self.render_text(verbose=verbose)

    def render_text(self, verbose: bool = False) -> None:
        """
        Render as human readable text, a key-value table.
        """
        if isinstance(self.data, list):
            for num, item in enumerate(self.data):
                if num > 0:
                    click.echo("---")
                self._render_item_text(item, verbose=verbose)
        elif self.data is not None:
            self._render_item_text(self.data, verbose=verbose)

    def _render_item_text(self, item: Any, verbose: bool) -> None:
        # process labels first
        labels = {}
        label_max_length = 0
        for field_name, field_cfg in self._fields.items():
            # determine label and cache it and remember the max lengh
            label = field_cfg.label if field_cfg.label else field_name.replace("_", " ").capitalize()
            labels[field_name] = label
            label_max_length = max(label_max_length, len(label))

        for field_name, field_cfg in self._fields.items():
            raw_value = getattr(item, field_name, None)

            if raw_value is None and not field_cfg.include_none:
                continue

            if field_cfg.verbose_only and not verbose:
                continue

            # format raw_value to sting
            if field_cfg.formatter and raw_value is not None:
                value_str = str(field_cfg.formatter(raw_value))
            else:
                value_str = "" if raw_value is None else str(raw_value)

            # apply style
            style = field_cfg.style
            if callable(style):
                style = style(raw_value)

            if style:
                if isinstance(style, str):
                    styled_val = click.style(value_str, fg=style)
                else:
                    styled_val = click.style(value_str, **style)
            else:
                styled_val = value_str

            label = labels[field_name]
            click.echo(f"{label:<{label_max_length}} : {styled_val}")

    def render_json(self) -> None:
        """
        Render as json.
        """
        if self.data is None:
            return
        json_bytes = msgspec.json.encode(self.data)
        json_bytes = msgspec.json.format(json_bytes, indent=2)
        click.echo(json_bytes.decode("utf-8"))
