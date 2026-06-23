# Defensive optimiser for Pokémon Champions
# Uses @smogon/calc via bridge.js for damage calculation

import subprocess
import json
import math
from plot import plot

BRIDGE = './bridge.js'

def calc_damage(attacker, defender, move, field) -> dict:
    payload = json.dumps({
        'attacker': attacker,
        'defender': defender,
        'move': move,
        'field': field,
    })
    result = subprocess.run(
        ['node', BRIDGE],
        input=payload, capture_output=True, text=True
    )
    return json.loads(result.stdout)

def calc_hp(base: int, sp: int) -> int:
    return base + sp + 75

def optimise(
    ATTACKER: dict,
    DEFENDER_NAME: str,
    DEFENDER_NATURE: str,
    BASE_HP: int,
    BUDGET: int,
    MOVE: dict,
    FIELD: dict,
) -> float:
    xs = []
    ys = []

    optimal_stats = {}
    minimum_dealt = float('inf')

    for i in range(min(BUDGET, 64) + 1):
        DEF_SP = i
        HP_SP  = min(BUDGET, 64) - DEF_SP

        if DEF_SP > 32 or HP_SP > 32:
            continue

        defender = {
            'name':   DEFENDER_NAME,
            'nature': DEFENDER_NATURE,
            'sp':     {'hp': HP_SP, 'def': DEF_SP},
        }

        result       = calc_damage(ATTACKER, defender, MOVE, FIELD)
        HP           = calc_hp(BASE_HP, HP_SP)
        DMG          = result['max']
        damage_dealt = DMG / HP

        xs.append((HP_SP, DEF_SP))
        ys.append(damage_dealt)

        print(f"({HP_SP}, {DEF_SP}) -> {damage_dealt * 100:.2f}%  [{result['desc']}]")

        if damage_dealt < minimum_dealt:
            minimum_dealt = damage_dealt
            optimal_stats = {
                'HP_SP': HP_SP, 'DEF_SP': DEF_SP,
                'DMG': DMG, 'HP': HP,
                'desc': result['desc'],
            }

    print()
    print(f"Optimal spread:  {optimal_stats['HP_SP']} HP, {optimal_stats['DEF_SP']} DEF")
    print(f"Damage dealt:    {optimal_stats['DMG']} / {optimal_stats['HP']} HP")
    print(f"% HP dealt:      {minimum_dealt * 100:.1f}%")
    print(f"% HP remaining:  {(1 - minimum_dealt) * 100:.1f}%")
    print(f"Desc:            {optimal_stats['desc']}")

    plot(xs, ys)
    return minimum_dealt


# ── inputs ──────────────────────────────────────────────
attacker = {
    'name':   input('Attacker name:   '),
    'nature': input('Attacker nature: '),
    'item':   input('Attacker item:   ') or None,
    'sp':     eval(input('Attacker SPs:    ')),   # e.g. {"atk": 32}
}

defender_name   = input('Defender name:   ')
defender_nature = input('Defender nature: ')
base_hp         = int(input('Defender base HP: '))
budget          = int(input('SP budget:        '))

move = {
    'name':   input('Move name:  '),
    'isCrit': input('Crit? (y/n): ').lower() == 'y',
}

field = {
    'gameType':    input('Game type (Singles/Doubles): '),
    'weather':     input('Weather (or blank):          ') or None,
    'isReflect':   input('Reflect? (y/n): ').lower() == 'y',
    'isLightScreen': input('Light Screen? (y/n): ').lower() == 'y',
}

optimise(attacker, defender_name, defender_nature, base_hp, budget, move, field)