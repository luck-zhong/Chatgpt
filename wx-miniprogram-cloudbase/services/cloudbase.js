const app = getApp();

function getDb() {
  return wx.cloud.database({
    env: app.globalData.envId
  });
}

function getOpenId() {
  return wx.cloud.callFunction({ name: 'getOpenId' }).then((res) => {
    return res.result.openid;
  });
}

module.exports = {
  getDb,
  getOpenId
};
