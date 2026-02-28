const { createGame, getPlayerPool } = require('../../services/gameService');
const { todayName } = require('../../utils/format');

function defaultPlayers() {
  return [
    { name: '玩家1', initialScore: 0 },
    { name: '玩家2', initialScore: 0 },
    { name: '玩家3', initialScore: 0 },
    { name: '玩家4', initialScore: 0 }
  ];
}

Page({
  data: {
    name: todayName(),
    unitOptions: ['分', '点', '元'],
    unitIndex: 0,
    balanceRequired: true,
    players: defaultPlayers(),
    pool: []
  },

  onShow() {
    this.setData({ pool: getPlayerPool() });
  },

  addPlayer() {
    if (this.data.players.length >= 8) {
      wx.showToast({ title: '最多8人', icon: 'none' });
      return;
    }
    const players = this.data.players.concat({ name: '', initialScore: 0 });
    this.setData({ players });
  },

  removePlayer(e) {
    const idx = Number(e.currentTarget.dataset.idx);
    if (this.data.players.length <= 2) {
      wx.showToast({ title: '至少2人', icon: 'none' });
      return;
    }
    const players = this.data.players.slice();
    players.splice(idx, 1);
    this.setData({ players });
  },

  onNameInput(e) {
    this.setData({ name: e.detail.value || '' });
  },

  onPlayerName(e) {
    const idx = Number(e.currentTarget.dataset.idx);
    this.setData({ [`players[${idx}].name`]: e.detail.value || '' });
  },

  onPlayerInit(e) {
    const idx = Number(e.currentTarget.dataset.idx);
    const value = Number(e.detail.value || 0);
    this.setData({ [`players[${idx}].initialScore`]: Number.isNaN(value) ? 0 : value });
  },

  onUnitChange(e) {
    this.setData({ unitIndex: Number(e.detail.value) });
  },

  onBalanceChange(e) {
    this.setData({ balanceRequired: !!e.detail.value });
  },

  fillName(e) {
    const name = e.currentTarget.dataset.name;
    const idx = this.data.players.findIndex((item) => !String(item.name || '').trim());
    if (idx < 0) {
      wx.showToast({ title: '请先新增空玩家位', icon: 'none' });
      return;
    }
    this.setData({ [`players[${idx}].name`]: name });
  },

  onSubmit() {
    const players = this.data.players.map((item) => ({
      name: String(item.name || '').trim(),
      initialScore: Number(item.initialScore || 0)
    }));

    if (players.some((item) => !item.name)) {
      wx.showToast({ title: '玩家名不能为空', icon: 'none' });
      return;
    }

    const game = createGame({
      name: String(this.data.name || '').trim() || todayName(),
      players,
      unit: this.data.unitOptions[this.data.unitIndex],
      balanceRequired: this.data.balanceRequired
    });

    wx.redirectTo({ url: `/pages/game/index?id=${game.id}` });
  }
});
