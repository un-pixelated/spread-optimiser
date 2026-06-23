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
BUDGET = int(input("BUDGET:   "))

POWER = int(input("POWER:    "))
ATTACK = int(input("ATTACK:   "))
MULT = list(input("MULT:     "))

def optimise(BASE_HP: int,
             BASE_DEF: int,
             NATURE: float,
             BUDGET: int,
             POWER: int,
             ATTACK: int,
             MULT: list[float]
             ) -> float:
    HP = BASE_HP + 75
    


print(damage_formula(75, 65, 123, 163, [0.85, 1.5, 4]))