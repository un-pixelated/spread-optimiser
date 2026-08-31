# Defensive optimiser for Pokémon Champions
# Uses @smogon/calc via bridge.js for damage calculation

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.shared import (
    ROOT_DIR,
    OUTPUTS_FILE,
    calc_damage,
    calc_hp,
    clamp_boost,
    build_defender,
    budget_cap,
    iter_spreads,
    VALID_NATURES,
    VALID_STATUSES,
)

import config

# ── tuner ────────────────────────────────────────────────
# Among all spreads whose damage % is within `tolerance` pp of the
# optimum, pick the one that maximises the prioritised stat's SP.
# Ties broken by maximising the other stat. If `tolerance` is omitted,
# skip the near-optimal filter entirely and instead maximise the
# prioritised stat's SP among only the spreads that survive the hit.


def tune(
    results: list[dict],  # list of {HP_SP, DEF_SP, damage_dealt, DMG, HP, desc}
    def_stat: str,
    priority: str,  # 'hp' or def_stat
    tolerance: float | None,  # percentage points, e.g. 0.5 means ±0.5%; or None
) -> dict | None:
    if not results:
        return None

    if tolerance is None:
        candidates = [r for r in results if r["damage_dealt"] < 1]
    else:
        best_pct = min(r["damage_dealt"] for r in results) * 100
        threshold = best_pct + tolerance  # we accept up to this % damage
        candidates = [r for r in results if r["damage_dealt"] * 100 <= threshold]

    if not candidates:
        return None

    if priority == "hp":
        return max(candidates, key=lambda r: (r["HP_SP"], r[f"{def_stat}_SP"]))
    else:
        return max(candidates, key=lambda r: (r[f"{def_stat}_SP"], r["HP_SP"]))


def print_optimal(optimal_stats, def_stat, minimum_dealt):
    print()
    print("OPTIMAL")
    print(
        f"  Spread:  {optimal_stats['HP_SP']} HP / {optimal_stats['DEF_SP']} {def_stat.upper()}"
        f"  (+{optimal_stats['delta_hp']} HP / +{optimal_stats['delta_def']} {def_stat.upper()})"
    )
    print(
        f"  Damage:  {optimal_stats['DMG']} / {optimal_stats['HP']} HP"
        f"  ({minimum_dealt * 100:.1f}% dealt, {(1 - minimum_dealt) * 100:.1f}% remaining)"
    )
    print(f"  Desc:    {optimal_stats['desc']}")


def print_tuned(all_results, optimal_stats, def_stat, minimum_dealt, tuner):
    priority = tuner["priority"]  # 'hp' or def_stat
    tolerance = tuner.get("tolerance")  # percentage points, optional

    tuned = tune(all_results, def_stat, priority, tolerance)

    print()
    if tolerance is None:
        print(f"TUNED  (priority: {priority.upper()}, max SP among survivors)")
    else:
        print(f"TUNED  (priority: {priority.upper()}, tolerance: +{tolerance}%)")

    if tuned is None:
        print(
            "  No surviving spread found in this budget."
            if tolerance is None
            else "  No spread found within tolerance."
        )
    elif (
        tuned["HP_SP"] == optimal_stats["HP_SP"]
        and tuned[f"{def_stat}_SP"] == optimal_stats["DEF_SP"]
    ):
        print("  No different spread found — same as optimal.")
    else:
        t_pct = tuned["damage_dealt"] * 100
        opt_pct = minimum_dealt * 100
        sacrifice = t_pct - opt_pct

        print(
            f"  Spread:  {tuned['HP_SP']} HP / {tuned[f'{def_stat}_SP']} {def_stat.upper()}"
            f"  (+{tuned['delta_hp']} HP / +{tuned[f'delta_{def_stat}']} {def_stat.upper()})"
        )
        print(
            f"  Damage:  {tuned['DMG']} / {tuned['HP']} HP"
            f"  ({t_pct:.1f}% dealt, {100 - t_pct:.1f}% remaining, +{sacrifice:.2f}% vs optimal)"
        )
        print(f"  Desc:    {tuned['desc']}")


