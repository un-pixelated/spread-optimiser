# core/shared.py — engine shared by calc/single and calc/multi:
# bridge process, damage/HP helpers, and nature/status validation constants.
# Nothing here is mode-specific — no config parsing, no nature auto-pick
# heuristics (single and multi each have their own, with different logic).

import subprocess
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
BRIDGE = str(ROOT_DIR / "bridge.js")

# Shared output-log location (single/ and multi/ all write the same file).
OUTPUTS_DIR = ROOT_DIR / "outputs"
OUTPUTS_DIR.mkdir(exist_ok=True)
OUTPUTS_FILE = OUTPUTS_DIR / "outputs.txt"

# Champions' two SP caps, in ONE place: 32 per stat, 66 total across all stats
# on the Pokemon. Every spread the optimiser considers is enumerated through
# iter_spreads() below, so these are the only definitions of the caps in the
# codebase -- there is no per-file copy to drift out of sync.
PER_STAT_CAP = 32
TOTAL_CAP = 66

# One persistent Node process per Python process that imports this module.
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


def build_defender(name, nature, item, ability, status, sp, boost_stat, boost) -> dict:
    """The @smogon/calc defender payload, built the same way everywhere.

    `sp` is the already-assembled SP dict (e.g. {"hp": 12, "def": 20}); the
    single stage boost lands on `boost_stat` (the stat the move hits).
    """
    return {
        "name": name,
        "nature": nature,
        "item": item,
        "ability": ability,
        "status": status,
        "sp": sp,
        "boosts": {boost_stat: boost},
    }


def budget_cap(existing_total: int, budget: int, hard_cap: int) -> int:
    """SP a sweep may actually spend, given SPs already invested.

    Caps `budget` so `existing_total + spent` never exceeds `hard_cap` -- this
    is the "user forgot to reduce the budget after adding existing stats, so
    just use all the bulk that fits" behaviour. `hard_cap` is 64 (2 x 32) for a
    2-stat sweep, 66 (the total-SP cap) for a 3-stat one.
    """
    return min(budget, hard_cap - existing_total)


def _stat_delta_tuples(total, n):
    """Yield every n-tuple of non-negative ints summing to <= `total`, in
    odometer order (first index outermost, each ascending). The leftover
    `total - sum(tuple)` is the HP delta, assigned by iter_spreads().

    For n == 1 this is (0,), (1,), ..., (total,); for n == 2 it is the
    delta_def-outer / delta_spd-inner nesting the search loops have always
    used -- reproducing it exactly keeps the sweep logs byte-identical.
    """
    if n == 0:
        yield ()
        return
    for first in range(total + 1):
        for rest in _stat_delta_tuples(total - first, n - 1):
            yield (first,) + rest


def iter_spreads(existing, stats_used, total):
    """Yield every valid (spread, deltas) whose deltas sum to exactly `total`.

    `existing` maps each tracked stat ("hp" plus each stat in `stats_used`) to
    its already-invested SP; `stats_used` is a sorted subset of ("def", "spd").
    Both dicts yielded are keyed the same way (absolute SPs in `spread`, the
    added SPs in `deltas`). Spreads breaking the 32-per-stat or 66-total cap are
    skipped, so this is the single chokepoint where those caps are enforced.

    Only the tracked stats count toward the total cap -- matching the search's
    long-standing behaviour of not folding an untracked stat's existing SP into
    the 66 check.
    """
    for stat_deltas in _stat_delta_tuples(total, len(stats_used)):
        delta_hp = total - sum(stat_deltas)
        deltas = {"hp": delta_hp}
        spread = {"hp": existing["hp"] + delta_hp}
        for stat, d in zip(stats_used, stat_deltas):
            deltas[stat] = d
            spread[stat] = existing[stat] + d
        if any(v > PER_STAT_CAP for v in spread.values()):
            continue
        if sum(spread.values()) > TOTAL_CAP:
            continue
        yield spread, deltas


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

VALID_STATUSES = {"slp", "psn", "brn", "frz", "par", "tox"}
