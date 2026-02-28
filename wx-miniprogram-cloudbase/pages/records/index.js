const { getGameById, deleteRecord } = require('../../services/gameService');
const { formatTime, formatSigned } = require('../../utils/format');

Page({
  data: {
    id: '',
    game: null,
    records: []
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

    const nameMap = {};
    game.players.forEach((p) => {
      nameMap[p.id] = p.name;
    });

    const records = game.records.slice().reverse().map((record, idx) => ({
      ...record,
      idx: game.records.length - idx,
      timeText: formatTime(record.createdAt),
      deltaText: record.deltas.map((d) => `${nameMap[d.playerId] || '未知'} ${formatSigned(d.delta)}`).join('，'),
      tagText: (record.tags || []).join('、')
    }));

    this.setData({ game, records });
  },

  onDelete(e) {
    const game = this.data.game;
    if (!game || game.status === 'finished') {
      wx.showToast({ title: '已结束牌局不可删除记录', icon: 'none' });
      return;
    }

    const id = e.currentTarget.dataset.id;
    wx.showModal({
      title: '删除记录',
      content: '确认删除该条记录并重算总分？',
      success: (res) => {
        if (!res.confirm) return;
        deleteRecord(game.id, id);
        this.loadData();
      }
    });
  }
});
