function pad(value) {
  return value < 10 ? `0${value}` : `${value}`;
}

function formatTime(timestamp) {
  const date = new Date(timestamp);
  const y = date.getFullYear();
  const m = pad(date.getMonth() + 1);
  const d = pad(date.getDate());
  const h = pad(date.getHours());
  const mm = pad(date.getMinutes());
  return `${y}-${m}-${d} ${h}:${mm}`;
}

function formatSigned(num) {
  if (num > 0) {
    return `+${num}`;
  }
  return `${num}`;
}

function todayName() {
  const date = new Date();
  const y = date.getFullYear();
  const m = pad(date.getMonth() + 1);
  const d = pad(date.getDate());
  return `${y}-${m}-${d} 麻将局`;
}

module.exports = {
  formatTime,
  formatSigned,
  todayName
};
