const { getGameById, buildSettlement, resumeGame } = require('../../services/gameService');
const { formatSigned, formatTime } = require('../../utils/format');

Page({
  data: {
    id: '',
    game: null,
    ranked: [],
    transfers: []
  },

  onLoad(options) {
    this.setData({ id: options.id || '' });
  },

  onShow() {
    this.loadData();
  },

  loadData() {
    const game = getGameById(this.data.id);
    if (!game) {
      wx.showToast({ title: '牌局不存在', icon: 'none' });
      return;
    }

    const settlement = buildSettlement(game);
    const ranked = settlement.ranked.map((p) => ({
      ...p,
      scoreText: formatSigned(p.currentScore),
      className: p.currentScore > 0 ? 'delta-plus' : (p.currentScore < 0 ? 'delta-minus' : '')
    }));

    this.setData({
      game: {
        ...game,
        createdText: formatTime(game.createdAt)
      },
      ranked,
      transfers: settlement.transfers
    });
  },

  reopen() {
    if (!this.data.game || this.data.game.status !== 'finished') {
      wx.navigateTo({ url: `/pages/game/index?id=${this.data.id}` });
      return;
    }

    resumeGame(this.data.id);
    wx.redirectTo({ url: `/pages/game/index?id=${this.data.id}` });
  }
});
