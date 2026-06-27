# Dual-attack defensive optimiser for Pokémon Champions
# Minimises (dmg1 + dmg2) / HP across all valid SP spreads within budget.
# Supports phys/phys, spec/spec, phys/spec — two-stat or three-stat search.
# Uses @smogon/calc via bridge.js for damage calculation.

import subprocess
import json

BRIDGE = './bridge.js'

_node = subprocess.Popen(
    ['node', BRIDGE],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    text=True,
)

# ── copied from calc.py (not imported to keep calc.py untouched) ─────────────

def calc_damage(attacker, defender, move, field) -> dict:
    payload = json.dumps({
        'attacker': attacker,
        'defender': defender,
        'move':     move,
        'field':    field,
    }) + '\n'
    _node.stdin.write(payload)
    _node.stdin.flush()
    return json.loads(_node.stdout.readline())

def calc_hp(base: int, sp: int) -> int:
    return base + sp + 75

def clamp_boost(n: int) -> int:
    return max(-6, min(6, n))

# ── input helpers ─────────────────────────────────────────────────────────────

TERRAINS = {
    'electric': 'Electric', 'grassy': 'Grassy',
    'misty':    'Misty',    'psychic': 'Psychic',
    '':         None,
}

def prompt_attacker(label: str) -> dict:
    print(f"\n── Attacker {label} ──")
    name    = input(f'  Name:             ')
    nature  = input(f'  Nature:           ')
    item    = input(f'  Item (or blank):  ') or None
    ability = input(f'  Ability (or blank): ') or None
    sp      = eval(input(f'  SPs (e.g. {{"atk": 32}}): '))
    return {'name': name, 'nature': nature, 'item': item, 'ability': ability, 'sp': sp}

def prompt_move(label: str, attacker: dict) -> tuple[dict, str, int, str, int]:
    """Returns (move_dict, attacking_stat, attacker_boost, defensive_stat, defender_boost)."""
    print(f"\n── Move {label} ──")
    move = {
        'name':   input(f'  Move name:    '),
        'isCrit': input(f'  Crit? (y/n):  ').lower() == 'y',
    }

    atk_stat = input('  Attacking stat (atk/spa): ').strip().lower()
    while atk_stat not in ('atk', 'spa'):
        atk_stat = input("  Please type 'atk' or 'spa': ").strip().lower()

    atk_boost = clamp_boost(int(input(
        f'  Attacker {atk_stat.upper()} stage boost (-6 to +6, 0 if none): ') or 0))
    attacker['boosts'] = {atk_stat: atk_boost}

    def_stat = input('  Defensive stat it hits (def/spd): ').strip().lower()
    while def_stat not in ('def', 'spd'):
        def_stat = input("  Please type 'def' or 'spd': ").strip().lower()

    def_boost = clamp_boost(int(input(
        f'  Defender {def_stat.upper()} stage boost (-6 to +6, 0 if none): ') or 0))

    return move, atk_stat, atk_boost, def_stat, def_boost

def prompt_field(label: str) -> dict:
    print(f"\n── Field conditions (Move {label}) ──")
    terrain_in = input('  Terrain (Electric/Grassy/Misty/Psychic, or blank): ').strip().lower()
    while terrain_in not in TERRAINS:
        terrain_in = input("  Please type Electric/Grassy/Misty/Psychic, or leave blank: ").strip().lower()

    return {
        'gameType':      input('  Game type (Singles/Doubles): '),
        'weather':       input('  Weather (or blank):          ') or None,
        'terrain':       TERRAINS[terrain_in],
        'isReflect':     input('  Reflect? (y/n): ').lower() == 'y',
        'isLightScreen': input('  Light Screen? (y/n): ').lower() == 'y',
        'isHelpingHand': input('  Helping Hand active for attacker? (y/n): ').lower() == 'y',
        'isFriendGuard': input("  Friend Guard active for defender's side? (y/n): ").lower() == 'y',
    }

# ── core optimiser ────────────────────────────────────────────────────────────

