const { getGameById, addRecord } = require('../../services/gameService');

Page({
  data: {
    id: '',
    game: null,
    deltas: {},
    note: '',
    tagOptions: [
      { name: '自摸', selected: false },
      { name: '点炮', selected: false },
      { name: '杠', selected: false },
      { name: '罚款', selected: false }
    ],
    step: 1,
    sum: 0,
    canSave: false,
    saving: false
  },

  onLoad(options) {
    this.setData({ id: options.id || '' });
    this.loadGame();
  },

  loadGame() {
    const game = getGameById(this.data.id);
    if (!game) {
      wx.showToast({ title: '牌局不存在', icon: 'none' });
      return;
    }
    const deltas = {};
    game.players.forEach((p) => {
      deltas[p.id] = 0;
    });
    this.setData({
      game,
      step: game.settings.stepValues[0] || 1,
      deltas
    }, () => this.recalc());
  },

  selectStep(e) {
    this.setData({ step: Number(e.currentTarget.dataset.value) || 1 });
  },

  adjust(e) {
    const id = e.currentTarget.dataset.id;
    const sign = Number(e.currentTarget.dataset.sign);
    const next = Number(this.data.deltas[id] || 0) + sign * Number(this.data.step || 1);
    this.setData({ [`deltas.${id}`]: next }, () => this.recalc());
  },

  onDeltaInput(e) {
    const id = e.currentTarget.dataset.id;
    const raw = String(e.detail.value || '').trim();
    const value = raw === '' || raw === '-' ? 0 : Number(raw);
    this.setData({ [`deltas.${id}`]: Number.isNaN(value) ? 0 : value }, () => this.recalc());
  },

  onNoteInput(e) {
    this.setData({ note: e.detail.value || '' });
  },

  toggleTag(e) {
    const idx = Number(e.currentTarget.dataset.idx);
    const tagOptions = this.data.tagOptions.slice();
    tagOptions[idx].selected = !tagOptions[idx].selected;
    this.setData({ tagOptions });
  },

  recalc() {
    const values = Object.values(this.data.deltas).map((n) => Number(n || 0));
    const sum = values.reduce((acc, n) => acc + n, 0);
    const hasDelta = values.some((n) => n !== 0);
    const game = this.data.game;
    const canSave = hasDelta && (!game.settings.balanceRequired || sum === 0);
    this.setData({ sum, canSave });
  },

  onSave() {
    if (!this.data.canSave || this.data.saving) return;
    this.setData({ saving: true });
    const deltas = this.data.game.players.map((p) => ({
      playerId: p.id,
      delta: Number(this.data.deltas[p.id] || 0)
    }));
    const tags = this.data.tagOptions.filter((item) => item.selected).map((item) => item.name);

    try {
      addRecord(this.data.id, {
        deltas,
        note: this.data.note,
        tags
      });
      wx.showToast({ title: '保存成功' });
      setTimeout(() => wx.navigateBack(), 250);
    } catch (err) {
      wx.showToast({ title: err.message || '保存失败', icon: 'none' });
    } finally {
      this.setData({ saving: false });
    }
  }
});
