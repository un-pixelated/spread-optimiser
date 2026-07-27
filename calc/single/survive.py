# Minimum-SP-to-survive finder for Pokémon Champions
# Ignores config.BUDGET/config.TUNER — finds the smallest total SP spend
# (across HP + DEFENSIVE_STAT) where the max damage roll doesn't KO.

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.shared import calc_damage, calc_hp

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
) -> dict | None:
    for total in range(0, 65):
        survivors = []
        for delta_def in range(0, total + 1):
            delta_hp = total - delta_def

            HP_SP = existing_hp + delta_hp
            DEF_SP = existing_def + delta_def

            if HP_SP > 32 or DEF_SP > 32:
                continue

            defender = {
                "name": defender_name,
                "nature": nature,
                "item": defender_item,
                "ability": defender_ability,
                "status": defender_status,
                "sp": {"hp": HP_SP, defensive_stat: DEF_SP},
                "boosts": {defensive_stat: defender_boost},
            }

            result = calc_damage(attacker, defender, move, field)
            HP = calc_hp(result["defenderBaseHp"], HP_SP)
            DMG = result["max"]

            if DMG < HP:
                survivors.append(
                    {
                        "HP_SP": HP_SP,
                        "DEF_SP": DEF_SP,
                        "delta_hp": delta_hp,
                        "delta_def": delta_def,
                        "total": total,
                        "DMG": DMG,
                        "HP": HP,
                        "desc": result["desc"],
                    }
                )

        if survivors:
            # tie-break: prefer more HP over more of the defensive stat — HP
            # helps against any threat, the defensive stat only helps this one.
            return max(survivors, key=lambda r: r["HP_SP"])

    return None


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
        )

        stat = parsed["defensive_stat"].upper()
        print()
        print("MINIMUM SP TO SURVIVE")
        if result is None:
            print(
                f"  Not survivable — even at 32 HP / 32 {stat}, the max roll still KOs."
            )
        else:
            pct = result["DMG"] / result["HP"] * 100
            print(
                f"  Spread:  {result['HP_SP']} HP / {result['DEF_SP']} {stat}"
                f"  (+{result['delta_hp']} HP / +{result['delta_def']} {stat}, total +{result['total']} SP)"
            )
            print(
                f"  Damage:  {result['DMG']} / {result['HP']} HP"
                f"  ({pct:.1f}% dealt, {100 - pct:.1f}% remaining)"
            )
            print(f"  Desc:    {result['desc']}")
