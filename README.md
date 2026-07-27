# Pokémon Champions Defensive SP Optimiser

Finds the HP / DEF (or HP / SPD) split that minimises the % of a defender's HP a given attack deals, within an SP budget. Uses [@smogon/calc](https://www.npmjs.com/package/@smogon/calc) under the hood via a small Node bridge (`bridge.js`).

## Setup

```bash
npm install
```

Python 3 + matplotlib:

```bash
pip install matplotlib
```

## Running

Edit `calc/config.py` with your attacker, defender, move, and field details, then run:

```bash
python3 calc/calc.py
```

`calc/config.py` holds, in order:

1. **Attacker** — name, nature, item, ability, status condition (all or `None`), SPs as a dict, e.g. `{"atk": 32}`.
2. **Attacking stat this move uses** (`ATTACKING_STAT`) — `"atk"` or `"spa"`, plus the attacker's stage boost (`ATTACKER_BOOST`, -6 to +6) on that stat — e.g. a Swords Dance boost.
3. **Defender** — name, nature, item, ability, status condition (all or `None`). Base HP is pulled automatically from species data.
   - Status condition (`ATTACKER_STATUS`/`DEFENDER_STATUS`) — `"slp"`, `"psn"`, `"brn"`, `"frz"`, `"par"`, `"tox"`, or `None`. Affects damage where the game mechanics say it should — e.g. burn halves physical damage unless the attacker has Guts.
4. **Move** — name, whether it's a crit.
5. **Defensive stat the move hits** (`DEFENSIVE_STAT`) — `"def"` or `"spd"`.
   - Physical moves usually hit `def`, special moves usually hit `spd`.
   - A few special moves break that rule (Psyshock, Psystrike, Secret Sword hit `def` instead of `spd`) — just set whichever one actually applies to your move.
6. **Defender's stage boost** (`DEFENDER_BOOST`, -6 to +6) on that stat — e.g. an Iron Defense boost.
7. **SPs already invested** (`EXISTING_HP_SP`, `EXISTING_DEF_SP`) — if the defender already has SPs sunk into HP and/or the relevant defensive stat, set them here (0 for a fresh spread).
8. **Additional SP budget** (`BUDGET`) — how many _more_ SPs you have to spend across HP + the defensive stat. Each stat is capped at 32, same as in-game.
9. **Terrain** (`TERRAIN`) — `"Electric"`/`"Grassy"`/`"Misty"`/`"Psychic"`, or `None`. Works the same whether it came from a move or an ability — e.g. set the attacker's ability to `"Hadron Engine"` and terrain to `"Electric"` and its Special Attack boost is applied automatically.
10. **Field conditions** — game type, weather, screens, Helping Hand (attacker's side), Friend Guard (defender's side).

## Output

- **Console**: the optimal spread (lowest % HP dealt), showing exactly how much _more_ HP/DEF(or SPD) you need on top of what's already invested.
- **outputs/outputs.txt**: every additional-SP split tried.
- **outputs/plot.png**: % HP dealt across every spread tried.

## Minimum SP to survive

If you just want to know the smallest SP investment that avoids getting KO'd — rather than the lowest-damage spread within a fixed budget — run:

```bash
python3 calc/survive.py
```

It reads the same `calc/config.py` and ignores `BUDGET`/`TUNER` entirely: it searches every valid HP/DEF(or SPD) split, starting from `EXISTING_HP_SP`/`EXISTING_DEF_SP`, and reports the smallest additional total that guarantees survival (the max damage roll doesn't KO). If even a full 32/32 investment can't survive, it says so. Console-only — no `outputs/` files or plot.

## Example

Defender already has 14 SPs in HP and 0 in DEF, and you've got 30 more SPs to spend:

```python
EXISTING_HP_SP = 14
EXISTING_DEF_SP = 0
BUDGET = 30
```

It searches every valid extra HP/DEF split on top of the existing 14, and tells you the smallest additional investment that still survives the hit.
