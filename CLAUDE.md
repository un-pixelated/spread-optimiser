# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

A Pokémon Champions defensive stat-point (SP) optimiser. Given an attacker/move and a defender, it brute-forces every valid HP/DEF (or HP/SPD) SP split within a budget and reports the split that minimises the % of the defender's HP the attack deals. Damage calculation is delegated to the `@smogon/calc` npm package (gen 9) via a small persistent Node bridge process; the optimisation loop, CLI, and plotting are all Python.

See README.md for the full config field reference and example usage.

## Layout

```
bridge.js, package.json, node_modules/   shared Node damage-calc bridge (repo root)
outputs/                                 shared, gitignored — plot.png, outputs.txt
calc/
  core/     shared.py                          mode-agnostic engine (bridge, calc_damage/calc_hp, validation sets)
  single/   calc.py, survive.py, config[.example].py, plot.py    single-attack optimiser (active)
  multi/    calc.py, config[.example].py                          2-4 attacker optimiser (active)
```

`calc/single/config.py` and `calc/multi/config.py` are both gitignored — they hold personal test values (attacker/defender picks, budget) that change on every run, not something to commit. Their `config.example.py` siblings are the tracked templates (schema + field comments; a fresh checkout needs `cp calc/single/config.example.py calc/single/config.py` and the same for `multi/` once, before either `calc.py` will import successfully). When you touch config fields (add/rename/document one), update both files in that folder — `config.example.py` is what ships, `config.py` is the user's own. The two `config.py` modules never clash despite sharing a filename: each is invoked as its own process with its own `sys.path[0]` (the script's own directory), so `import config` inside `single/calc.py` resolves to `single/config.py`, and inside `multi/calc.py` resolves to `multi/config.py`.

`bridge.js` and `node_modules` stay at the repo root since they're shared infrastructure — both `single/` and `multi/` spawn the same bridge rather than each vendoring their own. Path resolution (bridge, `outputs/`) happens once in `calc/core/shared.py` via `pathlib.Path(__file__)`, not the process's cwd. Since `core/` is a **sibling** of `single/` and `multi/` (not their subdirectory), both `single/calc.py` and `multi/calc.py` open with a `sys.path.insert(0, str(Path(__file__).resolve().parent.parent))` before importing `core.shared` — Python only auto-adds the *invoked script's own directory* to `sys.path`, so without this line `core` wouldn't be reachable from either folder. This is why both work whether invoked as `python3 calc/single/calc.py` from the repo root or `python3 calc.py` from inside `calc/single/` (same for `multi/`).

## Commands

```bash
npm install                                            # installs @smogon/calc (used by bridge.js)
pip install matplotlib matplotx                        # matplotlib + matplotx for calc/single/plot.py
black calc/single/*.py calc/multi/*.py calc/core/*.py  # formats all Python files (project convention, run before committing)

python3 calc/single/calc.py     # single-move optimiser, reads calc/single/config.py -> writes outputs/plot.png, outputs/outputs.txt
python3 calc/single/survive.py  # minimum-SP-to-survive finder, reads calc/single/config.py, console-only
python3 calc/multi/calc.py      # 2-4 attacker optimiser, reads calc/multi/config.py, console-only (no plot)
```

There is no test suite or build step in this repo.

## Architecture

**`bridge.js`** — a persistent Node process, not a one-shot script. It reads newline-delimited JSON requests from stdin (`{attacker, defender, move, field}`) and writes one JSON response per line to stdout, using `@smogon/calc`'s `Generations.get(9)`. Level is hardcoded to 50. Each entry-point script spawns its own instance once (`subprocess.Popen`) and keeps it alive for the whole run rather than re-spawning per calculation — this is what makes the brute-force sweeps fast.

**SP → EV conversion** happens inside `bridge.js`: each incoming `sp` value is multiplied by 8 to become an EV before constructing the `@smogon/calc` `Pokemon`. SP is capped at 32 per stat (matches in-game limits) — that cap is enforced in the Python optimisation loops, not in the bridge.

**`calc/core/shared.py`** — importable module shared by everything in `single/` and `multi/`. Holds only genuinely mode-agnostic pieces: the persistent Node bridge spawn + `ROOT_DIR`/`BRIDGE`, `calc_damage`/`calc_hp`/`clamp_boost`, and `VALID_NATURES`/`VALID_STATUSES` (validated against a hardcoded set each — a bad value used to crash deep inside the Node bridge with an opaque stack trace before this validation existed). Deliberately does **not** hold config parsing or nature-auto-pick logic — `single/` and `multi/` each have their own, with meaningfully different logic (see below), so those live in each folder's own `calc.py` rather than here.

