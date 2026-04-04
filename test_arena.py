import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from game.engine import GameEngine

e = GameEngine()
e.load_data()

# Start game
e.enter_game("test_guy", "M")
c = e.char

# Check initial spawns
initial_spawns = e.monster_mgr.get_room_monsters(2)
print("Initial passive Arena 1 spawns count (should be 0):", len(initial_spawns))

# Let's put the player in arena and hit gong
def test_arena(room_id, terr_name):
    c.loc = room_id
    c.attdly = 0  # Clear delay so we can ring again
    out = e._cmd_ring_gong()
    print(f"\n--- Ringing Gong in Arena Room {room_id} ({terr_name}) ---")
    print("Output text:")
    print(out.strip())
    
    # Get the latest spawns in room
    # Clear out room monsters first
    e.monster_mgr.instances.clear()
    c.attdly = 0
    e._cmd_ring_gong()
    mids = e.monster_mgr.get_room_monsters(room_id)
    print("Spawned monster names:")
    for m in mids:
        val = e.monster_mgr.instances[m]
        print(" -", val.type.name, "(terr:", val.type.terr, ")")

test_arena(2, "Arena 1 / terr=1")
test_arena(28, "Arena 2 / terr=10")
test_arena(47, "Arena 3 / terr=7")

if os.path.exists('data/players/test_guy.json'):
    os.remove('data/players/test_guy.json')
