const { listGames, getActiveGame, removeGame } = require('../../services/gameService');
const { formatTime } = require('../../utils/format');

Page({
  data: {
    activeGame: null,
    search: '',
    games: []
  },

  onShow() {
    this.loadData();
  },

  loadData() {
    const activeGame = getActiveGame();
    const games = listGames(this.data.search).map((item) => ({
      ...item,
      timeText: formatTime(item.updatedAt),
      statusLabel: item.status === 'running' ? '进行中' : (item.status === 'paused' ? '已暂停' : '已结束')
    }));
    this.setData({ activeGame, games });
  },

  onSearch(e) {
    this.setData({ search: e.detail.value || '' }, () => {
      this.loadData();
    });
  },

  goCreate() {
    wx.navigateTo({ url: '/pages/create/index' });
  },

  continueGame() {
    const game = this.data.activeGame;
    if (!game) return;
    wx.navigateTo({ url: `/pages/game/index?id=${game.id}` });
  },

  openGame(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({ url: `/pages/game/index?id=${id}` });
  },

  openSettlement(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({ url: `/pages/settlement/index?id=${id}` });
  },

  removeGame(e) {
    const id = e.currentTarget.dataset.id;
    wx.showModal({
      title: '删除牌局',
      content: '确认删除该牌局及全部记录？',
      success: (res) => {
        if (!res.confirm) return;
        removeGame(id);
        this.loadData();
      }
    });
  }
});
