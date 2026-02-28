const STORAGE_KEYS = {
  GAMES: 'mahjong_games',
  PLAYER_POOL: 'mahjong_player_pool'
};

function read(key, fallback) {
  const value = wx.getStorageSync(key);
  if (value === '' || value === undefined || value === null) {
    return fallback;
  }
  return value;
}

function write(key, value) {
  wx.setStorageSync(key, value);
}

module.exports = {
  STORAGE_KEYS,
  read,
  write
};
