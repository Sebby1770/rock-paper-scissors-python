#!/usr/bin/env python3
"""Mac Python Launcher entry point for Rock, Paper, Scissors."""

from __future__ import annotations

from rock_paper_scissors import main


if __name__ == "__main__":
    try:
        exit_code = main()
    except KeyboardInterrupt:
        print("\nGame cancelled.")
        exit_code = 130

    try:
        input("\nPress Enter to close this window...")
    except EOFError:
        pass

    raise SystemExit(exit_code)
