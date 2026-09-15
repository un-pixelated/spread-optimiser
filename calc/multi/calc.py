# Multi-attack defensive optimiser for Pokémon Champions
# Minimises the summed damage from 2-4 attackers against one shared defender.
# Uses @smogon/calc via bridge.js for damage calculation. Console output plus
# a full sweep log at outputs/outputs.txt.

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

# Printed when no spread fits the SP caps under the configured budget.
NO_SPREAD_MSG = (
    "\nNo valid spread found — check your existing SPs / budget don't "
    "push any stat past 32, or (with attackers hitting both DEF and "
    "SPD) the combined HP+DEF+SPD total past 66."
)

# Only these three natures are ever worth trying: the defender never attacks
# in this calculator, so a nature's "cost" only matters when it falls on the
# other defensive stat (Lax/Gentle) — it's always invisible when it falls on
# Atk/SpA/Speed (Bold/Calm). Lax/Gentle can only ever tie Bold/Calm (when the
# stat they trade away isn't being attacked) or lose to them — never win.
NATURE_CANDIDATES = ["Bold", "Calm", "Serious"]


def parse_config_multi() -> dict:
    assert (
        2 <= len(config.ATTACKERS) <= 4
    ), f"config.ATTACKERS must have 2 to 4 entries, got {len(config.ATTACKERS)}"

    for i, a in enumerate(config.ATTACKERS):
        assert a["attacking_stat"] in (
            "atk",
            "spa",
        ), f"config.ATTACKERS[{i}]['attacking_stat'] must be 'atk' or 'spa'"
        assert a["defensive_stat"] in (
            "def",
            "spd",
        ), f"config.ATTACKERS[{i}]['defensive_stat'] must be 'def' or 'spd'"
        assert (
            a["nature"] in VALID_NATURES
        ), f"config.ATTACKERS[{i}]['nature'] {a['nature']!r} is not a real nature"
        assert a["status"] is None or a["status"] in VALID_STATUSES, (
            f"config.ATTACKERS[{i}]['status'] {a['status']!r} is not a valid status "
            "(use one of 'slp', 'psn', 'brn', 'frz', 'par', 'tox', or None)"
        )

    assert config.DEFENDER_NATURE is None or config.DEFENDER_NATURE in VALID_NATURES, (
        f"config.DEFENDER_NATURE {config.DEFENDER_NATURE!r} is not a real nature "
        "(use the Python value None to auto-pick the best of Bold/Calm/Serious)"
    )
    assert config.DEFENDER_STATUS is None or config.DEFENDER_STATUS in VALID_STATUSES, (
        f"config.DEFENDER_STATUS {config.DEFENDER_STATUS!r} is not a valid status "
        "(use one of 'slp', 'psn', 'brn', 'frz', 'par', 'tox', or None)"
    )
    assert config.TERRAIN in (
        None,
        "Electric",
        "Grassy",
        "Misty",
        "Psychic",
    ), "config.TERRAIN must be one of None, 'Electric', 'Grassy', 'Misty', 'Psychic'"

    if config.TUNER is not None:
        # Priority must be a stat the search actually tracks: "hp" always,
        # "def"/"spd" only if some attacker's move hits it.
        tracked = ["hp"] + sorted({a["defensive_stat"] for a in config.ATTACKERS})
        assert config.TUNER["priority"] in tracked, (
            f"config.TUNER['priority'] {config.TUNER['priority']!r} must be one of "
            f"{tracked} (only stats your attackers' moves actually hit, plus 'hp')"
        )

    # Champions caps SP two ways: 32 per stat, 66 total across all stats on
    # one Pokemon. Checked upfront so a bad config value fails clearly here
    # instead of just silently filtering out every point in the search below.
    assert (
        config.EXISTING_HP_SP <= 32
    ), f"config.EXISTING_HP_SP {config.EXISTING_HP_SP!r} exceeds the 32-per-stat cap"
    assert (
        config.EXISTING_DEF_SP <= 32
    ), f"config.EXISTING_DEF_SP {config.EXISTING_DEF_SP!r} exceeds the 32-per-stat cap"
    assert (
        config.EXISTING_SPD_SP <= 32
    ), f"config.EXISTING_SPD_SP {config.EXISTING_SPD_SP!r} exceeds the 32-per-stat cap"
    existing_total = (
        config.EXISTING_HP_SP + config.EXISTING_DEF_SP + config.EXISTING_SPD_SP
    )
    assert existing_total <= 66, (
        f"config.EXISTING_HP_SP + EXISTING_DEF_SP + EXISTING_SPD_SP = {existing_total} "
        "exceeds the 66-total-SP cap"
    )

    attackers = []
    for a in config.ATTACKERS:
        attackers.append(
            {
                "attacker": {
                    "name": a["name"],
                    "nature": a["nature"],
                    "item": a["item"],
                    "ability": a["ability"],
                    "status": a["status"],
                    "sp": a["sp"],
                    "boosts": {a["attacking_stat"]: clamp_boost(a["boost"])},
                },
                "move": {
                    "name": a["move_name"],
                    "isCrit": a["move_is_crit"],
                },
                "defensive_stat": a["defensive_stat"],
                "defender_boost": clamp_boost(a["defender_boost"]),
            }
        )

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
        "attackers": attackers,
        "defender_name": config.DEFENDER_NAME,
        "defender_nature": config.DEFENDER_NATURE,
        "defender_item": config.DEFENDER_ITEM,
        "defender_ability": config.DEFENDER_ABILITY,
        "defender_status": config.DEFENDER_STATUS,
        "existing_hp": config.EXISTING_HP_SP,
        "existing_def": config.EXISTING_DEF_SP,
        "existing_spd": config.EXISTING_SPD_SP,
        "budget": config.BUDGET,
        "field": field,
        "tuner": config.TUNER,
    }


