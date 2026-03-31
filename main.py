#!/usr/bin/env python3
"""
Tele-Arena 5.6 Python Port - Main Entry Point
Launches a local curses-based single-player game session.
"""

import curses
import sys
import os
import argparse

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(__file__))

from game.engine import GameEngine
from game.ui.curses_ui import CursesUI


def parse_args():
    parser = argparse.ArgumentParser(description='Tele-Arena 5.6 Python Port')
    parser.add_argument('--user', '-u', default='player1',
                        help='User ID / save file name (default: player1)')
    parser.add_argument('--sex', '-s', choices=['m', 'f'], default='m',
                        help='Character sex if creating new (m/f, default: m)')
    parser.add_argument('--data-dir', default=None,
                        help='Override path to data directory')
    return parser.parse_args()


def main(stdscr, args):
    """Curses main — called by curses.wrapper()."""
    # Create engine
    engine = GameEngine()

    # Override data dir if specified
    if args.data_dir:
        engine.data_dir = args.data_dir

    # Load game data
    try:
        engine.load_data()
    except Exception as e:
        stdscr.addstr(0, 0, f'Error loading game data: {e}')
        stdscr.addstr(1, 0, 'Press any key to exit.')
        stdscr.getch()
        return

    # Create UI
    ui = CursesUI(stdscr, engine)

    # Enter game for this user
    intro = engine.enter_game(args.user, args.sex)
    if intro:
        ui.output(intro)

    # Run the UI event loop
    ui.run()


if __name__ == '__main__':
    args = parse_args()

    # Check that we're running from the right directory
    if not os.path.isdir(os.path.join(os.path.dirname(__file__), 'game')):
        print('Error: must be run from the telearena_py project directory.')
        sys.exit(1)

    try:
        curses.wrapper(main, args)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f'Fatal error: {e}', file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print('Goodbye!')
