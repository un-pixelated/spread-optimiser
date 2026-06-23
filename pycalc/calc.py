# Defensive optimiser for Pokémon Champions

import math
from pycalc.plot import plot

def ROUND(num: float) -> int:
    return math.ceil(num - 0.5)

def damage_formula(P: int, A: int, D: int, M: list[float]) -> int:
    base = math.floor((math.floor((2 * 50) / 5 + 2) * P * A / D) / 50 + 2)
    
    modifier = 1.0
    for m in M:
        modifier *= m
    
    return math.floor(base * modifier)

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
    xs = []
    ys = []

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

        xs.append((HP_STATS, DEF_STATS))
        ys.append(damage_dealt)

        print(f"({HP_STATS}, {DEF_STATS}) -> {damage_dealt * 100:.2f}%")

        if damage_dealt < minimum_dealt:
            minimum_dealt = damage_dealt
            optimal_stats = {"HP_STATS": HP_STATS, "DEF_STATS": DEF_STATS, "DMG": DMG, "HP": HP, "DEF": DEF}

    print(f"Optimal spread:  {optimal_stats['HP_STATS']} HP, {optimal_stats['DEF_STATS']} DEF")
    print(f"Final HP stat:   {optimal_stats['HP']}")
    print(f"Final DEF stat:  {optimal_stats['DEF']}")
    print(f"Damage dealt:    {optimal_stats['DMG']} / {optimal_stats['HP']} HP")
    print(f"% HP dealt:      {minimum_dealt * 100:.1f}%")
    print(f"% HP remaining:  {(1 - minimum_dealt) * 100:.1f}%")

    plot(xs, ys)

    return minimum_dealt

optimise(BASE_HP, BASE_DEF, NATURE, DEF_MULT, BUDGET, POWER, ATTACK, MULT)