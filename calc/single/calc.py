# Defensive optimiser for Pokémon Champions
# Uses @smogon/calc via bridge.js for damage calculation

import sys
import contextlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.shared import (
    ROOT_DIR,
    calc_damage,
    calc_hp,
    clamp_boost,
    VALID_NATURES,
    VALID_STATUSES,
)

import config

OUTPUTS_DIR = ROOT_DIR / "outputs"
OUTPUTS_DIR.mkdir(exist_ok=True)
OUTPUTS_FILE = OUTPUTS_DIR / "outputs.txt"


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


def optimise(
    ATTACKER: dict,
    DEFENDER_NAME: str,
    DEFENDER_NATURE: str,
    DEFENDER_ABILITY: str,
    DEFENDER_ITEM: str | None,
    DEF_STAT: str,
    DEFENDER_BOOST: int,
    DEFENDER_STATUS: str | None,
    EXISTING_HP: int,
    EXISTING_DEF: int,
    BUDGET: int,
    MOVE: dict,
    FIELD: dict,
    TUNER: (
        dict | None
    ) = None,  # {'priority': 'hp'|DEF_STAT, 'tolerance': float (optional)} or None
    PRIMARY: bool = True,  # writes outputs.txt; False for comparison-only runs
) -> float:
    all_results = []

    optimal_stats = {}
    minimum_dealt = float("inf")

    # Only 2 stats tracked here (HP + DEF_STAT), each capped at 32 below, so
    # the combined total can never exceed 64 -- already under Champions' real
    # 66-total-SP cap. No separate total check needed (see calc/multi/calc.py
    # for where that stops being true, with 3 tracked stats).
    log_ctx = open(OUTPUTS_FILE, "w") if PRIMARY else contextlib.nullcontext()
    with log_ctx as sweep_log:
        # The intent of the user in this branch is to use all available SPs
        # into bulk. Handle the case where they forget to reduce the budget
        # correclty when adding existing stats input.
        if EXISTING_HP + EXISTING_DEF + BUDGET > 64:
            BUDGET = 64 - (EXISTING_HP + EXISTING_DEF)
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
                "status": DEFENDER_STATUS,
                "sp": {"hp": HP_SP, DEF_STAT: DEF_SP},
                "boosts": {DEF_STAT: DEFENDER_BOOST},
            }

            result = calc_damage(ATTACKER, defender, MOVE, FIELD)
            HP = calc_hp(result["defenderBaseHp"], HP_SP)
            DMG = result["max"]
            damage_dealt = DMG / HP

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
        tolerance = TUNER.get("tolerance")  # percentage points, optional

        tuned = tune(all_results, DEF_STAT, priority, tolerance)

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
            and tuned[f"{DEF_STAT}_SP"] == optimal_stats["DEF_SP"]
        ):
            print("  No different spread found — same as optimal.")
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
            TUNER=parsed["tuner"],
            PRIMARY=primary,
        )
