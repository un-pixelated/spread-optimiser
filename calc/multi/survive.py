# Minimum-SP-to-survive finder for multi-attacker scenarios.
# Finds the smallest total SP spend across HP + whichever of DEF/SPD are in
# play where the combined max damage roll from all attackers doesn't KO.

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.shared import ROOT_DIR, OUTPUTS_FILE, iter_spreads

from calc import (
    parse_config_multi,
    NATURE_CANDIDATES,
    evaluate,
    select_nature,
    print_attacker_lines,
    sweep_log_line,
    _spread_label,
)


def _make_point(spread, deltas, total, HP, per_attacker, total_dmg):
    """A survive sweep point, keyed like the calc rows (plus the diagonal
    total) so sweep_log_line and _spread_label read it unchanged."""
    point = {"HP_SP": spread["hp"], "delta_hp": deltas["hp"]}
    for stat in spread:
        if stat == "hp":
            continue
        point[f"{stat}_SP"] = spread[stat]
        point[f"delta_{stat}"] = deltas[stat]
    point["total"] = total
    point["HP"] = HP
    point["per_attacker"] = per_attacker
    point["total_dmg"] = total_dmg
    return point


def find_min_sp_multi(
    attackers,
    defender_name,
    nature,
    defender_item,
    defender_ability,
    defender_status,
    existing_hp,
    existing_def,
    existing_spd,
    field,
) -> dict | None:
    stats_used = sorted({a["defensive_stat"] for a in attackers})
    all_existing = {"hp": existing_hp, "def": existing_def, "spd": existing_spd}
    existing = {"hp": existing_hp, **{s: all_existing[s] for s in stats_used}}
    # 1 stat -> diagonals up to 64 (2 x 32); 2 stats -> up to 66 (the total-SP
    # cap binds before 3 x 32 = 96 would). iter_spreads enforces both caps.
    max_total = 64 if len(stats_used) == 1 else 66

    evaluated = []
    best_effort = None
    best_effort_pct = None

    for total in range(0, max_total + 1):
        survivors = []
        for spread, deltas in iter_spreads(existing, stats_used, total):
            HP, per_attacker, total_dmg = evaluate(
                attackers,
                defender_name,
                nature,
                defender_item,
                defender_ability,
                defender_status,
                spread,
                field,
            )
            point = _make_point(spread, deltas, total, HP, per_attacker, total_dmg)
            evaluated.append(sweep_log_line(stats_used, point))

            sum_pct = total_dmg / HP * 100
            # tracked across the whole sweep as a fallback for the
            # not-survivable case, where the best available spread (lowest
            # % dealt) is more useful than a bare "not survivable".
            if best_effort_pct is None or sum_pct < best_effort_pct:
                best_effort_pct = sum_pct
                best_effort = point

            if total_dmg < HP:
                survivors.append(point)

        if survivors:
            best = max(survivors, key=lambda r: r["HP_SP"])
            best["survives"] = True
            return {
                "stats_used": stats_used,
                "best": best,
                "evaluated": evaluated,
            }

    if best_effort is not None:
        best_effort["survives"] = False
    return {
        "stats_used": stats_used,
        "best": best_effort,
        "evaluated": evaluated,
    }


def report(result, nature, primary: bool = True):
    stats_used = result["stats_used"]
    best = result["best"]

    if primary:
        with open(OUTPUTS_FILE, "w") as sweep_log:
            for line in result["evaluated"]:
                sweep_log.write(line + "\n")

    print(f"\nDefender nature: {nature}")
    print("MINIMUM SP TO SURVIVE" if best["survives"] else "NOT SURVIVABLE")
    print(f"  Spread:  {_spread_label(stats_used, best)}")
    print_attacker_lines(best)
    total_pct = best["total_dmg"] / best["HP"] * 100
    print(
        f"  Combined:  {best['total_dmg']} / {best['HP']} HP"
        f"  ({total_pct:.1f}% dealt, {100 - total_pct:.1f}% remaining, total +{best['total']} SP)"
    )

    if primary:
        print()
        print(f"Sweep log: {OUTPUTS_FILE.relative_to(ROOT_DIR)}")


if __name__ == "__main__":
    parsed = parse_config_multi()

    def run(nature):
        return find_min_sp_multi(
            parsed["attackers"],
            parsed["defender_name"],
            nature,
            parsed["defender_item"],
            parsed["defender_ability"],
            parsed["defender_status"],
            parsed["existing_hp"],
            parsed["existing_def"],
            parsed["existing_spd"],
            parsed["field"],
        )

    if parsed["defender_nature"] is not None:
        nature = parsed["defender_nature"]
        report(run(nature), nature, primary=True)
    else:
        candidates = {nature: run(nature) for nature in NATURE_CANDIDATES}
        survivable = {n: r for n, r in candidates.items() if r["best"]["survives"]}

        if survivable:
            winner = select_nature(survivable, lambda n: survivable[n]["best"]["total"])
        else:
            # nothing survives under any candidate nature — fall back to
            # whichever candidate deals the least combined damage instead.
            def pct(n):
                best = candidates[n]["best"]
                return best["total_dmg"] / best["HP"] * 100

            winner = select_nature(candidates, pct)

        report(candidates[winner], winner, primary=True)

        if winner != "Serious":
            report(candidates["Serious"], "Serious", primary=False)