def optimise(
    attacker: dict,
    defender_name: str,
    defender_nature: str,
    defender_ability: str,
    defender_item: str | None,
    def_stat: str,
    defender_boost: int,
    defender_status: str | None,
    existing_hp: int,
    existing_def: int,
    budget: int,
    move: dict,
    field: dict,
    tuner: (
        dict | None
    ) = None,  # {'priority': 'hp'|def_stat, 'tolerance': float?} or None
    primary: bool = True,  # writes outputs.txt; False for comparison-only runs
) -> float:
    all_results = []
    log_lines = []
    optimal_stats = {}
    minimum_dealt = float("inf")

    # Spread enumeration + the 32/stat and 66-total caps live in iter_spreads;
    # this branch tracks only HP + def_stat, so budget_cap's 64 (2 x 32) ceiling
    # already keeps the total under 66. The user may forget to reduce the budget
    # after adding existing SPs -- budget_cap spends only what still fits.
    existing = {"hp": existing_hp, def_stat: existing_def}
    cap = budget_cap(existing_hp + existing_def, budget, 64)
    for spread, deltas in iter_spreads(existing, [def_stat], cap):
        HP_SP = spread["hp"]
        DEF_SP = spread[def_stat]
        delta_hp = deltas["hp"]
        delta_def = deltas[def_stat]

        defender = build_defender(
            defender_name,
            defender_nature,
            defender_item,
            defender_ability,
            defender_status,
            spread,
            def_stat,
            defender_boost,
        )
        result = calc_damage(attacker, defender, move, field)
        HP = calc_hp(result["defenderBaseHp"], HP_SP)
        DMG = result["max"]
        damage_dealt = DMG / HP

        all_results.append(
            {
                "HP_SP": HP_SP,
                f"{def_stat}_SP": DEF_SP,
                "delta_hp": delta_hp,
                f"delta_{def_stat}": delta_def,
                "damage_dealt": damage_dealt,
                "DMG": DMG,
                "HP": HP,
                "desc": result["desc"],
            }
        )

        if primary:
            log_lines.append(
                f"+{delta_hp:>2} HP / +{delta_def:>2} {def_stat.upper()}  "
                f"(totals {HP_SP}/{DEF_SP}) -> {damage_dealt * 100:.2f}%  [{result['desc']}]"
            )

        if damage_dealt < minimum_dealt:
            minimum_dealt = damage_dealt
            optimal_stats = {
                "HP_SP": HP_SP,
                "DEF_SP": DEF_SP,
                "delta_hp": delta_hp,
                "delta_def": delta_def,
                "DMG": DMG,
                "HP": HP,
                "desc": result["desc"],
            }

    if primary:
        OUTPUTS_FILE.write_text("".join(line + "\n" for line in log_lines))

    if not optimal_stats:
        print(
            "No valid spread found — check your existing SPs / budget don't push either stat past 32."
        )
        return None

    print_optimal(optimal_stats, def_stat, minimum_dealt)

    if tuner:
        print_tuned(all_results, optimal_stats, def_stat, minimum_dealt, tuner)

    if primary:
        print()
        print(f"Sweep log: {OUTPUTS_FILE.relative_to(ROOT_DIR)}")

    return minimum_dealt


# Natures that boost the stat a move actually hits. Any nature in this table is
# equally "optimal" for this calculator: it only ever computes a single hit
# against DEF or SPD, so whichever stat each nature lowers (Atk/SpA/Speed/the
# other defensive stat) never factors into the damage math.
BEST_DEFENSIVE_NATURE = {"def": "Bold", "spd": "Calm"}


def resolve_defender_natures(defender_nature, defensive_stat):
    """Returns [(nature, label, primary), ...] to run.

    If defender_nature is None: auto-selected nature (primary, writes
    outputs.txt) plus a neutral "Serious" comparison pass. Otherwise: just
    the explicit nature, unlabeled (no banner printed), matching how this
    project always behaved before nature auto-selection existed.
    """
    if defender_nature is None:
        auto_nature = BEST_DEFENSIVE_NATURE[defensive_stat]
        return [
            (auto_nature, "auto-selected optimal nature", True),
            ("Serious", "neutral fallback, for comparison", False),
        ]
    return [(defender_nature, None, True)]


