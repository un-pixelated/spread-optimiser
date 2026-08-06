# Minimum-SP-to-survive finder for multi-attacker scenarios.
# Finds the smallest total SP spend across HP + whichever of DEF/SPD are in
# play where the combined max damage roll from all attackers doesn't KO.

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.shared import ROOT_DIR, calc_hp

from calc import parse_config_multi, NATURE_CANDIDATES, _hit, _spread_label

OUTPUTS_DIR = ROOT_DIR / "outputs"
OUTPUTS_DIR.mkdir(exist_ok=True)
OUTPUTS_FILE = OUTPUTS_DIR / "outputs.txt"


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
    evaluated = []

    def evaluate(HP_SP, spread):
        HP = None
        total_dmg = 0
        per_attacker = []
        for a in attackers:
            result = _hit(
                defender_name,
                nature,
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
        stat = stats_used[0]
        existing_stat = existing_def if stat == "def" else existing_spd

        for total in range(0, 65):
            survivors = []
            for delta_stat in range(0, total + 1):
                delta_hp = total - delta_stat
                HP_SP = existing_hp + delta_hp
                STAT_SP = existing_stat + delta_stat

                if HP_SP > 32 or STAT_SP > 32:
                    continue

                spread = {"hp": HP_SP, stat: STAT_SP}
                HP, per_attacker, total_dmg = evaluate(HP_SP, spread)

                move_pcts = "  ".join(
                    f"move{i}={pa['dmg'] / HP * 100:.1f}%"
                    for i, pa in enumerate(per_attacker, 1)
                )
                sum_pct = total_dmg / HP * 100
                evaluated.append(
                    f"+{delta_hp:>2} HP / +{delta_stat:>2} {stat.upper()}  "
                    f"(totals {HP_SP}/{STAT_SP})  {move_pcts}  sum={sum_pct:.2f}%"
                )

                if total_dmg < HP:
                    survivors.append(
                        {
                            "HP_SP": HP_SP,
                            f"{stat}_SP": STAT_SP,
                            "delta_hp": delta_hp,
                            f"delta_{stat}": delta_stat,
                            "total": total,
                            "HP": HP,
                            "per_attacker": per_attacker,
                            "total_dmg": total_dmg,
                        }
                    )

            if survivors:
                return {
                    "stats_used": stats_used,
                    "best": max(survivors, key=lambda r: r["HP_SP"]),
                    "evaluated": evaluated,
                }

        return None

    for total in range(0, 67):
        survivors = []
        for delta_def in range(0, total + 1):
            for delta_spd in range(0, total - delta_def + 1):
                delta_hp = total - delta_def - delta_spd

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

                move_pcts = "  ".join(
                    f"move{i}={pa['dmg'] / HP * 100:.1f}%"
                    for i, pa in enumerate(per_attacker, 1)
                )
                sum_pct = total_dmg / HP * 100
                evaluated.append(
                    f"+{delta_hp:>2} HP / +{delta_def:>2} DEF / +{delta_spd:>2} SPD  "
                    f"(totals {HP_SP}/{DEF_SP}/{SPD_SP})  {move_pcts}  sum={sum_pct:.2f}%"
                )

                if total_dmg < HP:
                    survivors.append(
                        {
                            "HP_SP": HP_SP,
                            "def_SP": DEF_SP,
                            "spd_SP": SPD_SP,
                            "delta_hp": delta_hp,
                            "delta_def": delta_def,
                            "delta_spd": delta_spd,
                            "total": total,
                            "HP": HP,
                            "per_attacker": per_attacker,
                            "total_dmg": total_dmg,
                        }
                    )

        if survivors:
            return {
                "stats_used": stats_used,
                "best": max(survivors, key=lambda r: r["HP_SP"]),
                "evaluated": evaluated,
            }

    return None


def report(result, nature, primary: bool = True):
    stats_used = result["stats_used"]
    best = result["best"]

    if primary:
        with open(OUTPUTS_FILE, "w") as sweep_log:
            for line in result["evaluated"]:
                sweep_log.write(line + "\n")

    print(f"\nDefender nature: {nature}")
    print("MINIMUM SP TO SURVIVE")
    print(f"  Spread:  {_spread_label(stats_used, best)}")
    for i, pa in enumerate(best["per_attacker"], 1):
        pct = pa["dmg"] / best["HP"] * 100
        print(
            f"  Move {i} ({pa['name']} — {pa['move']}):  {pa['dmg']} / {best['HP']} HP  ({pct:.1f}%)"
        )
        print(f"    {pa['desc']}")
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

    not_survivable_msg = (
        "\nNot survivable — even at the 32-per-stat / 66-total SP caps, "
        "the combined max roll still KOs."
    )

    if parsed["defender_nature"] is not None:
        nature = parsed["defender_nature"]
        result = run(nature)
        if result is None:
            print(not_survivable_msg)
        else:
            report(result, nature, primary=True)
    else:
        candidates = {nature: run(nature) for nature in NATURE_CANDIDATES}
        valid = {nature: r for nature, r in candidates.items() if r is not None}

        if not valid:
            print(not_survivable_msg)
        else:
            winner = min(
                valid,
                key=lambda n: (
                    valid[n]["best"]["total"],
                    NATURE_CANDIDATES.index(n),
                ),
            )
            report(valid[winner], winner, primary=True)

            if winner != "Serious" and "Serious" in valid:
                report(valid["Serious"], "Serious", primary=False)
