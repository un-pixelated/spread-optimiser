# Defensive optimiser for Pokémon Champions
# Uses @smogon/calc via bridge.js for damage calculation

import subprocess
import json
import math
from plot import plot

BRIDGE = './bridge.js'

# One persistent Node process for the whole run.
_node = subprocess.Popen(
    ['node', BRIDGE],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    text=True,
)

def calc_damage(attacker, defender, move, field) -> dict:
    payload = json.dumps({
        'attacker': attacker,
        'defender': defender,
        'move': move,
        'field': field,
    }) + '\n'
    _node.stdin.write(payload)
    _node.stdin.flush()
    return json.loads(_node.stdout.readline())

def calc_hp(base: int, sp: int) -> int:
    return base + sp + 75

def clamp_boost(n: int) -> int:
    return max(-6, min(6, n))

def optimise(
    ATTACKER: dict,
    DEFENDER_NAME: str,
    DEFENDER_NATURE: str,
    DEFENDER_ABILITY: str,
    DEFENDER_ITEM: str | None,
    DEF_STAT: str,
    DEFENDER_BOOST: int,
    EXISTING_HP: int,
    EXISTING_DEF: int,
    BUDGET: int,
    MOVE: dict,
    FIELD: dict,
) -> float:
    xs = []
    ys = []
    move_type = ''

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
            'name':    DEFENDER_NAME,
            'nature':  DEFENDER_NATURE,
            'item':    DEFENDER_ITEM,
            'ability': DEFENDER_ABILITY,
            'sp':      {'hp': HP_SP, DEF_STAT: DEF_SP},
            'boosts':  {DEF_STAT: DEFENDER_BOOST},
        }

        result       = calc_damage(ATTACKER, defender, MOVE, FIELD)
        if not xs:  # capture move type on first call
            move_type = result.get('moveType', '')
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
        move_type=move_type,
        best_index=best_index,
        best_dmg=optimal_stats['DMG'],
        best_hp=optimal_stats['HP'],
        best_desc=optimal_stats['desc'],
    )
    return minimum_dealt


# ── inputs ──────────────────────────────────────────────
attacker = {
    'name':    input('Attacker name:    '),
    'nature':  input('Attacker nature:  '),
    'item':    input('Attacker item:    ') or None,
    'ability': input('Attacker ability (or blank): ') or None,
    'sp':      eval(input('Attacker SPs:     ')),   # e.g. {"atk": 32}
}

defender_name    = input('Defender name:    ')
defender_nature  = input('Defender nature:  ')
defender_ability = input('Defender ability (or blank): ') or None
defender_item    = input('Defender item (or blank):    ') or None

move = {
    'name':   input('Move name:  '),
    'isCrit': input('Crit? (y/n): ').lower() == 'y',
}

# Which stat the move's damage is actually calculated off, on each side.
# Physical moves usually use atk/def, special moves usually use spa/spd —
# but a few moves break that (Psyshock/Psystrike/Secret Sword hit DEF
# despite being special; Body Press uses the attacker's own DEF, etc).
# Rather than guess off the move's category, just say which ones apply.
attacking_stat = input('Attacking stat this move uses - atk/spa: ').strip().lower()
while attacking_stat not in ('atk', 'spa'):
    attacking_stat = input("Please type 'atk' or 'spa': ").strip().lower()

attacker_boost = clamp_boost(int(input(
    f'Attacker {attacking_stat.upper()} stage boost (-6 to +6, 0 if none): ') or 0))
attacker['boosts'] = {attacking_stat: attacker_boost}

defensive_stat = input('Defensive stat this move hits - def/spd: ').strip().lower()
while defensive_stat not in ('def', 'spd'):
    defensive_stat = input("Please type 'def' or 'spd': ").strip().lower()

defender_boost = clamp_boost(int(input(
    f'Defender {defensive_stat.upper()} stage boost (-6 to +6, 0 if none): ') or 0))

existing_hp  = int(input('SPs already invested in HP (0 if none): ') or 0)
existing_def = int(input(f'SPs already invested in {defensive_stat.upper()} (0 if none): ') or 0)

budget = int(input(f'Additional SP budget to spend (HP + {defensive_stat.upper()}): '))

# Terrain works the same regardless of what set it — a move (Electric
# Terrain), or an ability (Hadron Engine, Electric Surge, etc.) — as long
# as the relevant Pokémon's ability is entered above, terrain-linked
# abilities like Hadron Engine's SpA boost are picked up automatically.
TERRAINS = {'electric': 'Electric', 'grassy': 'Grassy', 'misty': 'Misty', 'psychic': 'Psychic', '': None}
terrain_in = input('Terrain (Electric/Grassy/Misty/Psychic, or blank): ').strip().lower()
while terrain_in not in TERRAINS:
    terrain_in = input("Please type Electric/Grassy/Misty/Psychic, or leave blank: ").strip().lower()
terrain = TERRAINS[terrain_in]

field = {
    'gameType':      input('Game type (Singles/Doubles): '),
    'weather':       input('Weather (or blank):          ') or None,
    'terrain':       terrain,
    'isReflect':     input('Reflect? (y/n): ').lower() == 'y',
    'isLightScreen': input('Light Screen? (y/n): ').lower() == 'y',
    'isHelpingHand': input("Helping Hand active for attacker? (y/n): ").lower() == 'y',
    'isFriendGuard': input("Friend Guard active for defender's side? (y/n): ").lower() == 'y',
}

optimise(
    attacker, defender_name, defender_nature, defender_ability, defender_item,
    defensive_stat, defender_boost, existing_hp, existing_def,
    budget, move, field,
)