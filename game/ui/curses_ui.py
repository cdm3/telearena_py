"""
Tele-Arena 5.6 Python Port - Curses UI
Provides a local terminal interface with scrolling output, status bar, and input line.
"""

import curses
import curses.ascii
import textwrap
import os
import sys

from ..messages import parse_ansi_segments

# Color pair indices
CP_DEFAULT    = 0
CP_WHITE_BOLD = 1
CP_CYAN       = 2
CP_GREEN      = 3
CP_YELLOW     = 4
CP_RED        = 5
CP_MAGENTA    = 6
CP_BLUE       = 7
CP_WHITE      = 8
CP_STATUS     = 9
CP_INPUT      = 10
CP_CYAN_BOLD  = 11
CP_GREEN_BOLD = 12
CP_RED_BOLD   = 13

# Map message color names to curses color pair indices
COLOR_PAIR_MAP = {
    ('white',   True):   CP_WHITE_BOLD,
    ('white',   False):  CP_WHITE,
    ('cyan',    True):   CP_CYAN_BOLD,
    ('cyan',    False):  CP_CYAN,
    ('green',   True):   CP_GREEN_BOLD,
    ('green',   False):  CP_GREEN,
    ('yellow',  True):   CP_YELLOW,
    ('yellow',  False):  CP_YELLOW,
    ('red',     True):   CP_RED_BOLD,
    ('red',     False):  CP_RED,
    ('magenta', True):   CP_MAGENTA,
    ('magenta', False):  CP_MAGENTA,
    ('blue',    True):   CP_BLUE,
    ('blue',    False):  CP_BLUE,
    (None,      False):  CP_DEFAULT,
    (None,      True):   CP_WHITE_BOLD,
}


def init_colors():
    """Initialize curses color pairs."""
    curses.start_color()
    curses.use_default_colors()

    curses.init_pair(CP_WHITE_BOLD, curses.COLOR_WHITE,   -1)
    curses.init_pair(CP_CYAN,       curses.COLOR_CYAN,    -1)
    curses.init_pair(CP_GREEN,      curses.COLOR_GREEN,   -1)
    curses.init_pair(CP_YELLOW,     curses.COLOR_YELLOW,  -1)
    curses.init_pair(CP_RED,        curses.COLOR_RED,     -1)
    curses.init_pair(CP_MAGENTA,    curses.COLOR_MAGENTA, -1)
    curses.init_pair(CP_BLUE,       curses.COLOR_BLUE,    -1)
    curses.init_pair(CP_WHITE,      curses.COLOR_WHITE,   -1)
    curses.init_pair(CP_STATUS,     curses.COLOR_BLACK,   curses.COLOR_CYAN)
    curses.init_pair(CP_INPUT,      curses.COLOR_WHITE,   -1)
    curses.init_pair(CP_CYAN_BOLD,  curses.COLOR_CYAN,    -1)
    curses.init_pair(CP_GREEN_BOLD, curses.COLOR_GREEN,   -1)
    curses.init_pair(CP_RED_BOLD,   curses.COLOR_RED,     -1)


class ScrollBuffer:
    """Maintains a scrollable buffer of colored text lines."""

    def __init__(self, max_lines=2000):
        self.max_lines = max_lines
        # Each entry: list of (attr, text) segments for one screen line
        self.lines = []

    def add_text(self, text):
        """
        Parse text (possibly containing ANSI codes / *** markers) and add to buffer.
        Handles line wrapping for display width.
        """
        # Strip leading *** separator (used in engine output)
        if text.startswith('***\n'):
            text = text[4:]
        elif text == '***':
            text = ''

        # Split on newlines, process each line
        # Store as (color_name, bold, text) tuples — resolved to curses attrs at render time
        raw_lines = text.split('\n')
        for raw in raw_lines:
            if not raw:
                self.lines.append([(None, False, '')])
            else:
                self.lines.append(parse_ansi_segments(raw) or [(None, False, raw)])

        # Trim to max
        if len(self.lines) > self.max_lines:
            self.lines = self.lines[-self.max_lines:]

    def get_display_lines(self, width, count):
        """
        Return the last `count` lines, word-wrapped to `width`.
        Each line is a list of (curses_attr, text) pairs (resolved at render time).
        """
        wrapped = []
        for line_segs in self.lines:
            # line_segs is list of (color_name, bold, text) 3-tuples
            full_text = ''.join(t for _, _, t in line_segs)
            if len(full_text) <= width:
                wrapped.append(_resolve_attrs(line_segs))
            else:
                wrapped.extend(_wrap_segments(line_segs, width))

        return wrapped[-count:] if len(wrapped) > count else wrapped


