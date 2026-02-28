const { getDb } = require('./cloudbase');

const collection = 'devices';

function listDevices() {
  const db = getDb();
  return db.collection(collection)
    .orderBy('updatedAt', 'desc')
    .get()
    .then((res) => res.data || []);
}

function getDeviceById(id) {
  const db = getDb();
  return db.collection(collection)
    .doc(id)
    .get()
    .then((res) => res.data || null);
}

function updateDevice(id, payload) {
  const db = getDb();
  return db.collection(collection)
    .doc(id)
    .update({
      data: {
        ...payload,
        updatedAt: db.serverDate()
      }
    });
}

module.exports = {
  listDevices,
  getDeviceById,
  updateDevice
};
