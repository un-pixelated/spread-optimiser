# core/shared.py — engine shared by calc.py and survive.py:
# bridge process, damage/HP helpers, nature/status validation, config parsing.

import subprocess
import json
from pathlib import Path
import config

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

# Natures that boost the stat a move actually hits. Any nature in this table is
# equally "optimal" for this calculator: it only ever computes a single hit
# against DEF or SPD, so whichever stat each nature lowers (Atk/SpA/Speed/the
# other defensive stat) never factors into the damage math.
BEST_DEFENSIVE_NATURE = {"def": "Bold", "spd": "Calm"}


def resolve_defender_natures(defender_nature, defensive_stat):
    """Returns [(nature, label, primary), ...] to run.

    If defender_nature is None: auto-selected nature (primary, writes
    outputs/plot) plus a neutral "Serious" comparison pass. Otherwise: just
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
    ), "config.ATTACKING_STAT must be 'atk' or 'spa'"
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