def parse_config() -> dict:
    assert config.ATTACKING_STAT in (
        "atk",
        "spa",
        "def",
        "spd",
    ), "config.ATTACKING_STAT must be 'atk', 'spa', 'def', or 'spd'"
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
    assert config.ATTACKER_STATUS is None or config.ATTACKER_STATUS in VALID_STATUSES, (
        f"config.ATTACKER_STATUS {config.ATTACKER_STATUS!r} is not a valid status "
        "(use one of 'slp', 'psn', 'brn', 'frz', 'par', 'tox', or None)"
    )
    assert config.DEFENDER_STATUS is None or config.DEFENDER_STATUS in VALID_STATUSES, (
        f"config.DEFENDER_STATUS {config.DEFENDER_STATUS!r} is not a valid status "
        "(use one of 'slp', 'psn', 'brn', 'frz', 'par', 'tox', or None)"
    )
    # Champions caps SP at 32 per stat (checked upfront so a bad config value
    # fails clearly here rather than just silently filtering out every point
    # in the sweep below). The 66-total-across-all-stats cap never needs a
    # separate check here: this tool only ever tracks 2 stats at once
    # (HP + DEFENSIVE_STAT), and 2 x 32 = 64 is already under 66.
    assert (
        config.EXISTING_HP_SP <= 32
    ), f"config.EXISTING_HP_SP {config.EXISTING_HP_SP!r} exceeds the 32-per-stat cap"
    assert (
        config.EXISTING_DEF_SP <= 32
    ), f"config.EXISTING_DEF_SP {config.EXISTING_DEF_SP!r} exceeds the 32-per-stat cap"

    attacker = {
        "name": config.ATTACKER_NAME,
        "nature": config.ATTACKER_NATURE,
        "item": config.ATTACKER_ITEM,
        "ability": config.ATTACKER_ABILITY,
        "status": config.ATTACKER_STATUS,
        "sp": config.ATTACKER_SP,
        "boosts": {config.ATTACKING_STAT: clamp_boost(config.ATTACKER_BOOST)},
    }

    move = {
        "name": config.MOVE_NAME,
        "isCrit": config.MOVE_IS_CRIT,
    }

    field = {
        "gameType": config.GAME_TYPE,
        "weather": config.WEATHER,
        "terrain": config.TERRAIN,
        "isReflect": config.IS_REFLECT,
        "isLightScreen": config.IS_LIGHT_SCREEN,
        "isHelpingHand": config.IS_HELPING_HAND,
        "isFriendGuard": config.IS_FRIEND_GUARD,
    }

    return {
        "attacker": attacker,
        "defender_name": config.DEFENDER_NAME,
        "defender_ability": config.DEFENDER_ABILITY,
        "defender_item": config.DEFENDER_ITEM,
        "defender_nature": config.DEFENDER_NATURE,
        "defensive_stat": config.DEFENSIVE_STAT,
        "defender_boost": clamp_boost(config.DEFENDER_BOOST),
        "defender_status": config.DEFENDER_STATUS,
        "existing_hp": config.EXISTING_HP_SP,
        "existing_def": config.EXISTING_DEF_SP,
        "budget": config.BUDGET,
        "move": move,
        "field": field,
        "tuner": config.TUNER,
    }


if __name__ == "__main__":
    parsed = parse_config()
    for nature, label, primary in resolve_defender_natures(
        parsed["defender_nature"], parsed["defensive_stat"]
    ):
        if label:
            print(f"\nDefender nature: {nature}  ({label})")
        optimise(
            parsed["attacker"],
            parsed["defender_name"],
            nature,
            parsed["defender_ability"],
            parsed["defender_item"],
            parsed["defensive_stat"],
            parsed["defender_boost"],
            parsed["defender_status"],
            parsed["existing_hp"],
            parsed["existing_def"],
            parsed["budget"],
            parsed["move"],
            parsed["field"],
            tuner=parsed["tuner"],
            primary=primary,
        )
