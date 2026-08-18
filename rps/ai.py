"""AI opponent strategies for Rock Paper Scissors / RPSLS."""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Any, Callable

from rps.game import Choice, Mode, beats_map_for_mode, decide_winner, options_for_mode

AIName = str


class AIStrategy(ABC):
    """Base class for computer opponents."""

    name: str = "base"

    def __init__(self, mode: Mode = "classic", rng: random.Random | None = None) -> None:
        self.mode = mode
        self.rng = rng if rng is not None else random.Random()
        self.options = options_for_mode(mode)
        self.beats = beats_map_for_mode(mode)

    @abstractmethod
    def choose(self) -> Choice:
        """Return the computer's next move."""

    def observe(self, player_choice: Choice, computer_choice: Choice) -> None:
        """Update internal state after a round. Default: no-op."""

    def counter_to(self, move: Choice) -> Choice:
        """Return a move that beats ``move`` (picked at random if several)."""

        counters = [opt for opt in self.options if move in self.beats[opt]]
        if not counters:
            return self.rng.choice(self.options)
        return self.rng.choice(counters)


class RandomAI(AIStrategy):
    """Uniform random choice among valid options."""

    name = "random"

    def choose(self) -> Choice:
        return self.rng.choice(self.options)


class BiasedAI(AIStrategy):
    """Slightly prefers rock over other options."""

    name = "biased"

    def choose(self) -> Choice:
        # Rock gets a higher weight; remaining mass is split evenly.
        n = len(self.options)
        if n == 0:
            raise RuntimeError("No options available.")
        rock_weight = 0.4 if "rock" in self.options else 0.0
        remaining = 1.0 - rock_weight
        others = [o for o in self.options if o != "rock"]
        other_weight = remaining / len(others) if others else 0.0
        weights = [
            rock_weight if opt == "rock" else other_weight for opt in self.options
        ]
        return self.rng.choices(self.options, weights=weights, k=1)[0]


class CounterAI(AIStrategy):
    """Counters the player's most recent move; random on the first round."""

    name = "counter"

    def __init__(self, mode: Mode = "classic", rng: random.Random | None = None) -> None:
        super().__init__(mode=mode, rng=rng)
        self._last_player: Choice | None = None

    def choose(self) -> Choice:
        if self._last_player is None:
            return self.rng.choice(self.options)
        return self.counter_to(self._last_player)

    def observe(self, player_choice: Choice, computer_choice: Choice) -> None:
        self._last_player = player_choice


class MarkovAI(AIStrategy):
    """Predict the player's next move from 1-step transition frequencies."""

    name = "markov"

    def __init__(self, mode: Mode = "classic", rng: random.Random | None = None) -> None:
        super().__init__(mode=mode, rng=rng)
        self._last_player: Choice | None = None
        # transitions[prev][next] = count
        self._transitions: dict[Choice, dict[Choice, int]] = defaultdict(
            lambda: defaultdict(int)
        )

    def choose(self) -> Choice:
        if self._last_player is None:
            return self.rng.choice(self.options)

        counts = self._transitions.get(self._last_player)
        if not counts:
            return self.rng.choice(self.options)

        # Predict the most frequent follow-up; break ties with RNG.
        max_count = max(counts.values())
        candidates = [move for move, n in counts.items() if n == max_count]
        predicted = self.rng.choice(candidates)
        return self.counter_to(predicted)

    def observe(self, player_choice: Choice, computer_choice: Choice) -> None:
        if self._last_player is not None:
            self._transitions[self._last_player][player_choice] += 1
        self._last_player = player_choice


class PatternBreakAI(AIStrategy):
    """Punish repeats; otherwise avoid the obvious counter to the last move."""

    name = "pattern-break"

    def __init__(self, mode: Mode = "classic", rng: random.Random | None = None) -> None:
        super().__init__(mode=mode, rng=rng)
        self._history: list[Choice] = []

    def choose(self) -> Choice:
        if len(self._history) < 2:
            return self.rng.choice(self.options)

        last = self._history[-1]
        previous = self._history[-2]
        if last == previous:
            return self.counter_to(last)

        obvious = self.counter_to(last)
        alternatives = [opt for opt in self.options if opt != obvious]
        if not alternatives:
            return self.rng.choice(self.options)
        return self.rng.choice(alternatives)

    def observe(self, player_choice: Choice, computer_choice: Choice) -> None:
        self._history.append(player_choice)


