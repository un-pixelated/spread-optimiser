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

## Running (single attacker)

First time only — `calc/single/config.py` is gitignored (it holds your personal test values, not something to commit), so create your working copy from the tracked template:

```bash
cp calc/single/config.example.py calc/single/config.py
```

Edit `calc/single/config.py` with your defender, attacker, move, and field details, then run:

```bash
python3 calc/single/calc.py
```

`calc/single/config.py` holds, in order:

1. **Defender** — name, nature (or `None` to auto-pick), item, ability, status condition (all or `None`). Base HP is pulled automatically from species data.
   - Status condition (`DEFENDER_STATUS`, and `ATTACKER_STATUS` below) — `"slp"`, `"psn"`, `"brn"`, `"frz"`, `"par"`, `"tox"`, or `None`. Affects damage where the game mechanics say it should — e.g. burn halves physical damage unless the attacker has Guts.
2. **Defensive stat the move hits** (`DEFENSIVE_STAT`) — `"def"` or `"spd"`.
   - Physical moves usually hit `def`, special moves usually hit `spd`.
   - A few special moves break that rule (Psyshock, Psystrike, Secret Sword hit `def` instead of `spd`) — just set whichever one actually applies to your move.
   - **Defender's stage boost** (`DEFENDER_BOOST`, -6 to +6) on that stat — e.g. an Iron Defense boost.
3. **SPs already invested** (`EXISTING_HP_SP`, `EXISTING_DEF_SP`) — if the defender already has SPs sunk into HP and/or the relevant defensive stat, set them here (0 for a fresh spread).
4. **Additional SP budget** (`BUDGET`) — how many _more_ SPs you have to spend across HP + the defensive stat. Each stat is capped at 32, same as in-game.
5. **Attacker** — name, nature, item, ability, status condition (all or `None`), SPs as a dict, e.g. `{"atk": 32}`.
6. **Attacking stat this move uses** (`ATTACKING_STAT`) — `"atk"` or `"spa"`, plus the attacker's stage boost (`ATTACKER_BOOST`, -6 to +6) on that stat — e.g. a Swords Dance boost.
7. **Move** — name, whether it's a crit.
8. **Terrain** (`TERRAIN`) — `"Electric"`/`"Grassy"`/`"Misty"`/`"Psychic"`, or `None`. Works the same whether it came from a move or an ability — e.g. set the attacker's ability to `"Hadron Engine"` and terrain to `"Electric"` and its Special Attack boost is applied automatically.
9. **Field conditions** — game type, weather, screens, Helping Hand (attacker's side), Friend Guard (defender's side).

## Output

- **Console**: the optimal spread (lowest % HP dealt), showing exactly how much _more_ HP/DEF(or SPD) you need on top of what's already invested.
- **outputs/outputs.txt**: every additional-SP split tried.
- **outputs/plot.png**: % HP dealt across every spread tried.

## Minimum SP to survive

If you just want to know the smallest SP investment that avoids getting KO'd — rather than the lowest-damage spread within a fixed budget — run:

```bash
python3 calc/single/survive.py
```

It reads the same `calc/single/config.py` and ignores `BUDGET`/`TUNER` entirely: it searches every valid HP/DEF(or SPD) split, starting from `EXISTING_HP_SP`/`EXISTING_DEF_SP`, and reports the smallest additional total that guarantees survival (the max damage roll doesn't KO). If even a full 32/32 investment can't survive, it says so. Console-only — no `outputs/` files or plot.

## Example

Defender already has 14 SPs in HP and 0 in DEF, and you've got 30 more SPs to spend:

```python
EXISTING_HP_SP = 14
EXISTING_DEF_SP = 0
BUDGET = 30
```

It searches every valid extra HP/DEF split on top of the existing 14, and tells you the smallest additional investment that still survives the hit.

## Multiple attackers

If you're checking a defender against several incoming threats at once (e.g. two different attackers, or one attacker with two different moves) rather than a single hit, use the multi-attacker optimiser instead. It minimises the *combined* damage from all of them, across the same shared SP budget.

First time only:

```bash
cp calc/multi/config.example.py calc/multi/config.py
```

Edit `calc/multi/config.py`, then run:

```bash
python3 calc/multi/calc.py
```

`calc/multi/config.py` holds, in order:

1. **Defender** — name, nature (or `None` to auto-pick the best of Bold/Calm/Serious by actually comparing total damage), item, ability, status condition, existing SPs already invested (`EXISTING_HP_SP`, `EXISTING_DEF_SP`, `EXISTING_SPD_SP`), and the additional SP budget (`BUDGET`) shared across all attackers.
2. **`ATTACKERS`** — a list of **2 to 4** attacker+move dicts, each specifying that attacker's name/nature/item/ability/status/SPs, which stat its move uses (`attacking_stat`) and hits (`defensive_stat`), its boost, and the move itself. **To add an attacker** (up to 4), copy one of the dicts in the list and append it. **To remove one** (down to a minimum of 2), delete its dict. Attackers can freely mix physical (`def`-hitting) and special (`spd`-hitting) moves — even at the minimum of 2 attackers, one hitting `def` and the other `spd` is the normal case, not an edge case. There are only two possible defensive stats in the game no matter how many attackers you configure, so the search never grows past HP + DEF + SPD.
3. **Field conditions** — shared across every attacker (weather/terrain/screens are global battle state, not something that changes per incoming attack).

Output is console-only, no plot — a multi-attacker result doesn't reduce to a single 2D chart the way a one-move sweep does. The full sweep still goes to `outputs/outputs.txt`, and running this deletes any stale `outputs/plot.png` left over from a single-attacker run.
