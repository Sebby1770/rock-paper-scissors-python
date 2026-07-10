"""Core Rock Paper Scissors / RPSLS game logic."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Literal

Mode = Literal["classic", "rpsls"]
Choice = Literal["rock", "paper", "scissors", "lizard", "spock"]
Outcome = Literal["win", "lose", "tie"]

OPTIONS_CLASSIC: tuple[Choice, ...] = ("rock", "paper", "scissors")
OPTIONS_RPSLS: tuple[Choice, ...] = ("rock", "paper", "scissors", "lizard", "spock")

# Each choice maps to the set of choices it beats.
BEATS_CLASSIC: dict[Choice, frozenset[Choice]] = {
    "rock": frozenset({"scissors"}),
    "paper": frozenset({"rock"}),
    "scissors": frozenset({"paper"}),
}

BEATS_RPSLS: dict[Choice, frozenset[Choice]] = {
    "rock": frozenset({"scissors", "lizard"}),
    "paper": frozenset({"rock", "spock"}),
    "scissors": frozenset({"paper", "lizard"}),
    "lizard": frozenset({"spock", "paper"}),
    "spock": frozenset({"scissors", "rock"}),
}

# Backward-compatible single-target map (classic only).
BEATS: dict[str, str] = {
    "rock": "scissors",
    "paper": "rock",
    "scissors": "paper",
}

ALIASES_CLASSIC: dict[str, Choice] = {
    "1": "rock",
    "r": "rock",
    "rock": "rock",
    "2": "paper",
    "p": "paper",
    "paper": "paper",
    "3": "scissors",
    "s": "scissors",
    "scissor": "scissors",
    "scissors": "scissors",
}

ALIASES_RPSLS: dict[str, Choice] = {
    **ALIASES_CLASSIC,
    "4": "lizard",
    "l": "lizard",
    "lizard": "lizard",
    "5": "spock",
    "k": "spock",  # spocK — 's' is taken by scissors
    "v": "spock",  # Vulcan
    "spock": "spock",
}

ICONS: dict[Choice, str] = {
    "rock": "✊",
    "paper": "✋",
    "scissors": "✌️",
    "lizard": "🦎",
    "spock": "🖖",
}

# Verb phrases for flavourful win messages (attacker beats defender).
WIN_VERBS: dict[tuple[Choice, Choice], str] = {
    ("rock", "scissors"): "crushes",
    ("rock", "lizard"): "crushes",
    ("paper", "rock"): "covers",
    ("paper", "spock"): "disproves",
    ("scissors", "paper"): "cut",
    ("scissors", "lizard"): "decapitate",
    ("lizard", "spock"): "poisons",
    ("lizard", "paper"): "eats",
    ("spock", "scissors"): "smashes",
    ("spock", "rock"): "vaporizes",
}


def options_for_mode(mode: Mode = "classic") -> tuple[Choice, ...]:
    """Return the valid choices for a game mode."""

    if mode == "rpsls":
        return OPTIONS_RPSLS
    if mode == "classic":
        return OPTIONS_CLASSIC
    raise ValueError(f"Unknown mode: {mode!r}. Use 'classic' or 'rpsls'.")


def beats_map_for_mode(mode: Mode = "classic") -> dict[Choice, frozenset[Choice]]:
    """Return the BEATS mapping for a game mode."""

    if mode == "rpsls":
        return BEATS_RPSLS
    if mode == "classic":
        return BEATS_CLASSIC
    raise ValueError(f"Unknown mode: {mode!r}. Use 'classic' or 'rpsls'.")


def aliases_for_mode(mode: Mode = "classic") -> dict[str, Choice]:
    """Return input aliases for a game mode."""

    if mode == "rpsls":
        return ALIASES_RPSLS
    if mode == "classic":
        return ALIASES_CLASSIC
    raise ValueError(f"Unknown mode: {mode!r}. Use 'classic' or 'rpsls'.")


def normalize_choice(raw_choice: str, mode: Mode = "classic") -> Choice:
    """Convert user input into a game choice for the given mode."""

    choice = raw_choice.strip().lower()
    aliases = aliases_for_mode(mode)
    try:
        return aliases[choice]
    except KeyError as exc:
        opts = ", ".join(options_for_mode(mode))
        raise ValueError(f"Choose {opts}.") from exc


def decide_winner(
    player_choice: Choice | str,
    computer_choice: Choice | str,
    mode: Mode = "classic",
) -> Outcome:
    """Return the player's outcome for a validated pair of choices."""

    options = options_for_mode(mode)
    beats = beats_map_for_mode(mode)

    if player_choice not in options or computer_choice not in options:
        opts = ", ".join(options)
        raise ValueError(f"Choices must be one of: {opts}.")

    if player_choice == computer_choice:
        return "tie"
    if computer_choice in beats[player_choice]:  # type: ignore[index]
        return "win"
    return "lose"


