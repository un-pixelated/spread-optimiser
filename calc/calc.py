# Defensive optimiser for Pokémon Champions
# Uses @smogon/calc via bridge.js for damage calculation

import contextlib
from core.shared import (
    ROOT_DIR,
    calc_damage,
    calc_hp,
    parse_config,
    resolve_defender_natures,
)
from plot import plot

OUTPUTS_DIR = ROOT_DIR / "outputs"
OUTPUTS_DIR.mkdir(exist_ok=True)
OUTPUTS_FILE = OUTPUTS_DIR / "outputs.txt"
PLOT_FILE = OUTPUTS_DIR / "plot.png"


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
    DEFENDER_STATUS: str | None,
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
                "status": DEFENDER_STATUS,
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
        print(f"Sweep log: {OUTPUTS_FILE.relative_to(ROOT_DIR)}")

    if PRIMARY:
        plot(
            xs,
            ys,
            DEF_STAT,
            output_path=PLOT_FILE,
            attacker_name=ATTACKER["name"],
            defender_name=DEFENDER_NAME,
            move_name=MOVE["name"],
            move_type=move_type,
            best_index=best_index,
            best_dmg=optimal_stats["DMG"],
            best_hp=optimal_stats["HP"],
            best_desc=optimal_stats["desc"],
        )
        print(f"Plot saved to: {PLOT_FILE.relative_to(ROOT_DIR)}")
    return minimum_dealt


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