def optimise_two(
    # Defender
    defender_name:    str,
    defender_nature:  str,
    defender_ability: str | None,
    defender_item:    str | None,
    # Move 1
    attacker1:   dict,
    move1:       dict,
    def_stat1:   str,   # 'def' or 'spd'
    def_boost1:  int,
    field1:      dict,
    # Move 2
    attacker2:   dict,
    move2:       dict,
    def_stat2:   str,
    def_boost2:  int,
    field2:      dict,
    # Budget
    existing_hp:   int,
    existing_def1: int,
    existing_def2: int,  # ignored / same as existing_def1 when def_stat1 == def_stat2
    budget:        int,
):
    same_stat = (def_stat1 == def_stat2)

    optimal     = None
    minimum_sum = float('inf')
    all_results = []

    # ── two-stat search (both moves hit the same defensive stat) ──────────────
    if same_stat:
        def_stat = def_stat1
        existing_def = existing_def1  # def2 is the same stat

        print(f"\nBoth moves hit {def_stat.upper()} — two-stat search (HP / {def_stat.upper()}).\n")

        for delta_def in range(0, min(budget, 64) + 1):
            delta_hp = min(budget, 64) - delta_def

            HP_SP  = existing_hp  + delta_hp
            DEF_SP = existing_def + delta_def

            if HP_SP > 32 or DEF_SP > 32:
                continue

            defender = {
                'name':    defender_name,
                'nature':  defender_nature,
                'item':    defender_item,
                'ability': defender_ability,
                'sp':      {'hp': HP_SP, def_stat: DEF_SP},
                'boosts':  {def_stat: max(def_boost1, def_boost2)},  # same stat, use the active boost
            }

            r1 = calc_damage(attacker1, {**defender, 'boosts': {def_stat: def_boost1}}, move1, field1)
            r2 = calc_damage(attacker2, {**defender, 'boosts': {def_stat: def_boost2}}, move2, field2)

            HP     = calc_hp(r1['defenderBaseHp'], HP_SP)
            dmg1   = r1['max']
            dmg2   = r2['max']
            total  = (dmg1 + dmg2) / HP

            pct1   = dmg1 / HP * 100
            pct2   = dmg2 / HP * 100
            pct_sum = total * 100

            row = {
                'HP_SP': HP_SP, f'{def_stat}_SP': DEF_SP,
                'delta_hp': delta_hp, f'delta_{def_stat}': delta_def,
                'dmg1': dmg1, 'dmg2': dmg2, 'HP': HP,
                'pct1': pct1, 'pct2': pct2, 'total': total,
                'desc1': r1['desc'], 'desc2': r2['desc'],
            }
            all_results.append(row)

            print(f"+{delta_hp:>2} HP / +{delta_def:>2} {def_stat.upper()}  "
                  f"(totals {HP_SP}/{DEF_SP})  "
                  f"move1={pct1:.1f}%  move2={pct2:.1f}%  sum={pct_sum:.2f}%")

            if total < minimum_sum:
                minimum_sum = total
                optimal = row

        _print_result_two_stat(optimal, minimum_sum, def_stat)

    # ── three-stat search (moves hit different defensive stats) ───────────────
    else:
        stat_a = def_stat1   # e.g. 'def'
        stat_b = def_stat2   # e.g. 'spd'

        print(f"\nMoves hit different stats ({stat_a.upper()} and {stat_b.upper()}) "
              f"— three-stat search (HP / {stat_a.upper()} / {stat_b.upper()}).\n")

        cap = min(budget, 64)

        for delta_a in range(0, cap + 1):
            for delta_b in range(0, cap - delta_a + 1):
                delta_hp = cap - delta_a - delta_b

                HP_SP = existing_hp   + delta_hp
                A_SP  = existing_def1 + delta_a
                B_SP  = existing_def2 + delta_b

                if HP_SP > 32 or A_SP > 32 or B_SP > 32:
                    continue

                sp_dict = {'hp': HP_SP, stat_a: A_SP, stat_b: B_SP}

                defender_base = {
                    'name':    defender_name,
                    'nature':  defender_nature,
                    'item':    defender_item,
                    'ability': defender_ability,
                    'sp':      sp_dict,
                }

                r1 = calc_damage(attacker1, {**defender_base, 'boosts': {stat_a: def_boost1}}, move1, field1)
                r2 = calc_damage(attacker2, {**defender_base, 'boosts': {stat_b: def_boost2}}, move2, field2)

                HP    = calc_hp(r1['defenderBaseHp'], HP_SP)
                dmg1  = r1['max']
                dmg2  = r2['max']
                total = (dmg1 + dmg2) / HP

                pct1    = dmg1 / HP * 100
                pct2    = dmg2 / HP * 100
                pct_sum = total * 100

                row = {
                    'HP_SP': HP_SP, f'{stat_a}_SP': A_SP, f'{stat_b}_SP': B_SP,
                    'delta_hp': delta_hp, f'delta_{stat_a}': delta_a, f'delta_{stat_b}': delta_b,
                    'dmg1': dmg1, 'dmg2': dmg2, 'HP': HP,
                    'pct1': pct1, 'pct2': pct2, 'total': total,
                    'desc1': r1['desc'], 'desc2': r2['desc'],
                }
                all_results.append(row)

                print(f"+{delta_hp:>2} HP / +{delta_a:>2} {stat_a.upper()} / +{delta_b:>2} {stat_b.upper()}  "
                      f"(totals {HP_SP}/{A_SP}/{B_SP})  "
                      f"move1={pct1:.1f}%  move2={pct2:.1f}%  sum={pct_sum:.2f}%")

                if total < minimum_sum:
                    minimum_sum = total
                    optimal = row

        _print_result_three_stat(optimal, minimum_sum, stat_a, stat_b)

    return minimum_sum


