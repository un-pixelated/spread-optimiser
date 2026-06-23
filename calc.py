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
    DEF_STAT: str,
    EXISTING_HP: int,
    EXISTING_DEF: int,
    BUDGET: int,
    MOVE: dict,
    FIELD: dict,
) -> float:
    xs = []
    ys = []

    optimal_stats = {}
    minimum_dealt = float('inf')
    best_index = None

    for delta_def in range(0, min(BUDGET, 64) + 1):
        delta_hp = min(BUDGET, 64) - delta_def

        HP_SP  = EXISTING_HP + delta_hp
        DEF_SP = EXISTING_DEF + delta_def

        if HP_SP > 32 or DEF_SP > 32:
            continue

        defender = {
            'name':   DEFENDER_NAME,
            'nature': DEFENDER_NATURE,
            'sp':     {'hp': HP_SP, DEF_STAT: DEF_SP},
        }

        result       = calc_damage(ATTACKER, defender, MOVE, FIELD)
        HP           = calc_hp(result['defenderBaseHp'], HP_SP)
        DMG          = result['max']
        damage_dealt = DMG / HP

        xs.append((HP_SP, DEF_SP))
        ys.append(damage_dealt)

        print(f"+{delta_hp:>2} HP / +{delta_def:>2} {DEF_STAT.upper()}  "
              f"(totals {HP_SP}/{DEF_SP}) -> {damage_dealt * 100:.2f}%  [{result['desc']}]")

        if damage_dealt < minimum_dealt:
            minimum_dealt = damage_dealt
            best_index = len(xs) - 1
            optimal_stats = {
                'HP_SP': HP_SP, 'DEF_SP': DEF_SP,
                'delta_hp': delta_hp, 'delta_def': delta_def,
                'DMG': DMG, 'HP': HP,
                'desc': result['desc'],
            }

    if not optimal_stats:
        print("No valid spread found — check your existing SPs / budget don't push either stat past 32.")
        return None

    print()
    print(f"Optimal spread:     {optimal_stats['HP_SP']} HP, {optimal_stats['DEF_SP']} {DEF_STAT.upper()}")
    print(f"Additional needed:  +{optimal_stats['delta_hp']} HP, +{optimal_stats['delta_def']} {DEF_STAT.upper()}")
    print(f"Damage dealt:       {optimal_stats['DMG']} / {optimal_stats['HP']} HP")
    print(f"% HP dealt:         {minimum_dealt * 100:.1f}%")
    print(f"% HP remaining:     {(1 - minimum_dealt) * 100:.1f}%")
    print(f"Desc:               {optimal_stats['desc']}")

    plot(
        xs, ys, DEF_STAT,
        attacker_name=ATTACKER['name'],
        defender_name=DEFENDER_NAME,
        move_name=MOVE['name'],
        best_index=best_index,
    )
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

move = {
    'name':   input('Move name:  '),
    'isCrit': input('Crit? (y/n): ').lower() == 'y',
}

# Which defensive stat the move actually hits. Physical moves usually hit
# `def`, special moves usually hit `spd` — but a few special moves
# (Psyshock, Psystrike, Secret Sword...) hit DEF instead. Rather than guess
# off the move's category, just say which one applies.
defensive_stat = input('Defensive stat this move hits - def/spd: ').strip().lower()
while defensive_stat not in ('def', 'spd'):
    defensive_stat = input("Please type 'def' or 'spd': ").strip().lower()

existing_hp  = int(input('SPs already invested in HP                (0 if none): ') or 0)
existing_def = int(input(f'SPs already invested in {defensive_stat.upper()} (0 if none): ') or 0)

budget = int(input(f'Additional SP budget to spend (HP + {defensive_stat.upper()}): '))

field = {
    'gameType':    input('Game type (Singles/Doubles): '),
    'weather':     input('Weather (or blank):          ') or None,
    'isReflect':   input('Reflect? (y/n): ').lower() == 'y',
    'isLightScreen': input('Light Screen? (y/n): ').lower() == 'y',
}

optimise(
    attacker, defender_name, defender_nature,
    defensive_stat, existing_hp, existing_def,
    budget, move, field,
)