def _resolve_attrs(segs):
    """Convert (color_name, bold, text) segments to (curses_attr, text) pairs."""
    result = []
    for color_name, bold, text in segs:
        pair_idx = COLOR_PAIR_MAP.get((color_name, bold), CP_DEFAULT)
        attr = curses.color_pair(pair_idx)
        if bold and color_name in ('white', 'cyan', 'green', 'red'):
            attr |= curses.A_BOLD
        result.append((attr, text))
    return result


def _wrap_segments(segments, width):
    """
    Word-wrap a list of (color_name, bold, text) segments to fit within `width` columns.
    Returns list of resolved (curses_attr, text) segment lists.
    """
    # Flatten to (color_name, bold, char) triples
    chars = []
    for color_name, bold, text in segments:
        for ch in text:
            chars.append((color_name, bold, ch))

    lines = []
    while chars:
        chunk = chars[:width]
        chars = chars[width:]
        segs = []
        if chunk:
            cur_color, cur_bold = chunk[0][0], chunk[0][1]
            cur_text = ''
            for color_name, bold, ch in chunk:
                if color_name == cur_color and bold == cur_bold:
                    cur_text += ch
                else:
                    segs.append((cur_color, cur_bold, cur_text))
                    cur_color, cur_bold = color_name, bold
                    cur_text = ch
            segs.append((cur_color, cur_bold, cur_text))
        resolved = _resolve_attrs(segs) if segs else [(curses.color_pair(CP_DEFAULT), '')]
        lines.append(resolved)
    return lines if lines else [[(curses.color_pair(CP_DEFAULT), '')]]