def _hit(defender_name, nature, item, ability, status, spread, atk_entry, field):
    defender = build_defender(
        defender_name,
        nature,
        item,
        ability,
        status,
        spread,
        atk_entry["defensive_stat"],
        atk_entry["defender_boost"],
    )
    return calc_damage(atk_entry["attacker"], defender, atk_entry["move"], field)


def evaluate(
    attackers,
    defender_name,
    defender_nature,
    defender_item,
    defender_ability,
    defender_status,
    spread,
    field,
):
    """Sum every attacker's max-roll damage against one spread.

    Returns (HP, per_attacker, total_dmg). HP is computed once from the first
    result's base HP and the spread's HP SP. Shared by optimise_multi() and
    survive.py's find_min_sp_multi().
    """
    HP = None
    total_dmg = 0
    per_attacker = []
    for a in attackers:
        result = _hit(
            defender_name,
            defender_nature,
            defender_item,
            defender_ability,
            defender_status,
            spread,
            a,
            field,
        )
        if HP is None:
            HP = calc_hp(result["defenderBaseHp"], spread["hp"])
        dmg = result["max"]
        total_dmg += dmg
        per_attacker.append(
            {
                "name": a["attacker"]["name"],
                "move": a["move"]["name"],
                "dmg": dmg,
                "desc": result["desc"],
            }
        )
    return HP, per_attacker, total_dmg


def _make_row(spread, deltas, HP, per_attacker, total_dmg, total_pct):
    """Assemble a sweep row keyed the way _spread_label/report_multi expect:
    HP_SP + delta_hp, plus <stat>_SP + delta_<stat> for each tracked stat."""
    row = {"HP_SP": spread["hp"], "delta_hp": deltas["hp"]}
    for stat in spread:
        if stat == "hp":
            continue
        row[f"{stat}_SP"] = spread[stat]
        row[f"delta_{stat}"] = deltas[stat]
    row["HP"] = HP
    row["per_attacker"] = per_attacker
    row["total_dmg"] = total_dmg
    row["total_pct"] = total_pct
    return row


