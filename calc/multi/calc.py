# Multi-attack defensive optimiser for Pokémon Champions
# Minimises the summed damage from 2-4 attackers against one shared defender.
# Uses @smogon/calc via bridge.js for damage calculation. Console output plus
# a full sweep log at outputs/outputs.txt.

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
    }


def _hit(defender_name, nature, item, ability, status, spread, atk_entry, field):
    defender = {
        "name": defender_name,
        "nature": nature,
        "item": item,
        "ability": ability,
        "status": status,
        "sp": spread,
        "boosts": {atk_entry["defensive_stat"]: atk_entry["defender_boost"]},
    }
    return calc_damage(atk_entry["attacker"], defender, atk_entry["move"], field)


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
    sweep = []
    best = None

    def evaluate(HP_SP, spread):
        per_attacker = []
        total_dmg = 0
        HP = None
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
                HP = calc_hp(result["defenderBaseHp"], HP_SP)
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

    if len(stats_used) == 1:
        # Only 2 stats tracked here (HP + one defensive stat), each capped at
        # 32, so the combined total can never exceed 64 -- already under the
        # game's real 66-total-SP cap. No separate total check needed.
        stat = stats_used[0]
        existing_stat = existing_def if stat == "def" else existing_spd

        # The intent of the user in this branch is to use all available SPs
        # into bulk. Handle the case where they forget to reduce the budget
        # correclty when adding existing stats input.
        if existing_hp + existing_stat + budget > 64:
            budget = 64 - (existing_hp + existing_stat)
        cap = min(budget, 64)

        for delta_stat in range(0, cap + 1):
            delta_hp = cap - delta_stat
            HP_SP = existing_hp + delta_hp
            STAT_SP = existing_stat + delta_stat

            if HP_SP > 32 or STAT_SP > 32:
                continue

            spread = {"hp": HP_SP, stat: STAT_SP}
            HP, per_attacker, total_dmg = evaluate(HP_SP, spread)
            total_pct = total_dmg / HP

            row = {
                "HP_SP": HP_SP,
                f"{stat}_SP": STAT_SP,
                "delta_hp": delta_hp,
                f"delta_{stat}": delta_stat,
                "HP": HP,
                "per_attacker": per_attacker,
                "total_dmg": total_dmg,
                "total_pct": total_pct,
            }
            sweep.append(row)

            if best is None or total_pct < best["total_pct"]:
                best = row

    else:
        # Three stats tracked at once (HP + DEF + SPD) — unlike the single-stat
        # branch above, the per-stat 32 caps alone don't bound the total below
        # the game's real 66-total-SP cap (3 x 32 = 96 > 66), so it needs its
        # own explicit check below. The reachable ceiling for delta_hp +
        # delta_def + delta_spd is also 66 here, not 64 -- capping at 64 would
        # never even explore the 65/66-total spreads that check permits.
        if existing_hp + existing_def + existing_spd + budget > 66:
            budget = 66 - (existing_hp + existing_def + existing_spd)
        cap = min(budget, 66)

        for delta_def in range(0, cap + 1):
            for delta_spd in range(0, cap - delta_def + 1):
                delta_hp = cap - delta_def - delta_spd

                HP_SP = existing_hp + delta_hp
                DEF_SP = existing_def + delta_def
                SPD_SP = existing_spd + delta_spd

                if (
                    HP_SP > 32
                    or DEF_SP > 32
                    or SPD_SP > 32
                    or HP_SP + DEF_SP + SPD_SP > 66
                ):
                    continue

                spread = {"hp": HP_SP, "def": DEF_SP, "spd": SPD_SP}
                HP, per_attacker, total_dmg = evaluate(HP_SP, spread)
                total_pct = total_dmg / HP

                row = {
                    "HP_SP": HP_SP,
                    "def_SP": DEF_SP,
                    "spd_SP": SPD_SP,
                    "delta_hp": delta_hp,
                    "delta_def": delta_def,
                    "delta_spd": delta_spd,
                    "HP": HP,
                    "per_attacker": per_attacker,
                    "total_dmg": total_dmg,
                    "total_pct": total_pct,
                }
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


def report_multi(result: dict, primary: bool):
    stats_used = result["stats_used"]
    best = result["best"]

    if primary:
        with open(OUTPUTS_FILE, "w") as sweep_log:
            for row in result["sweep"]:
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
                sum_pct = row["total_pct"] * 100
                sweep_log.write(
                    f"{head}  (totals {totals})  {move_pcts}  sum={sum_pct:.2f}%\n"
                )

    print()
    print("OPTIMAL")
    print(f"  Spread:  {_spread_label(stats_used, best)}")
    for i, pa in enumerate(best["per_attacker"], 1):
        pct = pa["dmg"] / best["HP"] * 100
        print(
            f"  Move {i} ({pa['name']} — {pa['move']}):  {pa['dmg']} / {best['HP']} HP  ({pct:.1f}%)"
        )
        print(f"    {pa['desc']}")
    total_pct = best["total_pct"] * 100
    print(
        f"  Combined:  {best['total_dmg']} / {best['HP']} HP"
        f"  ({total_pct:.1f}% dealt, {100 - total_pct:.1f}% remaining)"
    )

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
            print(
                "\nNo valid spread found — check your existing SPs / budget don't "
                "push any stat past 32, or (with attackers hitting both DEF and "
                "SPD) the combined HP+DEF+SPD total past 66."
            )
        else:
            report_multi(result, primary=True)
    else:
        candidates = {nature: run(nature) for nature in NATURE_CANDIDATES}
        valid = {nature: r for nature, r in candidates.items() if r is not None}

        if not valid:
            print(
                "\nNo valid spread found — check your existing SPs / budget don't "
                "push any stat past 32, or (with attackers hitting both DEF and "
                "SPD) the combined HP+DEF+SPD total past 66."
            )
        else:
            winner = min(
                valid,
                key=lambda n: (
                    valid[n]["best"]["total_pct"],
                    NATURE_CANDIDATES.index(n),
                ),
            )
            print(
                f"\nDefender nature: {winner}  (auto-selected, lowest total damage among Bold/Calm/Serious)"
            )
            report_multi(valid[winner], primary=True)

            if winner != "Serious" and "Serious" in valid:
                print("\nDefender nature: Serious  (neutral fallback, for comparison)")
                report_multi(valid["Serious"], primary=False)
