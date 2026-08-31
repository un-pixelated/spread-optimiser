# Minimum-SP-to-survive finder for Pokémon Champions
# Ignores config.BUDGET/config.TUNER — finds the smallest total SP spend
# (across HP + DEFENSIVE_STAT) where the max damage roll doesn't KO.

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.shared import (
    ROOT_DIR,
    OUTPUTS_FILE,
    calc_damage,
    calc_hp,
    build_defender,
    iter_spreads,
)

from calc import parse_config, resolve_defender_natures


def find_min_sp(
    attacker,
    defender_name,
    nature,
    defender_ability,
    defender_item,
    defensive_stat,
    defender_boost,
    defender_status,
    existing_hp,
    existing_def,
    move,
    field,
    PRIMARY: bool = True,  # writes outputs.txt; False for comparison-only runs
) -> dict | None:
    # Only HP + DEFENSIVE_STAT are tracked; iter_spreads enforces the 32/stat
    # (and 66-total) caps, so walking totals 0..64 covers every valid spread.
    existing = {"hp": existing_hp, defensive_stat: existing_def}
    log_lines = []
    best = None
    best_pct = None

    def flush_log():
        if PRIMARY:
            OUTPUTS_FILE.write_text("".join(line + "\n" for line in log_lines))

    for total in range(0, 65):
        survivors = []
        for spread, deltas in iter_spreads(existing, [defensive_stat], total):
            HP_SP = spread["hp"]
            DEF_SP = spread[defensive_stat]
            delta_hp = deltas["hp"]
            delta_def = deltas[defensive_stat]

            defender = build_defender(
                defender_name,
                nature,
                defender_item,
                defender_ability,
                defender_status,
                spread,
                defensive_stat,
                defender_boost,
            )
            result = calc_damage(attacker, defender, move, field)
            HP = calc_hp(result["defenderBaseHp"], HP_SP)
            DMG = result["max"]
            pct = DMG / HP * 100

            if PRIMARY:
                log_lines.append(
                    f"+{delta_hp:>2} HP / +{delta_def:>2} {defensive_stat.upper()}  "
                    f"(totals {HP_SP}/{DEF_SP}) -> {DMG}/{HP} ({pct:.2f}%)  [{result['desc']}]"
                )

            point = {
                "HP_SP": HP_SP,
                "DEF_SP": DEF_SP,
                "delta_hp": delta_hp,
                "delta_def": delta_def,
                "total": total,
                "DMG": DMG,
                "HP": HP,
                "desc": result["desc"],
            }

            # tracked across the whole sweep as a fallback for the
            # not-survivable case, where the best available spread (lowest
            # % dealt) is more useful than a bare "not survivable".
            if best_pct is None or pct < best_pct:
                best_pct = pct
                best = point

            if DMG < HP:
                survivors.append(point)

        if survivors:
            # tie-break: prefer more HP over more of the defensive stat — HP
            # helps against any threat, the defensive stat only helps this one.
            winner = max(survivors, key=lambda r: r["HP_SP"])
            winner["survives"] = True
            flush_log()
            return winner

    flush_log()
    if best is not None:
        best["survives"] = False
    return best


if __name__ == "__main__":
    parsed = parse_config()
    for nature, label, primary in resolve_defender_natures(
        parsed["defender_nature"], parsed["defensive_stat"]
    ):
        if label:
            print(f"\nDefender nature: {nature}  ({label})")

        result = find_min_sp(
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
            parsed["move"],
            parsed["field"],
            PRIMARY=primary,
        )

        stat = parsed["defensive_stat"].upper()
        print()
        if result is None:
            print("NOT SURVIVABLE")
        else:
            pct = result["DMG"] / result["HP"] * 100
            print("MINIMUM SP TO SURVIVE" if result["survives"] else "NOT SURVIVABLE")
            print(
                f"  Spread:  {result['HP_SP']} HP / {result['DEF_SP']} {stat}"
                f"  (+{result['delta_hp']} HP / +{result['delta_def']} {stat}, total +{result['total']} SP)"
            )
            print(
                f"  Damage:  {result['DMG']} / {result['HP']} HP"
                f"  ({pct:.1f}% dealt, {100 - pct:.1f}% remaining)"
            )
            print(f"  Desc:    {result['desc']}")

        if primary:
            print()
            print(f"Sweep log: {OUTPUTS_FILE.relative_to(ROOT_DIR)}")