def optimise_multi(
    attackers: list[dict],
    defender_name: str,
    defender_nature: str,
    defender_item: str | None,
    defender_ability: str | None,
    defender_status: str | None,
    existing_hp: int,
    existing_def: int,
    existing_spd: int,
    budget: int,
    field: dict,
) -> dict | None:
    stats_used = sorted({a["defensive_stat"] for a in attackers})
    # Track HP + only the defensive stats actually in play. With one stat the
    # 2 x 32 = 64 ceiling already sits under the 66-total cap; with two, 66 is
    # the binding ceiling (3 x 32 = 96 would overshoot it). iter_spreads owns
    # the 32-per-stat and 66-total enforcement either way.
    hard_cap = 64 if len(stats_used) == 1 else 66
    all_existing = {"hp": existing_hp, "def": existing_def, "spd": existing_spd}
    existing = {"hp": existing_hp, **{s: all_existing[s] for s in stats_used}}
    cap = budget_cap(sum(existing.values()), budget, hard_cap)

    sweep = []
    best = None
    for spread, deltas in iter_spreads(existing, stats_used, cap):
        HP, per_attacker, total_dmg = evaluate(
            attackers,
            defender_name,
            defender_nature,
            defender_item,
            defender_ability,
            defender_status,
            spread,
            field,
        )
        total_pct = total_dmg / HP
        row = _make_row(spread, deltas, HP, per_attacker, total_dmg, total_pct)
        sweep.append(row)

        if best is None or total_pct < best["total_pct"]:
            best = row

    if best is None:
        return None

    return {"stats_used": stats_used, "sweep": sweep, "best": best}


def _spread_label(stats_used, row, prefix="") -> str:
    if len(stats_used) == 1:
        stat = stats_used[0]
        return (
            f"{prefix}{row['HP_SP']} HP / {row[f'{stat}_SP']} {stat.upper()}"
            f"  ({prefix}+{row['delta_hp']} HP / +{row[f'delta_{stat}']} {stat.upper()})"
        )
    return (
        f"{prefix}{row['HP_SP']} HP / {row['def_SP']} DEF / {row['spd_SP']} SPD"
        f"  (+{row['delta_hp']} HP / +{row['delta_def']} DEF / +{row['delta_spd']} SPD)"
    )


def sweep_log_line(stats_used, row) -> str:
    """One outputs.txt sweep line for `row` (a calc row or a survive point):
    HP/stat deltas, running totals, each move's %, and the summed %."""
    if len(stats_used) == 1:
        stat = stats_used[0]
        head = f"+{row['delta_hp']:>2} HP / +{row[f'delta_{stat}']:>2} {stat.upper()}"
        totals = f"{row['HP_SP']}/{row[f'{stat}_SP']}"
    else:
        head = (
            f"+{row['delta_hp']:>2} HP / +{row['delta_def']:>2} DEF"
            f" / +{row['delta_spd']:>2} SPD"
        )
        totals = f"{row['HP_SP']}/{row['def_SP']}/{row['spd_SP']}"

    move_pcts = "  ".join(
        f"move{i}={pa['dmg'] / row['HP'] * 100:.1f}%"
        for i, pa in enumerate(row["per_attacker"], 1)
    )
    sum_pct = row["total_dmg"] / row["HP"] * 100
    return f"{head}  (totals {totals})  {move_pcts}  sum={sum_pct:.2f}%"


def print_attacker_lines(best):
    for i, pa in enumerate(best["per_attacker"], 1):
        pct = pa["dmg"] / best["HP"] * 100
        print(
            f"  Move {i} ({pa['name']} — {pa['move']}):  {pa['dmg']} / {best['HP']} HP  ({pct:.1f}%)"
        )
        print(f"    {pa['desc']}")


# ── tuner ────────────────────────────────────────────────
# Among all spreads whose combined damage % is within `tolerance` pp of the
# optimum, pick the one that maximises the prioritised stat's SP. Ties broken
# by maximising the remaining tracked stats. If `tolerance` is omitted, skip
# the near-optimal filter entirely and instead maximise the prioritised
# stat's SP among only the spreads that survive the combined damage.


