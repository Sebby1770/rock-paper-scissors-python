"""Command-line interface for Rock Paper Scissors / RPSLS."""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

from rps import __version__
from rps.ai import AIStrategy, available_ais, create_ai, run_tournament
from rps.game import (
    ICONS,
    Choice,
    Mode,
    Scoreboard,
    normalize_choice,
    options_for_mode,
    play_round,
)
from rps.stats import (
    LifetimeStats,
    default_stats_path,
    export_stats_csv,
    load_stats,
    reset_stats,
    save_stats,
)


# ANSI color helpers (no third-party deps).
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"


def supports_color(stream=None, no_color: bool = False) -> bool:
    """Return True when ANSI colors should be used."""

    if no_color:
        return False
    if os_environ_no_color():
        return False
    stream = stream if stream is not None else sys.stdout
    return hasattr(stream, "isatty") and stream.isatty()


def os_environ_no_color() -> bool:
    import os

    return bool(os.environ.get("NO_COLOR"))


def paint(text: str, *codes: str, enabled: bool = True) -> str:
    if not enabled or not codes:
        return text
    return "".join(codes) + text + Colors.RESET


def format_choice(choice: Choice | str, use_icons: bool = True) -> str:
    icon = ICONS.get(choice, "")  # type: ignore[arg-type]
    if use_icons and icon:
        return f"{icon} {choice}"
    return str(choice)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rock-paper-scissors",
        description="Rock Paper Scissors (classic) and RPSLS (lizard/spock).",
    )
    parser.add_argument(
        "--mode",
        choices=("classic", "rpsls"),
        default="classic",
        help="Game mode: classic RPS or RPSLS (default: classic).",
    )
    parser.add_argument(
        "--ai",
        choices=available_ais(),
        default="random",
        help="AI opponent strategy (default: random).",
    )
    parser.add_argument(
        "--best-of",
        type=int,
        default=None,
        metavar="N",
        dest="best_of",
        help="Play a best-of-N match (first to N//2+1 wins).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Seed the RNG for reproducible AI play.",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colors.",
    )
    parser.add_argument(
        "--no-icons",
        action="store_true",
        help="Disable emoji/hand icons.",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Print lifetime stats and exit.",
    )
    parser.add_argument(
        "--reset-stats",
        action="store_true",
        dest="reset_stats",
        help="Clear lifetime stats and exit.",
    )
    parser.add_argument(
        "--stats-file",
        type=Path,
        default=None,
        dest="stats_file",
        help="Override path for the stats JSON file.",
    )
    parser.add_argument(
        "--tournament",
        action="store_true",
        help="Run a round-robin AI tournament and exit.",
    )
    parser.add_argument(
        "--tournament-rounds",
        type=int,
        default=30,
        metavar="N",
        dest="tournament_rounds",
        help="Rounds per tournament matchup (default: 30).",
    )
    parser.add_argument(
        "--export-stats",
        type=Path,
        default=None,
        dest="export_stats",
        metavar="PATH",
        help="Write lifetime stats to a CSV file and exit.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def prompt_choices(mode: Mode, use_icons: bool) -> str:
    options = options_for_mode(mode)
    parts = []
    for i, opt in enumerate(options, start=1):
        label = format_choice(opt, use_icons=use_icons)
        parts.append(f"{i}:{label}")
    return ", ".join(parts)


def run_game(
    mode: Mode = "classic",
    ai_name: str = "random",
    best_of: int | None = None,
    seed: int | None = None,
    no_color: bool = False,
    use_icons: bool = True,
    stats_path: Path | None = None,
    input_fn=input,
    output_fn=print,
) -> int:
    """Run the interactive game loop. Returns a process exit code."""

    color = supports_color(no_color=no_color)
    rng = random.Random(seed)
    ai: AIStrategy = create_ai(ai_name, mode=mode, rng=rng)
    board = Scoreboard()
    lifetime = load_stats(stats_path)
    session_best_streak = 0

    title = "Rock Paper Scissors Lizard Spock" if mode == "rpsls" else "Rock Paper Scissors"
    output_fn(paint(title, Colors.BOLD, Colors.CYAN, enabled=color))
    output_fn(
        paint(
            f"Mode: {mode}  |  AI: {ai.name}  |  v{__version__}",
            Colors.DIM,
            enabled=color,
        )
    )
    if best_of is not None:
        if best_of < 1:
            output_fn("Error: --best-of must be a positive integer.")
            return 2
        needed = best_of // 2 + 1
        output_fn(f"Best-of-{best_of}: first to {needed} wins.")
    output_fn(f"Choices: {prompt_choices(mode, use_icons)}")
    output_fn("Type q / quit / exit to stop.\n")

    while True:
        if board.match_over(best_of):
            break

        try:
            player_input = input_fn("Your choice: ").strip()
        except EOFError:
            output_fn("")
            break

        if player_input.lower() in {"q", "quit", "exit"}:
            break

        try:
            # Peek normalized choice so AI can react only after the round
            # (counter/markov use observe after play).
            normalize_choice(player_input, mode=mode)
            computer_move = ai.choose()
            result = play_round(
                player_input,
                computer_choice=computer_move,
                mode=mode,
            )
        except ValueError as error:
            output_fn(paint(str(error), Colors.YELLOW, enabled=color))
            continue

        ai.observe(result.player_choice, result.computer_choice)
        board.record(result)
        lifetime.record_round(result)
        # Track best streak across the session for lifetime merge later.
        if board.current_streak > session_best_streak:
            session_best_streak = board.current_streak
        if board.best_streak > lifetime.best_streak:
            lifetime.best_streak = board.best_streak

        p_label = format_choice(result.player_choice, use_icons=use_icons)
        c_label = format_choice(result.computer_choice, use_icons=use_icons)
        output_fn(f"You: {p_label}   Computer: {c_label}")

        if result.outcome == "win":
            output_fn(paint(result.message, Colors.GREEN, Colors.BOLD, enabled=color))
        elif result.outcome == "lose":
            output_fn(paint(result.message, Colors.RED, Colors.BOLD, enabled=color))
        else:
            output_fn(paint(result.message, Colors.YELLOW, enabled=color))

        output_fn(paint(f"Score — {board.summary()}", Colors.DIM, enabled=color))
        output_fn("")

        if board.match_over(best_of):
            break

    # Persist: games_played increments once per interactive session that had rounds.
    if board.rounds_played > 0:
        lifetime.games_played += 1
        save_stats(lifetime, stats_path)

    output_fn(paint("Thanks for playing!", Colors.CYAN, enabled=color))
    output_fn(f"Final score — {board.summary()}")

    if best_of is not None:
        winner = board.match_winner(best_of)
        if winner == "win":
            output_fn(paint(f"You won the best-of-{best_of} match!", Colors.GREEN, Colors.BOLD, enabled=color))
        elif winner == "lose":
            output_fn(paint(f"Computer won the best-of-{best_of} match.", Colors.RED, Colors.BOLD, enabled=color))
        else:
            output_fn(f"Match incomplete (needed {best_of // 2 + 1} wins).")

    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""

    parser = build_parser()
    args = parser.parse_args(argv)

    stats_path = args.stats_file

    if args.reset_stats:
        path = reset_stats(stats_path)
        print(f"Stats reset: {path}")
        return 0

    if args.stats:
        path = stats_path if stats_path is not None else default_stats_path()
        stats = load_stats(path)
        print(stats.format_report())
        print(f"\n(stats file: {path})")
        return 0

    if args.export_stats is not None:
        path = stats_path if stats_path is not None else default_stats_path()
        written = export_stats_csv(load_stats(path), args.export_stats)
        print(f"Stats exported: {written}")
        return 0

    if args.tournament:
        if args.tournament_rounds < 1:
            parser.error("--tournament-rounds must be a positive integer")
        result = run_tournament(
            rounds=args.tournament_rounds,
            mode=args.mode,
            seed=args.seed,
        )
        print(f"Tournament ({result['mode']}, {result['rounds']} rounds/match)")
        print(f"{'AI':<16} {'W':>5} {'L':>5} {'T':>5} {'M':>5}")
        for row in result["standings"]:
            print(
                f"{row['name']:<16} {row['wins']:>5} {row['losses']:>5} "
                f"{row['ties']:>5} {row['matches']:>5}"
            )
        return 0

    if args.best_of is not None and args.best_of < 1:
        parser.error("--best-of must be a positive integer")

    return run_game(
        mode=args.mode,
        ai_name=args.ai,
        best_of=args.best_of,
        seed=args.seed,
        no_color=args.no_color,
        use_icons=not args.no_icons,
        stats_path=stats_path,
    )


if __name__ == "__main__":
    raise SystemExit(main())
