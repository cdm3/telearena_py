import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from game.engine import GameEngine
from game.constants import PLYING

e = GameEngine()
e.load_data()

# Enter the game
e.enter_game("test_guy4", "M")
c = e.char

# Force bypass of character creation
e.state = PLYING
c.hits = 50

# Give player level 20 so they COULD see max tier items if they were available
c.level = 20
c.loc = 6 # Teleport directly to Weapon Shop in Town Area 1 (Tier 1)
c.gold = 50000 # Make sure we have enough money

print("=== AT WEAPON SHOP (TOWN 1) ===")
print("Sending `look`:")
print(e.process_input("look"))

print("\nSending `list items` (Should NOT contain tier 2/3 weapons like Elven Bow or Demonhide):")
print(e.process_input("list items"))

print("\nSending `buy shortsword`:")
print(e.process_input("buy shortsword"))

print("\nSending `sell shortsword`:")
print(e.process_input("sell shortsword"))

print("\n=== AT WEAPON SHOP (TOWN 3) ===")
c.loc = 46 # Teleport to Weapon Shop in Town Area 3 (Tier 2)

print("Sending `look`:")
print(e.process_input("look"))

print("\nSending `list items` (Should contain better weapons now!):")
print(e.process_input("list items"))

# Clean up
if os.path.exists('data/players/test_guy4.json'):
    os.remove('data/players/test_guy4.json')

