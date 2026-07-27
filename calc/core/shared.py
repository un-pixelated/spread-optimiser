# core/shared.py — engine shared by calc/single and calc/multi:
# bridge process, damage/HP helpers, and nature/status validation constants.
# Nothing here is mode-specific — no config parsing, no nature auto-pick
# heuristics (single and multi each have their own, with different logic).

import subprocess
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
BRIDGE = str(ROOT_DIR / "bridge.js")

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
