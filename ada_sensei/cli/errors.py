from __future__ import annotations


class CLIError(Exception):
    """A user-facing CLI error; renders with exit code 2 and no stack trace."""