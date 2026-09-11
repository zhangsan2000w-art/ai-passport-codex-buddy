"""Cross-platform desktop controller for Codex Buddy devices."""

import sys


def _configure_console_output() -> None:
    """Keep localized install messages from crashing narrow console codepages."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


_configure_console_output()
