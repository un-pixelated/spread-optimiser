# Defensive optimiser for Pokémon Champions
# Uses @smogon/calc via bridge.js for damage calculation

import subprocess
import json
import math
import contextlib
import config
from plot import plot

BRIDGE = "./bridge.js"
OUTPUTS_FILE = "outputs.txt"

# One persistent Node process for the whole run.
_node = subprocess.Popen(
    ["node", BRIDGE],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    text=True,
)


def calc_damage(attacker, defender, move, field) -> dict:
    payload = (
        json.dumps(
            {
                "attacker": attacker,
                "defender": defender,
                "move": move,
                "field": field,
            }
        )
        + "\n"
    )
    _node.stdin.write(payload)
    _node.stdin.flush()
    return json.loads(_node.stdout.readline())


def calc_hp(base: int, sp: int) -> int:
    return base + sp + 75


def clamp_boost(n: int) -> int:
    return max(-6, min(6, n))


VALID_NATURES = {
    "Adamant",
    "Bashful",
    "Bold",
    "Brave",
    "Calm",
    "Careful",
    "Docile",
    "Gentle",
    "Hardy",
    "Hasty",
    "Impish",
    "Jolly",
    "Lax",
    "Lonely",
    "Mild",
    "Modest",
    "Naive",
    "Naughty",
    "Quiet",
    "Quirky",
    "Rash",
    "Relaxed",
    "Sassy",
    "Serious",
    "Timid",
}

# Natures that boost the stat a move actually hits. Any nature in this table is
# equally "optimal" for this calculator: it only ever computes a single hit
# against DEF or SPD, so whichever stat each nature lowers (Atk/SpA/Speed/the
# other defensive stat) never factors into the damage math.
BEST_DEFENSIVE_NATURE = {"def": "Bold", "spd": "Calm"}


# ── tuner ────────────────────────────────────────────────
# Among all spreads whose damage % is within `tolerance` pp of the
# optimum, pick the one that maximises the prioritised stat's SP.
# Ties broken by maximising the other stat.


def tune(
    results: list[dict],  # list of {HP_SP, DEF_SP, damage_dealt, DMG, HP, desc}
    def_stat: str,
    priority: str,  # 'hp' or def_stat
    tolerance: float,  # percentage points, e.g. 0.5 means ±0.5%
) -> dict | None:
    if not results:
        return None

    best_pct = min(r["damage_dealt"] for r in results) * 100
    threshold = best_pct + tolerance  # we accept up to this % damage

    candidates = [r for r in results if r["damage_dealt"] * 100 <= threshold]
    if not candidates:
        return None

    if priority == "hp":
        return max(candidates, key=lambda r: (r["HP_SP"], r[f"{def_stat}_SP"]))
    else:
        return max(candidates, key=lambda r: (r[f"{def_stat}_SP"], r["HP_SP"]))


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
    TUNER: (
        dict | None
    ) = None,  # {'priority': 'hp'|DEF_STAT, 'tolerance': float} or None
    PRIMARY: bool = True,  # writes outputs.txt / plot.png; False for comparison-only runs
) -> float:
    xs = []
    ys = []
    move_type = ""
    all_results = []

    optimal_stats = {}
    minimum_dealt = float("inf")
    best_index = None

    log_ctx = open(OUTPUTS_FILE, "w") if PRIMARY else contextlib.nullcontext()
    with log_ctx as sweep_log:
        for delta_def in range(0, min(BUDGET, 64) + 1):
            delta_hp = min(BUDGET, 64) - delta_def

            HP_SP = EXISTING_HP + delta_hp
            DEF_SP = EXISTING_DEF + delta_def

            if HP_SP > 32 or DEF_SP > 32:
                continue

            defender = {
                "name": DEFENDER_NAME,
                "nature": DEFENDER_NATURE,
                "item": DEFENDER_ITEM,
                "ability": DEFENDER_ABILITY,
                "sp": {"hp": HP_SP, DEF_STAT: DEF_SP},
                "boosts": {DEF_STAT: DEFENDER_BOOST},
            }

            result = calc_damage(ATTACKER, defender, MOVE, FIELD)
            if not xs:  # capture move type on first call
                move_type = result.get("moveType", "")
            HP = calc_hp(result["defenderBaseHp"], HP_SP)
            DMG = result["max"]
            damage_dealt = DMG / HP

            xs.append((HP_SP, DEF_SP))
            ys.append(damage_dealt)
            all_results.append(
                {
                    "HP_SP": HP_SP,
                    f"{DEF_STAT}_SP": DEF_SP,
                    "delta_hp": delta_hp,
                    f"delta_{DEF_STAT}": delta_def,
                    "damage_dealt": damage_dealt,
                    "DMG": DMG,
                    "HP": HP,
                    "desc": result["desc"],
                }
            )

            if PRIMARY:
                sweep_log.write(
                    f"+{delta_hp:>2} HP / +{delta_def:>2} {DEF_STAT.upper()}  "
                    f"(totals {HP_SP}/{DEF_SP}) -> {damage_dealt * 100:.2f}%  [{result['desc']}]\n"
                )

            if damage_dealt < minimum_dealt:
                minimum_dealt = damage_dealt
                best_index = len(xs) - 1
                optimal_stats = {
                    "HP_SP": HP_SP,
                    "DEF_SP": DEF_SP,
                    "delta_hp": delta_hp,
                    "delta_def": delta_def,
                    "DMG": DMG,
                    "HP": HP,
                    "desc": result["desc"],
                }

    if not optimal_stats:
        print(
            "No valid spread found — check your existing SPs / budget don't push either stat past 32."
        )
        return None

    # ── optimal output ───────────────────────────────────
    print()
    print("OPTIMAL")
    print(
        f"  Spread:  {optimal_stats['HP_SP']} HP / {optimal_stats['DEF_SP']} {DEF_STAT.upper()}"
        f"  (+{optimal_stats['delta_hp']} HP / +{optimal_stats['delta_def']} {DEF_STAT.upper()})"
    )
    print(
        f"  Damage:  {optimal_stats['DMG']} / {optimal_stats['HP']} HP"
        f"  ({minimum_dealt * 100:.1f}% dealt, {(1 - minimum_dealt) * 100:.1f}% remaining)"
    )
    print(f"  Desc:    {optimal_stats['desc']}")

    # ── tuner output ─────────────────────────────────────
    if TUNER:
        priority = TUNER["priority"]  # 'hp' or DEF_STAT
        tolerance = TUNER["tolerance"]  # percentage points

        tuned = tune(all_results, DEF_STAT, priority, tolerance)

        print()
        print(f"TUNED  (priority: {priority.upper()}, tolerance: +{tolerance}%)")

        if tuned is None or (
            tuned["HP_SP"] == optimal_stats["HP_SP"]
            and tuned[f"{DEF_STAT}_SP"] == optimal_stats["DEF_SP"]
        ):
            print("  No different spread found within tolerance — same as optimal.")
        else:
            t_pct = tuned["damage_dealt"] * 100
            opt_pct = minimum_dealt * 100
            sacrifice = t_pct - opt_pct

            print(
                f"  Spread:  {tuned['HP_SP']} HP / {tuned[f'{DEF_STAT}_SP']} {DEF_STAT.upper()}"
                f"  (+{tuned['delta_hp']} HP / +{tuned[f'delta_{DEF_STAT}']} {DEF_STAT.upper()})"
            )
            print(
                f"  Damage:  {tuned['DMG']} / {tuned['HP']} HP"
                f"  ({t_pct:.1f}% dealt, {100 - t_pct:.1f}% remaining, +{sacrifice:.2f}% vs optimal)"
            )
            print(f"  Desc:    {tuned['desc']}")

    if PRIMARY:
        print()
        print(f"Sweep log: {OUTPUTS_FILE}")

    if PRIMARY:
        plot(
            xs,
            ys,
            DEF_STAT,
            attacker_name=ATTACKER["name"],
            defender_name=DEFENDER_NAME,
            move_name=MOVE["name"],
            move_type=move_type,
            best_index=best_index,
            best_dmg=optimal_stats["DMG"],
            best_hp=optimal_stats["HP"],
            best_desc=optimal_stats["desc"],
        )
    return minimum_dealt


