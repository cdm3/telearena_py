import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from game.engine import GameEngine
from game.constants import PLYING

e = GameEngine()
e.load_data()

e.enter_game("test_guy5", "M")
c = e.char
e.state = PLYING
c.hits = 50
c.light = 0 # No active light charges

# Add a glowstone (item name 'glowstone')
glowstone_type = next((i for i, item in enumerate(e.items_db) if item.get('name') == 'glowstone'), None)
c.invent[0] = glowstone_type

# Teleport to Mountains
c.loc = 1183
print("=== AT MOUNTAINS WITH GLOWSTONE ===")
print("Sending `look`:")
print(e.process_input("look"))

# Remove glowstone
c.invent[0] = -1
print("\n=== AT MOUNTAINS WITHOUT GLOWSTONE ===")
print("Sending `look`:")
print(e.process_input("look"))

# Clean up
if os.path.exists('data/players/test_guy5.json'):
    os.remove('data/players/test_guy5.json')