class CursesUI:
    """
    Main curses-based UI for Tele-Arena.

    Layout:
      +--------------------------------------------------+
      | [scrolling game output area]                     |
      |                                                  |
      +--------------------------------------------------+
      | Status: HP:xx/xx  SP:xx/xx  Gold:xxx  Loc:xxx   |
      +--------------------------------------------------+
      | > _                                              |
      +--------------------------------------------------+
    """

    INPUT_HISTORY_MAX = 50

    def __init__(self, stdscr, engine):
        self.stdscr  = stdscr
        self.engine  = engine
        self.scroll  = ScrollBuffer()
        self.input_line  = ''
        self.input_hist  = []
        self.hist_idx    = -1
        self.running     = True

        self._setup_screen()

    def _setup_screen(self):
        init_colors()
        curses.cbreak()
        curses.noecho()
        self.stdscr.keypad(True)
        self.stdscr.timeout(100)  # 100 ms input poll for game ticks
        curses.curs_set(1)

        self._recalc_layout()

    def _recalc_layout(self):
        self.max_y, self.max_x = self.stdscr.getmaxyx()
        # Reserve 2 rows: 1 for status bar, 1 for input line
        self.output_rows = max(3, self.max_y - 2)
        self.output_cols = self.max_x
        self.status_row  = self.max_y - 2
        self.input_row   = self.max_y - 1

    def output(self, text):
        """Add text to the scroll buffer and refresh."""
        if text:
            self.scroll.add_text(text)
        self._draw_output()
        self._draw_status()
        self._draw_input()
        self.stdscr.refresh()

    def _draw_output(self):
        """Render the scrolling output area."""
        lines = self.scroll.get_display_lines(self.output_cols, self.output_rows)
        # Pad with empty lines if fewer than output_rows
        while len(lines) < self.output_rows:
            lines.insert(0, [(CP_DEFAULT, '')])

        for row_idx, segs in enumerate(lines):
            if row_idx >= self.output_rows:
                break
            try:
                self.stdscr.move(row_idx, 0)
                self.stdscr.clrtoeol()
                col = 0
                for attr, text in segs:
                    if col >= self.output_cols:
                        break
                    remaining = self.output_cols - col
                    chunk = text[:remaining]
                    if chunk:
                        try:
                            self.stdscr.addstr(row_idx, col, chunk, attr)
                        except curses.error:
                            pass
                        col += len(chunk)
            except curses.error:
                pass

    def _draw_status(self):
        """Render the status bar."""
        try:
            status = self.engine.get_status_line()
            # Pad/truncate to screen width
            status = status[:self.max_x - 1].ljust(self.max_x - 1)
            attr = curses.color_pair(CP_STATUS) | curses.A_BOLD
            self.stdscr.addstr(self.status_row, 0, status, attr)
        except curses.error:
            pass

    def _draw_input(self):
        """Render the input line."""
        try:
            prompt = '> '
            line = (prompt + self.input_line)[:self.max_x - 1]
            line = line.ljust(self.max_x - 1)
            self.stdscr.addstr(self.input_row, 0, line,
                               curses.color_pair(CP_INPUT))
            # Position cursor after input text
            cursor_col = min(len(prompt) + len(self.input_line), self.max_x - 1)
            self.stdscr.move(self.input_row, cursor_col)
        except curses.error:
            pass

    def _handle_key(self, key):
        """Process a single keypress. Returns True if a command was submitted."""
        if key in (curses.KEY_ENTER, ord('\n'), ord('\r')):
            cmd = self.input_line.strip()
            self._draw_input_echo(cmd)
            self.input_line = ''
            self.hist_idx   = -1
            if cmd:
                self.input_hist.insert(0, cmd)
                if len(self.input_hist) > self.INPUT_HISTORY_MAX:
                    self.input_hist.pop()
            # Always process — creation states need empty Enter to advance
            self._process_command(cmd)
            return True

        elif key in (curses.KEY_BACKSPACE, 127, curses.ascii.BS):
            if self.input_line:
                self.input_line = self.input_line[:-1]

        elif key == curses.KEY_DC:  # Delete key
            pass  # No cursor movement support needed for simplicity

        elif key == curses.KEY_UP:
            if self.input_hist:
                self.hist_idx = min(self.hist_idx + 1, len(self.input_hist) - 1)
                self.input_line = self.input_hist[self.hist_idx]

        elif key == curses.KEY_DOWN:
            if self.hist_idx > 0:
                self.hist_idx -= 1
                self.input_line = self.input_hist[self.hist_idx]
            else:
                self.hist_idx = -1
                self.input_line = ''

        elif key == curses.KEY_RESIZE:
            self._recalc_layout()
            self.stdscr.clear()

        elif key == curses.KEY_PPAGE:  # Page Up — scroll not implemented, ignore
            pass

        elif isinstance(key, int) and 32 <= key <= 126:
            self.input_line += chr(key)

        return False

    def _draw_input_echo(self, cmd):
        """Echo the submitted command to the output buffer in green."""
        if cmd:
            self.scroll.add_text(f'\x1b[1;32m> {cmd}\x1b[1;37m\n')

    def _process_command(self, cmd):
        """Send command to engine, display result."""
        if cmd.lower() in ('quit', 'exit game', 'bye') and not self.engine.is_playing():
            self.running = False
            return

        result = self.engine.process_input(cmd)
        if result:
            self.output(result)

        if not self.engine.running:
            self.running = False

    def run(self):
        """Main UI event loop."""
        # Initial display
        self.output('')

        tick_counter = 0
        while self.running:
            self._draw_output()
            self._draw_status()
            self._draw_input()
            self.stdscr.refresh()

            key = self.stdscr.getch()

            if key == -1:
                # Timeout — run a game tick periodically
                tick_counter += 1
                if tick_counter >= 10:  # every ~1 second
                    tick_counter = 0
                    if self.engine.is_playing():
                        self.engine._game_tick()
            else:
                self._handle_key(key)
