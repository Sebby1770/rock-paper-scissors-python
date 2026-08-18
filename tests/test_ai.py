"""Tests for AI opponent strategies."""

from __future__ import annotations

import random
import unittest
from collections import Counter

from rps.ai import (
    BiasedAI,
    CounterAI,
    MarkovAI,
    PatternBreakAI,
    RandomAI,
    available_ais,
    create_ai,
    play_ai_match,
    run_tournament,
)


class FactoryTests(unittest.TestCase):
    def test_available_ais(self):
        names = available_ais()
        self.assertIn("random", names)
        self.assertIn("biased", names)
        self.assertIn("counter", names)
        self.assertIn("markov", names)
        self.assertIn("pattern-break", names)

    def test_create_ai_unknown(self):
        with self.assertRaises(ValueError):
            create_ai("psychic")

    def test_create_ai_case_insensitive(self):
        ai = create_ai("RaNdOm", rng=random.Random(1))
        self.assertEqual(ai.name, "random")


class RandomAITests(unittest.TestCase):
    def test_seeded_reproducible(self):
        a = RandomAI(rng=random.Random(42))
        b = RandomAI(rng=random.Random(42))
        self.assertEqual(
            [a.choose() for _ in range(10)],
            [b.choose() for _ in range(10)],
        )

    def test_rpsls_options(self):
        ai = RandomAI(mode="rpsls", rng=random.Random(0))
        choices = {ai.choose() for _ in range(50)}
        self.assertTrue(choices <= set(ai.options))
        # With enough samples, expect more than classic-only options likely.
        self.assertTrue(len(choices) >= 2)


class BiasedAITests(unittest.TestCase):
    def test_prefers_rock(self):
        ai = BiasedAI(rng=random.Random(123))
        counts = Counter(ai.choose() for _ in range(3000))
        self.assertGreater(counts["rock"], counts["paper"])
        self.assertGreater(counts["rock"], counts["scissors"])
        # Roughly ~40% rock
        self.assertGreater(counts["rock"], 900)


class CounterAITests(unittest.TestCase):
    def test_first_move_is_valid(self):
        ai = CounterAI(rng=random.Random(0))
        self.assertIn(ai.choose(), ai.options)

    def test_counters_last_player_move(self):
        ai = CounterAI(mode="classic", rng=random.Random(1))
        ai.observe("rock", "paper")
        # Anything that beats rock must be paper in classic.
        self.assertEqual(ai.choose(), "paper")

        ai.observe("scissors", "rock")
        self.assertEqual(ai.choose(), "rock")

    def test_counters_rpsls(self):
        ai = CounterAI(mode="rpsls", rng=random.Random(2))
        ai.observe("spock", "rock")
        # Counters to spock: paper or lizard
        move = ai.choose()
        self.assertIn(move, {"paper", "lizard"})


class MarkovAITests(unittest.TestCase):
    def test_predicts_frequent_transition(self):
        ai = MarkovAI(mode="classic", rng=random.Random(0))
        # After rock, player always plays paper.
        sequence = ["rock", "paper", "rock", "paper", "rock", "paper"]
        prev_computer = "scissors"
        for move in sequence:
            ai.observe(move, prev_computer)  # type: ignore[arg-type]
            prev_computer = "scissors"

        # Last player move is paper. No transitions from paper yet well-known,
        # so train paper -> scissors repeatedly.
        for _ in range(5):
            ai.observe("scissors", "rock")
            ai.observe("paper", "rock")

        # Last player move is paper; most common next after paper is scissors.
        # Counter to scissors is rock.
        # Rebuild a clean markov for clarity:
        ai2 = MarkovAI(mode="classic", rng=random.Random(0))
        # Transitions: rock -> paper (many times)
        pairs = [("rock", "paper")] * 10 + [("rock", "scissors")] * 2
        last = "rock"
        ai2.observe(last, "scissors")
        for prev, nxt in pairs:
            # ensure last is prev
            ai2._last_player = prev  # intentional test of internal transition update
            ai2.observe(nxt, "scissors")

        ai2._last_player = "rock"
        predicted_counter = ai2.choose()
        # Most common after rock is paper → counter is scissors
        self.assertEqual(predicted_counter, "scissors")

    def test_seeded_markov_cold_start(self):
        a = MarkovAI(rng=random.Random(7))
        b = MarkovAI(rng=random.Random(7))
        self.assertEqual(a.choose(), b.choose())


class PatternBreakAITests(unittest.TestCase):
    def test_counters_repeated_player_move(self):
        ai = PatternBreakAI(mode="classic", rng=random.Random(0))
        ai.observe("rock", "scissors")
        ai.observe("rock", "scissors")
        self.assertEqual(ai.choose(), "paper")

    def test_avoids_obvious_counter_after_a_switch(self):
        ai = PatternBreakAI(mode="classic", rng=random.Random(1))
        ai.observe("rock", "scissors")
        ai.observe("paper", "rock")
        self.assertNotEqual(ai.choose(), "scissors")

    def test_seeded_cold_start_is_reproducible(self):
        a = PatternBreakAI(rng=random.Random(11))
        b = PatternBreakAI(rng=random.Random(11))
        self.assertEqual(a.choose(), b.choose())


class TournamentTests(unittest.TestCase):
    def test_play_ai_match_counts_rounds(self):
        first = RandomAI(rng=random.Random(1))
        second = RandomAI(rng=random.Random(2))
        result = play_ai_match(first, second, rounds=12)
        self.assertEqual(result["rounds"], 12)
        self.assertEqual(result["wins"] + result["losses"] + result["ties"], 12)

    def test_run_tournament_ranks_every_pair(self):
        result = run_tournament(
            ("random", "biased", "pattern-break"),
            rounds=8,
            seed=3,
        )
        self.assertEqual(len(result["matches"]), 3)
        self.assertEqual(len(result["standings"]), 3)
        names = {row["name"] for row in result["standings"]}
        self.assertEqual(names, {"random", "biased", "pattern-break"})
        self.assertEqual(result["standings"][0]["matches"], 2)
        self.assertGreaterEqual(result["standings"][0]["wins"], result["standings"][1]["wins"])


if __name__ == "__main__":
    unittest.main()
