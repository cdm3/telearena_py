import sys
import os
import random

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from game.engine import GameEngine
from game.character import Character
from game.world import World

def test_traps():
    world = World()
    world.load()
    char = Character()
    char.userid = "TestRogue"
    char.clas = 3 # Rogue
    char.agil = 20
    char.know = 20
    char.level = 10
    char.hits = 100
    char.mhits = 100
    
    engine = GameEngine()
    engine.load_data()
    engine.char = char
    
    # Give a glowstone so we can see
    char.invent[0] = 25 # Glowstone Item ID (26 in items.db, but 0-indexed maybe?)
    # Wait, item 25 in items.db is glowstone (ID 26 in Gold).
    char.charge[0] = 100
    
    print("--- Testing Situational Trap (Message Link) ---")
    # Room 1927 in original data becomes 1927 + 100 = 2027
    char.loc = 2027
    print(f"Starting Room: {char.loc} ({engine.world.get_room(char.loc).short_desc})")
    
    # NE is index 6 in constants.py
    # EXIT1927 Slot 6 points to 1926 (Special Message)
    res = engine._cmd_move(6) 
    print(f"Result: {res}")
    
    print("\n--- Testing Room Entry Trap (Room 211 Pit) ---")
    # Room 211 (world) = dungeon RID 111, has type=1 pit trap, falls to RID 5 (world 105)
    # Enter from room 281 going south (direction 4) into the pit room 211
    char.clas = 1  # warrior — no rogue avoidance
    char.loc = 281
    print(f"Starting Room: {char.loc} ({engine.world.get_room(char.loc).short_desc})")
    res = engine._cmd_move(4)  # S = 4
    print(f"Result: {res}")
    print(f"Final loc: {char.loc} ({engine.world.get_room(char.loc).short_desc})")
    print(f"Health: {char.hits}/{char.mhits}")

if __name__ == "__main__":
    test_traps()
