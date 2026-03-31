"""
Tele-Arena 5.6 Python Port - Shop System
Handles equipment, weapon, armor, magic shops, guild, temple, vault, tavern.
"""

import random
from .constants import *
from . import messages as msg


# Items that each shop type sells (by shop field value in item data)
SHOP_SELLS = {
    SHOP_EQUIPMENT: [1],      # shop field values for equipment shops
    SHOP_WEAPON:    [2],
    SHOP_ARMOR:     [3],
    SHOP_MAGIC:     [4],
}


def get_shop_inventory(shop_type, items_db, char_level=1):
    """
    Return list of item indices available in the given shop type.
    Filtered by character level if provided.
    """
    shop_field = {
        SHOP_EQUIPMENT: 1,
        SHOP_WEAPON:    2,
        SHOP_ARMOR:     3,
        SHOP_MAGIC:     4,
    }.get(shop_type, 0)

    if shop_field == 0:
        return []

    result = []
    for i, item in enumerate(items_db):
        if item.get('shop', 0) == shop_field:
            # Filter by item level requirement
            req_level = item.get('level', 0)
            if req_level <= char_level:
                result.append(i)
    return result


def buy_item(char, item_name, shop_type, items_db, world):
    """
    Handle buying an item from a shop.
    Returns (success, message).
    """
    from .character import find_empty_slot, check_encumbrance, recalc_encumbrance

    inventory = get_shop_inventory(shop_type, items_db, char.level)
    if not inventory:
        return False, '***\nThis shop has nothing for sale.\n'

    # Find item by name
    name_lower = item_name.lower()
    found_idx = -1
    for i in inventory:
        if name_lower in items_db[i]['name'].lower():
            found_idx = i
            break

    if found_idx == -1:
        return False, f'***\nThis shop doesn\'t carry {item_name}.\n'

    item = items_db[found_idx]
    price = item.get('price', 0)

    # Check gold
    if char.gold < price:
        return False, f'***\nYou don\'t have enough gold! (need {price} gold)\n'

    # Check encumbrance
    if not check_encumbrance(char, item.get('wt', 0)):
        return False, '***\nYou can\'t carry any more weight!\n'

    # Check inventory space
    slot = find_empty_slot(char)
    if slot == -1:
        return False, '***\nYour inventory is full!\n'

    # Check class restriction
    req_clas = item.get('clas', 0)
    if req_clas != 0 and char.clas != req_clas:
        return False, f'***\nYou cannot use that item.\n'

    # Purchase
    char.gold -= price
    char.invent[slot] = found_idx
    char.charge[slot] = item.get('charges', 0)
    recalc_encumbrance(char, items_db)

    iname = item.get('desc', item.get('name', 'item'))
    return True, f'***\nYou buy {iname} for {price} gold.\n'