def _print_result_two_stat(opt: dict, minimum_sum: float, def_stat: str):
    if not opt:
        print("\nNo valid spread found — check your existing SPs / budget don't push either stat past 32.")
        return

    print()
    print("─" * 60)
    print("  OPTIMAL (minimises move1 + move2 damage)")
    print("─" * 60)
    print(f"  Spread:     {opt['HP_SP']} HP / {opt[f'{def_stat}_SP']} {def_stat.upper()}")
    print(f"  Additional: +{opt['delta_hp']} HP / +{opt[f'delta_{def_stat}']} {def_stat.upper()}")
    print(f"  Move 1:     {opt['dmg1']} / {opt['HP']} HP  ({opt['pct1']:.1f}%)")
    print(f"              {opt['desc1']}")
    print(f"  Move 2:     {opt['dmg2']} / {opt['HP']} HP  ({opt['pct2']:.1f}%)")
    print(f"              {opt['desc2']}")
    print(f"  Combined:   {opt['dmg1'] + opt['dmg2']} total dmg / {opt['HP']} HP  ({minimum_sum * 100:.1f}% sum, {(1 - minimum_sum) * 100:.1f}% remaining after both)")
    print("─" * 60)


def _print_result_three_stat(opt: dict, minimum_sum: float, stat_a: str, stat_b: str):
    if not opt:
        print("\nNo valid spread found — check your existing SPs / budget don't push any stat past 32.")
        return

    print()
    print("─" * 60)
    print("  OPTIMAL (minimises move1 + move2 damage)")
    print("─" * 60)
    print(f"  Spread:     {opt['HP_SP']} HP / {opt[f'{stat_a}_SP']} {stat_a.upper()} / {opt[f'{stat_b}_SP']} {stat_b.upper()}")
    print(f"  Additional: +{opt['delta_hp']} HP / +{opt[f'delta_{stat_a}']} {stat_a.upper()} / +{opt[f'delta_{stat_b}']} {stat_b.upper()}")
    print(f"  Move 1:     {opt['dmg1']} / {opt['HP']} HP  ({opt['pct1']:.1f}%)")
    print(f"              {opt['desc1']}")
    print(f"  Move 2:     {opt['dmg2']} / {opt['HP']} HP  ({opt['pct2']:.1f}%)")
    print(f"              {opt['desc2']}")
    print(f"  Combined:   {opt['dmg1'] + opt['dmg2']} total dmg / {opt['HP']} HP  ({minimum_sum * 100:.1f}% sum, {(1 - minimum_sum) * 100:.1f}% remaining after both)")
    print("─" * 60)


# ── inputs ────────────────────────────────────────────────────────────────────

print("═" * 60)
print("  Dual-Attack Defensive Optimiser")
print("═" * 60)

# Defender (shared)
print("\n── Defender ──")
defender_name    = input('  Name:               ')
defender_nature  = input('  Nature:             ')
defender_ability = input('  Ability (or blank): ') or None
defender_item    = input('  Item (or blank):    ') or None

# Attacker + move 1
attacker1 = prompt_attacker('1')
move1, atk_stat1, atk_boost1, def_stat1, def_boost1 = prompt_move('1', attacker1)
field1 = prompt_field('1')

# Attacker + move 2
same_attacker = input('\nSame attacker for move 2? (y/n): ').strip().lower() == 'y'
if same_attacker:
    attacker2 = dict(attacker1)  # shallow copy; boosts get overwritten per move anyway
else:
    attacker2 = prompt_attacker('2')

move2, atk_stat2, atk_boost2, def_stat2, def_boost2 = prompt_move('2', attacker2)

same_field = input('\nSame field conditions for move 2? (y/n): ').strip().lower() == 'y'
field2 = field1 if same_field else prompt_field('2')

# Budget
print("\n── SP Budget ──")
existing_hp   = int(input('  SPs already in HP (0 if none):              ') or 0)
existing_def1 = int(input(f'  SPs already in {def_stat1.upper()} (0 if none):            ') or 0)

if def_stat1 != def_stat2:
    existing_def2 = int(input(f'  SPs already in {def_stat2.upper()} (0 if none):            ') or 0)
else:
    existing_def2 = existing_def1

stat_label = (f'HP + {def_stat1.upper()}' if def_stat1 == def_stat2
              else f'HP + {def_stat1.upper()} + {def_stat2.upper()}')
budget = int(input(f'  Additional SP budget ({stat_label}): '))

optimise_two(
    defender_name, defender_nature, defender_ability, defender_item,
    attacker1, move1, def_stat1, def_boost1, field1,
    attacker2, move2, def_stat2, def_boost2, field2,
    existing_hp, existing_def1, existing_def2, budget,
)