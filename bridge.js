// bridge.js - called by Python via subprocess
// stdin: JSON with attacker, defender, move, field
// stdout: JSON with rolls, min, max, desc

const {
  calculate,
  Generations,
  Pokemon,
  Move,
  Field,
} = require("@smogon/calc");

const gen = Generations.get(9);

process.stdin.setEncoding("utf8");
let raw = "";
process.stdin.on("data", (chunk) => (raw += chunk));
process.stdin.on("end", () => {
  const { attacker, defender, move, field } = JSON.parse(raw);

  const atk = new Pokemon(gen, attacker.name, {
    level: 50,
    nature: attacker.nature ?? "Hardy",
    item: attacker.item,
    ability: attacker.ability,
    evs: Object.fromEntries(
      Object.entries(attacker.sp ?? {}).map(([k, v]) => [k, v * 8]),
    ),
    boosts: attacker.boosts ?? {},
  });

  const def = new Pokemon(gen, defender.name, {
    level: 50,
    nature: defender.nature ?? "Hardy",
    item: defender.item,
    ability: defender.ability,
    evs: Object.fromEntries(
      Object.entries(defender.sp ?? {}).map(([k, v]) => [k, v * 8]),
    ),
    boosts: defender.boosts ?? {},
  });

  const mv = new Move(gen, move.name, {
    isCrit: move.isCrit ?? false,
  });

  const fd = new Field({
    gameType: field?.gameType ?? "Singles",
    weather: field?.weather,
    terrain: field?.terrain,
    defenderSide: {
      isReflect: field?.isReflect ?? false,
      isLightScreen: field?.isLightScreen ?? false,
      isAuroraVeil: field?.isAuroraVeil ?? false,
      isFriendGuard: field?.isFriendGuard ?? false,
    },
    attackerSide: {
      isHelpingHand: field?.isHelpingHand ?? false,
    },
  });

  const result = calculate(gen, atk, def, mv, fd);
  const [min, max] = result.range();

  console.log(
    JSON.stringify({
      rolls: result.damage,
      min,
      max,
      defenderBaseHp: def.species.baseStats.hp,
      desc: result.desc(),
      koChance: result.kochance().text,
    }),
  );
});
