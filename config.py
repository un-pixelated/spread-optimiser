# config.py — edit these values, then run `python3 calc.py`.

ATTACKER_NAME = "Sneasler"
ATTACKER_NATURE = "Timid"
ATTACKER_ITEM = "White Herb"  # or None
ATTACKER_ABILITY = None
ATTACKER_SP = {"atk": 32}  # e.g. {"atk": 32}

ATTACKING_STAT = "atk"  # "atk" or "spa" — which stat the move uses
ATTACKER_BOOST = (
    0  # attacker's stage boost (-6 to +6) on ATTACKING_STAT, e.g. Swords Dance
)

DEFENDER_NAME = "Floette-Mega"
DEFENDER_NATURE = None  # or None to auto-pick a nature that boosts DEFENSIVE_STAT
# (also runs and prints a second pass with the neutral "Serious" nature for comparison)
DEFENDER_ITEM = None
DEFENDER_ABILITY = "Fairy Aura"

MOVE_NAME = "Poison Jab"
MOVE_IS_CRIT = False

# Physical moves usually hit "def", special moves usually hit "spd" — but a few
# break that rule (Psyshock, Psystrike, Secret Sword hit "def" despite being
# special; Body Press uses the attacker's own "def", etc). Set whichever one
# actually applies to your move.
DEFENSIVE_STAT = "def"  # "def" or "spd" — which stat the move hits
DEFENDER_BOOST = (
    0  # defender's stage boost (-6 to +6) on DEFENSIVE_STAT, e.g. Iron Defense
)

EXISTING_HP_SP = 0  # SPs the defender already has invested in HP
EXISTING_DEF_SP = 0  # SPs the defender already has invested in DEFENSIVE_STAT
BUDGET = (
    40  # additional SP budget to spend across HP + DEFENSIVE_STAT (each capped at 32)
)

# Terrain works the same whether it came from a move or an ability — e.g. set
# ATTACKER_ABILITY to "Hadron Engine" and TERRAIN to "Electric" and its Special
# Attack boost is applied automatically.
GAME_TYPE = "Singles"  # "Singles" or "Doubles"
WEATHER = None
TERRAIN = None  # "Electric", "Grassy", "Misty", "Psychic", or None
IS_REFLECT = False
IS_LIGHT_SCREEN = False
IS_HELPING_HAND = False  # active for the attacker's side
IS_FRIEND_GUARD = False  # active for the defender's side

# Among all spreads within TOLERANCE percentage points of optimal, pick the one
# that maximises PRIORITY's SP instead of the outright lowest-damage spread.
# Set to None to disable.
TUNER = None  # {"priority": "hp", "tolerance": 1}
# TUNER = {"priority": "hp", "tolerance": 0.5}  # priority: "hp" or DEFENSIVE_STAT