# ── inputs (from config.py) ──────────────────────────────
assert config.ATTACKING_STAT in (
    "atk",
    "spa",
), "config.ATTACKING_STAT must be 'atk' or 'spa'"
assert config.DEFENSIVE_STAT in (
    "def",
    "spd",
), "config.DEFENSIVE_STAT must be 'def' or 'spd'"
assert config.TERRAIN in (
    None,
    "Electric",
    "Grassy",
    "Misty",
    "Psychic",
), "config.TERRAIN must be one of None, 'Electric', 'Grassy', 'Misty', 'Psychic'"
assert (
    config.ATTACKER_NATURE in VALID_NATURES
), f"config.ATTACKER_NATURE {config.ATTACKER_NATURE!r} is not a real nature"
assert config.DEFENDER_NATURE is None or config.DEFENDER_NATURE in VALID_NATURES, (
    f"config.DEFENDER_NATURE {config.DEFENDER_NATURE!r} is not a real nature "
    '(use the Python value None, not the string "None", to auto-select one)'
)

attacker = {
    "name": config.ATTACKER_NAME,
    "nature": config.ATTACKER_NATURE,
    "item": config.ATTACKER_ITEM,
    "ability": config.ATTACKER_ABILITY,
    "sp": config.ATTACKER_SP,
    "boosts": {config.ATTACKING_STAT: clamp_boost(config.ATTACKER_BOOST)},
}

defender_name = config.DEFENDER_NAME
defender_ability = config.DEFENDER_ABILITY
defender_item = config.DEFENDER_ITEM

move = {
    "name": config.MOVE_NAME,
    "isCrit": config.MOVE_IS_CRIT,
}

defensive_stat = config.DEFENSIVE_STAT
defender_boost = clamp_boost(config.DEFENDER_BOOST)

existing_hp = config.EXISTING_HP_SP
existing_def = config.EXISTING_DEF_SP
budget = config.BUDGET

field = {
    "gameType": config.GAME_TYPE,
    "weather": config.WEATHER,
    "terrain": config.TERRAIN,
    "isReflect": config.IS_REFLECT,
    "isLightScreen": config.IS_LIGHT_SCREEN,
    "isHelpingHand": config.IS_HELPING_HAND,
    "isFriendGuard": config.IS_FRIEND_GUARD,
}

if config.DEFENDER_NATURE is None:
    auto_nature = BEST_DEFENSIVE_NATURE[defensive_stat]
    for nature, label, primary in [
        (auto_nature, "auto-selected optimal nature", True),
        ("Serious", "neutral fallback, for comparison", False),
    ]:
        print(f"\nDefender nature: {nature}  ({label})")
        optimise(
            attacker,
            defender_name,
            nature,
            defender_ability,
            defender_item,
            defensive_stat,
            defender_boost,
            existing_hp,
            existing_def,
            budget,
            move,
            field,
            TUNER=config.TUNER,
            PRIMARY=primary,
        )
else:
    optimise(
        attacker,
        defender_name,
        config.DEFENDER_NATURE,
        defender_ability,
        defender_item,
        defensive_stat,
        defender_boost,
        existing_hp,
        existing_def,
        budget,
        move,
        field,
        TUNER=config.TUNER,
    )
