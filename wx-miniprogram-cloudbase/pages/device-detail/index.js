const { getDeviceById, updateDevice } = require('../../services/deviceService');

Page({
  data: {
    id: '',
    loading: false,
    saving: false,
    form: {
      name: '',
      status: 'offline',
      location: '',
      note: ''
    },
    statusOptions: ['online', 'offline', 'maintenance']
  },

  onLoad(options) {
    const id = options.id || '';
    this.setData({ id });
    if (id) {
      this.fetchDetail();
    }
  },

  fetchDetail() {
    this.setData({ loading: true });
    getDeviceById(this.data.id)
      .then((data) => {
        if (!data) {
          wx.showToast({ title: '设备不存在', icon: 'none' });
          return;
        }
        this.setData({
          form: {
            name: data.name || '',
            status: data.status || 'offline',
            location: data.location || '',
            note: data.note || ''
          }
        });
      })
      .catch((err) => {
        console.error('加载详情失败', err);
        wx.showToast({ title: '加载失败', icon: 'none' });
      })
      .finally(() => {
        this.setData({ loading: false });
      });
  },

  onInput(e) {
    const field = e.currentTarget.dataset.field;
    this.setData({
      [`form.${field}`]: e.detail.value
    });
  },

  onStatusChange(e) {
    const idx = Number(e.detail.value);
    const status = this.data.statusOptions[idx];
    this.setData({ 'form.status': status });
  },

  onSave() {
    const { id, form } = this.data;
    if (!form.name.trim()) {
      wx.showToast({ title: '请输入设备名称', icon: 'none' });
      return;
    }

    this.setData({ saving: true });
    updateDevice(id, {
      name: form.name.trim(),
      status: form.status,
      location: form.location.trim(),
      note: form.note.trim()
    })
      .then(() => {
        wx.showToast({ title: '保存成功', icon: 'success' });
        setTimeout(() => {
          wx.navigateBack();
        }, 500);
      })
      .catch((err) => {
        console.error('保存失败', err);
        wx.showToast({ title: '保存失败', icon: 'none' });
      })
      .finally(() => {
        this.setData({ saving: false });
      });
  }
});
