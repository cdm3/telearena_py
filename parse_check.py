import sys, os
from parse_data import parse_town_data

town_rooms, townsfolk_types = parse_town_data()
r10 = [r for r in town_rooms if r['id'] == 10][0]
print("Room 10 exits in town_rooms.json:", r10['exits'])

