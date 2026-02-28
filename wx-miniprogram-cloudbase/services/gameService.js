const { STORAGE_KEYS, read, write } = require('../utils/storage');

function uid(prefix) {
  return `${prefix}_${Date.now()}_${Math.floor(Math.random() * 100000)}`;
}

function getGames() {
  return read(STORAGE_KEYS.GAMES, []);
}

function saveGames(games) {
  write(STORAGE_KEYS.GAMES, games);
}

function getPlayerPool() {
  return read(STORAGE_KEYS.PLAYER_POOL, []);
}

function savePlayerPool(names) {
  const unique = [];
  names.forEach((name) => {
    const clean = String(name || '').trim();
    if (clean && unique.indexOf(clean) === -1) {
      unique.push(clean);
    }
  });
  write(STORAGE_KEYS.PLAYER_POOL, unique.slice(0, 50));
}

function upsertPlayerPool(names) {
  const merged = getPlayerPool().concat(names);
  savePlayerPool(merged);
}

function calcScores(players, records) {
  const scoreMap = {};
  players.forEach((player) => {
    scoreMap[player.id] = Number(player.initialScore) || 0;
  });

  records.forEach((record) => {
    record.deltas.forEach((item) => {
      scoreMap[item.playerId] = (scoreMap[item.playerId] || 0) + Number(item.delta || 0);
    });
  });

  return players.map((player) => ({
    ...player,
    currentScore: scoreMap[player.id] || 0
  }));
}

function decorateGame(game) {
  const lastRecord = game.records[game.records.length - 1];
  const deltaMap = {};
  if (lastRecord) {
    lastRecord.deltas.forEach((item) => {
      deltaMap[item.playerId] = Number(item.delta || 0);
    });
  }

  const players = game.players.map((player) => ({
    ...player,
    lastDelta: deltaMap[player.id] || 0
  }));

  return {
    ...game,
    players
  };
}

function listGames(keyword) {
  const word = String(keyword || '').trim().toLowerCase();
  const games = getGames().slice().sort((a, b) => b.updatedAt - a.updatedAt);
  if (!word) {
    return games;
  }
  return games.filter((game) => game.name.toLowerCase().indexOf(word) >= 0);
}

function getGameById(gameId) {
  const game = getGames().find((item) => item.id === gameId);
  if (!game) {
    return null;
  }
  return decorateGame(game);
}

function getActiveGame() {
  const games = getGames().slice().sort((a, b) => b.updatedAt - a.updatedAt);
  const active = games.find((item) => item.status === 'running' || item.status === 'paused');
  return active ? decorateGame(active) : null;
}

function createGame(payload) {
  const now = Date.now();
  const players = payload.players.map((player) => ({
    id: uid('p'),
    name: String(player.name).trim(),
    initialScore: Number(player.initialScore) || 0,
    currentScore: Number(player.initialScore) || 0,
    active: true
  }));

  const game = {
    id: uid('g'),
    name: payload.name,
    createdAt: now,
    updatedAt: now,
    status: 'running',
    settings: {
      unit: payload.unit || '分',
      balanceRequired: payload.balanceRequired !== false,
      stepValues: payload.stepValues || [1, 2, 5, 10, 20, 50]
    },
    players,
    records: []
  };

  const games = getGames();
  games.push(game);
  saveGames(games);
  upsertPlayerPool(players.map((item) => item.name));
  return game;
}

function saveGame(nextGame) {
  const games = getGames();
  const idx = games.findIndex((item) => item.id === nextGame.id);
  if (idx < 0) {
    return null;
  }
  games[idx] = {
    ...nextGame,
    updatedAt: Date.now()
  };
  saveGames(games);
  return decorateGame(games[idx]);
}

function addRecord(gameId, payload) {
  const game = getGameById(gameId);
  if (!game || game.status === 'finished') {
    throw new Error('牌局不存在或已结束');
  }

  const deltas = payload.deltas
    .map((item) => ({
      playerId: item.playerId,
      delta: Number(item.delta || 0)
    }))
    .filter((item) => item.delta !== 0);

  if (!deltas.length) {
    throw new Error('至少要有一位玩家分数变动');
  }

  if (game.settings.balanceRequired) {
    const sum = deltas.reduce((acc, item) => acc + item.delta, 0);
    if (sum !== 0) {
      throw new Error('本把分数不平衡（总和需为0）');
    }
  }

  const record = {
    id: uid('r'),
    createdAt: Date.now(),
    deltas,
    note: String(payload.note || '').trim(),
    tags: (payload.tags || []).filter(Boolean),
    operator: 'local_user'
  };

  const nextGame = {
    ...game,
    records: game.records.concat(record)
  };
  nextGame.players = calcScores(nextGame.players, nextGame.records);
  return saveGame(nextGame);
}

function undoLastRecord(gameId) {
  const game = getGameById(gameId);
  if (!game || !game.records.length || game.status === 'finished') {
    return null;
  }

  const records = game.records.slice(0, -1);
  const nextGame = {
    ...game,
    records,
    players: calcScores(game.players, records)
  };
  return saveGame(nextGame);
}

function deleteRecord(gameId, recordId) {
  const game = getGameById(gameId);
  if (!game || game.status === 'finished') {
    return null;
  }

  const records = game.records.filter((item) => item.id !== recordId);
  const nextGame = {
    ...game,
    records,
    players: calcScores(game.players, records)
  };
  return saveGame(nextGame);
}

function setGameStatus(gameId, status) {
  const game = getGameById(gameId);
  if (!game) {
    return null;
  }
  const nextGame = {
    ...game,
    status
  };
  return saveGame(nextGame);
}

function finishGame(gameId) {
  return setGameStatus(gameId, 'finished');
}

function pauseGame(gameId) {
  return setGameStatus(gameId, 'paused');
}

function resumeGame(gameId) {
  return setGameStatus(gameId, 'running');
}

function removeGame(gameId) {
  const games = getGames().filter((item) => item.id !== gameId);
  saveGames(games);
}

function buildSettlement(game) {
  const ranked = game.players.slice().sort((a, b) => b.currentScore - a.currentScore);
  const winners = ranked
    .filter((item) => item.currentScore > 0)
    .map((item) => ({ id: item.id, name: item.name, value: item.currentScore }));
  const losers = ranked
    .filter((item) => item.currentScore < 0)
    .map((item) => ({ id: item.id, name: item.name, value: Math.abs(item.currentScore) }));

  const transfers = [];
  let i = 0;
  let j = 0;
  while (i < losers.length && j < winners.length) {
    const amount = Math.min(losers[i].value, winners[j].value);
    transfers.push({ from: losers[i].name, to: winners[j].name, amount });
    losers[i].value -= amount;
    winners[j].value -= amount;
    if (losers[i].value === 0) i += 1;
    if (winners[j].value === 0) j += 1;
  }

  return {
    ranked,
    transfers
  };
}

module.exports = {
  listGames,
  getGameById,
  getActiveGame,
  createGame,
  addRecord,
  undoLastRecord,
  deleteRecord,
  finishGame,
  pauseGame,
  resumeGame,
  removeGame,
  getPlayerPool,
  buildSettlement
};
