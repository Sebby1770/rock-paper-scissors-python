"""Tests for lifetime stats persistence."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from rps.game import Scoreboard, play_round
from rps.stats import (
    LifetimeStats,
    export_stats_csv,
    load_stats,
    reset_stats,
    save_stats,
)


class LifetimeStatsTests(unittest.TestCase):
    def test_record_session_and_favorite(self):
        board = Scoreboard()
        board.record(play_round("rock", computer_choice="scissors"))
        board.record(play_round("rock", computer_choice="scissors"))
        board.record(play_round("paper", computer_choice="rock"))

        stats = LifetimeStats()
        stats.record_session(board)

        self.assertEqual(stats.wins, 3)
        self.assertEqual(stats.games_played, 1)
        self.assertEqual(stats.rounds_played, 3)
        self.assertEqual(stats.favorite_move, "rock")
        self.assertEqual(stats.best_streak, 3)

    def test_record_round(self):
        stats = LifetimeStats()
        stats.record_round(play_round("scissors", computer_choice="paper"))
        self.assertEqual(stats.wins, 1)
        self.assertEqual(stats.rounds_played, 1)
        self.assertEqual(stats.move_counts["scissors"], 1)

    def test_favorite_none_when_empty(self):
        self.assertIsNone(LifetimeStats().favorite_move)

    def test_win_rate_ignores_ties(self):
        stats = LifetimeStats(wins=3, losses=1, ties=6)
        self.assertEqual(stats.win_rate, 0.75)
        self.assertIsNone(LifetimeStats().win_rate)

    def test_format_report_contains_headers(self):
        stats = LifetimeStats(wins=1, losses=2, ties=3, best_streak=4)
        report = stats.format_report()
        self.assertIn("Wins", report)
        self.assertIn("Best streak", report)
        self.assertIn("Win rate", report)


class StatsFileTests(unittest.TestCase):
    def test_save_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "stats.json"
            stats = LifetimeStats(wins=5, losses=2, ties=1, best_streak=3)
            stats.move_counts = {"rock": 4, "paper": 1}
            save_stats(stats, path)

            loaded = load_stats(path)
            self.assertEqual(loaded.wins, 5)
            self.assertEqual(loaded.losses, 2)
            self.assertEqual(loaded.ties, 1)
            self.assertEqual(loaded.best_streak, 3)
            self.assertEqual(loaded.move_counts["rock"], 4)
            self.assertTrue(path.exists())
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["wins"], 5)

    def test_load_missing_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nope.json"
            loaded = load_stats(path)
            self.assertEqual(loaded.wins, 0)
            self.assertEqual(loaded.games_played, 0)

    def test_load_corrupt_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text("{not json", encoding="utf-8")
            loaded = load_stats(path)
            self.assertEqual(loaded.wins, 0)

    def test_reset_stats(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "stats.json"
            save_stats(LifetimeStats(wins=99, losses=1), path)
            reset_stats(path)
            loaded = load_stats(path)
            self.assertEqual(loaded.wins, 0)
            self.assertEqual(loaded.losses, 0)

    def test_export_stats_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "stats.csv"
            stats = LifetimeStats(wins=4, losses=1, ties=2, best_streak=3, games_played=2)
            stats.move_counts = {"rock": 5, "paper": 1}
            written = export_stats_csv(stats, path)
            text = written.read_text(encoding="utf-8")
            self.assertIn("wins,4", text)
            self.assertIn("favorite_move,rock", text)
            self.assertIn("move_paper,1", text)


if __name__ == "__main__":
    unittest.main()
