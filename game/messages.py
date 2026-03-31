"""
Tele-Arena 5.6 Python Port - Message System

Replaces the Major BBS message system (prfmlt/outmlt/pmlt).
Loads messages from data/messages.json and provides formatted output.
"""

import json
import os
import re

_messages = {}
_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')


def load_messages():
    """Load messages from JSON file."""
    global _messages
    path = os.path.join(_data_dir, 'messages.json')
    if os.path.exists(path):
        with open(path) as f:
            _messages = json.load(f)


def get(key, *args):
    """
    Get a formatted message by key.
    Handles C-style %s/%d/%u/%l format specifiers.
    Strips ANSI escape sequences (handled separately by UI).
    """
    text = _messages.get(key, f'[{key}]')
    if args:
        text = _fmt(text, args)
    return text


def _fmt(text, args):
    """Convert C printf-style format specifiers to actual values."""
    result = []
    arg_idx = 0
    i = 0
    while i < len(text):
        if text[i] == '%' and i + 1 < len(text):
            spec = text[i + 1]
            if spec in ('s', 'd', 'u', 'i', 'x', 'X'):
                if arg_idx < len(args):
                    val = args[arg_idx]
                    if spec in ('d', 'u', 'i'):
                        result.append(str(int(val)) if val is not None else '0')
                    elif spec in ('x', 'X'):
                        result.append(format(int(val), spec))
                    else:
                        result.append(str(val) if val is not None else '')
                    arg_idx += 1
                i += 2
            elif spec == 'l' and i + 2 < len(text) and text[i + 2] in ('d', 'u'):
                if arg_idx < len(args):
                    result.append(str(int(args[arg_idx])))
                    arg_idx += 1
                i += 3
            elif spec == '%':
                result.append('%')
                i += 2
            else:
                result.append(text[i])
                i += 1
        else:
            result.append(text[i])
            i += 1
    return ''.join(result)


# ANSI color code pattern
_ANSI_RE = re.compile(r'\x1b\[[0-9;]*m|\[[\d;]+m')


def strip_ansi(text):
    """Remove ANSI escape codes from text."""
    return _ANSI_RE.sub('', text)


def parse_ansi_segments(text):
    """
    Parse text with ANSI codes into list of (color_attr, text) segments.
    color_attr is a string like '1;37' or None for default.
    Also handles the bare '[1;37m' format used in the .MSG files (no ESC prefix).
    Returns list of (color_name, bold, text) tuples.
    """
    segments = []
    # Normalize: replace bare [N;Nm with ESC[N;Nm
    normalized = re.sub(r'(?<!\x1b)\[([0-9;]+m)', '\x1b[' + r'\1', text)
    parts = re.split(r'(\x1b\[[0-9;]*m)', normalized)
    current_color, current_bold = None, False
    for part in parts:
        if part.startswith('\x1b['):
            attr = part[2:-1]  # strip ESC[ and m
            current_color, current_bold = color_for_attr(attr)
        elif part:
            segments.append((current_color, current_bold, part))
    return segments


# Map ANSI color codes to (color_name, bold) pairs
# Format: 'attr' -> (fg_color, bold)
ANSI_COLOR_MAP = {
    None:   ('white', False),
    '':     ('white', False),
    '0':    ('white', False),
    '1;37': ('white', True),
    '0;37': ('white', False),
    '1;31': ('red', True),
    '0;31': ('red', False),
    '1;32': ('green', True),
    '0;32': ('green', False),
    '1;33': ('yellow', True),
    '0;33': ('yellow', False),
    '1;34': ('blue', True),
    '0;34': ('blue', False),
    '1;35': ('magenta', True),
    '0;35': ('magenta', False),
    '1;36': ('cyan', True),
    '0;36': ('cyan', False),
    '1;5;31': ('red', True),   # blinking red -> just bold red
    '0m':   ('white', False),
    '1;37m': ('white', True),
}


def color_for_attr(attr):
    """Return (color_name, bold) for an ANSI attribute string."""
    if attr is None or attr == '' or attr == '0m':
        return ('white', False)
    # Strip trailing 'm' if present
    key = attr.rstrip('m')
    return ANSI_COLOR_MAP.get(attr, ANSI_COLOR_MAP.get(key, ('white', False)))
