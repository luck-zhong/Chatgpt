const { getGameById, pauseGame, resumeGame, undoLastRecord, finishGame } = require('../../services/gameService');
const { formatSigned, formatTime } = require('../../utils/format');

Page({
  data: {
    id: '',
    game: null,
    ranking: []
  },

  onLoad(options) {
    this.setData({ id: options.id || '' });
  },

  onShow() {
    this.loadGame();
  },

  loadGame() {
    const game = getGameById(this.data.id);
    if (!game) {
      wx.showToast({ title: '牌局不存在', icon: 'none' });
      setTimeout(() => wx.navigateBack(), 300);
      return;
    }
    const ranking = game.players
      .slice()
      .sort((a, b) => b.currentScore - a.currentScore)
      .map((item) => ({
        ...item,
        scoreText: formatSigned(item.currentScore),
        deltaText: formatSigned(item.lastDelta || 0),
        deltaClass: item.lastDelta > 0 ? 'delta-plus' : (item.lastDelta < 0 ? 'delta-minus' : '')
      }));
    this.setData({
      game: {
        ...game,
        createdText: formatTime(game.createdAt)
      },
      ranking
    });
  },

  goRound() {
    if (!this.data.game || this.data.game.status === 'finished') return;
    wx.navigateTo({ url: `/pages/round/index?id=${this.data.id}` });
  },

  goRecords() {
    wx.navigateTo({ url: `/pages/records/index?id=${this.data.id}` });
  },

  goSettlement() {
    wx.navigateTo({ url: `/pages/settlement/index?id=${this.data.id}` });
  },

  togglePause() {
    const game = this.data.game;
    if (!game || game.status === 'finished') return;
    if (game.status === 'paused') {
      resumeGame(game.id);
    } else {
      pauseGame(game.id);
    }
    this.loadGame();
  },

  undoLast() {
    const game = this.data.game;
    if (!game || !game.records.length || game.status === 'finished') return;
    wx.showModal({
      title: '撤销上一把',
      content: '确认撤销最近一条记录？',
      success: (res) => {
        if (!res.confirm) return;
        undoLastRecord(game.id);
        this.loadGame();
        wx.showToast({ title: '已撤销', icon: 'none' });
      }
    });
  },

  finishGame() {
    const game = this.data.game;
    if (!game || game.status === 'finished') return;
    wx.showModal({
      title: '结束牌局',
      content: '结束后默认只读，确定结束？',
      success: (res) => {
        if (!res.confirm) return;
        finishGame(game.id);
        wx.redirectTo({ url: `/pages/settlement/index?id=${game.id}` });
      }
    });
  }
});
