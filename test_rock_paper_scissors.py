import unittest

from rock_paper_scissors import decide_winner, normalize_choice, play_round


class RockPaperScissorsTests(unittest.TestCase):
    def test_normalize_choice_accepts_names_numbers_and_letters(self):
        self.assertEqual(normalize_choice("rock"), "rock")
        self.assertEqual(normalize_choice("  P  "), "paper")
        self.assertEqual(normalize_choice("3"), "scissors")

    def test_normalize_choice_rejects_invalid_input(self):
        with self.assertRaises(ValueError):
            normalize_choice("lizard")

    def test_decide_winner_handles_all_outcomes(self):
        self.assertEqual(decide_winner("rock", "scissors"), "win")
        self.assertEqual(decide_winner("paper", "scissors"), "lose")
        self.assertEqual(decide_winner("scissors", "scissors"), "tie")

    def test_play_round_returns_a_clear_result(self):
        result = play_round("r", computer_choice="scissors")

        self.assertEqual(result.player_choice, "rock")
        self.assertEqual(result.computer_choice, "scissors")
        self.assertEqual(result.outcome, "win")
        self.assertIn("You win", result.message)


if __name__ == "__main__":
    unittest.main()