class AdaptiveAI(AIStrategy):
    """Switch strategy from the current match record.

    Behind by two or more: pattern-break. Ahead by two or more: counter.
    Otherwise markov.
    """

    name = "adaptive"

    def __init__(self, mode: Mode = "classic", rng: random.Random | None = None) -> None:
        super().__init__(mode=mode, rng=rng)
        self._markov = MarkovAI(mode=mode, rng=rng)
        self._counter = CounterAI(mode=mode, rng=rng)
        self._pattern = PatternBreakAI(mode=mode, rng=rng)
        self._wins = 0
        self._losses = 0
        self.active_strategy = "markov"

    def choose(self) -> Choice:
        margin = self._wins - self._losses
        if margin <= -2:
            self.active_strategy = "pattern-break"
            return self._pattern.choose()
        if margin >= 2:
            self.active_strategy = "counter"
            return self._counter.choose()
        self.active_strategy = "markov"
        return self._markov.choose()

    def observe(self, player_choice: Choice, computer_choice: Choice) -> None:
        player_outcome = decide_winner(player_choice, computer_choice, mode=self.mode)
        if player_outcome == "lose":
            self._wins += 1
        elif player_outcome == "win":
            self._losses += 1
        self._markov.observe(player_choice, computer_choice)
        self._counter.observe(player_choice, computer_choice)
        self._pattern.observe(player_choice, computer_choice)


_STRATEGIES: dict[str, Callable[..., AIStrategy]] = {
    "random": RandomAI,
    "biased": BiasedAI,
    "counter": CounterAI,
    "markov": MarkovAI,
    "pattern-break": PatternBreakAI,
    "adaptive": AdaptiveAI,
}


def available_ais() -> tuple[str, ...]:
    """Return the names of registered AI strategies."""

    return tuple(_STRATEGIES.keys())


def create_ai(
    name: str = "random",
    mode: Mode = "classic",
    rng: random.Random | None = None,
) -> AIStrategy:
    """Construct an AI strategy by name."""

    key = name.strip().lower()
    try:
        cls = _STRATEGIES[key]
    except KeyError as exc:
        known = ", ".join(available_ais())
        raise ValueError(f"Unknown AI strategy {name!r}. Choose from: {known}.") from exc
    return cls(mode=mode, rng=rng)


def play_ai_match(
    first: AIStrategy,
    second: AIStrategy,
    rounds: int,
    mode: Mode = "classic",
) -> dict[str, Any]:
    """Play ``rounds`` of first-vs-second and return the first AI's record."""

    if rounds < 1:
        raise ValueError("rounds must be a positive integer.")

    wins = losses = ties = 0
    for _ in range(rounds):
        first_move = first.choose()
        second_move = second.choose()
        outcome = decide_winner(first_move, second_move, mode=mode)
        first.observe(second_move, first_move)
        second.observe(first_move, second_move)
        if outcome == "win":
            wins += 1
        elif outcome == "lose":
            losses += 1
        else:
            ties += 1

    return {
        "first": first.name,
        "second": second.name,
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "rounds": rounds,
    }


def run_tournament(
    names: tuple[str, ...] | list[str] | None = None,
    *,
    rounds: int = 30,
    mode: Mode = "classic",
    seed: int | None = None,
) -> dict[str, Any]:
    """Round-robin every named AI against every other named AI."""

    if rounds < 1:
        raise ValueError("rounds must be a positive integer.")

    contestants = tuple(names) if names else available_ais()
    if len(contestants) < 2:
        raise ValueError("A tournament needs at least two AIs.")

    rng = random.Random(seed)
    standings: dict[str, dict[str, int | str]] = {
        name: {"name": name, "wins": 0, "losses": 0, "ties": 0, "matches": 0}
        for name in contestants
    }
    matches: list[dict[str, Any]] = []

    for index, first_name in enumerate(contestants):
        for second_name in contestants[index + 1 :]:
            first = create_ai(
                first_name, mode=mode, rng=random.Random(rng.randint(0, 1_000_000_000))
            )
            second = create_ai(
                second_name, mode=mode, rng=random.Random(rng.randint(0, 1_000_000_000))
            )
            result = play_ai_match(first, second, rounds, mode=mode)
            matches.append(result)
            standings[first_name]["wins"] = int(standings[first_name]["wins"]) + result["wins"]
            standings[first_name]["losses"] = int(standings[first_name]["losses"]) + result["losses"]
            standings[first_name]["ties"] = int(standings[first_name]["ties"]) + result["ties"]
            standings[first_name]["matches"] = int(standings[first_name]["matches"]) + 1
            standings[second_name]["wins"] = int(standings[second_name]["wins"]) + result["losses"]
            standings[second_name]["losses"] = int(standings[second_name]["losses"]) + result["wins"]
            standings[second_name]["ties"] = int(standings[second_name]["ties"]) + result["ties"]
            standings[second_name]["matches"] = int(standings[second_name]["matches"]) + 1

    ranking = sorted(
        standings.values(),
        key=lambda row: (-int(row["wins"]), int(row["losses"]), str(row["name"])),
    )
    return {
        "mode": mode,
        "rounds": rounds,
        "seed": seed,
        "standings": ranking,
        "matches": matches,
    }
