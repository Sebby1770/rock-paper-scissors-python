# Rock Paper Scissors

[![CI](https://github.com/sebastianforbes/rock-paper-scissors-python/actions/workflows/ci.yml/badge.svg)](https://github.com/sebastianforbes/rock-paper-scissors-python/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-2.0.0-brightgreen.svg)](./pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-lightgrey.svg)](./pyproject.toml)

A polished command-line **Rock Paper Scissors** suite with:

- Classic RPS **and** RPSLS (lizard / Spock)
- Four AI opponents (random, biased, counter, markov)
- Best-of-N match mode
- Win-streak tracking and round history
- Lifetime stats persisted to disk
- Colored TTY output (no third-party deps)

## Quick start

```bash
python3 rock_paper_scissors.py
```

Or as a module after install:

```bash
pip install -e .
rock-paper-scissors
# or: rps
```

### Examples

```bash
# Classic game, random AI
python3 rock_paper_scissors.py

# RPSLS with a markov AI, best of 5, reproducible seed
python3 rock_paper_scissors.py --mode rpsls --ai markov --best-of 5 --seed 42

# Biased opponent, no colors
python3 rock_paper_scissors.py --ai biased --no-color

# Lifetime stats
python3 rock_paper_scissors.py --stats
python3 rock_paper_scissors.py --reset-stats
```

### Input

| Input | Choice |
|------:|--------|
| `1` / `r` / `rock` | rock |
| `2` / `p` / `paper` | paper |
| `3` / `s` / `scissors` | scissors |
| `4` / `l` / `lizard` | lizard *(RPSLS)* |
| `5` / `k` / `v` / `spock` | spock *(RPSLS)* |
| `q` / `quit` / `exit` | leave the game |

## CLI options

| Flag | Description |
|------|-------------|
| `--mode classic\|rpsls` | Game ruleset (default: `classic`) |
| `--ai random\|biased\|counter\|markov` | Opponent strategy (default: `random`) |
| `--best-of N` | First to `N//2+1` wins |
| `--seed INT` | Seed RNG for reproducible AI play |
| `--no-color` | Disable ANSI colors |
| `--no-icons` | Disable hand/emoji icons |
| `--stats` | Print lifetime stats and exit |
| `--reset-stats` | Clear lifetime stats and exit |
| `--stats-file PATH` | Override stats JSON path |
| `--version` | Print version |

Stats file resolution: `RPS_STATS_PATH` env → existing `./.rps_stats.json` → `~/.rps_stats.json`.

## AI strategies

| Name | Behavior |
|------|----------|
| `random` | Uniform choice among valid options |
| `biased` | Slightly prefers rock (~40%) |
| `counter` | Counters your previous move |
| `markov` | Predicts your next move from 1-step transitions, then counters |

## Library API

Backward compatible:

```python
from rock_paper_scissors import play_round, decide_winner, normalize_choice

result = play_round("r", computer_choice="scissors")
assert result.outcome == "win"

# RPSLS
from rock_paper_scissors import decide_winner
assert decide_winner("spock", "rock", mode="rpsls") == "win"
```

Package modules:

```python
from rps.game import Scoreboard, play_round
from rps.ai import create_ai
from rps.stats import load_stats, save_stats
```

## Tests

```bash
python3 -m unittest discover -s tests -v
python3 -m unittest test_rock_paper_scissors -v
```

## macOS Python Launcher

Open `Rock Paper Scissors.py` with Python Launcher. The launcher keeps the
window open after the game ends so you can read the final score.

## Project layout

```
rock_paper_scissors.py   # BC entry + re-exports
Rock Paper Scissors.py   # macOS double-click launcher
rps/
  game.py                # core rules, scoreboard, RPSLS
  ai.py                  # opponent strategies
  stats.py               # lifetime stats I/O
  cli.py                 # argparse + interactive loop
tests/
pyproject.toml
.github/workflows/ci.yml
```

## Version

**2.0.0** — full suite overhaul (modes, AI, stats, packaging).
