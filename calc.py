# Defensive optimiser for Pokémon Champions
# Uses @smogon/calc via bridge.js for damage calculation

import subprocess
import json
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

def clamp_boost(n: int) -> int:
    return max(-6, min(6, n))

# ── tuner ────────────────────────────────────────────────
# Among all spreads whose damage % is within `tolerance` pp of the
# optimum, pick the one that maximises the prioritised stat's SP.
# Ties broken by maximising the other stat.

def tune(
    results: list[dict],       # list of {HP_SP, DEF_SP, damage_dealt, DMG, HP, desc}
    def_stat: str,
    priority: str,             # 'hp' or def_stat
    tolerance: float,          # percentage points, e.g. 0.5 means ±0.5%
) -> dict | None:
    if not results:
        return None

    best_pct = min(r['damage_dealt'] for r in results) * 100
    threshold = best_pct + tolerance          # we accept up to this % damage

    candidates = [r for r in results if r['damage_dealt'] * 100 <= threshold]
    if not candidates:
        return None

    if priority == 'hp':
        return max(candidates, key=lambda r: (r['HP_SP'], r[f'{def_stat}_SP']))
    else:
        return max(candidates, key=lambda r: (r[f'{def_stat}_SP'], r['HP_SP']))


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
    TUNER: dict | None = None,   # {'priority': 'hp'|DEF_STAT, 'tolerance': float} or None
) -> float:
    xs = []
    ys = []
    move_type = ''
    all_results = []

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
        if not xs:
            move_type = result.get('moveType', '')
        HP           = calc_hp(result['defenderBaseHp'], HP_SP)
        DMG          = result['max']
        damage_dealt = DMG / HP

        xs.append((HP_SP, DEF_SP))
        ys.append(damage_dealt)
        all_results.append({
            'HP_SP': HP_SP, f'{DEF_STAT}_SP': DEF_SP,
            'delta_hp': delta_hp, f'delta_{DEF_STAT}': delta_def,
            'damage_dealt': damage_dealt, 'DMG': DMG, 'HP': HP,
            'desc': result['desc'],
        })

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

    # ── optimal output ───────────────────────────────────
    print()
    print("─" * 60)
    print("  OPTIMAL")
    print("─" * 60)
    print(f"  Spread:         {optimal_stats['HP_SP']} HP / {optimal_stats['DEF_SP']} {DEF_STAT.upper()}")
    print(f"  Additional:     +{optimal_stats['delta_hp']} HP / +{optimal_stats['delta_def']} {DEF_STAT.upper()}")
    print(f"  Damage:         {optimal_stats['DMG']} / {optimal_stats['HP']} HP  ({minimum_dealt * 100:.1f}% dealt, {(1 - minimum_dealt) * 100:.1f}% remaining)")
    print(f"  Desc:           {optimal_stats['desc']}")

    # ── tuner output ─────────────────────────────────────
    if TUNER:
        priority  = TUNER['priority']   # 'hp' or DEF_STAT
        tolerance = TUNER['tolerance']  # percentage points

        tuned = tune(all_results, DEF_STAT, priority, tolerance)

        print()
        print("─" * 60)
        print(f"  TUNED OPTIMAL  (priority: {priority.upper()}, tolerance: ±{tolerance}%)")
        print("─" * 60)

        if tuned is None or (
            tuned['HP_SP'] == optimal_stats['HP_SP'] and
            tuned[f'{DEF_STAT}_SP'] == optimal_stats['DEF_SP']
        ):
            print("  No different spread found within tolerance — tuned result is identical to optimal.")
        else:
            t_pct   = tuned['damage_dealt'] * 100
            opt_pct = minimum_dealt * 100
            sacrifice = t_pct - opt_pct

            print(f"  Spread:         {tuned['HP_SP']} HP / {tuned[f'{DEF_STAT}_SP']} {DEF_STAT.upper()}")
            print(f"  Additional:     +{tuned['delta_hp']} HP / +{tuned[f'delta_{DEF_STAT}']} {DEF_STAT.upper()}")
            print(f"  Damage:         {tuned['DMG']} / {tuned['HP']} HP  ({t_pct:.1f}% dealt, {100 - t_pct:.1f}% remaining)")
            print(f"  Sacrifice:      +{sacrifice:.2f}% vs optimal")
            print(f"  Desc:           {tuned['desc']}")

    print("─" * 60)

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
    'sp':      eval(input('Attacker SPs:     ')),
}

defender_name    = input('Defender name:    ')
defender_nature  = input('Defender nature:  ')
defender_ability = input('Defender ability (or blank): ') or None
defender_item    = input('Defender item (or blank):    ') or None

move = {
    'name':   input('Move name:  '),
    'isCrit': input('Crit? (y/n): ').lower() == 'y',
}

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

# ── tuner ────────────────────────────────────────────────
tuner = None
use_tuner = input('Enable tuner mode? (y/n): ').strip().lower() == 'y'
if use_tuner:
    # Normalise stat label: hp stays hp, anything else → defensive_stat
    raw_priority = input(f'Prioritise stat (hp / {defensive_stat}): ').strip().lower()
    priority = 'hp' if raw_priority in ('hp',) else defensive_stat

    tolerance = float(input('Tolerance — max % HP you\'re willing to sacrifice vs optimal (e.g. 0.5): ') or 0)
    tuner = {'priority': priority, 'tolerance': tolerance}

optimise(
    attacker, defender_name, defender_nature, defender_ability, defender_item,
    defensive_stat, defender_boost, existing_hp, existing_def,
    budget, move, field,
    TUNER=tuner,
)