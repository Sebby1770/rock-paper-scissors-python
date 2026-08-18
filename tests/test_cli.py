"""Tests for CLI helpers and non-interactive entry points."""

from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rps.cli import build_parser, main, paint, run_game, supports_color
from rps.stats import LifetimeStats, load_stats, save_stats


class ParserTests(unittest.TestCase):
    def test_defaults(self):
        parser = build_parser()
        args = parser.parse_args([])
        self.assertEqual(args.mode, "classic")
        self.assertEqual(args.ai, "random")
        self.assertIsNone(args.best_of)
        self.assertIsNone(args.seed)
        self.assertFalse(args.no_color)
        self.assertFalse(args.tournament)
        self.assertEqual(args.tournament_rounds, 30)
        self.assertIsNone(args.export_stats)

    def test_flags(self):
        parser = build_parser()
        args = parser.parse_args(
            ["--mode", "rpsls", "--ai", "markov", "--best-of", "5", "--seed", "7", "--no-color"]
        )
        self.assertEqual(args.mode, "rpsls")
        self.assertEqual(args.ai, "markov")
        self.assertEqual(args.best_of, 5)
        self.assertEqual(args.seed, 7)
        self.assertTrue(args.no_color)


class ColorTests(unittest.TestCase):
    def test_paint_disabled(self):
        self.assertEqual(paint("hi", "\033[31m", enabled=False), "hi")

    def test_paint_enabled(self):
        out = paint("hi", "\033[31m", enabled=True)
        self.assertIn("hi", out)
        self.assertIn("\033[31m", out)

    def test_supports_color_no_color_flag(self):
        self.assertFalse(supports_color(no_color=True))


class MainEntryTests(unittest.TestCase):
    def test_stats_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.json"
            save_stats(LifetimeStats(wins=3, losses=1, ties=0, best_streak=2), path)
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                code = main(["--stats", "--stats-file", str(path)])
            self.assertEqual(code, 0)
            self.assertIn("Wins", buf.getvalue())
            self.assertIn("3", buf.getvalue())

    def test_reset_stats_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.json"
            save_stats(LifetimeStats(wins=9), path)
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                code = main(["--reset-stats", "--stats-file", str(path)])
            self.assertEqual(code, 0)
            self.assertEqual(load_stats(path).wins, 0)

    def test_export_stats_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            stats_path = Path(tmp) / "s.json"
            csv_path = Path(tmp) / "s.csv"
            save_stats(LifetimeStats(wins=6, losses=2), stats_path)
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                code = main(
                    ["--export-stats", str(csv_path), "--stats-file", str(stats_path)]
                )
            self.assertEqual(code, 0)
            self.assertTrue(csv_path.exists())
            self.assertIn("wins,6", csv_path.read_text(encoding="utf-8"))

    def test_tournament_flag(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code = main(["--tournament", "--tournament-rounds", "4", "--seed", "1"])
        self.assertEqual(code, 0)
        output = buf.getvalue()
        self.assertIn("Tournament", output)
        self.assertIn("pattern-break", output)

    def test_run_game_best_of_and_quit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.json"
            inputs = iter(["rock", "q"])
            lines: list[str] = []

            def fake_input(prompt=""):
                return next(inputs)

            code = run_game(
                mode="classic",
                ai_name="random",
                best_of=5,
                seed=1,
                no_color=True,
                use_icons=False,
                stats_path=path,
                input_fn=fake_input,
                output_fn=lines.append,
            )
            self.assertEqual(code, 0)
            joined = "\n".join(lines)
            self.assertIn("Best-of-5", joined)
            self.assertIn("Thanks for playing", joined)
            # One round should have been persisted.
            stats = load_stats(path)
            self.assertEqual(stats.rounds_played, 1)
            self.assertEqual(stats.games_played, 1)

    def test_run_game_best_of_auto_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.json"
            # Counter AI with seeded rng; force wins by mocking play via fixed inputs
            # Use ai that we can beat: random with seed, keep playing rock until match ends
            # For reliability, use best_of=1 so one decisive non-tie ends it — but ties possible.
            # Instead feed enough moves and let best_of=3 with a scripted computer via seed.
            moves = ["rock"] * 20

            def fake_input(prompt=""):
                if not moves:
                    return "q"
                return moves.pop(0)

            lines: list[str] = []
            code = run_game(
                mode="classic",
                ai_name="random",
                best_of=3,
                seed=99,
                no_color=True,
                use_icons=False,
                stats_path=path,
                input_fn=fake_input,
                output_fn=lines.append,
            )
            self.assertEqual(code, 0)
            joined = "\n".join(lines)
            self.assertTrue(
                "won the best-of-3" in joined or "Computer won" in joined,
                msg=joined,
            )

    def test_invalid_choice_continues(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.json"
            inputs = iter(["nope", "q"])

            def fake_input(prompt=""):
                return next(inputs)

            lines: list[str] = []
            code = run_game(
                no_color=True,
                stats_path=path,
                input_fn=fake_input,
                output_fn=lines.append,
                seed=0,
            )
            self.assertEqual(code, 0)
            self.assertTrue(any("Choose" in line for line in lines))


if __name__ == "__main__":
    unittest.main()