def _outcome_message(
    player_choice: Choice,
    computer_choice: Choice,
    outcome: Outcome,
) -> str:
    """Build a human-readable result message."""

    if outcome == "tie":
        return f"Both chose {player_choice}. It is a tie."

    if outcome == "win":
        verb = WIN_VERBS.get((player_choice, computer_choice), "beats")
        return f"{player_choice.title()} {verb} {computer_choice}. You win!"

    verb = WIN_VERBS.get((computer_choice, player_choice), "beats")
    return f"{computer_choice.title()} {verb} {player_choice}. You lose."


@dataclass(frozen=True)
class RoundResult:
    """The result of one round."""

    player_choice: Choice
    computer_choice: Choice
    outcome: Outcome
    message: str


@dataclass
class Scoreboard:
    """Running scores, streak, and round history for a session."""

    wins: int = 0
    losses: int = 0
    ties: int = 0
    current_streak: int = 0
    best_streak: int = 0
    history: list[RoundResult] = field(default_factory=list)

    def record(self, result: RoundResult) -> None:
        """Apply a round result to the scoreboard."""

        self.history.append(result)
        if result.outcome == "win":
            self.wins += 1
            self.current_streak += 1
            if self.current_streak > self.best_streak:
                self.best_streak = self.current_streak
        elif result.outcome == "lose":
            self.losses += 1
            self.current_streak = 0
        else:
            self.ties += 1
            # Ties do not break or extend the win streak.

    @property
    def rounds_played(self) -> int:
        return len(self.history)

    def summary(self) -> str:
        """Return a one-line score summary."""

        return (
            f"wins: {self.wins} losses: {self.losses} ties: {self.ties} "
            f"(streak: {self.current_streak}, best: {self.best_streak})"
        )

    def match_over(self, best_of: int | None) -> bool:
        """Return True when a best-of-N match has a decisive winner."""

        if best_of is None:
            return False
        if best_of < 1:
            raise ValueError("best_of must be a positive integer.")
        needed = best_of // 2 + 1
        return self.wins >= needed or self.losses >= needed

    def match_winner(self, best_of: int | None) -> Outcome | None:
        """Return 'win'/'lose' if the match is decided, else None."""

        if not self.match_over(best_of):
            return None
        assert best_of is not None
        needed = best_of // 2 + 1
        if self.wins >= needed:
            return "win"
        if self.losses >= needed:
            return "lose"
        return None


def play_round(
    player_input: str,
    computer_choice: Choice | str | None = None,
    rng: random.Random | None = None,
    mode: Mode = "classic",
    ai_choice: Choice | str | None = None,
) -> RoundResult:
    """Play a single round and return a structured result.

    Parameters
    ----------
    player_input:
        Raw player input (name, alias, or number).
    computer_choice:
        Optional fixed computer choice (also accepted as ``ai_choice``).
    rng:
        Optional RNG used when the computer choice is not fixed.
    mode:
        ``classic`` (3 options) or ``rpsls`` (5 options).
    ai_choice:
        Alias for ``computer_choice`` used by the AI layer.
    """

    if computer_choice is None and ai_choice is not None:
        computer_choice = ai_choice

    player_choice = normalize_choice(player_input, mode=mode)
    options = options_for_mode(mode)

    if computer_choice is None:
        chooser = rng if rng is not None else random
        computer: Choice = chooser.choice(options)
    else:
        computer = computer_choice  # type: ignore[assignment]
        if computer not in options:
            opts = ", ".join(options)
            raise ValueError(f"Computer choice must be one of: {opts}.")

    outcome = decide_winner(player_choice, computer, mode=mode)
    message = _outcome_message(player_choice, computer, outcome)
    return RoundResult(player_choice, computer, outcome, message)