def tune_multi(
    sweep: list[dict],  # optimise_multi()'s sweep rows
    stats_used: list[str],
    priority: str,  # 'hp', 'def', or 'spd' (must be tracked)
    tolerance: float | None,  # percentage points, e.g. 0.5 means ±0.5%; or None
) -> dict | None:
    if not sweep:
        return None

    if tolerance is None:
        candidates = [r for r in sweep if r["total_pct"] < 1]
    else:
        best_pct = min(r["total_pct"] for r in sweep) * 100
        threshold = best_pct + tolerance  # we accept up to this % damage
        candidates = [r for r in sweep if r["total_pct"] * 100 <= threshold]

    if not candidates:
        return None

    order = [priority] + [s for s in ["hp", *stats_used] if s != priority]
    return max(
        candidates,
        key=lambda r: tuple(r["HP_SP" if s == "hp" else f"{s}_SP"] for s in order),
    )


def print_tuned_multi(result: dict, tuner: dict):
    stats_used = result["stats_used"]
    best = result["best"]
    priority = tuner["priority"]  # 'hp', 'def', or 'spd'
    tolerance = tuner.get("tolerance")  # percentage points, optional

    tuned = tune_multi(result["sweep"], stats_used, priority, tolerance)

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
    elif tuned is best:
        print("  No different spread found — same as optimal.")
    else:
        t_pct = tuned["total_pct"] * 100
        opt_pct = best["total_pct"] * 100
        sacrifice = t_pct - opt_pct

        print(f"  Spread:  {_spread_label(stats_used, tuned)}")
        print_attacker_lines(tuned)
        print(
            f"  Combined:  {tuned['total_dmg']} / {tuned['HP']} HP"
            f"  ({t_pct:.1f}% dealt, {100 - t_pct:.1f}% remaining, +{sacrifice:.2f}% vs optimal)"
        )


def select_nature(natures, metric):
    """Lowest metric(nature) wins; ties break toward NATURE_CANDIDATES order."""
    return min(natures, key=lambda n: (metric(n), NATURE_CANDIDATES.index(n)))


def report_multi(result: dict, primary: bool, tuner: dict | None = None):
    stats_used = result["stats_used"]
    best = result["best"]

    if primary:
        with open(OUTPUTS_FILE, "w") as sweep_log:
            for row in result["sweep"]:
                sweep_log.write(sweep_log_line(stats_used, row) + "\n")

    print()
    print("OPTIMAL")
    print(f"  Spread:  {_spread_label(stats_used, best)}")
    print_attacker_lines(best)
    total_pct = best["total_pct"] * 100
    print(
        f"  Combined:  {best['total_dmg']} / {best['HP']} HP"
        f"  ({total_pct:.1f}% dealt, {100 - total_pct:.1f}% remaining)"
    )

    if tuner:
        print_tuned_multi(result, tuner)

    if primary:
        print()
        print(f"Sweep log: {OUTPUTS_FILE.relative_to(ROOT_DIR)}")


if __name__ == "__main__":
    parsed = parse_config_multi()

    def run(nature):
        return optimise_multi(
            parsed["attackers"],
            parsed["defender_name"],
            nature,
            parsed["defender_item"],
            parsed["defender_ability"],
            parsed["defender_status"],
            parsed["existing_hp"],
            parsed["existing_def"],
            parsed["existing_spd"],
            parsed["budget"],
            parsed["field"],
        )

    if parsed["defender_nature"] is not None:
        nature = parsed["defender_nature"]
        print(f"\nDefender nature: {nature}")
        result = run(nature)
        if result is None:
            print(NO_SPREAD_MSG)
        else:
            report_multi(result, primary=True, tuner=parsed["tuner"])
    else:
        candidates = {nature: run(nature) for nature in NATURE_CANDIDATES}
        valid = {nature: r for nature, r in candidates.items() if r is not None}

        if not valid:
            print(NO_SPREAD_MSG)
        else:
            winner = select_nature(valid, lambda n: valid[n]["best"]["total_pct"])
            print(
                f"\nDefender nature: {winner}  (auto-selected, lowest total damage among Bold/Calm/Serious)"
            )
            report_multi(valid[winner], primary=True, tuner=parsed["tuner"])

            if winner != "Serious" and "Serious" in valid:
                print("\nDefender nature: Serious  (neutral fallback, for comparison)")
                report_multi(valid["Serious"], primary=False, tuner=parsed["tuner"])
