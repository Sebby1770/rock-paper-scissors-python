"""Tests for core game logic (classic + RPSLS)."""

from __future__ import annotations

import random
import unittest

from rock_paper_scissors import (
    BEATS,
    decide_winner,
    normalize_choice,
    play_round,
)
from rps.game import (
    BEATS_RPSLS,
    OPTIONS_RPSLS,
    Scoreboard,
    options_for_mode,
)


class NormalizeChoiceTests(unittest.TestCase):
    def test_accepts_names_numbers_and_letters(self):
        self.assertEqual(normalize_choice("rock"), "rock")
        self.assertEqual(normalize_choice("  P  "), "paper")
        self.assertEqual(normalize_choice("3"), "scissors")

    def test_rejects_invalid_input_classic(self):
        with self.assertRaises(ValueError):
            normalize_choice("lizard")

    def test_rpsls_accepts_lizard_and_spock(self):
        self.assertEqual(normalize_choice("lizard", mode="rpsls"), "lizard")
        self.assertEqual(normalize_choice("spock", mode="rpsls"), "spock")
        self.assertEqual(normalize_choice("4", mode="rpsls"), "lizard")
        self.assertEqual(normalize_choice("5", mode="rpsls"), "spock")
        self.assertEqual(normalize_choice("l", mode="rpsls"), "lizard")
        self.assertEqual(normalize_choice("k", mode="rpsls"), "spock")

    def test_rpsls_aliases_include_classic(self):
        self.assertEqual(normalize_choice("r", mode="rpsls"), "rock")
        self.assertEqual(normalize_choice("scissor", mode="rpsls"), "scissors")

    def test_unknown_mode_raises(self):
        with self.assertRaises(ValueError):
            normalize_choice("rock", mode="chaos")  # type: ignore[arg-type]


class DecideWinnerClassicTests(unittest.TestCase):
    def test_all_outcomes(self):
        self.assertEqual(decide_winner("rock", "scissors"), "win")
        self.assertEqual(decide_winner("paper", "scissors"), "lose")
        self.assertEqual(decide_winner("scissors", "scissors"), "tie")

    def test_beats_map_classic_targets(self):
        self.assertEqual(BEATS["rock"], "scissors")
        self.assertEqual(BEATS["paper"], "rock")
        self.assertEqual(BEATS["scissors"], "paper")

    def test_invalid_choice_raises(self):
        with self.assertRaises(ValueError):
            decide_winner("lizard", "rock")  # type: ignore[arg-type]


class DecideWinnerRPSLSTests(unittest.TestCase):
    def test_rpsls_win_cases(self):
        cases = [
            ("rock", "scissors"),
            ("rock", "lizard"),
            ("paper", "rock"),
            ("paper", "spock"),
            ("scissors", "paper"),
            ("scissors", "lizard"),
            ("lizard", "spock"),
            ("lizard", "paper"),
            ("spock", "scissors"),
            ("spock", "rock"),
        ]
        for player, computer in cases:
            with self.subTest(player=player, computer=computer):
                self.assertEqual(
                    decide_winner(player, computer, mode="rpsls"),
                    "win",
                )

    def test_rpsls_lose_is_inverse(self):
        self.assertEqual(decide_winner("spock", "lizard", mode="rpsls"), "lose")
        self.assertEqual(decide_winner("lizard", "rock", mode="rpsls"), "lose")

    def test_rpsls_tie(self):
        for choice in OPTIONS_RPSLS:
            self.assertEqual(decide_winner(choice, choice, mode="rpsls"), "tie")

    def test_beats_rpsls_each_beats_two(self):
        for choice, victims in BEATS_RPSLS.items():
            self.assertEqual(len(victims), 2, msg=choice)


class PlayRoundTests(unittest.TestCase):
    def test_returns_clear_result(self):
        result = play_round("r", computer_choice="scissors")

        self.assertEqual(result.player_choice, "rock")
        self.assertEqual(result.computer_choice, "scissors")
        self.assertEqual(result.outcome, "win")
        self.assertIn("You win", result.message)

    def test_play_round_rpsls(self):
        result = play_round("spock", computer_choice="rock", mode="rpsls")
        self.assertEqual(result.outcome, "win")
        self.assertIn("vaporizes", result.message)

    def test_play_round_with_seeded_rng(self):
        rng = random.Random(0)
        first = play_round("rock", rng=rng)
        rng2 = random.Random(0)
        second = play_round("rock", rng=rng2)
        self.assertEqual(first.computer_choice, second.computer_choice)

    def test_ai_choice_alias(self):
        result = play_round("paper", ai_choice="rock")
        self.assertEqual(result.computer_choice, "rock")
        self.assertEqual(result.outcome, "win")


class ScoreboardTests(unittest.TestCase):
    def test_history_and_streak(self):
        board = Scoreboard()
        w = play_round("rock", computer_choice="scissors")
        l = play_round("rock", computer_choice="paper")
        t = play_round("rock", computer_choice="rock")

        board.record(w)
        self.assertEqual(board.wins, 1)
        self.assertEqual(board.current_streak, 1)
        self.assertEqual(board.best_streak, 1)

        board.record(w)
        self.assertEqual(board.current_streak, 2)
        self.assertEqual(board.best_streak, 2)

        board.record(t)  # tie does not break streak
        self.assertEqual(board.ties, 1)
        self.assertEqual(board.current_streak, 2)

        board.record(l)
        self.assertEqual(board.losses, 1)
        self.assertEqual(board.current_streak, 0)
        self.assertEqual(board.best_streak, 2)

        self.assertEqual(len(board.history), 4)

    def test_best_of_match(self):
        board = Scoreboard()
        self.assertFalse(board.match_over(3))
        board.record(play_round("rock", computer_choice="scissors"))
        self.assertFalse(board.match_over(3))
        board.record(play_round("rock", computer_choice="scissors"))
        self.assertTrue(board.match_over(3))
        self.assertEqual(board.match_winner(3), "win")

    def test_best_of_computer_wins(self):
        board = Scoreboard()
        for _ in range(3):
            board.record(play_round("rock", computer_choice="paper"))
        self.assertTrue(board.match_over(5))
        self.assertEqual(board.match_winner(5), "lose")

    def test_best_of_none_never_over(self):
        board = Scoreboard()
        board.record(play_round("rock", computer_choice="scissors"))
        self.assertFalse(board.match_over(None))
        self.assertIsNone(board.match_winner(None))

    def test_options_for_mode(self):
        self.assertEqual(len(options_for_mode("classic")), 3)
        self.assertEqual(len(options_for_mode("rpsls")), 5)


if __name__ == "__main__":
    unittest.main()
