# Pokémon Champions Defensive SP Optimiser

Finds the HP/DEF (or HP/SPD) split that minimises the % HP a given attack deals, within an SP budget. Uses [@smogon/calc](https://www.npmjs.com/package/@smogon/calc) via a small Node bridge (`bridge.js`).

> [!WARNING]
> This is a vibe-coded project. Every line of it was written by an LLM, including this
> warning. Verify outputs against [the Champions damage calculator](https://calc.pokemonshowdown.com/champions.html) before
> trusting a spread it gives you. There exist some known issues which are being worked
> upon, but there also exist unknown bugs.

## Setup

```bash
npm install
```

## Single attacker

First time only — `calc/single/config.py` is gitignored (personal values):

```bash
cp calc/single/config.example.py calc/single/config.py
```

Edit it, then:

```bash
python3 calc/single/calc.py
```

Config fields, in order:

1. **Defender** — name, nature (`None` to auto-pick), item, ability, status (`"slp"`/`"psn"`/`"brn"`/`"frz"`/`"par"`/`"tox"`/`None`). Base HP is pulled from species data automatically.
2. **`DEFENSIVE_STAT`** — `"def"` or `"spd"`, whichever the move hits (usually `def` for physical, `spd` for special; exceptions like Psyshock/Psystrike/Secret Sword hit `def`). Plus `DEFENDER_BOOST` (-6 to +6) on that stat.
3. **`EXISTING_HP_SP` / `EXISTING_DEF_SP`** — SPs the defender already has invested.
4. **`BUDGET`** — additional SPs to spend across HP + the defensive stat (each capped at 32).
5. **Attacker** — name, nature, item, ability, status, SPs (e.g. `{"atk": 32}`).
6. **`ATTACKING_STAT`** — `"atk"`, `"spa"`, or `"def"` (e.g. Body Press). Plus `ATTACKER_BOOST` (-6 to +6) on that stat.
7. **Move** — name, crit flag.
8. **`TERRAIN`** — `"Electric"`/`"Grassy"`/`"Misty"`/`"Psychic"`/`None`. Also applies from an ability (e.g. Hadron Engine + Electric terrain).
9. **Field** — game type, weather, screens, Helping Hand, Friend Guard.
10. **`TUNER`** (optional) — `None`, or `{"priority": "hp"|DEFENSIVE_STAT, "tolerance": <pp>}` to pick the spread maximising `priority`'s SP among all spreads within `tolerance` of optimal.

**Output**: console prints the optimal spread; `outputs/outputs.txt` logs every split tried.

## Minimum SP to survive

```bash
python3 calc/single/survive.py
```

Same config, ignoring `BUDGET`/`TUNER`. Searches every valid split from the existing SPs up and reports the smallest addition that survives the max damage roll — or says so if even 32/32 can't. Console-only.

## Multiple attackers

For several simultaneous threats (multiple attackers, or one attacker with multiple moves), minimising _combined_ damage:

```bash
cp calc/multi/config.example.py calc/multi/config.py
python3 calc/multi/calc.py
```

Config fields:

1. **Defender** — as above, but nature `None` auto-picks the best of Bold/Calm/Serious by comparing total damage. Existing SPs: `EXISTING_HP_SP`, `EXISTING_DEF_SP`, `EXISTING_SPD_SP`. `BUDGET` is shared across all attackers. Champions caps SP at 32/stat and 66 total — both are validated.
2. **`ATTACKERS`** — list of 2-4 attacker+move dicts (name/nature/item/ability/status/SPs, `attacking_stat`, `defensive_stat`, boost, move). Copy/append or delete a dict to change the count. Attackers can freely mix `def`- and `spd`-hitting moves.
3. **Field** — shared across all attackers.

Console-only; the full sweep also goes to `outputs/outputs.txt`.

For minimum SP to survive combined damage:

```bash
python3 calc/multi/survive.py
```

Same config, ignoring `BUDGET`.
