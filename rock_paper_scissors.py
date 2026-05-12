#!/usr/bin/env python3
"""A tiny command-line Rock, Paper, Scissors game."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Literal


Choice = Literal["rock", "paper", "scissors"]
Outcome = Literal["win", "lose", "tie"]

OPTIONS: tuple[Choice, ...] = ("rock", "paper", "scissors")
ALIASES: dict[str, Choice] = {
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
BEATS: dict[Choice, Choice] = {
    "rock": "scissors",
    "paper": "rock",
    "scissors": "paper",
}


@dataclass(frozen=True)
class RoundResult:
    """The result of one round."""

    player_choice: Choice
    computer_choice: Choice
    outcome: Outcome
    message: str


def normalize_choice(raw_choice: str) -> Choice:
    """Convert user input into a game choice."""

    choice = raw_choice.strip().lower()
    try:
        return ALIASES[choice]
    except KeyError as exc:
        raise ValueError("Choose rock, paper, or scissors.") from exc


def decide_winner(player_choice: Choice, computer_choice: Choice) -> Outcome:
    """Return the player's outcome for a validated pair of choices."""

    if player_choice not in OPTIONS or computer_choice not in OPTIONS:
        raise ValueError("Choices must be rock, paper, or scissors.")

    if player_choice == computer_choice:
        return "tie"
    if BEATS[player_choice] == computer_choice:
        return "win"
    return "lose"


def play_round(
    player_input: str,
    computer_choice: Choice | None = None,
    rng: random.Random | None = None,
) -> RoundResult:
    """Play a single round and return a structured result."""

    player_choice = normalize_choice(player_input)
    chooser = rng if rng is not None else random
    computer = computer_choice if computer_choice is not None else chooser.choice(OPTIONS)
    outcome = decide_winner(player_choice, computer)

    if outcome == "tie":
        message = f"Both chose {player_choice}. It is a tie."
    elif outcome == "win":
        message = f"{player_choice.title()} beats {computer}. You win!"
    else:
        message = f"{computer.title()} beats {player_choice}. You lose."

    return RoundResult(player_choice, computer, outcome, message)


def main() -> int:
    """Run the interactive game loop."""

    scores = {"win": 0, "lose": 0, "tie": 0}

    print("Rock, Paper, Scissors")
    print("Type rock, paper, scissors, or q to quit.")

    while True:
        player_input = input("\nYour choice: ").strip()
        if player_input.lower() in {"q", "quit", "exit"}:
            break

        try:
            result = play_round(player_input)
        except ValueError as error:
            print(error)
            continue

        scores[result.outcome] += 1
        print(f"Computer chose: {result.computer_choice}")
        print(result.message)
        print(
            "Score "
            f"- wins: {scores['win']} "
            f"losses: {scores['lose']} "
            f"ties: {scores['tie']}"
        )

    print("\nThanks for playing!")
    print(
        "Final score "
        f"- wins: {scores['win']} "
        f"losses: {scores['lose']} "
        f"ties: {scores['tie']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
