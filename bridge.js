// bridge.js - persistent process, newline-delimited JSON on stdin/stdout
// one request per line in, one response per line out

const {
  calculate,
  Generations,
  Pokemon,
  Move,
  Field,
} = require("@smogon/calc");

const gen = Generations.get(9);
const readline = require("readline");

const rl = readline.createInterface({
  input: process.stdin,
  crlfDelay: Infinity,
});

rl.on("line", (line) => {
  line = line.trim();
  if (!line) return;

  const { attacker, defender, move, field } = JSON.parse(line);

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

  process.stdout.write(
    JSON.stringify({
      rolls: result.damage,
      min,
      max,
      defenderBaseHp: def.species.baseStats.hp,
      moveType: mv.type,
      desc: result.desc(),
      koChance: result.kochance().text,
    }) + "\n",
  );
});
