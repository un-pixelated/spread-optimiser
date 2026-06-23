import math

def ROUND(num) -> int:
    return math.ceil(num - 0.5)

def damage_formula(L: int, P: int, A: int, D: int, M: list[float]) -> int:
    dmg = ROUND((((2 * L) / 5 + 2) * P * A / D) / 50 + 2)
    
    for modifier in M:
        dmg = ROUND(dmg * modifier)
    
    return dmg

print(damage_formula(75, 65, 123, 163, [1.5, 4]))