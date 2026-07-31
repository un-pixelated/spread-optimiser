# config.py — edit these values, then run `python3 calc/multi/calc.py`.

DEFENDER_NAME = ...
DEFENDER_NATURE = (
    None  # explicit nature, or None to auto-pick the best of Bold/Calm/Serious
)
DEFENDER_ITEM = ...
DEFENDER_ABILITY = ...
DEFENDER_STATUS = None  # "slp", "psn", "brn", "frz", "par", "tox", or None

EXISTING_HP_SP = 0  # SPs the defender already has invested in HP
EXISTING_DEF_SP = 0  # only relevant if any attacker's defensive_stat is "def"
EXISTING_SPD_SP = 0  # only relevant if any attacker's defensive_stat is "spd"
BUDGET = 32  # additional SP budget across HP + whichever of DEF/SPD are in play

# ATTACKERS: 2 to 4 entries. Each is one attacker+move pairing whose damage
# gets summed against the shared defender above. To add another attacker (up
# to 4), copy one of the dicts below and append it to the list; to remove one
# (down to a minimum of 2), delete its dict. Attackers can freely mix
# physical (def-hitting) and special (spd-hitting) moves — even with just 2
# attackers, one hitting def and the other spd is a normal case, not an edge
# case. There are only two possible defensive stats in the game no matter how
# many attackers you add — the search is always over HP + whichever of
# DEF/SPD your attackers' moves actually hit.
ATTACKERS = [
    {
        "name": ...,
        "nature": ...,
        "item": ...,  # or None
        "ability": ...,  # or None
        "status": None,  # "slp", "psn", "brn", "frz", "par", "tox", or None
        "sp": {"atk": 32},  # e.g. {"atk": 32}
        "attacking_stat": "atk",  # "atk" or "spa" — which stat this move uses
        "boost": 0,  # attacker's stage boost (-6 to +6) on attacking_stat
        "move_name": ...,
        "move_is_crit": False,
        "defensive_stat": "def",  # "def" or "spd" — which stat this move hits
        "defender_boost": 0,  # defender's stage boost (-6 to +6) on defensive_stat
    },
    {
        "name": ...,
        "nature": ...,
        "item": ...,  # or None
        "ability": ...,  # or None
        "status": None,
        "sp": {"spa": 32},
        "attacking_stat": "spa",
        "boost": 0,
        "move_name": ...,
        "move_is_crit": False,
        "defensive_stat": "spd",
        "defender_boost": 0,
    },
]

GAME_TYPE = "Singles"  # "Singles" or "Doubles"
WEATHER = None  # "Sand", "Sun", "Rain", "Snow", or None
TERRAIN = None  # "Electric", "Grassy", "Misty", "Psychic", or None
IS_REFLECT = False
IS_LIGHT_SCREEN = False
IS_HELPING_HAND = False  # active for the attackers' side
IS_FRIEND_GUARD = False  # active for the defender's side
