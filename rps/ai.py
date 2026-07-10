"""AI opponent strategies for Rock Paper Scissors / RPSLS."""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Callable

from rps.game import Choice, Mode, beats_map_for_mode, options_for_mode

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


_STRATEGIES: dict[str, Callable[..., AIStrategy]] = {
    "random": RandomAI,
    "biased": BiasedAI,
    "counter": CounterAI,
    "markov": MarkovAI,
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
