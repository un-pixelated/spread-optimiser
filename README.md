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

```bash
python3 calc.py
```

You'll be prompted for, in order:

1. **Attacker** — name, nature, item, SPs as a Python dict, e.g. `{"atk": 32}`.
2. **Defender** — name, nature, base HP.
3. **Move** — name, whether it's a crit.
4. **Defensive stat the move hits** — `def` or `spd`.
   - Physical moves usually hit `def`, special moves usually hit `spd`.
   - A few special moves break that rule (Psyshock, Psystrike, Secret Sword hit `def` instead of `spd`) — just type whichever one actually applies to your move.
5. **SPs already invested** — if the defender already has SPs sunk into HP and/or the relevant defensive stat, enter them here (0 for a fresh spread).
6. **Additional SP budget** — how many *more* SPs you have to spend across HP + the defensive stat. Each stat is capped at 32, same as in-game.
7. **Field conditions** — game type, weather, screens.

## Output

- **Console**: every additional-SP split tried, then the optimal one (lowest % HP dealt), showing exactly how much *more* HP/DEF(or SPD) you need on top of what's already invested.
- **plot.png**: % HP dealt across every spread tried, saved in the project folder.

## Example

Defender already has 14 SPs in HP and 0 in DEF, and you've got 30 more SPs to spend:

```
SPs already invested in HP                (0 if none): 14
SPs already invested in DEF (0 if none): 0
Additional SP budget to spend (HP + DEF): 30
```

It searches every valid extra HP/DEF split on top of the existing 14, and tells you the smallest additional investment that still survives the hit.
