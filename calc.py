# Defensive optimiser for Pokémon Champions

import math

def ROUND(num: float) -> int:
    return math.ceil(num - 0.5)

def damage_formula(P: int, A: int, D: int, M: list[float]) -> int:
    dmg = ROUND((((2 * 50) / 5 + 2) * P * A / D) / 50 + 2)
    
    for modifier in M:
        dmg = ROUND(dmg * modifier)
    
    return dmg

BASE_HP = int(input("BASE HP:  "))
BASE_DEF = int(input("BASE DEF: "))
NATURE = float(input("NATURE:   "))
DEF_MULT = float(input("DEF MULT: "))
BUDGET = min(int(input("BUDGET:   ")), 64)

POWER = int(input("POWER:    "))
ATTACK = int(input("ATTACK:   "))
MULT = eval(input("MULT:     "))

def optimise(BASE_HP: int,
             BASE_DEF: int,
             NATURE: float,
             DEF_MULT: float,
             BUDGET: int,
             POWER: int,
             ATTACK: int,
             MULT: list[float]
             ) -> float:
    optimal_stats = {}
    minimum_dealt = float("inf")
    for i in range(BUDGET + 1):
        DEF_STATS = i
        HP_STATS = BUDGET - DEF_STATS

        if DEF_STATS > 32 or HP_STATS > 32:
            continue

        HP = BASE_HP + HP_STATS + 75
        DEF = math.floor((BASE_DEF + DEF_STATS + 20) * NATURE)
        DEF = math.floor(DEF * DEF_MULT)
        
        DMG = damage_formula(POWER, ATTACK, DEF, MULT)
        damage_dealt = DMG / HP

        if damage_dealt < minimum_dealt:
            minimum_dealt = damage_dealt
            optimal_stats = {"HP_STATS": HP_STATS, "DEF_STATS": DEF_STATS, "DMG": DMG, "HP": HP}

    print(f"Optimal spread:  {optimal_stats['HP_STATS']} SP → HP  |  {optimal_stats['DEF_STATS']} SP → DEF")
    print(f"Damage dealt:    {optimal_stats['DMG']} / {optimal_stats['HP']} HP")
    print(f"% HP dealt:      {minimum_dealt * 100:.1f}%")
    print(f"% HP remaining:  {(1 - minimum_dealt) * 100:.1f}%")

    return minimum_dealt

optimise(BASE_HP, BASE_DEF, NATURE, DEF_MULT, BUDGET, POWER, ATTACK, MULT)