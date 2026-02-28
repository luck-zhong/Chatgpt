const { listDevices } = require('../../services/deviceService');
const { formatStatus } = require('../../utils/format');

Page({
  data: {
    loading: false,
    devices: []
  },

  onShow() {
    this.fetchDevices();
  },

  onPullDownRefresh() {
    this.fetchDevices().finally(() => {
      wx.stopPullDownRefresh();
    });
  },

  fetchDevices() {
    this.setData({ loading: true });
    return listDevices()
      .then((list) => {
        const devices = list.map((item) => ({
          ...item,
          statusLabel: formatStatus(item.status)
        }));
        this.setData({ devices });
      })
      .catch((err) => {
        console.error('拉取设备列表失败', err);
        wx.showToast({ title: '加载失败', icon: 'none' });
      })
      .finally(() => {
        this.setData({ loading: false });
      });
  },

  goDetail(e) {
    const { id } = e.detail;
    wx.navigateTo({
      url: `/pages/device-detail/index?id=${id}`
    });
  }
});
