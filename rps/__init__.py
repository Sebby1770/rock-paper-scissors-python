"""Rock Paper Scissors (and RPSLS) game suite."""

from __future__ import annotations

from rps.game import (
    BEATS,
    BEATS_CLASSIC,
    BEATS_RPSLS,
    OPTIONS_CLASSIC,
    OPTIONS_RPSLS,
    Choice,
    Mode,
    Outcome,
    RoundResult,
    Scoreboard,
    decide_winner,
    normalize_choice,
    options_for_mode,
    play_round,
)

__version__ = "2.0.0"

__all__ = [
    "BEATS",
    "BEATS_CLASSIC",
    "BEATS_RPSLS",
    "OPTIONS_CLASSIC",
    "OPTIONS_RPSLS",
    "Choice",
    "Mode",
    "Outcome",
    "RoundResult",
    "Scoreboard",
    "decide_winner",
    "normalize_choice",
    "options_for_mode",
    "play_round",
    "__version__",
]
