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
c.light = 100 # Give a light source!

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

print("\nSending `north` (trying directions from 183):")
print(e.process_input("n"))
print("\nSending `south`:")
print(e.process_input("s"))
print("\nSending `east`:")
print(e.process_input("e"))

# Clean up
if os.path.exists('data/players/test_guy5.json'):
    os.remove('data/players/test_guy5.json')

