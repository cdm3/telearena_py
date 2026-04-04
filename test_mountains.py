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

# Teleport to South Plaza (Room 10)
c.loc = 10
print("=== AT SOUTH PLAZA (ROOM 10) ===")
print("Sending `look`:")
print(e.process_input("look"))

print("\nSending `sw`:")
print(e.process_input("sw"))

print("\n=== AT MOUNTAINS ===")
print("Sending `look`:")
print(e.process_input("look"))

print("\nSending `s` (which returns to -90, i.e., Room 10):")
print(e.process_input("s"))

print("\n=== BACK TO SOUTH PLAZA ===")
print("Sending `look`:")
print(e.process_input("look"))

# Clean up
if os.path.exists('data/players/test_guy5.json'):
    os.remove('data/players/test_guy5.json')

