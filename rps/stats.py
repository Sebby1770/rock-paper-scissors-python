"""Lifetime stats persistence for Rock Paper Scissors."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from rps.game import Choice, RoundResult, Scoreboard

DEFAULT_FILENAME = ".rps_stats.json"
ENV_STATS_PATH = "RPS_STATS_PATH"


@dataclass
class LifetimeStats:
    """Cumulative stats across game sessions."""

    wins: int = 0
    losses: int = 0
    ties: int = 0
    best_streak: int = 0
    games_played: int = 0
    rounds_played: int = 0
    move_counts: dict[str, int] = field(default_factory=dict)

    def record_session(self, board: Scoreboard) -> None:
        """Merge a finished session scoreboard into lifetime totals."""

        self.wins += board.wins
        self.losses += board.losses
        self.ties += board.ties
        self.games_played += 1
        self.rounds_played += board.rounds_played
        if board.best_streak > self.best_streak:
            self.best_streak = board.best_streak
        for result in board.history:
            key = str(result.player_choice)
            self.move_counts[key] = self.move_counts.get(key, 0) + 1

    def record_round(self, result: RoundResult) -> None:
        """Merge a single round into lifetime totals (for live updates)."""

        if result.outcome == "win":
            self.wins += 1
        elif result.outcome == "lose":
            self.losses += 1
        else:
            self.ties += 1
        self.rounds_played += 1
        key = str(result.player_choice)
        self.move_counts[key] = self.move_counts.get(key, 0) + 1

    @property
    def win_rate(self) -> float | None:
        """Return wins / (wins + losses), or None when no decided rounds exist."""

        decided = self.wins + self.losses
        if decided == 0:
            return None
        return self.wins / decided

    @property
    def favorite_move(self) -> str | None:
        """Return the most-played player move, or None if no data."""

        if not self.move_counts:
            return None
        max_count = max(self.move_counts.values())
        # Stable pick: first among ties sorted alphabetically.
        favorites = sorted(m for m, n in self.move_counts.items() if n == max_count)
        return favorites[0] if favorites else None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LifetimeStats:
        return cls(
            wins=int(data.get("wins", 0)),
            losses=int(data.get("losses", 0)),
            ties=int(data.get("ties", 0)),
            best_streak=int(data.get("best_streak", 0)),
            games_played=int(data.get("games_played", 0)),
            rounds_played=int(data.get("rounds_played", 0)),
            move_counts={str(k): int(v) for k, v in dict(data.get("move_counts", {})).items()},
        )

    def format_report(self) -> str:
        """Return a multi-line human-readable stats report."""

        fav = self.favorite_move or "(none)"
        rate = f"{self.win_rate * 100:.1f}%" if self.win_rate is not None else "(none)"
        lines = [
            "Lifetime stats",
            f"  Games played : {self.games_played}",
            f"  Rounds played: {self.rounds_played}",
            f"  Wins         : {self.wins}",
            f"  Losses       : {self.losses}",
            f"  Ties         : {self.ties}",
            f"  Win rate     : {rate}",
            f"  Best streak  : {self.best_streak}",
            f"  Favorite move: {fav}",
        ]
        if self.move_counts:
            lines.append("  Move counts  :")
            for move in sorted(self.move_counts):
                lines.append(f"    {move}: {self.move_counts[move]}")
        return "\n".join(lines)


def default_stats_path() -> Path:
    """Resolve the stats file path.

    Priority:
    1. ``RPS_STATS_PATH`` environment variable
    2. ``./.rps_stats.json`` if it already exists in the cwd
    3. ``~/.rps_stats.json``
    """

    env = os.environ.get(ENV_STATS_PATH)
    if env:
        return Path(env).expanduser()

    local = Path.cwd() / DEFAULT_FILENAME
    if local.exists():
        return local

    return Path.home() / DEFAULT_FILENAME


def load_stats(path: Path | None = None) -> LifetimeStats:
    """Load stats from disk, or return empty stats if missing/corrupt."""

    target = path if path is not None else default_stats_path()
    if not target.exists():
        return LifetimeStats()
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return LifetimeStats()
        return LifetimeStats.from_dict(raw)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return LifetimeStats()


def save_stats(stats: LifetimeStats, path: Path | None = None) -> Path:
    """Write stats to disk and return the path used."""

    target = path if path is not None else default_stats_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(stats.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target


def reset_stats(path: Path | None = None) -> Path:
    """Clear stats by writing an empty file (or removing if desired).

    Returns the path that was reset.
    """

    target = path if path is not None else default_stats_path()
    empty = LifetimeStats()
    save_stats(empty, target)
    return target


def track_move(stats: LifetimeStats, choice: Choice | str) -> None:
    """Increment the count for a player move."""

    key = str(choice)
    stats.move_counts[key] = stats.move_counts.get(key, 0) + 1


def export_stats_csv(stats: LifetimeStats, path: Path) -> Path:
    """Write a one-table CSV summary of lifetime stats and return the path."""

    rows = [
        ("metric", "value"),
        ("wins", str(stats.wins)),
        ("losses", str(stats.losses)),
        ("ties", str(stats.ties)),
        ("best_streak", str(stats.best_streak)),
        ("games_played", str(stats.games_played)),
        ("rounds_played", str(stats.rounds_played)),
        ("favorite_move", stats.favorite_move or ""),
        (
            "win_rate",
            f"{stats.win_rate:.4f}" if stats.win_rate is not None else "",
        ),
    ]
    for move in sorted(stats.move_counts):
        rows.append((f"move_{move}", str(stats.move_counts[move])))

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "".join(f"{metric},{value}\n" for metric, value in rows),
        encoding="utf-8",
    )
    return target