**`calc/single/calc.py`** — single-attack optimiser. Defines `tune()`/`optimise()` (its search engine), plus `parse_config()` and `resolve_defender_natures()` (moved in from `core/shared.py` when `multi/` was added, since they're single-mode-specific), plus the `if __name__ == "__main__":` driver — guarded so `survive.py` can `from calc import parse_config, resolve_defender_natures` without triggering calc.py's own CLI run. Sweeps every `(delta_hp, delta_def)` pair that fits the SP budget (capped at 32/stat), calls the bridge once per point, and tracks the split with the lowest `damage / HP` ratio. `HP = base_hp + SP + 75` (`calc_hp`), a Pokémon Champions-specific formula distinct from mainline games. Has an optional "tuner" mode (`tune()`, enabled via `config.TUNER`): among all splits within a tolerance (percentage points) of optimal, pick the one that maximises a prioritised stat's SP instead of blindly taking the lowest-damage point.

If `config.DEFENDER_NATURE` is `None`, `calc.py` runs the sweep twice — once with a nature auto-picked to boost `DEFENSIVE_STAT` (`BEST_DEFENSIVE_NATURE`: Bold for def, Calm for spd), once with the neutral `Serious` nature — and prints both, labeled, for comparison. Only the auto-selected (primary) run writes `outputs/outputs.txt` and `outputs/plot.png`; the comparison run is console-only (`optimise()`'s `PRIMARY` flag controls this).

Terminal output is intentionally plain — no `═`/`─` box-drawing separators, just labeled lines (`OPTIMAL`, `TUNED`, blank-line spacing). Keep it that way; don't reintroduce ASCII dividers. This applies to `multi/calc.py` too.

To change a run, edit `calc/single/config.py` and re-run `calc/single/calc.py` — don't add CLI args or prompts back in.

**`calc/single/survive.py`** — minimum-SP-to-survive finder, sharing `core.shared` for the bridge/`calc_damage`/`calc_hp`, and importing `parse_config`/`resolve_defender_natures` from its sibling `calc.py`. Ignores `config.BUDGET`/`config.TUNER` entirely — instead of a fixed-budget sweep, `find_min_sp()` walks increasing total-SP diagonals (same diagonal shape `optimise()` uses: `delta_def` in `range(0, total+1)`, `delta_hp = total - delta_def`), checking `DMG < HP` (strict — a roll equal to HP is a KO) at each point, and stops at the first diagonal with a survivor (tie-broken toward maximizing `HP_SP`, since HP helps against any threat while the defensive stat only helps this one matchup). Reports "not survivable" if nothing up to 32/32 survives. Console-only by design — no `outputs/` writes, no plot.

**`calc/single/plot.py`** — matplotlib rendering for `calc.py`'s single-attack sweep, color-keyed by the attacking move's Pokémon type (`TYPE_COLORS`/`TYPE_BG_COLORS`). Saves to whatever `output_path` the caller passes (`calc.py` passes `outputs/plot.png`). Not used by `survive.py` or anything in `multi/` — multi-attacker results don't reduce to a single 2D chart.

**Status conditions** (`ATTACKER_STATUS`/`DEFENDER_STATUS` in either `config.py`, `None` or one of `"slp"`/`"psn"`/`"brn"`/`"frz"`/`"par"`/`"tox"`) pass straight through `bridge.js` into `@smogon/calc`'s `Pokemon` constructor — no extra wiring needed on the JS side (`pokemon.ts`'s `this.status = options.status || ''` already collapses Python `None`/JSON `null` to "no status"). This is what `@smogon/calc`'s gen9 mechanics actually key off of for burn halving physical damage, Guts/Toxic Boost/Flare Boost, Marvel Scale, Facade, Hex, Barb Barrage, and Venoshock — verified by reading `node_modules/@smogon/calc/src/mechanics/gen789.ts` directly, not assumed.

**`calc/multi/calc.py`** — 2-4 attacker optimiser, fully self-contained (own `parse_config_multi()`, own nature resolution — does not import anything from `single/`). Minimises the *summed* damage from every configured attacker against one shared defender. `config.ATTACKERS` is a list of 2-4 attacker+move dicts (`assert 2 <= len(config.ATTACKERS) <= 4` in `parse_config_multi()`); field conditions are shared once at the top of the config, not per-attacker, since weather/terrain/screens are global battle state.

The search space is always at most 3D (`HP`, `DEF`, `SPD`) regardless of attacker count — `optimise_multi()` computes `stats_used = sorted({a["defensive_stat"] for a in attackers})` and branches on its length: 1 distinct stat → 2D search (same shape as `single/calc.py`'s `optimise()`); 2 distinct stats → 3D search (nested loop, budget split three ways, generalizing `archived/multicalc.py`'s old different-stat branch to N attackers via a loop instead of two hardcoded `calc_damage` calls — even at the *minimum* of 2 attackers, one hitting `def` and the other `spd` is the normal case, not an edge case, so this path gets exercised often). `optimise_multi()` returns full result data rather than printing — `report_multi()` handles output separately, which is what lets nature auto-pick (below) run the search 3× without 3× the printing.

`DEFENDER_NATURE = None` auto-pick tries exactly `NATURE_CANDIDATES = ["Bold", "Calm", "Serious"]` and picks whichever produces the lowest combined damage — **not** a lookup table like `single/`'s `BEST_DEFENSIVE_NATURE`, because with attackers hitting both `def` and `spd` there's no single nature that's provably best without actually computing it. Lax/Gentle are deliberately excluded from the candidate set: since the defender never attacks in this calculator, a nature's "cost" side only matters when it falls on the *other* defensive stat (Lax costs SpD, Gentle costs Def) — it's invisible when it falls on Atk/SpA/Speed (Bold/Calm's cost). That means Lax can only ever tie Bold (when SpD isn't being attacked) or lose to it (when it is) — never win — and symmetrically for Gentle vs. Calm. Ties among the three candidates break toward `NATURE_CANDIDATES`'s order (Bold, then Calm, then Serious).

No plot — deletes any stale `outputs/plot.png` from a prior `single/calc.py` run (`PLOT_FILE.unlink(missing_ok=True)`, first thing `__main__` does) rather than leaving it around looking current. Full sweep still goes to `outputs/outputs.txt`, same convention as `single/calc.py`.

`archived/multicalc.py` no longer exists — it's been fully superseded by `calc/multi/calc.py` (generalized to 2-4 attackers, properly maintained). Git history has it if needed.

---

Behavioral guidelines below apply to all work in this repo, not just this project's code.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:

- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:

- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:

```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