def sell_item(char, item_name, shop_type, items_db, world):
    """
    Handle selling an item to a shop.
    Returns (success, message).
    """
    from .character import find_item_in_inv, recalc_encumbrance

    slot = find_item_in_inv(char, item_name, items_db)
    if slot == -1:
        return False, f'***\nYou don\'t have {item_name}.\n'

    item_idx = char.invent[slot]
    item = items_db[item_idx]
    shop_field = item.get('shop', 0)

    # Check if this shop buys this type
    expected_shop_field = {
        SHOP_EQUIPMENT: 1,
        SHOP_WEAPON:    2,
        SHOP_ARMOR:     3,
        SHOP_MAGIC:     4,
    }.get(shop_type, 0)

    if shop_field == 0 or shop_field != expected_shop_field:
        return False, f'***\nThis shop doesn\'t buy that type of item.\n'

    # Sell price = half purchase price
    sell_price = max(1, item.get('price', 0) // 2)

    # Remove from inventory
    char.invent[slot] = -1
    char.charge[slot] = 0
    char.gold = min(60000, char.gold + sell_price)
    recalc_encumbrance(char, items_db)

    # Unequip if equipped
    if char.weapon == item_idx:
        char.weapon = DEFWEP
    if char.armor == item_idx:
        char.armor = DEFARM if DEFARM < len(items_db) else 0

    iname = item.get('name', 'item')
    return True, f'***\nYou sell {iname} for {sell_price} gold.\n'


def list_shop_items(shop_type, items_db, char):
    """Return formatted list of items for sale."""
    inventory = get_shop_inventory(shop_type, items_db, char.level)
    if not inventory:
        return '***\nThis shop has nothing for sale.\n'

    lines = ['***\nItems for sale:\n']
    for i in inventory:
        item = items_db[i]
        name = item.get('name', 'unknown')
        price = item.get('price', 0)
        level = item.get('level', 0)
        lvl_str = f' (lvl {level})' if level > 0 else ''
        lines.append(f'  {name:<25} {price:>6} gold{lvl_str}\n')
    return ''.join(lines)


def buy_spell(char, spell_name, items_db, spells_db):
    """
    Buy a spell at the guild hall.
    Returns (success, message).
    """
    if not char.can_cast:
        cname = char.class_plural
        return False, f'***\n{cname} don\'t use spellbooks!\n'

    # Find an empty spellbook slot
    empty_slot = -1
    for i in range(SPLBOK):
        if char.splbook[i] == 255:
            empty_slot = i
            break

    if empty_slot == -1:
        return False, '***\nYour spellbook is full!\n'

    # Find the spell
    name_lower = spell_name.lower()
    found_idx = -1
    for i, sp in enumerate(spells_db):
        if name_lower in sp['name'].lower():
            if sp.get('level', 1) <= char.level:
                found_idx = i
                break

    if found_idx == -1:
        return False, f'***\nThe guild doesn\'t have "{spell_name}" available for your level.\n'

    # Check if already known
    if found_idx in char.splbook:
        return False, f'***\nYou already know {spells_db[found_idx]["name"]}!\n'

    price = spells_db[found_idx].get('price', 0)
    if char.gold < price:
        return False, f'***\nYou don\'t have enough gold! (need {price} gold)\n'

    char.gold -= price
    char.splbook[empty_slot] = found_idx

    sname = spells_db[found_idx]['name']
    return True, f'***\nYou learn {sname} for {price} gold.\n'


def purge_spell(char, spell_name, spells_db):
    """Remove a spell from the spellbook."""
    name_lower = spell_name.lower()
    for i in range(SPLBOK):
        si = char.splbook[i]
        if si == 255:
            continue
        if si < len(spells_db) and name_lower in spells_db[si]['name'].lower():
            char.splbook[i] = 255
            sname = spells_db[si]['name']
            return True, f'***\nYou purge {sname} from your spellbook.\n'
    return False, f'***\nYou don\'t have {spell_name} in your spellbook.\n'


def list_spells(spells_db, char):
    """Return formatted list of available spells for purchase."""
    lines = ['***\nSpells available:\n']
    for i, sp in enumerate(spells_db):
        lvl = sp.get('level', 1)
        price = sp.get('price', 0)
        name = sp.get('name', 'unknown')
        avail = '*' if lvl <= char.level else ' '
        lines.append(f'  {avail} {name:<25} (lvl {lvl}) {price:>5} gold\n')
    return ''.join(lines)


def bank_deposit(char, amount):
    """Deposit gold to bank."""
    amount = max(0, int(amount))
    if amount > char.gold:
        return False, '***\nYou don\'t have that much gold!\n'
    char.gold -= amount
    char.accbal += amount
    return True, f'***\nYou deposit {amount} gold. Balance: {char.accbal} gold.\n'


def bank_withdraw(char, amount):
    """Withdraw gold from bank."""
    amount = max(0, int(amount))
    if amount > char.accbal:
        return False, '***\nYou don\'t have that much in your account!\n'
    if (char.gold + amount) > 60000:
        amount = 60000 - char.gold
    char.accbal -= amount
    char.gold += amount
    return True, f'***\nYou withdraw {amount} gold. Balance: {char.accbal} gold.\n'


def bank_balance(char):
    return f'***\nBalance: {char.accbal} gold  On hand: {char.gold} gold\n'


def donate_to_temple(char, amount):
    """Donate gold to temple for XP."""
    amount = max(0, int(amount))
    if amount > char.gold:
        return False, '***\nYou don\'t have that much gold!\n'
    char.gold -= amount
    xp_gain = amount // 2
    char.exp += xp_gain
    return True, f'***\nYou donate {amount} gold to the temple and gain {xp_gain} experience.\n'


def tavern_options(char, items_db):
    """Return available tavern interactions."""
    return ('***\nWelcome to the tavern!\n'
            'Commands: buy food, buy drink, play slots, play bones\n')


def buy_food_drink(char, what, items_db):
    """Buy food or drink at tavern."""
    if 'food' in what.lower():
        # Find food item
        for i, item in enumerate(items_db):
            if item.get('effect') == EFF_FOOD:
                price = max(1, item.get('price', 2))
                if char.gold < price:
                    return False, '***\nYou can\'t afford it!\n'
                char.gold -= price
                char.food = min(START_FOOD, char.food + 3600)
                return True, f'***\nYou eat a hearty meal and feel satisfied.\n'
    elif 'drink' in what.lower() or 'water' in what.lower():
        price = 1
        if char.gold < price:
            return False, '***\nYou can\'t afford it!\n'
        char.gold -= price
        char.water = min(START_WATER, char.water + 1800)
        return True, '***\nYou drink deeply and feel refreshed.\n'
    return False, '***\nThe bartender doesn\'t have that.\n'


def play_slots(char):
    """Simple slot machine game."""
    cost = 10
    if char.gold < cost:
        return '***\nYou don\'t have enough gold to play!\n'

    char.gold -= cost
    char.pulls = (char.pulls or 0) + 1

    # 3 reels, 6 symbols
    symbols = ['cherry', 'lemon', 'orange', 'plum', 'bell', 'bar']
    r1 = random.choice(symbols)
    r2 = random.choice(symbols)
    r3 = random.choice(symbols)

    result = f'***\n[ {r1} | {r2} | {r3} ]\n'
    if r1 == r2 == r3:
        win = cost * 10
        char.gold += win
        result += f'JACKPOT! You win {win} gold!\n'
    elif r1 == r2 or r2 == r3 or r1 == r3:
        win = cost * 2
        char.gold += win
        result += f'Two of a kind! You win {win} gold!\n'
    else:
        result += 'Sorry, no match. Better luck next time!\n'
    return result


def play_dice(char):
    """Dice game (Bones)."""
    cost = 5
    if char.gold < cost:
        return '***\nYou don\'t have enough gold to play!\n'

    char.gold -= cost
    player_roll = random.randint(1, 6) + random.randint(1, 6)
    house_roll = random.randint(1, 6) + random.randint(1, 6)
    result = f'***\nYou roll: {player_roll}   House rolls: {house_roll}\n'
    if player_roll > house_roll:
        win = cost * 2
        char.gold += win
        result += f'You win {win} gold!\n'
    elif player_roll < house_roll:
        result += 'House wins!\n'
    else:
        char.gold += cost  # push
        result += 'Push! You get your bet back.\n'
    return result
